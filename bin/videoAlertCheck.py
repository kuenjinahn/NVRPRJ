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
from scipy import stats
import argparse
import pymysql
import socket
import atexit
import cv2
import base64
import numpy as np
import subprocess
import tempfile
import zipfile
import io
import csv

def load_config():
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

logger = logging.getLogger("VideoAlertChecker")
logger.setLevel(logging.INFO)
logger.addHandler(handler)

# 콘솔 출력을 위한 핸들러 추가
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(levelname)s - %(message)s'
))
logger.addHandler(console_handler)


class VideoAlertChecker:
    def __init__(self, debug_mode=False):
        self.debug_mode = debug_mode
        self.config = config
        self.alert_settings = None
        self.zone_list = None
        self.camera_info_list = None
        self.last_settings_check = 0
        self.last_data_check = 0
        self.settings_check_interval = 30  # 30 seconds
        self.data_check_interval = 60  # 60 seconds
        self.running = True
        self.force_exit = False  # 강제 종료 플래그
        
        # 시그널 핸들러 등록
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        # 종료 시 정리 작업 등록
        atexit.register(self.cleanup)

    def signal_handler(self, signum, frame):
        """시그널 핸들러"""
        logger.info(f"Received signal {signum}, immediately shutting down...")
        self.running = False
        # 즉시 종료를 위한 강제 종료 플래그
        self.force_exit = True
        # 프로그램 즉시 종료
        os._exit(0)

    def cleanup(self):
        """프로그램 종료 시 정리 작업"""
        try:
            logger.info("Performing cleanup...")
            self.disconnect_db()
            logger.info("Cleanup completed successfully")
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")

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

    def get_alert_settings(self):
        try:
            logger.info("Alert settings 조회 시작...")
            cursor = self.get_db_cursor()
            if not cursor:
                return False

            query = """
                SELECT alert_setting_json 
                FROM tb_alert_setting 
                LIMIT 1
            """
            cursor.execute(query)
            result = cursor.fetchone()
            
            if result and result['alert_setting_json']:
                self.alert_settings = json.loads(result['alert_setting_json'])
                logger.info("Alert settings 조회 성공")
                return True
            else:
                logger.error("Alert settings를 찾을 수 없습니다")
                return False

        except Exception as e:
            logger.error(f"Alert settings 조회 오류: {str(e)}")
            return False
        finally:
            if cursor:
                cursor.close()

    def get_zone_list(self):
        """
        tb_event_detection_zone 테이블에서 zone_segment_json과 zone_type 필드 내용을 리스트로 가져오기
        """
        try:
            cursor = self.get_db_cursor()
            if not cursor:
                return []

            query = """
                SELECT zone_segment_json, zone_type 
                FROM tb_event_detection_zone 
                WHERE zone_active = 1 
                AND zone_segment_json IS NOT NULL 
                AND zone_segment_json != ''
                ORDER BY id
            """
            cursor.execute(query)
            results = cursor.fetchall()
            
            zone_segments = []
            for row in results:
                if row['zone_segment_json']:
                    try:
                        # JSON 파싱하여 zone_segment_json 내용을 리스트로 변환
                        segment_data = json.loads(row['zone_segment_json'])
                        zone_type = row['zone_type']
                        
                        if isinstance(segment_data, list):
                            # 리스트인 경우 각 항목에 zone_type 추가
                            for segment in segment_data:
                                if isinstance(segment, dict):
                                    segment['zone_type'] = zone_type
                                zone_segments.append(segment)
                        elif isinstance(segment_data, dict):
                            # 딕셔너리인 경우 zone_type 추가
                            segment_data['zone_type'] = zone_type
                            zone_segments.append(segment_data)
                        else:
                            # 기타 타입인 경우 zone_type과 함께 딕셔너리로 변환
                            zone_segments.append({
                                'data': segment_data,
                                'zone_type': zone_type
                            })
                    except json.JSONDecodeError as e:
                        logger.error(f"zone_segment_json 파싱 오류: {str(e)}, data: {row['zone_segment_json']}")
                        continue
            
            self.zone_list = zone_segments
            logger.info(f"Zone segments 조회 완료: {len(zone_segments)}개")
            return zone_segments

        except Exception as e:
            logger.error(f"Zone list 조회 오류: {str(e)}")
            return []
        finally:
            if cursor:
                cursor.close()

    def get_camera_info_list(self):
        """
        tb_cameras 테이블에서 videoConfig 필드의 JSON을 파싱하여 source 키값과 videoType을 읽어서 리스트 변수에 저장
        """
        try:
            cursor = self.get_db_cursor()
            if not cursor:
                return []

            query = """
                SELECT videoConfig 
                FROM tb_cameras 
                WHERE videoConfig IS NOT NULL 
                AND videoConfig != ''
            """
            cursor.execute(query)
            results = cursor.fetchall()
            
            camera_info_list = []
            for row in results:
                try:
                    if row['videoConfig']:
                        video_config = json.loads(row['videoConfig'])
                        if 'source' in video_config:
                            # RTSP URL에서 -i 파라미터 제거
                            rtsp_url = video_config['source']
                            print("rtsp_url : ", rtsp_url)
                            # URL이 문자열인지 확인
                            if not isinstance(rtsp_url, str):
                                logger.warning(f"Invalid source type: {type(rtsp_url)}, value: {rtsp_url}")
                                continue
                            
                            # 빈 문자열 체크
                            if not rtsp_url.strip():
                                logger.warning(f"Empty source URL: {rtsp_url}")
                                continue
                            
                            # -i 파라미터 제거 (rtsp://로 시작하는 부분만 유지)
                            if '-i' in rtsp_url:
                                # rtsp://로 시작하는 부분을 찾아서 추출
                                rtsp_start = rtsp_url.find('rtsp://')
                                if rtsp_start != -1:
                                    rtsp_url = rtsp_url[rtsp_start:]
                                else:
                                    # rtsp://가 없으면 http:// 또는 https:// 찾기
                                    http_start = rtsp_url.find('http://')
                                    if http_start != -1:
                                        rtsp_url = rtsp_url[http_start:]
                                    else:
                                        https_start = rtsp_url.find('https://')
                                        if https_start != -1:
                                            rtsp_url = rtsp_url[https_start:]
                                        else:
                                            logger.warning(f"No valid protocol found in URL: {rtsp_url}")
                                            continue
                            
                            # URL 정리 (앞뒤 공백 제거)
                            rtsp_url = rtsp_url.strip()
                            print("rtsp_url 2: ", rtsp_url)
                            # videoType 값 가져오기 (기본값: 'unknown')
                            video_type = video_config.get('videoType', 'unknown')
                            
                            camera_info = {
                                'rtsp_url': rtsp_url,
                                'video_type': video_type
                            }
                            print("camera_info : ", camera_info)
                            camera_info_list.append(camera_info)
                            logger.info(f"Found camera - RTSP: {rtsp_url}, Type: {video_type}")
                except json.JSONDecodeError as e:
                    logger.error(f"Error parsing videoConfig JSON: {str(e)}")
                except Exception as e:
                    logger.error(f"Error processing videoConfig: {str(e)}")
            
            self.camera_info_list = camera_info_list
            logger.info(f"Retrieved {len(camera_info_list)} camera configurations")
            return camera_info_list

        except Exception as e:
            logger.error(f"Error getting camera RTSP sources: {str(e)}")
            return []
        finally:
            if cursor:
                cursor.close()

    def get_latest_temperature_data(self):
        """
        tb_video_panorama_data 테이블에서 마지막 파노라마 이미지 데이터 조회
        """
        try:
            cursor = self.get_db_cursor()
            if not cursor:
                return None

            # 최신 파노라마 데이터 조회
            query = """
                SELECT * FROM tb_video_panorama_data 
                ORDER BY create_date DESC 
                LIMIT 1
            """
            cursor.execute(query)
            result = cursor.fetchone()
            
            if result:
                logger.info(f"파노라마 데이터 조회 성공: ID={result.get('id')}, 생성일={result['create_date']}")
                logger.info(f"파노라마 데이터 필드: {list(result.keys())}")
                panorama_data_json = result.get('panoramaData')
                if panorama_data_json:
                    logger.info(f"panoramaData 필드 존재, 길이: {len(panorama_data_json)} 문자")
                else:
                    logger.warning("panoramaData 필드가 없습니다")
                return result
            else:
                logger.info("파노라마 데이터가 없습니다")
                return None

        except Exception as e:
            logger.error(f"파노라마 데이터 조회 오류: {str(e)}")
            return None
        finally:
            if cursor:
                cursor.close()

    def extract_panorama_temperature_data(self, panorama_data_json):
        """
        파노라마 데이터에서 온도 데이터 추출 및 생성
        파노라마 이미지는 1920x480 크기이므로 온도 데이터도 이에 맞게 생성
        """
        try:
            if not panorama_data_json:
                return None
            
            # panoramaData JSON 파싱
            panorama_data = json.loads(panorama_data_json)
            
            # image base64 데이터 추출
            image_base64 = panorama_data.get('image')
            if not image_base64:
                logger.error("파노라마 데이터에 image 필드가 없습니다")
                return None
            
            # base64 이미지를 디코딩하여 OpenCV로 로드
            image_data = base64.b64decode(image_base64)
            nparr = np.frombuffer(image_data, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if image is None:
                logger.error("파노라마 이미지 디코딩 실패")
                return None
            
            # 이미지 크기 확인 (1920x480 예상)
            height, width = image.shape[:2]
            logger.info(f"파노라마 이미지 크기: {width}x{height}")
            
            # 파노라마 이미지에서 온도 데이터 생성 (가상의 온도 데이터)
            # 실제로는 열화상 카메라에서 온도 데이터를 받아야 하지만,
            # 여기서는 이미지의 밝기나 색상 정보를 기반으로 가상 온도 데이터 생성
            temperature_data = []
            
            # 샘플링 간격 (성능을 위해 모든 픽셀을 사용하지 않고 샘플링)
            sample_interval = 4  # 4픽셀마다 샘플링
            
            for y in range(0, height, sample_interval):
                for x in range(0, width, sample_interval):
                    # BGR 이미지에서 픽셀 값 추출
                    pixel = image[y, x]
                    b, g, r = pixel[0], pixel[1], pixel[2]
                    
                    # 간단한 온도 변환 (실제로는 열화상 카메라의 온도 데이터 사용)
                    # 밝기 기반 가상 온도 계산 (20-60도 범위)
                    brightness = (r + g + b) / 3
                    temperature = 20 + (brightness / 255) * 40  # 20-60도 범위
                    
                    temperature_data.append({
                        'x': x,
                        'y': y,
                        'temperature': temperature
                    })
            
            logger.info(f"파노라마 온도 데이터 생성 완료: {len(temperature_data)}개 픽셀 (샘플링 간격: {sample_interval})")
            return temperature_data
            
        except Exception as e:
            logger.error(f"파노라마 온도 데이터 추출 오류: {str(e)}")
            return None

    def decompress_temperature_data(self, compressed_data):
        """
        ZIP으로 압축된 온도 데이터를 압축 해제하여 파싱하고 CSV 파일로 저장
        (기존 방식 유지 - 호환성을 위해)
        """
        try:
            if not compressed_data:
                return None
            
            # base64 디코딩
            zip_data = base64.b64decode(compressed_data)
            
            # ZIP 압축 해제
            with zipfile.ZipFile(io.BytesIO(zip_data), 'r') as zip_file:
                # temperature_data.json 파일 읽기
                if 'temperature_data.json' in zip_file.namelist():
                    json_data = zip_file.read('temperature_data.json')
                    temperature_data = json.loads(json_data.decode('utf-8'))
                    logger.info(f"온도 데이터 압축 해제 완료: {len(temperature_data)}개 픽셀")
                    
                    # CSV 파일로 저장
                    # self.save_temperature_data_to_csv(temperature_data)
                    
                    return temperature_data
                else:
                    logger.error("ZIP 파일에 temperature_data.json이 없습니다")
                    return None
                    
        except Exception as e:
            logger.error(f"온도 데이터 압축 해제 오류: {str(e)}")
            return None

    def save_temperature_data_to_csv(self, temperature_data):
        """
        온도 데이터를 CSV 파일로 저장
        """
        try:
            if not temperature_data:
                logger.warning("저장할 온도 데이터가 없습니다")
                return
            
            # 현재 시간을 파일명에 포함
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            csv_filename = f"temperature_data_{timestamp}.csv"
            
            # CSV 파일 경로 설정 (bin 디렉토리 내)
            csv_path = os.path.join(os.path.dirname(__file__), csv_filename)
            
            # CSV 파일 생성
            with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
                # CSV 헤더 작성
                fieldnames = ['x', 'y', 'temperature']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                
                # 온도 데이터 작성
                for pixel_data in temperature_data:
                    writer.writerow({
                        'x': pixel_data.get('x', 0),
                        'y': pixel_data.get('y', 0),
                        'temperature': pixel_data.get('temperature', 0.0)
                    })
            
            logger.info(f"온도 데이터 CSV 파일 저장 완료: {csv_path}")
            print(f"온도 데이터 CSV 파일 저장 완료: {csv_path}")
            
        except Exception as e:
            logger.error(f"온도 데이터 CSV 파일 저장 오류: {str(e)}")
            print(f"온도 데이터 CSV 파일 저장 오류: {str(e)}")

    def create_temperature_matrix(self, temperature_data, width=1920, height=480):
        """
        온도 데이터를 2D 매트릭스로 변환하고 CSV 파일로 저장
        파노라마 이미지 크기에 맞게 1920x480으로 변경
        """
        try:
            if not temperature_data:
                return None
            
            # 2D 매트릭스 초기화 (1920x480 - 파노라마 크기)
            temp_matrix = np.full((height, width), np.nan, dtype=np.float64)
            
            # 온도 데이터를 매트릭스에 배치
            for pixel_data in temperature_data:
                x = pixel_data.get('x', 0)
                y = pixel_data.get('y', 0)
                temperature = pixel_data.get('temperature', np.nan)
                
                if 0 <= x < width and 0 <= y < height:
                    temp_matrix[y, x] = temperature
            
            logger.info(f"온도 매트릭스 생성 완료: {width}x{height} (파노라마 크기)")
            
            # 온도 매트릭스를 CSV 파일로 저장
            #self.save_temperature_matrix_to_csv(temp_matrix, width, height)
            
            return temp_matrix
            
        except Exception as e:
            logger.error(f"온도 매트릭스 생성 오류: {str(e)}")
            return None

    def save_temperature_matrix_to_csv(self, temp_matrix, width, height):
        """
        온도 매트릭스를 CSV 파일로 저장 (2D 그리드 형태)
        """
        try:
            if temp_matrix is None:
                logger.warning("저장할 온도 매트릭스가 없습니다")
                return
            
            # 현재 시간을 파일명에 포함
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            csv_filename = f"temperature_matrix_{timestamp}.csv"
            
            # CSV 파일 경로 설정 (bin 디렉토리 내)
            csv_path = os.path.join(os.path.dirname(__file__), csv_filename)
            
            # CSV 파일 생성
            with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
                # CSV 헤더 작성 (x 좌표)
                header = ['y\\x'] + [str(i) for i in range(width)]
                writer = csv.writer(csvfile)
                writer.writerow(header)
                
                # 온도 매트릭스 데이터 작성
                for y in range(height):
                    row = [str(y)]  # y 좌표
                    for x in range(width):
                        temp_value = temp_matrix[y, x]
                        if np.isnan(temp_value):
                            row.append('NaN')
                        else:
                            row.append(f"{temp_value:.2f}")
                    writer.writerow(row)
            
            logger.info(f"온도 매트릭스 CSV 파일 저장 완료: {csv_path}")
            print(f"온도 매트릭스 CSV 파일 저장 완료: {csv_path}")
            
        except Exception as e:
            logger.error(f"온도 매트릭스 CSV 파일 저장 오류: {str(e)}")
            print(f"온도 매트릭스 CSV 파일 저장 오류: {str(e)}")

    def extract_roi_temperature_data(self, temp_matrix, zone_info):
        """
        ROI 영역의 온도 데이터 추출
        """
        try:
            if temp_matrix is None or zone_info is None:
                return None
            
            # zone_info에서 rect 정보 추출
            rect = None
            if isinstance(zone_info, dict):
                if 'rect' in zone_info:
                    # 기존 rect 형식: [x, y, w, h]
                    rect = zone_info['rect']
                elif all(key in zone_info for key in ['left', 'right', 'top', 'bottom']):
                    # left, right, top, bottom 형식: [left, top, width, height]
                    left = zone_info['left']
                    right = zone_info['right']
                    top = zone_info['top']
                    bottom = zone_info['bottom']
                    width = right - left
                    height = bottom - top
                    rect = [left, top, width, height]
                    logger.info(f"zone_info 좌표 변환: left={left}, top={top}, right={right}, bottom={bottom} -> rect=[{left}, {top}, {width}, {height}]")
                else:
                    logger.warning(f"유효하지 않은 zone_info 형식: {zone_info}")
                    return None
            
            if rect is None:
                logger.warning(f"rect 정보를 추출할 수 없습니다: {zone_info}")
                return None
            
            x, y, w, h = rect
            
            # ROI 영역 추출
            roi_temp = temp_matrix[y:y+h, x:x+w]
            # print("temp_matrix :", temp_matrix)
            # print("roi_temp :", roi_temp)
            # NaN 값 제거하고 유효한 온도 데이터만 추출
            valid_temps = roi_temp[~np.isnan(roi_temp)]
            
            if len(valid_temps) > 0:
                roi_data = {
                    'zone_type': zone_info.get('zone_type', 'unknown'),
                    'rect': rect,
                    'temperatures': valid_temps.tolist(),
                    'min_temp': float(np.min(valid_temps)),
                    'max_temp': float(np.max(valid_temps)),
                    'avg_temp': float(np.mean(valid_temps)),
                    'temp_diff': float(np.max(valid_temps) - np.min(valid_temps))
                }
                logger.info(f"ROI 영역 {zone_info.get('zone_type', 'unknown')} 온도 데이터 추출 완료: {len(valid_temps)}개 픽셀")
                return roi_data
            else:
                logger.warning(f"ROI 영역 {zone_info.get('zone_type', 'unknown')}에 유효한 온도 데이터가 없습니다")
                return None
                
        except Exception as e:
            logger.error(f"ROI 온도 데이터 추출 오류: {str(e)}")
            return None

    def create_roi_polygon(self, rect):
        """
        ROI 사각형을 다각형 좌표로 변환
        rect: [x, y, w, h] 또는 [left, top, width, height] 형식
        """
        try:
            if len(rect) == 4:
                x, y, w, h = rect
                polygon = [
                    [x, y],           # 좌상단
                    [x + w, y],       # 우상단
                    [x + w, y + h],   # 우하단
                    [x, y + h]        # 좌하단
                ]
                logger.debug(f"폴리곤 생성 성공: rect={rect} -> polygon={polygon}")
                return polygon
            else:
                logger.warning(f"유효하지 않은 rect 형식: {rect}, 길이: {len(rect)}")
                return []
        except Exception as e:
            logger.error(f"폴리곤 생성 오류: rect={rect}, 오류: {str(e)}")
            return []

    def create_20x20_boxes(self, rect, box_size=20):
        """
        ROI 영역을 20x20 박스로 분할
        rect: [x, y, w, h] 형식 (절대 좌표)
        """
        try:
            x, y, w, h = rect
            boxes = []
            
            # 20x20 박스로 분할
            for box_y in range(0, h, box_size):
                for box_x in range(0, w, box_size):
                    # 박스의 실제 크기 계산 (경계 처리)
                    box_w = min(box_size, w - box_x)
                    box_h = min(box_size, h - box_y)
                    
                    # 박스 좌표 (절대 좌표)
                    abs_x = x + box_x
                    abs_y = y + box_y
                    
                    box_info = {
                        'box_id': f"{box_x//box_size}_{box_y//box_size}",
                        'relative_pos': [box_x, box_y],  # ROI 내 상대 위치
                        'absolute_pos': [abs_x, abs_y],  # 전체 이미지 내 절대 위치
                        'size': [box_w, box_h],
                        'rect': [abs_x, abs_y, box_w, box_h]
                    }
                    boxes.append(box_info)
            
            logger.info(f"ROI 영역 {rect}을 {len(boxes)}개의 20x20 박스로 분할 완료 (절대 좌표 사용)")
            return boxes
            
        except Exception as e:
            logger.error(f"20x20 박스 생성 오류: {str(e)}")
            return []

    def analyze_20x20_boxes(self, temp_matrix, boxes, threshold_levels):
        """
        20x20 박스들의 온도차를 분석하여 경보 조건을 만족하는 박스들을 찾음
        """
        try:
            alert_boxes = []
            
            for box_info in boxes:
                # 박스 영역의 온도 데이터 추출
                x, y, w, h = box_info['rect']
                
                # 경계 체크
                if x + w > temp_matrix.shape[1] or y + h > temp_matrix.shape[0]:
                    logger.warning(f"박스 {box_info['box_id']}가 매트릭스 범위를 벗어남: {box_info['rect']}")
                    continue
                
                # 박스 영역의 온도 데이터 추출
                box_temp = temp_matrix[y:y+h, x:x+w]
                
                # NaN 값 제거하고 유효한 온도 데이터만 추출
                valid_temps = box_temp[~np.isnan(box_temp)]
                
                if len(valid_temps) > 0:
                    # 온도 통계 계산
                    min_temp = float(np.min(valid_temps))
                    max_temp = float(np.max(valid_temps))
                    avg_temp = float(np.mean(valid_temps))
                    temp_diff = max_temp - min_temp
                    
                    # 경보 레벨 결정
                    alert_level = None
                    for level, threshold in enumerate(threshold_levels):
                        if temp_diff >= threshold:
                            alert_level = level
                    
                    # 경보 조건을 만족하는 경우
                    if alert_level is not None:
                        # 폴리곤 생성 및 검증 (절대 좌표 사용)
                        polygon = self.create_roi_polygon(box_info['rect'])
                        if not polygon:
                            logger.warning(f"박스 {box_info['box_id']} 폴리곤 생성 실패, rect: {box_info['rect']}")
                            continue
                        
                        alert_box_data = {
                            'box_id': box_info['box_id'],
                            'rect': box_info['rect'],  # 절대 좌표 [x, y, w, h]
                            'relative_pos': box_info['relative_pos'],  # ROI 내 상대 위치
                            'absolute_pos': box_info['absolute_pos'],  # 전체 이미지 내 절대 위치
                            'size': box_info['size'],
                            'temperatures': valid_temps.tolist(),
                            'min_temp': min_temp,
                            'max_temp': max_temp,
                            'avg_temp': avg_temp,
                            'temp_diff': temp_diff,
                            'alert_level': alert_level,
                            'polygon': polygon  # 절대 좌표로 생성된 폴리곤
                        }
                        alert_boxes.append(alert_box_data)
                        
                        logger.info(f"박스 {box_info['box_id']} 경보 감지: 온도차 {temp_diff:.1f}°C >= {threshold_levels[alert_level]}°C (Level {alert_level}), 절대 좌표 폴리곤: {polygon}")
            
            logger.info(f"총 {len(alert_boxes)}개의 20x20 박스에서 경보 조건 감지")
            return alert_boxes
            
        except Exception as e:
            logger.error(f"20x20 박스 분석 오류: {str(e)}")
            return []

    def log_roi_polygon_structure(self, roi_polygon_data):
        """
        roi_polygon 구조를 로그로 출력하여 디버깅
        """
        try:
            logger.info("=== ROI_POLYGON 구조 분석 ===")
            
            if isinstance(roi_polygon_data, dict):
                if 'alert_boxes' in roi_polygon_data:
                    logger.info(f"20x20 박스 분석 결과 구조:")
                    logger.info(f"  - 메인 ROI: {roi_polygon_data['main_roi']['zone_type']}")
                    logger.info(f"  - 총 경보 박스: {roi_polygon_data['total_alert_boxes']}개")
                    
                    for i, box in enumerate(roi_polygon_data['alert_boxes'][:5]):  # 처음 5개만
                        logger.info(f"  - 박스 {i+1}: ID={box['box_id']}, 온도차={box['temp_diff']:.1f}°C, 폴리곤={len(box['polygon'])}개 좌표")
                        if box['polygon']:
                            logger.info(f"    폴리곤 좌표: {box['polygon']}")
                else:
                    logger.info("단일 ROI 구조")
                    logger.info(f"  - 폴리곤 좌표: {roi_polygon_data}")
            elif isinstance(roi_polygon_data, list):
                logger.info(f"리스트 구조: {len(roi_polygon_data)}개 좌표")
                logger.info(f"  - 폴리곤 좌표: {roi_polygon_data}")
            else:
                logger.info(f"알 수 없는 구조: {type(roi_polygon_data)}")
                logger.info(f"  - 내용: {roi_polygon_data}")
            
            logger.info("=== ROI_POLYGON 구조 분석 완료 ===")
            
        except Exception as e:
            logger.error(f"ROI_POLYGON 구조 분석 오류: {str(e)}")

    def extract_panorama_image(self, panorama_data_json):
        """
        파노라마 데이터에서 이미지를 추출하여 스냅샷 데이터 형태로 반환
        """
        try:
            if not panorama_data_json:
                logger.warning("파노라마 데이터가 없어 이미지를 추출할 수 없습니다")
                return None
            
            logger.info(f"파노라마 데이터 JSON 길이: {len(panorama_data_json)} 문자")
            
            # panoramaData JSON 파싱
            panorama_data = json.loads(panorama_data_json)
            logger.info(f"파노라마 데이터 JSON 파싱 성공, 키: {list(panorama_data.keys())}")
            
            # image base64 데이터 추출
            image_base64 = panorama_data.get('image')
            if not image_base64:
                logger.error("파노라마 데이터에 image 필드가 없습니다")
                return None
            
            logger.info(f"파노라마 이미지 base64 데이터 길이: {len(image_base64)} 문자")
            
            # 파노라마 이미지를 파일로 저장
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"panorama_{timestamp}.jpg"
            
            # 이미지 파일 경로 설정
            snapshots_dir = os.path.join(os.path.dirname(__file__), 'snapshots')
            os.makedirs(snapshots_dir, exist_ok=True)
            
            image_path = os.path.join(snapshots_dir, filename)
            
            # base64 디코딩하여 파일로 저장
            image_data = base64.b64decode(image_base64)
            with open(image_path, 'wb') as f:
                f.write(image_data)
            
            logger.info(f"파노라마 이미지 저장 완료: {image_path} (크기: {len(image_data)} bytes)")
            
            # 스냅샷 데이터 형태로 반환
            snapshot_data = {
                'panorama_image': True,
                'image_type': 'panorama',
                'timestamp': datetime.now().isoformat(),
                'image_data': image_base64,
                'file_path': image_path,
                'filename': filename
            }
            
            logger.info(f"파노라마 스냅샷 데이터 생성 완료: {filename}")
            return snapshot_data
            
        except Exception as e:
            logger.error(f"파노라마 이미지 추출 오류: {str(e)}")
            logger.error(f"예외 상세: {traceback.format_exc()}")
            return None

    def capture_video_snapshots(self):
        """
        FFmpeg를 사용하여 RTSP 소스에서 비디오 이미지를 캡처하여 base64로 인코딩하고 파일로도 저장
        """
        snapshot_images = []
        
        if not hasattr(self, 'camera_info_list') or not self.camera_info_list:
            logger.warning("카메라 정보가 없어 스냅샷을 캡처할 수 없습니다")
            return snapshot_images
        
        for camera_info in self.camera_info_list:
            try:
                # 강제 종료 체크
                if self.force_exit:
                    logger.info("강제 종료 요청됨, 스냅샷 캡처 중단")
                    return snapshot_images
                
                rtsp_url = camera_info['rtsp_url']
                video_type = camera_info['video_type']
                camera_name = camera_info.get('camera_name', 'unknown')
                
                # RTSP URL 유효성 검사
                if not rtsp_url or not isinstance(rtsp_url, str) or rtsp_url.strip() == '':
                    logger.warning(f"유효하지 않은 RTSP URL: {rtsp_url}")
                    continue
                
                rtsp_url = rtsp_url.strip()
                
                # RTSP 프로토콜 확인
                if not rtsp_url.startswith(('rtsp://', 'http://', 'https://')):
                    logger.warning(f"RTSP URL에 유효하지 않은 프로토콜: {rtsp_url}")
                    continue
                
                logger.info(f"스냅샷 캡처 중: {rtsp_url}")
                
                try:
                    # FFmpeg 명령어 구성 (메모리로 직접 출력)
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
                        img_base64 = base64.b64encode(stdout_data).decode('utf-8')
                        
                        # 스냅샷 이미지를 파일로 저장
                        filename, file_path = self.save_snapshot_to_file(stdout_data, camera_name, video_type)
                        
                        snapshot_data = {
                            'rtsp_url': rtsp_url,
                            'video_type': video_type,
                            'camera_name': camera_name,
                            'timestamp': datetime.now().isoformat(),
                            'image_data': img_base64,
                            'file_path': file_path if file_path else ''
                        }
                        snapshot_images.append(snapshot_data)
                        logger.info(f"스냅샷 캡처 성공: {rtsp_url} (Type: {video_type}, Camera: {camera_name})")
                    else:
                        error_msg = stderr_data.decode('utf-8') if stderr_data else "알 수 없는 오류"
                        logger.error(f"FFmpeg 실패 {rtsp_url}: {error_msg}")
                        
                except subprocess.TimeoutExpired:
                    logger.error(f"FFmpeg 타임아웃 {rtsp_url}")
                    if process:
                        process.kill()
                        process.wait()
                except Exception as e:
                    logger.error(f"FFmpeg 오류 {rtsp_url}: {str(e)}")
                
            except Exception as e:
                logger.error(f"스냅샷 캡처 오류 {rtsp_url}: {str(e)}")
                logger.error(f"예외 상세: {traceback.format_exc()}")
                continue
        
        logger.info(f"총 {len(snapshot_images)}개의 스냅샷 캡처 완료")
        return snapshot_images

    def save_snapshot_to_file(self, image_data, camera_name, video_type):
        """
        스냅샷 이미지를 파일로 저장
        """
        try:
            if not image_data:
                logger.warning("저장할 이미지 데이터가 없습니다")
                return
            
            # 현재 시간을 파일명에 포함
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # 카메라 이름과 비디오 타입을 파일명에 포함
            safe_camera_name = "".join(c for c in camera_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
            safe_camera_name = safe_camera_name.replace(' ', '_')
            
            # 파일명 생성: 카메라명_비디오타입_날짜시간.jpg
            filename = f"{safe_camera_name}_{video_type}_{timestamp}.jpg"
            
            # 이미지 파일 경로 설정 (bin 디렉토리 내 snapshots 폴더)
            snapshots_dir = os.path.join(os.path.dirname(__file__), 'snapshots')
            os.makedirs(snapshots_dir, exist_ok=True)
            
            image_path = os.path.join(snapshots_dir, filename)
            
            # 이미지 파일 저장
            with open(image_path, 'wb') as f:
                f.write(image_data)
            
            logger.info(f"스냅샷 이미지 저장 완료: {image_path}")
            print(f"스냅샷 이미지 저장 완료: {image_path}")
            
            return filename, image_path
            
        except Exception as e:
            logger.error(f"스냅샷 이미지 저장 오류: {str(e)}")
            print(f"스냅샷 이미지 저장 오류: {str(e)}")
            return None, None

    def scenario1_judge(self):
        """
        시나리오1: tb_video_panorama_data의 최신 파노라마 데이터에서 temperature_matrix를 통해
        각 ROI 구간별 온도차를 계산하고, 차이가 발생하는 폴리곤 영역을 roi_polygon에 저장
        """
        try:
            logger.info("시나리오1 판단 시작 (파노라마 데이터 사용)")
            
            # 강제 종료 체크
            if self.force_exit:
                logger.info("강제 종료 요청됨, 시나리오1 중단")
                return False
            
            # 최신 파노라마 데이터 조회
            panorama_data_record = self.get_latest_temperature_data()
            if not panorama_data_record:
                logger.info("시나리오1: 파노라마 데이터가 없습니다")
                return False
            
            # 파노라마 데이터에서 온도 데이터 추출
            temperature_data = self.extract_panorama_temperature_data(panorama_data_record['panoramaData'])
            if not temperature_data:
                logger.error("시나리오1: 파노라마 온도 데이터 추출 실패")
                return False
            
            # 온도 매트릭스 생성 (1920x480 파노라마 크기)
            temp_matrix = self.create_temperature_matrix(temperature_data)
            if temp_matrix is None:
                logger.error("시나리오1: 온도 매트릭스 생성 실패")
                return False

            # zone_type 리스트 가져오기
            if not self.zone_list:
                logger.warning("시나리오1: zone_list가 없어 기본 ROI 영역을 사용합니다")
                # 기본 ROI 영역 설정 (1920x480 파노라마 전체 영역을 6개 구역으로 분할)
                default_zones = [
                    {'zone_type': '1', 'rect': [0, 0, 640, 240]},        # 좌상단 (0,0 ~ 639,239)
                    {'zone_type': '2', 'rect': [640, 0, 640, 240]},     # 중상단 (640,0 ~ 1279,239)
                    {'zone_type': '3', 'rect': [1280, 0, 640, 240]},    # 우상단 (1280,0 ~ 1919,239)
                    {'zone_type': '4', 'rect': [0, 240, 640, 240]},      # 좌하단 (0,240 ~ 639,479)
                    {'zone_type': '5', 'rect': [640, 240, 640, 240]},   # 중하단 (640,240 ~ 1279,479)
                    {'zone_type': '6', 'rect': [1280, 240, 640, 240]}   # 우하단 (1280,240 ~ 1919,479)
                ]
                zones_to_check = default_zones
            else:
                zones_to_check = self.zone_list



            # scenario1의 4단계 기준값 가져오기
            if not self.alert_settings or 'alarmLevels' not in self.alert_settings or 'scenario1' not in self.alert_settings['alarmLevels']:
                logger.error("시나리오1: alert_setting_json의 alarmLevels.scenario1을 찾을 수 없습니다")
                return False
            
            levels = self.alert_settings['alarmLevels']['scenario1']
            logger.info(f"시나리오1 기준값: {levels}")
            # 4단계 기준값: [2, 5, 8, 10]

            # 각 ROI 영역을 20x20 박스로 분할하여 검사
            alert_detected = False
            for zone_info in zones_to_check:
                # 강제 종료 체크
                if self.force_exit:
                    logger.info("강제 종료 요청됨, 시나리오1 중단")
                    return False
                
                # zone_segment_json에서 실제 ROI 좌표 추출
                if 'left' in zone_info and 'top' in zone_info and 'right' in zone_info and 'bottom' in zone_info:
                    # zone_segment_json의 실제 좌표 사용
                    actual_rect = [
                        zone_info['left'],      # x
                        zone_info['top'],       # y
                        zone_info['right'] - zone_info['left'],  # width
                        zone_info['bottom'] - zone_info['top']   # height
                    ]
                    logger.info(f"Zone {zone_info.get('zone_type', 'unknown')}: zone_segment_json 좌표 사용 - {actual_rect}")
                else:
                    # 기존 rect 정보 사용 (fallback)
                    actual_rect = zone_info.get('rect', [0, 0, 320, 240])
                    logger.info(f"Zone {zone_info.get('zone_type', 'unknown')}: 기존 rect 좌표 사용 - {actual_rect}")
                
                # ROI 영역을 20x20 박스로 분할 (절대 좌표로)
                boxes = self.create_20x20_boxes(actual_rect, box_size=20)
                
                if not boxes:
                    logger.warning(f"Zone {zone_info.get('zone_type', 'unknown')}: 20x20 박스 생성 실패")
                    continue
                
                # 20x20 박스들의 온도차 분석
                alert_boxes = self.analyze_20x20_boxes(temp_matrix, boxes, levels)
                
                logger.info(f"Zone {zone_info.get('zone_type', 'unknown')}: 20x20 박스 분석 완료, 총 {len(boxes)}개 박스 중 {len(alert_boxes) if alert_boxes else 0}개에서 경보 조건 감지")
                
                if alert_boxes:
                    # 경보 생성 (여러 박스의 정보를 포함)
                    # zone_segment_json의 실제 좌표 정보를 zone_info에 추가
                    if 'left' in zone_info and 'top' in zone_info and 'right' in zone_info and 'bottom' in zone_info:
                        zone_info['actual_rect'] = actual_rect
                        zone_info['zone_segment_coords'] = {
                            'left': zone_info['left'],
                            'top': zone_info['top'],
                            'right': zone_info['right'],
                            'bottom': zone_info['bottom']
                        }
                    
                    self.create_scenario1_alert(
                        panorama_data_record['id'],
                        zone_info,
                        'S001',
                        len(alert_boxes),  # 경보 조건을 만족하는 박스 개수
                        1,  # 기본 alert_level
                        alert_boxes  # 20x20 박스 분석 결과
                    )
                    alert_detected = True

            # 전체 영역 온도차 변화율 검사 (25% 이상) - OR 조건으로 추가
            if len(zones_to_check) > 1:
                # 강제 종료 체크
                if self.force_exit:
                    logger.info("강제 종료 요청됨, 시나리오1 중단")
                    return False
                    
                # 전체 영역의 온도 데이터 수집
                all_temps = []
                for zone_info in zones_to_check:
                    roi_data = self.extract_roi_temperature_data(temp_matrix, zone_info)
                    if roi_data and roi_data['temperatures']:
                        all_temps.extend(roi_data['temperatures'])
                
                # 전체 영역 온도차 변화율 계산
                if len(all_temps) > 0:
                    overall_temp_diff = max(all_temps) - min(all_temps)
                    overall_avg_temp = np.mean(all_temps)
                    
                    if overall_avg_temp > 0:
                        temp_change_percent = (overall_temp_diff / overall_avg_temp) * 100
                        logger.info(f"전체 영역 온도차 변화율: {temp_change_percent:.1f}% (최대: {max(all_temps):.1f}°C, 최소: {min(all_temps):.1f}°C)")
                        
                        # 25% 이상인 경우 경보 생성
                        if temp_change_percent >= 25.0:
                            logger.info(f"시나리오1 경보 감지: 전체 영역 온도차 변화율 {temp_change_percent:.1f}% >= 25%")
                            
                            # 전체 영역 ROI 데이터 생성 (파노라마 크기)
                            overall_zone_info = {
                                'zone_type': 'overall',
                                'rect': [0, 0, 1920, 480]  # 1920x480 파노라마 전체 영역
                            }
                            
                            # 경보 생성 (25% 기준은 별도 alert_type으로 처리)
                            self.create_scenario1_alert(
                                panorama_data_record['id'],
                                overall_zone_info,
                                'S002',
                                temp_change_percent,
                                3,  # 최고 레벨로 설정
                                None  # alert_boxes는 없음
                            )
                            alert_detected = True

            if not alert_detected:
                logger.info("시나리오1: 경보 조건을 만족하지 않습니다")
            
            return alert_detected
            
        except Exception as e:
            logger.error(f"시나리오1 판단 오류: {str(e)}")
            logger.error(traceback.format_exc())
            return False

    def create_scenario1_alert(self, video_data_id, zone_info, alert_type, threshold_value, alert_level=1, alert_boxes=None):
        """
        시나리오1 경보 생성 및 DB 저장 (20x20 박스 분석 결과 포함)
        """
        try:
            cursor = self.get_db_cursor()
            if not cursor:
                return False
            
            # 파노라마 데이터 조회 및 이미지 추출
            panorama_data_record = self.get_latest_temperature_data()
            panorama_snapshot = None
            if panorama_data_record:
                logger.info(f"파노라마 데이터 조회 성공: ID={panorama_data_record.get('id')}, 생성일={panorama_data_record.get('create_date')}")
                panorama_snapshot = self.extract_panorama_image(panorama_data_record['panoramaData'])
                if panorama_snapshot:
                    logger.info("파노라마 이미지 추출 성공")
                else:
                    logger.warning("파노라마 이미지 추출 실패")
            else:
                logger.warning("파노라마 데이터 조회 실패 - 데이터가 없습니다")
            
            # 스트림 스냅샷 이미지 캡처
            stream_snapshots = self.capture_video_snapshots()
            
            # 모든 스냅샷 이미지 통합
            snapshot_images = []
            
            # 파노라마 이미지 추가
            if panorama_snapshot:
                snapshot_images.append(panorama_snapshot)
                logger.info("파노라마 이미지가 snapshot_images에 추가됨")
            else:
                logger.warning("파노라마 이미지가 없어 snapshot_images에 추가되지 않음")
            
            # 스트림 캡처 이미지들 추가
            if stream_snapshots:
                snapshot_images.extend(stream_snapshots)
                logger.info(f"{len(stream_snapshots)}개의 스트림 이미지가 snapshot_images에 추가됨")
            else:
                logger.warning("스트림 이미지가 없음")
            
            logger.info(f"총 {len(snapshot_images)}개의 스냅샷 이미지 준비 완료 (파노라마: {1 if panorama_snapshot else 0}개, 스트림: {len(stream_snapshots)}개)")
            
            # 디버깅: snapshot_images 내용 확인
            for i, img in enumerate(snapshot_images):
                img_type = img.get('image_type', 'stream')
                logger.info(f"스냅샷 {i+1}: 타입={img_type}, 파일명={img.get('filename', 'N/A')}")
            
            # roi_polygon 구성 (20x20 박스 분석 결과가 있는 경우)
            if alert_boxes and len(alert_boxes) > 0:
                # 여러 박스에서 온도차가 발생한 경우, 각 박스의 폴리곤과 온도차를 리스트로 저장
                roi_polygon_list = []
                for box_data in alert_boxes:
                    polygon_info = {
                        'box_id': box_data['box_id'],
                        'polygon': box_data['polygon'],
                        'temp_diff': box_data['temp_diff'],
                        'alert_level': box_data['alert_level'],
                        'min_temp': box_data['min_temp'],
                        'max_temp': box_data['max_temp'],
                        'avg_temp': box_data['avg_temp'],
                        'relative_pos': box_data['relative_pos'],
                        'absolute_pos': box_data['absolute_pos'],
                        'size': box_data['size']
                    }
                    roi_polygon_list.append(polygon_info)
                
                # 전체 ROI 영역의 폴리곤도 포함 (zone_segment_json의 실제 좌표 사용)
                if 'actual_rect' in zone_info:
                    main_rect = zone_info['actual_rect']
                    main_polygon = self.create_roi_polygon(main_rect)
                    logger.info(f"zone_segment_json 실제 좌표로 main_roi 생성: {main_rect}")
                else:
                    main_rect = zone_info.get('rect', [0, 0, 640, 240])  # 파노라마 기본 크기로 변경
                    main_polygon = self.create_roi_polygon(main_rect)
                    logger.info(f"기존 rect 좌표로 main_roi 생성: {main_rect}")
                
                roi_polygon_data = {
                    'main_roi': {
                        'zone_type': zone_info.get('zone_type', 'unknown'),
                        'rect': main_rect,
                        'polygon': main_polygon
                    },
                    'alert_boxes': roi_polygon_list,
                    'total_alert_boxes': len(roi_polygon_list)
                }
            else:
                # 기존 방식 (단일 ROI)
                roi_polygon_data = self.create_roi_polygon(zone_info.get('rect', [0, 0, 640, 240]))  # 파노라마 기본 크기로 변경
            
            # 경보 정보 구성 (zone_segment_json의 실제 좌표 사용)
            if 'actual_rect' in zone_info:
                alert_rect = zone_info['actual_rect']
                logger.info(f"alert_info에 zone_segment_json 실제 좌표 사용: {alert_rect}")
            else:
                alert_rect = zone_info.get('rect', [0, 0, 640, 240])  # 파노라마 기본 크기로 변경
                logger.info(f"alert_info에 기존 rect 좌표 사용: {alert_rect}")
            
            alert_info = {
                'scenario': 'scenario1',
                'alert_type': alert_type,
                'threshold_value': threshold_value,
                'alert_level': alert_level,
                'zone_type': zone_info.get('zone_type', 'unknown'),
                'rect': alert_rect,
                'detection_time': datetime.now().isoformat(),
                'roi_polygon': roi_polygon_data
            }
            
            # 20x20 박스 분석 결과가 있는 경우 추가 정보 포함
            if alert_boxes and len(alert_boxes) > 0:
                alert_info['box_analysis'] = {
                    'total_boxes': len(alert_boxes),
                    'box_size': 20,
                    'analysis_method': '20x20_grid'
                }
                
                # 온도 통계 (모든 박스의 통합)
                all_temps = []
                for box_data in alert_boxes:
                    all_temps.extend(box_data['temperatures'])
                
                if all_temps:
                    alert_info['temperature_stats'] = {
                        'min': min(all_temps),
                        'max': max(all_temps),
                        'average': np.mean(all_temps),
                        'difference': max(all_temps) - min(all_temps),
                        'total_pixels': len(all_temps)
                    }
            
            # overall_change_percent 타입인 경우 추가 정보 포함
            if alert_type == 'overall_change_percent':
                if 'temperature_stats' not in alert_info:
                    alert_info['temperature_stats'] = {}
                alert_info['temperature_stats']['change_percent'] = threshold_value
                alert_info['overall_analysis'] = True
            
            # 디버깅을 위한 로그 추가
            logger.info(f"경보 정보 구성 완료: roi_polygon 구조 = {type(roi_polygon_data)}")
            if isinstance(roi_polygon_data, dict) and 'alert_boxes' in roi_polygon_data:
                logger.info(f"20x20 박스 분석 결과: {len(roi_polygon_data['alert_boxes'])}개 박스")
                for i, box in enumerate(roi_polygon_data['alert_boxes'][:3]):  # 처음 3개만 로그
                    logger.info(f"박스 {i+1}: ID={box['box_id']}, 온도차={box['temp_diff']:.1f}°C, 폴리곤={len(box['polygon'])}개 좌표")
            else:
                logger.info(f"단일 ROI 폴리곤: {len(roi_polygon_data)}개 좌표")
            
            # alert_info를 JSON으로 직렬화하여 크기 확인
            alert_info_json = json.dumps(alert_info, ensure_ascii=False)
            logger.info(f"alert_info JSON 크기: {len(alert_info_json)} 문자")
            
            # DB에 경보 저장
            query = """
                INSERT INTO tb_alert_history 
                (fk_camera_id, alert_accur_time, alert_type, alert_level, 
                alert_status, alert_info_json, fk_detect_zone_id, 
                fk_process_user_id, create_date, update_date, fk_video_receive_data_id, snapshotImages)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            now = datetime.now()
            values = (
                1,  # fk_camera_id
                now,  # alert_accur_time
                alert_type,  # alert_type
                alert_level,  # alert_level (0~3)
                'P001',  # alert_status
                alert_info_json,  # alert_info_json (이미 직렬화됨)
                int(zone_info.get('zone_type', 1)),  # fk_detect_zone_id
                0,  # fk_process_user_id
                now,  # create_date
                now,  # update_date
                video_data_id,  # fk_video_receive_data_id
                json.dumps(snapshot_images, ensure_ascii=False) if snapshot_images else None  # snapshotImages
            )
            
            cursor.execute(query, values)
            logger.info(f"시나리오1 경보 생성 완료: Zone {zone_info.get('zone_type', 'unknown')}, {alert_type}: {threshold_value}, Level: {alert_level}, Alert Boxes: {len(alert_boxes) if alert_boxes else 0}")
            
            # DB 저장 후 roi_polygon 구조 재확인
            self.log_roi_polygon_structure(roi_polygon_data)
            
            return True
            
        except Exception as e:
            logger.error(f"시나리오1 경보 생성 오류: {str(e)}")
            return False
        finally:
            if cursor:
                cursor.close()

    def collect_hourly_average_temperatures(self, hours=24):
        """
        시나리오3: 1시간 평균온도 데이터 수집
        """
        try:
            cursor = self.get_db_cursor()
            if not cursor:
                return None
            
            # 최근 24시간의 파노라마 데이터 조회
            query = """
                SELECT panoramaData, create_date 
                FROM tb_video_panorama_data 
                WHERE create_date >= DATE_SUB(NOW(), INTERVAL %s HOUR)
                ORDER BY create_date ASC
            """
            cursor.execute(query, (hours,))
            results = cursor.fetchall()
            
            if not results:
                logger.warning(f"시나리오3: 최근 {hours}시간 파노라마 데이터가 없습니다")
                return None
            
            hourly_temps = []
            for row in results:
                try:
                    # 파노라마 데이터에서 온도 데이터 추출
                    temperature_data = self.extract_panorama_temperature_data(row['panoramaData'])
                    if temperature_data:
                        # 픽셀별 온도 데이터를 평균온도로 변환
                        pixel_temps = [pixel['temperature'] for pixel in temperature_data]
                        avg_temp = np.mean(pixel_temps)
                        hourly_temps.append({
                            'timestamp': row['create_date'],
                            'average_temperature': avg_temp,
                            'pixel_count': len(pixel_temps)
                        })
                except Exception as e:
                    logger.error(f"시나리오3: 온도 데이터 추출 오류: {str(e)}")
                    continue
            
            logger.info(f"시나리오3: {len(hourly_temps)}시간의 평균온도 데이터 수집 완료")
            return hourly_temps
            
        except Exception as e:
            logger.error(f"시나리오3: 1시간 평균온도 데이터 수집 오류: {str(e)}")
            return None
        finally:
            if cursor:
                cursor.close()

    def analyze_normal_distribution(self, hourly_temps):
        """
        시나리오3: 정규분포 분석 및 기준라인 설정
        """
        try:
            if not hourly_temps or len(hourly_temps) < 10:
                logger.warning("시나리오3: 충분한 데이터가 없어 정규분포 분석을 수행할 수 없습니다")
                return None
            
            # 온도 데이터 추출
            temperatures = [temp['average_temperature'] for temp in hourly_temps]
            temps_array = np.array(temperatures)
            
            # 정규분포 파라미터 계산
            mean_temp = np.mean(temps_array)
            std_temp = np.std(temps_array)
            
            # 95% 신뢰구간 계산
            from scipy import stats
            confidence_interval = stats.norm.interval(0.95, loc=mean_temp, scale=std_temp)
            
            # 기준라인 = 정규분포의 평균값
            baseline_line = mean_temp
            
            distribution_info = {
                'mean': mean_temp,
                'std': std_temp,
                'baseline_line': baseline_line,
                'confidence_interval': confidence_interval,
                'data_count': len(temperatures),
                'min_temp': np.min(temps_array),
                'max_temp': np.max(temps_array)
            }
            
            logger.info(f"시나리오3: 정규분포 분석 완료")
            logger.info(f"  평균온도: {mean_temp:.2f}°C")
            logger.info(f"  표준편차: {std_temp:.2f}°C")
            logger.info(f"  기준라인: {baseline_line:.2f}°C")
            logger.info(f"  95% 신뢰구간: {confidence_interval[0]:.2f}°C ~ {confidence_interval[1]:.2f}°C")
            
            return distribution_info
            
        except Exception as e:
            logger.error(f"시나리오3: 정규분포 분석 오류: {str(e)}")
            return None

    def calculate_c2m_distance(self, current_temp, baseline_line):
        """
        시나리오3: C2M Distance 계산 (Center to Margin)
        """
        try:
            # C2M distance = |현재온도 - 기준라인|
            c2m_distance = abs(current_temp - baseline_line)
            return c2m_distance
            
        except Exception as e:
            logger.error(f"시나리오3: C2M distance 계산 오류: {str(e)}")
            return None

    def detect_leakage_concern_areas(self, temp_matrix, distribution_info, threshold_diff=5.0):
        """
        시나리오3: 누수발생 우려지역 감지
        """
        try:
            if not distribution_info:
                logger.error("시나리오3: 분포 정보가 없어 누수 감지를 수행할 수 없습니다")
                return []
            
            baseline_line = distribution_info['baseline_line']
            concern_areas = []
            
            height, width = temp_matrix.shape
            
            # 각 픽셀별로 C2M distance 계산
            for y in range(height):
                for x in range(width):
                    current_temp = temp_matrix[y, x]
                    
                    # NaN 값 제외
                    if np.isnan(current_temp):
                        continue
                    
                    # C2M distance 계산
                    c2m_distance = self.calculate_c2m_distance(current_temp, baseline_line)
                    
                    # 기준라인과의 차이가 임계값 이상이면 누수발생 우려지역
                    if c2m_distance >= threshold_diff:
                        concern_area = {
                            'x': x,
                            'y': y,
                            'temperature': current_temp,
                            'c2m_distance': c2m_distance,
                            'baseline_line': baseline_line,
                            'temperature_diff': current_temp - baseline_line
                        }
                        concern_areas.append(concern_area)
            
            logger.info(f"시나리오3: 누수발생 우려지역 {len(concern_areas)}개 감지 (임계값: {threshold_diff}°C)")
            return concern_areas
            
        except Exception as e:
            logger.error(f"시나리오3: 누수발생 우려지역 감지 오류: {str(e)}")
            return []

    def scenario2_judge(self):
        """
        시나리오3: 1시간 평균온도 기반 정규분포 분석으로 누수발생 우려지역 감지
        - 1시간 평균온도 데이터 수집 (최근 24시간)
        - 정규분포 분석 및 기준라인 설정
        - C2M distance 계산 (Center to Margin)
        - 누수발생 우려지역 감지 (5℃ 이상 차이)
        """
        try:
            logger.info("시나리오3 판단 시작 (1시간 평균온도 기반 정규분포 분석)")
            
            # 강제 종료 체크
            if self.force_exit:
                logger.info("강제 종료 요청됨, 시나리오3 중단")
                return False
            
            # 1단계: 1시간 평균온도 데이터 수집 (최근 24시간)
            hourly_temps = self.collect_hourly_average_temperatures(hours=24)
            if not hourly_temps:
                logger.warning("시나리오3: 1시간 평균온도 데이터가 없습니다")
                return False
            
            # 2단계: 정규분포 분석 및 기준라인 설정
            distribution_info = self.analyze_normal_distribution(hourly_temps)
            if not distribution_info:
                logger.error("시나리오3: 정규분포 분석 실패")
                return False
            
            # 3단계: 현재 파노라마 데이터에서 온도 매트릭스 생성
            panorama_data_record = self.get_latest_temperature_data()
            if not panorama_data_record:
                logger.warning("시나리오3: 현재 파노라마 데이터가 없습니다")
                return False
            
            # 현재 스냅샷 데이터 ID를 인스턴스 변수로 저장
            self.current_snapshot_data_id = panorama_data_record['id']
            
            # 파노라마 데이터에서 온도 데이터 추출
            temperature_data = self.extract_panorama_temperature_data(panorama_data_record['panoramaData'])
            if not temperature_data:
                logger.error("시나리오3: 파노라마 온도 데이터 추출 실패")
                return False
            
            # 온도 매트릭스 생성 (1920x480 파노라마 크기)
            temp_matrix = self.create_temperature_matrix(temperature_data)
            if temp_matrix is None:
                logger.error("시나리오3: 온도 매트릭스 생성 실패")
                return False
            
            # 4단계: 누수발생 우려지역 감지 (C2M distance 기반)
            concern_areas = self.detect_leakage_concern_areas(temp_matrix, distribution_info, threshold_diff=5.0)
            
            # 5단계: 경보 생성
            alert_detected = False
            if concern_areas:
                logger.info(f"시나리오3: 누수발생 우려지역 {len(concern_areas)}개 감지")
                
                # 누수발생 우려지역별로 경보 생성
                for i, concern_area in enumerate(concern_areas):
                    # 경보 레벨 결정 (온도차에 따라)
                    temp_diff = abs(concern_area['temperature_diff'])
                    if temp_diff >= 10.0:
                        alert_level = 3  # 최고 레벨
                    elif temp_diff >= 7.5:
                        alert_level = 2  # 높은 레벨
                    elif temp_diff >= 5.0:
                        alert_level = 1  # 기본 레벨
                    else:
                        alert_level = 0  # 낮은 레벨
                    
                    # 경보 생성
                    self.create_scenario3_alert(concern_area, 'S003', temp_diff, alert_level, distribution_info)
                    alert_detected = True
                    
                    # 로그 출력 (처음 5개만)
                    if i < 5:
                        logger.info(f"누수발생 우려지역 {i+1}: 좌표=({concern_area['x']},{concern_area['y']}), "
                                  f"온도={concern_area['temperature']:.1f}°C, "
                                  f"C2M거리={concern_area['c2m_distance']:.1f}°C, "
                                  f"레벨={alert_level}")
            else:
                logger.info("시나리오3: 누수발생 우려지역이 감지되지 않았습니다")
            
            return alert_detected
            
        except Exception as e:
            logger.error(f"시나리오3 판단 오류: {str(e)}")
            logger.error(traceback.format_exc())
            return False

    def create_scenario3_alert(self, concern_area, alert_type, threshold_value, alert_level=1, distribution_info=None):
        """
        시나리오3 경보 생성 및 DB 저장 (누수발생 우려지역)
        """
        try:
            cursor = self.get_db_cursor()
            if not cursor:
                return False
            
            # 파노라마 데이터 조회 및 이미지 추출
            panorama_data_record = self.get_latest_temperature_data()
            panorama_snapshot = None
            if panorama_data_record:
                logger.info(f"파노라마 데이터 조회 성공: ID={panorama_data_record.get('id')}, 생성일={panorama_data_record.get('create_date')}")
                panorama_snapshot = self.extract_panorama_image(panorama_data_record['panoramaData'])
                if panorama_snapshot:
                    logger.info("파노라마 이미지 추출 성공")
                else:
                    logger.warning("파노라마 이미지 추출 실패")
            else:
                logger.warning("파노라마 데이터 조회 실패 - 데이터가 없습니다")
            
            # 스트림 스냅샷 이미지 캡처
            stream_snapshots = self.capture_video_snapshots()
            
            # 모든 스냅샷 이미지 통합
            snapshot_images = []
            
            # 파노라마 이미지 추가
            if panorama_snapshot:
                snapshot_images.append(panorama_snapshot)
                logger.info("파노라마 이미지가 snapshot_images에 추가됨")
            else:
                logger.warning("파노라마 이미지가 없어 snapshot_images에 추가되지 않음")
            
            # 스트림 캡처 이미지들 추가
            if stream_snapshots:
                snapshot_images.extend(stream_snapshots)
                logger.info(f"{len(stream_snapshots)}개의 스트림 이미지가 snapshot_images에 추가됨")
            else:
                logger.warning("스트림 이미지가 없음")
            
            logger.info(f"총 {len(snapshot_images)}개의 스냅샷 이미지 준비 완료 (파노라마: {1 if panorama_snapshot else 0}개, 스트림: {len(stream_snapshots)}개)")
            
            # 디버깅: snapshot_images 내용 확인
            for i, img in enumerate(snapshot_images):
                img_type = img.get('image_type', 'stream')
                logger.info(f"스냅샷 {i+1}: 타입={img_type}, 파일명={img.get('filename', 'N/A')}")
            
            # 누수발생 우려지역 정보 구성
            concern_info = {
                'scenario': 'scenario3',
                'alert_type': alert_type,
                'threshold_value': threshold_value,
                'alert_level': alert_level,
                'concern_area': {
                    'x': concern_area['x'],
                    'y': concern_area['y'],
                    'temperature': concern_area['temperature'],
                    'c2m_distance': concern_area['c2m_distance'],
                    'baseline_line': concern_area['baseline_line'],
                    'temperature_diff': concern_area['temperature_diff']
                },
                'distribution_info': distribution_info,
                'detection_time': datetime.now().isoformat(),
                'leakage_detection': True
            }
            
            # DB에 경보 저장
            query = """
                INSERT INTO tb_alert_history 
                (fk_camera_id, alert_accur_time, alert_type, alert_level, 
                alert_status, alert_info_json, fk_detect_zone_id, 
                fk_process_user_id, create_date, update_date, fk_video_receive_data_id, snapshotImages)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            now = datetime.now()
            values = (
                1,  # fk_camera_id
                now,  # alert_accur_time
                alert_type,  # alert_type
                alert_level,  # alert_level (0~3)
                'P001',  # alert_status
                json.dumps(concern_info, ensure_ascii=False),  # alert_info_json
                0,  # fk_detect_zone_id (시나리오3는 전체 영역 분석)
                0,  # fk_process_user_id
                now,  # create_date
                now,  # update_date
                self.current_snapshot_data_id,  # fk_video_receive_data_id
                json.dumps(snapshot_images, ensure_ascii=False) if snapshot_images else None  # snapshotImages
            )
            
            cursor.execute(query, values)
            logger.info(f"시나리오3 경보 생성 완료: 좌표=({concern_area['x']},{concern_area['y']}), "
                       f"온도={concern_area['temperature']:.1f}°C, C2M거리={concern_area['c2m_distance']:.1f}°C, "
                       f"레벨={alert_level}")
            
            return True
            
        except Exception as e:
            logger.error(f"시나리오3 경보 생성 오류: {str(e)}")
            return False
        finally:
            if cursor:
                cursor.close()


    def run(self):
        logger.info("VideoAlertChecker 시작...")
        
        # 프로그램 시작 시 초기 데이터 로드
        try:
            logger.info("초기 설정 및 데이터 로드 중...")
            self.get_alert_settings()
            self.get_zone_list()
            self.get_camera_info_list()
            logger.info("초기 데이터 로드 완료")
        except Exception as e:
            logger.error(f"초기 데이터 로드 오류: {str(e)}")
        
        try:
            while self.running:
                try:
                    # 강제 종료 체크 (매 루프마다 확인)
                    if self.force_exit:
                        logger.info("강제 종료 요청됨, 즉시 종료")
                        break
                    
                    current_time = time.time()
                    
                    # 설정 및 zone 정보 주기적 업데이트
                    if current_time - self.last_settings_check >= self.settings_check_interval:
                        # 강제 종료 체크
                        if self.force_exit:
                            logger.info("강제 종료 요청됨, 즉시 종료")
                            break
                            
                        self.get_alert_settings()
                        self.get_zone_list()
                        self.get_camera_info_list()
                        self.last_settings_check = current_time

                    # 강제 종료 체크
                    if self.force_exit:
                        logger.info("강제 종료 요청됨, 즉시 종료")
                        break
                    
                    # 시나리오1과 시나리오2 실행
                    self.scenario1_judge()
                    self.scenario2_judge()
                   
                    # 강제 종료 체크
                    if self.force_exit:
                        logger.info("강제 종료 요청됨, 즉시 종료")
                        break
                        
                    time.sleep(self.data_check_interval)

                except Exception as e:
                    logger.error(f"메인 루프 오류: {str(e)}")
                    logger.error(traceback.format_exc())
                    # 오류 발생 시에도 강제 종료 체크
                    if self.force_exit:
                        logger.info("강제 종료 요청됨, 즉시 종료")
                        break
                    time.sleep(5)

        except Exception as e:
            logger.error(f"치명적 오류: {str(e)}")
            logger.error(traceback.format_exc())
        finally:
            # 강제 종료가 아닌 경우에만 cleanup 실행
            if not self.force_exit:
                self.cleanup()
                logger.info("VideoAlertChecker 정상 종료됨")
            else:
                logger.info("VideoAlertChecker 강제 종료됨")

if __name__ == "__main__":
    try:
        # 명령행 인자 파싱
        parser = argparse.ArgumentParser(description='Video Alert Checker')
        parser.add_argument('--debug', action='store_true', help='Enable debug mode with UI')
        args = parser.parse_args()
        
        alertChecker = VideoAlertChecker(debug_mode=args.debug)
        alertChecker.run()

    except KeyboardInterrupt:
        logger.info("키보드 인터럽트 수신, 즉시 종료...")
        # 즉시 종료
        os._exit(0)
    except Exception as e:
        logger.error(f"메인 오류: {str(e)}")
        logger.error(traceback.format_exc())
    finally:
        logger.info("프로그램 종료됨")

