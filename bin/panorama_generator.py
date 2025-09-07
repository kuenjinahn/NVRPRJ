# -*- coding:utf-8 -*-
# 파노라마 이미지 생성 프로그램
# PTZ 프리셋 투어를 통해 3개 위치에서 스냅샷을 촬영하고 수평으로 머지하여 파노라마 이미지 생성
# 글로벌 변수로 설정된 간격마다 실행 (기본값: 1시간)

import logging
import time
import json
import os
import sys
import platform
from logging.handlers import RotatingFileHandler
import signal
import pymysql
from configparser import ConfigParser
from datetime import datetime, timedelta
import traceback
from pathlib import Path
import argparse
import socket
import atexit
import cv2
import base64
import numpy as np
import requests
from PIL import Image
import io
import subprocess
import tempfile

def load_config():
    """설정 파일 로드"""
    config = ConfigParser()
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.ini')
    
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    config.read(config_path, encoding='utf-8')
    return config

# 설정 로드
config = load_config()

# API 설정
API_BASE_URL = config.get('API', 'base_url', fallback='http://localhost:9001')

# 글로벌 상수 설정
PANORAMA_INTERVAL_SECONDS = 3600  # 1시간 = 3600초
PANORAMA_INTERVAL_MINUTES = PANORAMA_INTERVAL_SECONDS // 60  # 60분

# PTZ 프리셋 이동 여부 설정
ENABLE_PRESET_MOVEMENT = True  # True: 실제 이동, False: 이동 없이 대기만
PRESET_WAIT_SECONDS = 5  # 프리셋 이동 비활성화 시 대기 시간 (초)

### mariadb 연결정보 ####
DBSERVER_IP = config.get('DATABASE', 'host')
DBSERVER_PORT = config.getint('DATABASE', 'port')
DBSERVER_USER = config.get('DATABASE', 'user')
DBSERVER_PASSWORD = config.get('DATABASE', 'password')
DBSERVER_DB = config.get('DATABASE', 'database')
DBSERVER_CHARSET = config.get('DATABASE', 'charset')
nvrdb = None
########################

# 로깅 설정
log_dir = Path(config.get('LOGGING', 'log_dir'))
log_dir.mkdir(exist_ok=True)
log_file = log_dir / 'panorama_generator.log'

handler = RotatingFileHandler(
    log_file,
    maxBytes=config.getint('LOGGING', 'max_bytes'),
    backupCount=config.getint('LOGGING', 'backup_count'),
    encoding='utf-8'
)
handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
))

logger = logging.getLogger("PanoramaGenerator")
logger.setLevel(logging.INFO)
logger.addHandler(handler)

# 콘솔 출력을 위한 핸들러 추가
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
))
logger.addHandler(console_handler)

# =========================
# PNT protocol helpers (ptz_preset_tour.py에서 가져옴)
# =========================
RMID = 0xB8  # 184
TMID = 0xAC  # 172
PNT_ID = 0x01  # 장치 Address는 내부 고정(비노출)

PID_PRESET_SAVE = 24    # 0x18
PID_PRESET_RECALL = 25  # 0x19
PID_TOUR = 46           # 0x2E (1 = start, 0 = stop)
PID_SET_EACH_TOUR_DATA = 222  # 0xDE: [D0=preset(1~8), D1~D2= speed(rpm LSB/MSB), D3=delay(1~255s)]

def _chk_twos_complement(payload_bytes):
    total = sum(payload_bytes) & 0xFF
    return ((~total) + 1) & 0xFF

def _int_le16(n: int):
    n &= 0xFFFF
    return [n & 0xFF, (n >> 8) & 0xFF]

def build_pnt_packet(pid: int, data_bytes=None) -> bytes:
    data = list(data_bytes or [])
    base = [RMID, TMID, PNT_ID, pid, len(data)] + data
    chk = _chk_twos_complement(base)
    return bytes(base + [chk])

class PNTClient:
    """PNT 프로토콜 클라이언트"""
    def __init__(self):
        self.sock = None

    def connect(self, host: str, port: int):
        self.close()
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(5.0)
        s.connect((host, port))
        s.settimeout(1.0)
        self.sock = s

    def close(self):
        if self.sock:
            try:
                self.sock.close()
            except:
                pass
        self.sock = None

    def send(self, pid: int, data_bytes=None) -> bytes:
        if not self.sock:
            raise RuntimeError("소켓이 연결되지 않았습니다.")
        pkt = build_pnt_packet(pid, data_bytes)
        self.sock.sendall(pkt)
        return pkt

    def preset_recall(self, num: int): 
        return self.send(PID_PRESET_RECALL, [num & 0xFF])

