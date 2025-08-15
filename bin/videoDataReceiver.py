# -*- coding:utf-8 -*-
# 한글 주석 처리
__author__ = 'bychem'

import logging
import time
import json
import os
import sys
import platform
from logging.handlers import RotatingFileHandler
import signal
import json
import MySQLdb
from configparser import ConfigParser
from glob import glob
import requests
from datetime import datetime, timedelta
import traceback
from pathlib import Path
import argparse
import pymysql
import socket
import cv2
import base64
import numpy as np
import subprocess
import tempfile
import zipfile
import io

def load_config():
    config = ConfigParser()
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.ini')
    
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    config.read(config_path, encoding='utf-8')
    return config

# 설정 로드
# config.ini 파일에 다음 설정을 추가할 수 있습니다:
# [CAMERA]
# snapshot_interval = 10  # 스냅샷 처리 간격 (초 단위)
config = load_config()

# 카메라 설정
CAMERA_IP = config.get('CAMERA', 'ip')
CAMERA_PORT = config.getint('CAMERA', 'port')
RTSP_URL = config.get('CAMERA', 'rtsp')

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
log_file = log_dir / config.get('LOGGING', 'log_file')

handler = RotatingFileHandler(
    log_file,
    maxBytes=config.getint('LOGGING', 'max_bytes'),
    backupCount=config.getint('LOGGING', 'backup_count'),
    encoding='utf-8'
)
handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
))

logger = logging.getLogger("VideoDataReceiver")
logger.setLevel(logging.INFO)
logger.addHandler(handler)

# 콘솔 출력을 위한 핸들러 추가
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
))
logger.addHandler(console_handler)