class PanoramaGenerator:
    """파노라마 이미지 생성기"""
    
    def __init__(self, debug_mode=False):
        self.debug_mode = debug_mode
        self.config = config
        self.running = True
        self.thermal_camera_ip = None
        self.thermal_camera_port = None
        
        # PTZ 이동이 활성화된 경우에만 PTZ 클라이언트 생성
        if ENABLE_PRESET_MOVEMENT:
            self.ptz_client = PNTClient()
        else:
            self.ptz_client = None
        
        # 신호 핸들러 등록
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        atexit.register(self.cleanup)
        
        logger.info("PanoramaGenerator 초기화 완료")

    def signal_handler(self, signum, frame):
        """신호 핸들러"""
        logger.info(f"신호 {signum} 수신, 종료 중...")
        self.running = False

    def cleanup(self):
        """정리 작업"""
        try:
            if ENABLE_PRESET_MOVEMENT and self.ptz_client:
                self.ptz_client.close()
            if nvrdb:
                nvrdb.close()
            logger.info("정리 작업 완료")
        except Exception as e:
            logger.error(f"정리 작업 중 오류: {e}")

    def connect_database(self):
        """데이터베이스 연결"""
        global nvrdb
        try:
            nvrdb = pymysql.connect(
                host=DBSERVER_IP,
                port=DBSERVER_PORT,
                user=DBSERVER_USER,
                password=DBSERVER_PASSWORD,
                database=DBSERVER_DB,
                charset='utf8mb4',  # panoramaData 필드가 utf8mb4_bin이므로 utf8mb4 사용
                autocommit=True
            )
            logger.info("데이터베이스 연결 성공")
            return True
        except Exception as e:
            logger.error(f"데이터베이스 연결 실패: {e}")
            return False

    def get_thermal_camera_config(self):
        """tb_event_setting에서 열화상 카메라 설정 조회"""
        try:
            cursor = nvrdb.cursor()
            query = "SELECT object_json FROM tb_event_setting WHERE id = 1"
            cursor.execute(query)
            result = cursor.fetchone()
            cursor.close()
            
            if result and result[0]:
                object_json = json.loads(result[0])
                thermal_camera = object_json.get('thermalCamera', {})
                
                self.thermal_camera_ip = thermal_camera.get('ip')
                self.thermal_camera_port = thermal_camera.get('port')
                
                if self.thermal_camera_ip and self.thermal_camera_port:
                    logger.info(f"열화상 카메라 설정: {self.thermal_camera_ip}:{self.thermal_camera_port}")
                    return True
                else:
                    logger.error("열화상 카메라 IP/Port 설정이 없습니다")
                    return False
            else:
                logger.error("tb_event_setting에서 object_json을 찾을 수 없습니다")
                return False
                
        except Exception as e:
            logger.error(f"열화상 카메라 설정 조회 실패: {e}")
            return False

    def connect_ptz(self):
        """PTZ 카메라 연결"""
        try:
            self.ptz_client.connect(self.thermal_camera_ip, int(self.thermal_camera_port))
            logger.info(f"PTZ 카메라 연결 성공: {self.thermal_camera_ip}:{self.thermal_camera_port}")
            return True
        except Exception as e:
            logger.error(f"PTZ 카메라 연결 실패: {e}")
            return False

    def move_to_preset(self, preset_number):
        """지정된 프리셋으로 이동 (설정에 따라 실제 이동 또는 대기만)"""
        try:
            if ENABLE_PRESET_MOVEMENT and self.ptz_client:
                logger.info(f"프리셋 {preset_number}로 이동 중...")
                self.ptz_client.preset_recall(preset_number)
                time.sleep(3)  # 카메라 이동 대기
                logger.info(f"프리셋 {preset_number} 이동 완료")
            else:
                logger.info(f"프리셋 이동 비활성화됨 - 프리셋 {preset_number} 위치에서 {PRESET_WAIT_SECONDS}초 대기...")
                time.sleep(PRESET_WAIT_SECONDS)
                logger.info(f"프리셋 {preset_number} 위치 대기 완료")
            return True
        except Exception as e:
            if ENABLE_PRESET_MOVEMENT:
                logger.error(f"프리셋 {preset_number} 이동 실패: {e}")
            else:
                logger.error(f"프리셋 {preset_number} 대기 실패: {e}")
            return False

    def capture_snapshot(self, preset_number):
        """현재 위치에서 스냅샷 캡처 - RTSP 연결을 통해 실제 이미지 캡처"""
        try:
            logger.info(f"프리셋 {preset_number}에서 스냅샷 캡처 중...")
            
            # config.ini에서 RTSP URL 가져오기
            rtsp_url = self.config.get('CAMERA', 'rtsp', fallback='')
            if not rtsp_url:
                logger.error("config.ini에서 RTSP URL을 찾을 수 없습니다")
                return None
            
            # RTSP URL 유효성 검사
            if not rtsp_url.strip():
                logger.error("RTSP URL이 비어있습니다")
                return None
            
            rtsp_url = rtsp_url.strip()
            
            # RTSP 프로토콜 확인
            if not rtsp_url.startswith(('rtsp://', 'http://', 'https://')):
                logger.error(f"RTSP URL에 유효하지 않은 프로토콜: {rtsp_url}")
                return None
            
            logger.info(f"RTSP URL로 스냅샷 캡처: {rtsp_url}")
            
            try:
                # FFmpeg 명령어 구성 (videoAlertCheck.py 참조)
                ffmpeg_cmd = [
                    'ffmpeg',
                    '-hide_banner',
                    '-loglevel', 'error',
                    '-rtsp_transport', 'tcp',  # TCP 전송 사용
                    '-i', rtsp_url,  # 입력 소스
                    '-vframes', '1',  # 1프레임만 캡처
                    '-q:v', '2',  # 품질 설정
                    '-f', 'image2',  # 이미지 포맷
                    '-'  # stdout으로 출력
                ]
                
                # FFmpeg 프로세스 실행
                process = subprocess.Popen(
                    ffmpeg_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                
                # 출력 데이터 수집 (타임아웃 설정)
                stdout_data, stderr_data = process.communicate(timeout=30)
                
                # 디버깅을 위한 로그
                if stderr_data:
                    stderr_text = stderr_data.decode('utf-8', errors='ignore')
                    logger.debug(f"FFmpeg stderr for {rtsp_url}: {stderr_text}")
                
                if process.returncode == 0 and stdout_data:
                    # base64로 인코딩
                    image_base64 = base64.b64encode(stdout_data).decode('utf-8')
                    
                    # 추가 정보를 이미지에 오버레이 (선택사항)
                    try:
                        # OpenCV로 이미지 디코딩
                        img_array = np.frombuffer(stdout_data, dtype=np.uint8)
                        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
                        
                        if img is not None:
                            # 프리셋 정보와 타임스탬프 오버레이
                            cv2.putText(img, f"Preset {preset_number}", (10, 30), 
                                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                            cv2.putText(img, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), (10, 70), 
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                            
                            # 오버레이된 이미지를 다시 base64로 인코딩
                            _, buffer = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 90])
                            image_base64 = base64.b64encode(buffer).decode('utf-8')
                    except Exception as overlay_error:
                        logger.warning(f"이미지 오버레이 실패, 원본 이미지 사용: {overlay_error}")
                    
                    logger.info(f"프리셋 {preset_number} 스냅샷 캡처 완료")
                    return image_base64
                else:
                    error_msg = stderr_data.decode('utf-8') if stderr_data else "알 수 없는 오류"
                    logger.error(f"FFmpeg 실패 {rtsp_url}: {error_msg}")
                    return None
                    
            except subprocess.TimeoutExpired:
                logger.error(f"FFmpeg 타임아웃 {rtsp_url}")
                if process:
                    process.kill()
                    process.wait()
                return None
            except Exception as e:
                logger.error(f"FFmpeg 오류 {rtsp_url}: {str(e)}")
                return None
            
        except Exception as e:
            logger.error(f"프리셋 {preset_number} 스냅샷 캡처 실패: {e}")
            logger.error(traceback.format_exc())
            return None

    def merge_images_horizontally(self, images_base64):
        """3개 이미지를 수평으로 머지"""
        try:
            logger.info("이미지 머지 시작...")
            
            # base64 이미지들을 디코딩
            images = []
            for i, img_base64 in enumerate(images_base64):
                if img_base64:
                    img_data = base64.b64decode(img_base64)
                    img_array = np.frombuffer(img_data, dtype=np.uint8)
                    img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
                    images.append(img)
                else:
                    logger.warning(f"이미지 {i+1}이 None입니다")
            
            if len(images) < 3:
                logger.error("3개 이미지가 모두 필요합니다")
                return None
            
            # 이미지 크기 통일 (가장 작은 높이에 맞춤)
            min_height = min(img.shape[0] for img in images)
            resized_images = []
            
            for img in images:
                # 비율을 유지하면서 높이를 맞춤
                ratio = min_height / img.shape[0]
                new_width = int(img.shape[1] * ratio)
                resized_img = cv2.resize(img, (new_width, min_height))
                resized_images.append(resized_img)
            
            # 수평으로 머지
            panorama = np.hstack(resized_images)
            
            # 머지된 이미지를 base64로 인코딩
            _, buffer = cv2.imencode('.jpg', panorama, [cv2.IMWRITE_JPEG_QUALITY, 90])
            panorama_base64 = base64.b64encode(buffer).decode('utf-8')
            
            logger.info("이미지 머지 완료")
            return panorama_base64
            
        except Exception as e:
            logger.error(f"이미지 머지 실패: {e}")
            return None

    def save_panorama_to_db(self, panorama_base64):
        """파노라마 이미지를 데이터베이스에 저장"""
        try:
            cursor = nvrdb.cursor()
            
            # 파노라마 데이터 구성 (테이블 구조에 맞게 최적화)
            panorama_data = {
                "type": "panorama",
                "timestamp": datetime.now().isoformat(),
                "image": panorama_base64,
                "presets": [1, 2, 3],
                "description": "PTZ 프리셋 투어 파노라마",
                "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # panoramaData 필드에 JSON 데이터 저장
            query = "INSERT INTO tb_video_panorama_data (panoramaData) VALUES (%s)"
            cursor.execute(query, (json.dumps(panorama_data, ensure_ascii=False),))
            cursor.close()
            
            logger.info("파노라마 데이터 저장 완료")
            return True
            
        except Exception as e:
            logger.error(f"파노라마 데이터 저장 실패: {e}")
            return False

    def generate_panorama(self):
        """파노라마 생성 메인 로직"""
        try:
            logger.info("파노라마 생성 시작")
            
            # 1. 열화상 카메라 설정 조회 (PTZ 이동이 활성화된 경우에만)
            if ENABLE_PRESET_MOVEMENT:
                if not self.get_thermal_camera_config():
                    return False
                
                # 2. PTZ 카메라 연결
                if not self.connect_ptz():
                    return False
            else:
                logger.info("프리셋 이동이 비활성화되어 PTZ 설정 조회 및 연결을 건너뜁니다")
            
            # 3. 3개 프리셋에서 스냅샷 캡처
            snapshots = []
            for preset_num in [1, 2, 3]:
                if not self.move_to_preset(preset_num):
                    logger.error(f"프리셋 {preset_num} 이동 실패")
                    return False
                
                snapshot = self.capture_snapshot(preset_num)
                if snapshot:
                    snapshots.append(snapshot)
                else:
                    logger.error(f"프리셋 {preset_num} 스냅샷 캡처 실패")
                    return False
            
            # 4. 3개 이미지를 수평으로 머지
            panorama_base64 = self.merge_images_horizontally(snapshots)
            if not panorama_base64:
                logger.error("이미지 머지 실패")
                return False
            
            # 5. 데이터베이스에 저장
            if not self.save_panorama_to_db(panorama_base64):
                logger.error("데이터베이스 저장 실패")
                return False
            
            logger.info("파노라마 생성 완료")
            return True
            
        except Exception as e:
            logger.error(f"파노라마 생성 중 오류: {e}")
            logger.error(traceback.format_exc())
            return False
        finally:
            if ENABLE_PRESET_MOVEMENT and self.ptz_client:
                self.ptz_client.close()

    def run_scheduler(self):
        """스케줄러 실행 (설정된 간격마다)"""
        movement_status = "활성화" if ENABLE_PRESET_MOVEMENT else "비활성화"
        logger.info(f"파노라마 생성 스케줄러 시작 (간격: {PANORAMA_INTERVAL_MINUTES}분, 프리셋 이동: {movement_status})")
        
        while self.running:
            try:
                current_time = datetime.now()
                logger.info(f"현재 시간: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
                
                # 파노라마 생성 실행
                if self.generate_panorama():
                    logger.info("파노라마 생성 성공")
                else:
                    logger.error("파노라마 생성 실패")
                
                # 다음 실행까지 대기
                logger.info(f"다음 실행까지 {PANORAMA_INTERVAL_MINUTES}분 대기...")
                for i in range(PANORAMA_INTERVAL_SECONDS):  # 설정된 간격을 1초씩 나누어 대기
                    if not self.running:
                        break
                    time.sleep(1)
                
            except KeyboardInterrupt:
                logger.info("사용자에 의해 중단됨")
                break
            except Exception as e:
                logger.error(f"스케줄러 실행 중 오류: {e}")
                logger.error(traceback.format_exc())
                time.sleep(60)  # 오류 발생 시 1분 대기 후 재시도

def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description='파노라마 이미지 생성 프로그램')
    parser.add_argument('--debug', action='store_true', help='디버그 모드')
    parser.add_argument('--once', action='store_true', help='한 번만 실행')
    args = parser.parse_args()
    
    try:
        generator = PanoramaGenerator(debug_mode=args.debug)
        
        # 데이터베이스 연결
        if not generator.connect_database():
            logger.error("데이터베이스 연결 실패")
            return 1
        
        if args.once:
            # 한 번만 실행
            logger.info("한 번만 실행 모드")
            success = generator.generate_panorama()
            return 0 if success else 1
        else:
            # 스케줄러 실행
            generator.run_scheduler()
            return 0
            
    except Exception as e:
        logger.error(f"프로그램 실행 중 오류: {e}")
        logger.error(traceback.format_exc())
        return 1

if __name__ == "__main__":
    sys.exit(main())