class VideoDataReceiver:
    def __init__(self, debug_mode=False):
        self.debug_mode = debug_mode
        self.config = config
        self.data_reception_enabled = True  # 데이터 수신 상태 플래그
        self.last_check_time = 0  # 마지막 상태 확인 시간
        self.last_snapshot_time = 0  # 마지막 스냅샷 캡처 시간
        # 스냅샷 처리 간격을 클래스 변수로 설정 (초 단위)
        self.snapshot_interval = 10  # 10초마다 스냅샷 캡처
        # 설정 파일에서 간격을 읽어올 수 있도록 수정
        try:
            config_interval = self.config.getint('CAMERA', 'snapshot_interval', fallback=10)
            self.snapshot_interval = config_interval
            logger.info(f"스냅샷 처리 간격 설정: {self.snapshot_interval}초")
        except Exception as e:
            logger.warning(f"설정 파일에서 스냅샷 간격을 읽을 수 없어 기본값 사용: {self.snapshot_interval}초")

    def connect_to_db(self):
        global nvrdb
        try:
            if nvrdb is not None:
                try:
                    cursor = nvrdb.cursor()
                    cursor.execute('SELECT 1')
                    cursor.close()
                    return True
                except Exception as e:
                    logger.error(f"Connection check failed: {str(e)}")
                    nvrdb = None
            
            nvrdb = pymysql.connect(
                host=DBSERVER_IP,
                port=DBSERVER_PORT,
                user=DBSERVER_USER,
                password=DBSERVER_PASSWORD,
                db=DBSERVER_DB,
                charset=DBSERVER_CHARSET,
                autocommit=True,
                cursorclass=pymysql.cursors.DictCursor,
                connect_timeout=5
            )
            logger.info("Database connected successfully")
            return True
        except Exception as e:
            logger.error(f'Database connection failed: {str(e)}')
            logger.error(f'Connection params: host={DBSERVER_IP}, port={DBSERVER_PORT}, user={DBSERVER_USER}, db={DBSERVER_DB}')
            nvrdb = None
            return False

    def disconnect_db(self):
        global nvrdb
        try:
            if nvrdb:
                nvrdb.close()
                nvrdb = None
                logger.info("Database disconnected")
        except Exception as e:
            logger.error(f'Error disconnecting database: {str(e)}')

    def get_db_cursor(self):
        global nvrdb
        if not self.connect_to_db():
            return None
        try:
            return nvrdb.cursor(pymysql.cursors.DictCursor)
        except Exception as e:
            logger.error(f'Error getting cursor: {str(e)}')
            return None

    def capture_rtsp_snapshot(self):
        """
        RTSP 스트림에서 이미지를 캡처하여 base64로 인코딩
        """
        try:
            logger.info(f"RTSP 스냅샷 캡처 시작: {RTSP_URL}")
            
            # FFmpeg 명령어 구성 (메모리로 직접 출력)
            ffmpeg_cmd = [
                'ffmpeg',
                '-hide_banner',
                '-loglevel', 'error',
                '-rtsp_transport', 'tcp',  # TCP 전송 사용
                '-i', RTSP_URL,  # 입력 소스
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
            
            if process.returncode == 0 and stdout_data:
                # base64로 인코딩
                img_base64 = base64.b64encode(stdout_data).decode('utf-8')
                logger.info("RTSP 스냅샷 캡처 성공")
                return img_base64
            else:
                error_msg = stderr_data.decode('utf-8') if stderr_data else "Unknown error"
                logger.error(f"FFmpeg failed: {error_msg}")
                return None
                
        except subprocess.TimeoutExpired:
            logger.error("FFmpeg timeout")
            if process:
                process.kill()
                process.wait()
            return None
        except Exception as e:
            logger.error(f"RTSP 스냅샷 캡처 오류: {str(e)}")
            return None

    def analyze_colorbar(self, colorbar_image_path, temp_min, temp_max, num_steps=256):
        """
        컬러바 이미지 분석하여 색상-온도 매핑 생성
        """
        try:
            if not os.path.exists(colorbar_image_path):
                logger.warning(f"컬러바 이미지 파일이 존재하지 않습니다: {colorbar_image_path}")
                return None
                
            colorbar_img = cv2.imread(colorbar_image_path)
            if colorbar_img is None:
                logger.warning(f"컬러바 이미지를 로드할 수 없습니다: {colorbar_image_path}")
                return None
                
            h, w, _ = colorbar_img.shape
            center_column = colorbar_img[:, w // 2, :]
            color_to_temp_map = {}
            
            for i in range(num_steps):
                pixel_y = int(i * (h - 1) / (num_steps - 1))
                b, g, r = center_column[pixel_y]
                norm_pos = pixel_y / (h - 1)
                temperature = temp_min + norm_pos * (temp_max - temp_min)
                color_to_temp_map[tuple(map(int, (r, g, b)))] = temperature
                
            logger.info(f"컬러바 분석 완료: {len(color_to_temp_map)}개 색상-온도 매핑")
            return color_to_temp_map
            
        except Exception as e:
            logger.error(f"컬러바 분석 오류: {str(e)}")
            return None

    def create_color_lookup_table(self, color_map, temp_min, temp_max):
        """
        색상 매핑을 3차원 배열로 변환하여 빠른 검색 가능하게 함
        """
        logger.info("색상 룩업 테이블 생성 시작...")
        
        # RGB 각 채널별로 256x256x256 크기의 배열 생성 (float64 사용하여 JSON 호환성 확보)
        lookup_table = np.full((256, 256, 256), (temp_min + temp_max) / 2, dtype=np.float64)
        
        # 기존 매핑을 배열에 적용
        mapped_count = 0
        for (r, g, b), temp in color_map.items():
            lookup_table[r, g, b] = float(temp)  # float로 명시적 변환
            mapped_count += 1
        
        logger.info(f"색상 룩업 테이블 생성 완료: {mapped_count}개 색상 매핑")
        return lookup_table

    def get_temperature_fast(self, pixel_color_bgr, lookup_table):
        """
        룩업 테이블을 사용한 빠른 온도 검색
        """
        r, g, b = pixel_color_bgr[2], pixel_color_bgr[1], pixel_color_bgr[0]
        return float(lookup_table[r, g, b])  # float로 명시적 변환

    def get_temperature_from_color_with_map(self, pixel_color_bgr, color_map, temp_min, temp_max):
        """
        색상 매핑을 사용하여 픽셀의 온도 추정 (폴백 함수)
        """
        try:
            r_pixel, g_pixel, b_pixel = pixel_color_bgr[2], pixel_color_bgr[1], pixel_color_bgr[0]  # BGR을 RGB로

            if (r_pixel, g_pixel, b_pixel) in color_map:
                return color_map[(r_pixel, g_pixel, b_pixel)]
            
            min_dist = float('inf')
            closest_temp = (temp_min + temp_max) / 2  # 기본값

            for map_rgb, map_temp in color_map.items():
                r_map, g_map, b_map = map_rgb[0], map_rgb[1], map_rgb[2]

                diff_r = np.int64(r_map) - np.int64(r_pixel)
                diff_g = np.int64(g_map) - np.int64(g_pixel)
                diff_b = np.int64(b_map) - np.int64(b_pixel)

                dist = np.sqrt(diff_r**2 + diff_g**2 + diff_b**2)

                if dist < min_dist:
                    min_dist = dist
                    closest_temp = map_temp
                    
            return closest_temp
            
        except Exception as e:
            logger.error(f"온도 추정 오류: {str(e)}")
            return (temp_min + temp_max) / 2

    def extract_temperature_data_optimized(self, image_base64):
        """
        최적화된 온도 데이터 추출 (룩업 테이블 사용)
        """
        try:
            # base64 디코딩
            image_data = base64.b64decode(image_base64)
            
            # numpy 배열로 변환
            nparr = np.frombuffer(image_data, np.uint8)
            img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if img is None:
                logger.error("이미지 디코딩 실패")
                return None
            
            # 이미지를 640x480 해상도로 리사이즈
            target_width = 640
            target_height = 480
            img = cv2.resize(img, (target_width, target_height), interpolation=cv2.INTER_AREA)
            
            h, w, _ = img.shape
            logger.info(f"이미지 해상도: {w}x{h} (640x480)")
            
            # 컬러바 이미지 경로 (기본값 설정)
            colorbar_path = os.path.join(os.path.dirname(__file__), 'temp_extractor', 'temp_extractor', 'color_bar.png')
            
            # 온도 범위 설정 (기본값)
            temp_min = 30.0
            temp_max = 49.0
            
            # 컬러바 분석 및 룩업 테이블 생성 (한 번만)
            if not hasattr(self, 'color_lookup_table'):
                logger.info("첫 번째 실행: 컬러바 분석 및 룩업 테이블 생성")
                color_mapping = self.analyze_colorbar(colorbar_path, temp_min, temp_max)
                if color_mapping is None:
                    logger.warning("컬러바 분석 실패, 기본 온도값 사용")
                    # 기본 온도 데이터 생성
                    temperature_data = []
                    for r in range(h):
                        for c in range(w):
                            temperature_data.append({
                                'x': c,
                                'y': r,
                                'temperature': (temp_min + temp_max) / 2
                            })
                    return temperature_data
                
                # 룩업 테이블 생성
                self.color_lookup_table = self.create_color_lookup_table(color_mapping, temp_min, temp_max)
                logger.info("색상 룩업 테이블 생성 완료")
            
            # 룩업 테이블을 사용한 빠른 온도 계산
            temperature_data = []
            logger.info("룩업 테이블을 사용한 온도 계산 시작...")
            
            for r in range(h):
                for c in range(w):
                    pixel_color_bgr = img[r, c]
                    estimated_temp = self.get_temperature_fast(
                        pixel_color_bgr, self.color_lookup_table
                    )
                    temperature_data.append({
                        'x': c,
                        'y': r,
                        'temperature': round(estimated_temp, 2)
                    })
            
            logger.info(f"최적화된 온도 데이터 추출 완료: {len(temperature_data)}개 픽셀")
            return temperature_data
            
        except Exception as e:
            logger.error(f"최적화된 온도 데이터 추출 오류: {str(e)}")
            logger.error(traceback.format_exc())
            return None

    def compress_temperature_data(self, temperature_data):
        """
        온도 데이터를 ZIP 압축하여 base64로 인코딩
        """
        try:
            if not temperature_data:
                return None
                
            # JSON 문자열로 변환
            json_data = json.dumps(temperature_data, ensure_ascii=False)
            
            # ZIP 압축
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                zip_file.writestr('temperature_data.json', json_data)
            
            # base64 인코딩
            compressed_data = base64.b64encode(zip_buffer.getvalue()).decode('utf-8')
            logger.info("온도 데이터 압축 완료")
            return compressed_data
            
        except Exception as e:
            logger.error(f"온도 데이터 압축 오류: {str(e)}")
            return None

    def save_snapshot_data_to_db(self, snapshot_data, temperature_data):
        """
        스냅샷 이미지와 온도 데이터를 데이터베이스에 저장
        """
        try:
            cursor = self.get_db_cursor()
            if not cursor:
                logger.error("DB 커서 획득 실패")
                return False

            # 온도 데이터 압축
            compressed_temp_data = self.compress_temperature_data(temperature_data)
            if compressed_temp_data is None:
                logger.error("온도 데이터 압축 실패")
                return False

            # 데이터베이스에 저장
            sql = """
                INSERT INTO tb_video_snapshot_data (create_date, snapshotData, temperatureData)
                VALUES (NOW(), %s, %s)
            """
            cursor.execute(sql, (snapshot_data, compressed_temp_data))
            nvrdb.commit()
            
            logger.info("스냅샷 데이터 DB 저장 성공")
            return True
            
        except Exception as e:
            logger.error(f"스냅샷 데이터 DB 저장 실패: {str(e)}")
            logger.error(traceback.format_exc())
            return False

    def process_snapshot_and_temperature(self):
        """
        설정된 간격마다 스냅샷을 캡처하고 온도를 추출하여 DB에 저장
        """
        current_time = time.time()
        
        # 설정된 간격마다 실행
        if current_time - self.last_snapshot_time >= self.snapshot_interval:
            self.last_snapshot_time = current_time
            
            try:
                logger.info(f"스냅샷 처리 시작 (간격: {self.snapshot_interval}초)")
                
                # RTSP 스냅샷 캡처
                snapshot_data = self.capture_rtsp_snapshot()
                if snapshot_data is None:
                    logger.error("RTSP 스냅샷 캡처 실패")
                    return
                
                # 온도 데이터 추출
                temperature_data = self.extract_temperature_data_optimized(snapshot_data)
                if temperature_data is None:
                    logger.error("온도 데이터 추출 실패")
                    return
                
                # 데이터베이스에 저장
                if self.save_snapshot_data_to_db(snapshot_data, temperature_data):
                    logger.info("스냅샷 및 온도 데이터 처리 완료")
                else:
                    logger.error("스냅샷 및 온도 데이터 처리 실패")
                    
            except Exception as e:
                logger.error(f"스냅샷 및 온도 데이터 처리 중 오류: {str(e)}")
                logger.error(traceback.format_exc())
        else:
            # 다음 스냅샷까지 남은 시간 계산
            remaining_time = self.snapshot_interval - (current_time - self.last_snapshot_time)
            if remaining_time > 0:
                logger.debug(f"다음 스냅샷까지 {remaining_time:.1f}초 남음")

    def build_packet(self,cmd, data):
        print("[*] 패킷 구성 시작...")

        header = 0xFF
        address = 0x00
        cmd_h = (cmd >> 8) & 0xFF
        cmd_l = cmd & 0xFF
        data_h = (data >> 8) & 0xFF
        data_l = data & 0xFF

        print(f"    Header      : 0x{header:02X}")
        print(f"    Address     : 0x{address:02X}")
        print(f"    CMD_H       : 0x{cmd_h:02X}")
        print(f"    CMD_L       : 0x{cmd_l:02X}")
        print(f"    DATA_H      : 0x{data_h:02X}")
        print(f"    DATA_L      : 0x{data_l:02X}")

        # Checksum: Byte2~Byte6의 8bit 합
        payload = [address, cmd_h, cmd_l, data_h, data_l]
        checksum = sum(payload) & 0xFF
        print(f"    Checksum    : 0x{checksum:02X}")

        packet = bytes([header] + payload + [checksum])
        print(f"[*] 최종 패킷 (hex): {packet.hex()}")
        return packet
    
    def send_command_and_receive_limited(self, cmd, data, max_duration=30):
        """
        제한된 시간 동안만 데이터 수신을 실행 (스냅샷 처리가 중단되지 않도록)
        """
        start_time = time.time()
        packet = self.build_packet(cmd, data)
        
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(5)
                sock.connect((CAMERA_IP, CAMERA_PORT))
                logger.info("TCP 연결 성공 - 제한된 시간 동안 데이터 수신")

                sock.sendall(packet)
                logger.info("명령 전송 완료")

                # 제한된 시간 동안만 데이터 수신
                while (time.time() - start_time) < max_duration:
                    try:
                        # 데이터 수신 여부 확인
                        if not self.should_receive_data():
                            logger.info("데이터 수신 중지 상태 감지 - 연결 종료")
                            break
                        
                        recv_data = sock.recv(1024)
                        if recv_data:
                            logger.info(f"데이터 수신: {len(recv_data)} bytes")
                            
                            # 데이터 파싱 및 DB 저장
                            self.process_received_data(recv_data)
                            
                            # 1초 대기 후 다음 수신
                            time.sleep(1)
                        else:
                            logger.info("수신 데이터 없음 - 연결 종료")
                            break
                            
                    except socket.timeout:
                        logger.info("수신 타임아웃 - 계속 진행")
                        continue
                        
        except Exception as e:
            logger.error(f"제한된 데이터 수신 중 오류: {e}")
        finally:
            logger.info(f"제한된 데이터 수신 완료 (실행 시간: {time.time() - start_time:.1f}초)")

    def process_received_data(self, recv_data):
        """
        수신된 데이터를 파싱하고 DB에 저장
        """
        try:
            # 데이터 파싱
            data_raw_list = []
            for i in range(49):
                start = i * 2
                end = start + 2
                if end <= len(recv_data):
                    value = recv_data[start:end].hex()
                    # big-endian → little-endian 변환
                    if len(value) == 4:
                        value = value[2:4] + value[0:2]
                    data_raw_list.append(value)
                else:
                    data_raw_list.append('')

            # 해석값 변환
            def signed16(val):
                return val if val < 0x8000 else val - 0x10000

            data_value_list = []
            for idx, x in enumerate(data_raw_list):
                if x == '':
                    data_value_list.append(None)
                    continue
                intval = int(x, 16)
                # 온도 관련 데이터(예시: 19~41번)는 signed/10 적용, 나머지는 int값
                if 18 <= idx <= 41:
                    data_value_list.append(signed16(intval) / 10)
                else:
                    data_value_list.append(intval)

            # JSON 변환
            data_raw_json = {f"data_{i+1}": v for i, v in enumerate(data_raw_list)}
            data_value_json = {f"data_{i+1}": v for i, v in enumerate(data_value_list)}
            data_raw_str = json.dumps(data_raw_json, ensure_ascii=False)
            data_value_str = json.dumps(data_value_json, ensure_ascii=False)

            # DB Insert
            cursor = self.get_db_cursor()
            if cursor:
                sql = """
                    INSERT INTO tb_video_receive_data (fk_camera_id, create_date, data_raw, data_value)
                    VALUES (1, NOW(), %s, %s)
                """
                cursor.execute(sql, (data_raw_str, data_value_str))
                nvrdb.commit()
                logger.info("DB Insert 성공")
            else:
                logger.error("DB 커서 획득 실패")
                
        except Exception as e:
            logger.error(f"수신 데이터 처리 오류: {e}")
            logger.error(traceback.format_exc())

    def send_command_and_receive(self, cmd, data):
        packet = self.build_packet(cmd, data)

        while True:
            # 카메라 연결 전에 데이터 수신 여부 확인
            if not self.should_receive_data():
                print("[!] 데이터 수신 중지 상태 - 5초 대기 후 재확인")
                time.sleep(5)
                continue
            
            print(f"\n[*] 카메라에 연결 시도: {CAMERA_IP}:{CAMERA_PORT}")
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    sock.settimeout(5)
                    sock.connect((CAMERA_IP, CAMERA_PORT))
                    print("[+] TCP 연결 성공")

                    print("[*] 명령 전송 중...")
                    sock.sendall(packet)
                    print("[+] 명령 전송 완료")

                    while True:
                        try:
                            # 데이터 수신 여부 확인 (연결 중에도 상태 변경 감지)
                            if not self.should_receive_data():
                                print("[!] 데이터 수신 중지 상태 - 연결 종료")
                                break  # 연결 종료하고 재연결 시도
                            
                            recv_data = sock.recv(1024)
                            if recv_data:
                                print(f"[RECV {len(recv_data)} bytes] {recv_data.hex()}")

                                # 데이터 파싱 및 DB 저장
                                self.process_received_data(recv_data)

                                # 1초 대기 후 다음 수신
                                time.sleep(1)

                            else:
                                print("[-] 수신 데이터 없음 (소켓은 열려 있음)")
                                break  # 소켓 연결 종료
                        except socket.timeout:
                            print("[!] 수신 타임아웃 - 응답 없음")
                            break  # 소켓 연결 종료

            except Exception as e:
                print(f"[!] 소켓 오류 또는 연결 실패: {e}")
                logger.error(f"소켓 오류 또는 연결 실패: {e}")
            finally:
                print("[*] 소켓 종료 및 5초 후 재접속 시도")
                time.sleep(5)  # 재접속 대기

    def insert_video_receive_data(self, data_list):
        """
        data_list: 49개 항목의 리스트 (각 항목은 문자열)
        """
        if len(data_list) != 49:
            logger.error(f"data_list length is not 49: {len(data_list)}")
            return False

        try:
            cursor = self.get_db_cursor()
            if not cursor:
                logger.error("DB 커서 획득 실패")
                return False

            columns = ', '.join([f'data_{i+1}' for i in range(49)])
            placeholders = ', '.join(['%s'] * 49)
            sql = f"""
                INSERT INTO tb_video_receive_data (fk_camera_id, {columns})
                VALUES (1, {placeholders})
            """
            cursor.execute(sql, data_list)
            nvrdb.commit()
            logger.info("DB Insert 성공")
            return True
        except Exception as e:
            logger.error(f"DB Insert 실패: {e}")
            logger.error(traceback.format_exc())
            return False
        
    def check_in_page_zone_status(self):
        """
        tb_event_setting 테이블의 in_page_zone 값을 확인하여 데이터 수신 상태를 결정
        """
        try:
            cursor = self.get_db_cursor()
            if not cursor:
                logger.error("DB 커서 획득 실패 - in_page_zone 상태 확인 불가")
                return True  # DB 연결 실패 시 기본적으로 수신 허용
            
            sql = """
                SELECT in_page_zone 
                FROM tb_event_setting 
                ORDER BY id DESC 
                LIMIT 1
            """
            cursor.execute(sql)
            result = cursor.fetchone()
            
            if result and result['in_page_zone'] is not None:
                in_page_zone = result['in_page_zone']
                new_status = in_page_zone == 0  # 0이면 수신 허용, 1이면 수신 중지
                
                if new_status != self.data_reception_enabled:
                    if new_status:
                        logger.info("in_page_zone=0 감지 - 데이터 수신 재개")
                    else:
                        logger.info("in_page_zone=1 감지 - 데이터 수신 중지")
                    self.data_reception_enabled = new_status
                
                return self.data_reception_enabled
            else:
                # 레코드가 없거나 in_page_zone이 NULL인 경우 기본적으로 수신 허용
                if not self.data_reception_enabled:
                    logger.info("in_page_zone 레코드 없음 - 데이터 수신 재개")
                    self.data_reception_enabled = True
                return True
                
        except Exception as e:
            logger.error(f"in_page_zone 상태 확인 실패: {e}")
            return self.data_reception_enabled  # 오류 발생 시 현재 상태 유지

    def should_receive_data(self):
        """
        3초마다 in_page_zone 상태를 확인하고 데이터 수신 여부를 결정
        """
        current_time = time.time()
        
        # 3초마다 상태 확인
        if current_time - self.last_check_time >= 3:
            self.last_check_time = current_time
            return self.check_in_page_zone_status()
        
        return self.data_reception_enabled

    def run(self):
        logger.info("VideoDataReceiver 시작")
        
        # 초기 in_page_zone 상태 확인
        initial_status = self.check_in_page_zone_status()
        if initial_status:
            logger.info("초기 상태: 데이터 수신 허용")
        else:
            logger.info("초기 상태: 데이터 수신 중지")
        
        cmd_input = "2304"
        data_input = "0001"

        cmd = int(cmd_input, 16)
        data = int(data_input, 16)
        
        # 메인 루프: 스냅샷 처리와 데이터 수신을 지속적으로 실행
        while True:
            try:
                # 스냅샷 및 온도 데이터 처리 (지속적으로 실행)
                self.process_snapshot_and_temperature()
                
                # 데이터 수신 상태 확인
                if self.should_receive_data():
                    logger.info("데이터 수신 시작")
                    # 데이터 수신 로직 실행 (짧은 시간만 실행)
                    self.send_command_and_receive_limited(cmd, data, max_duration=10)  # 10초만 실행
                else:
                    # 데이터 수신 중지 상태일 때는 스냅샷만 계속 처리
                    logger.info("데이터 수신 중지 상태 - 스냅샷 처리만 계속")
                    # 스냅샷 처리를 위해 짧은 대기 (CPU 사용량 조절)
                    time.sleep(0.1)
                    
            except KeyboardInterrupt:
                logger.info("사용자에 의해 중단됨")
                break
            except Exception as e:
                logger.error(f"메인 루프 오류: {str(e)}")
                logger.error(traceback.format_exc())
                time.sleep(1)  # 오류 발생 시 1초 대기


if __name__ == "__main__":
    try:
        # 명령행 인자 파싱
        parser = argparse.ArgumentParser(description='Video Data Receiver')
        parser.add_argument('--debug', action='store_true', help='Enable debug mode with UI')
        args = parser.parse_args()
        
        dataReceiver = VideoDataReceiver(debug_mode=args.debug)
        dataReceiver.run()

    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
        logger.error(traceback.format_exc())
