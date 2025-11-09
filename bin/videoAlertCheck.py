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
import re
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
import paramiko

# 컬러바 분석 모듈 import (logger 정의 후에 경고 메시지 출력)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'temp_extractor', 'temp_extractor'))
try:
    from colorbar_analyzer import get_temperature_from_color_with_map
    COLORBAR_ANALYZER_AVAILABLE = True
except ImportError:
    COLORBAR_ANALYZER_AVAILABLE = False

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

### MSDB 연결정보 (tic_data INSERT용) ####
MSDB_IP = config.get('MSDB', 'ip')
MSDB_PORT = config.getint('MSDB', 'port')
MSDB_USER = config.get('MSDB', 'user')
MSDB_PASSWORD = config.get('MSDB', 'password')
MSDB_DB = config.get('MSDB', 'dbname')
MSDB_DAMNAME = config.get('MSDB', 'damname', fallback='')
MSDB_CODE = config.get('MSDB', 'code', fallback='1001210')
msdb_conn = None
########################

### SFTP 설정 (파일 업로드용) ####
SFTP_IP = config.get('SFTP', 'ip')
SFTP_PORT = config.getint('SFTP', 'port')
SFTP_USER = config.get('SFTP', 'user')
SFTP_PASSWORD = config.get('SFTP', 'password')
SFTP_ROOT_PATH = config.get('SFTP', 'root_path', fallback='ftp_data')
SFTP_CODE = config.get('SFTP', 'code', fallback='1001210')
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

# colorbar_analyzer 모듈을 찾을 수 없는 경우 경고 메시지 출력
if not COLORBAR_ANALYZER_AVAILABLE:
    logger.warning("colorbar_analyzer 모듈을 찾을 수 없습니다. 밝기 기반 온도 계산을 사용합니다.")

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
        self.data_check_interval = 600  # 1 hour (3600 seconds)
        self.running = True
        self.force_exit = False  # 강제 종료 플래그
        self.uploaded_panorama_filename = None  # SFTP 업로드된 파일명
        self.uploaded_panorama_snapshot = None  # SFTP 업로드된 파노라마 스냅샷
        
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

    def disconnect_msdb(self):
        """MSDB 연결 종료"""
        global msdb_conn
        try:
            if msdb_conn:
                msdb_conn.close()
                msdb_conn = None
                logger.info("MSDB disconnected")
        except Exception as e:
            logger.error(f'Error disconnecting MSDB: {str(e)}')

    def cleanup(self):
        """프로그램 종료 시 정리 작업"""
        try:
            logger.info("Performing cleanup...")
            self.disconnect_db()
            self.disconnect_msdb()
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

    def connect_to_msdb(self):
        """MSDB에 연결 (tic_data INSERT용)"""
        global msdb_conn
        try:
            if msdb_conn is not None:
                try:
                    cursor = msdb_conn.cursor()
                    cursor.execute('SELECT 1')
                    cursor.close()
                    return True
                except Exception as e:
                    logger.error(f"MSDB connection check failed: {str(e)}")
                    msdb_conn = None
            
            msdb_conn = pymysql.connect(
                host=MSDB_IP,
                port=MSDB_PORT,
                user=MSDB_USER,
                password=MSDB_PASSWORD,
                db=MSDB_DB,
                charset='utf8mb4',
                autocommit=True,
                cursorclass=pymysql.cursors.DictCursor,
                connect_timeout=5
            )
            logger.info("MSDB connected successfully")
            return True
        except Exception as e:
            logger.error(f'MSDB connection failed: {str(e)}')
            logger.error(f'Connection params: host={MSDB_IP}, port={MSDB_PORT}, user={MSDB_USER}, db={MSDB_DB}')
            msdb_conn = None
            return False

    def insert_tic_data(self, max_temp, min_temp, avg_temp, alert_level, file_path, file_name):
        """MSDB의 tic_data 테이블에 데이터 INSERT"""
        try:
            if not self.connect_to_msdb():
                logger.error("MSDB 연결 실패 - tic_data INSERT 건너뜀")
                return False

            cursor = msdb_conn.cursor(pymysql.cursors.DictCursor)
            
            # 현재 시간
            now = datetime.now()
            
            # Decimal 타입을 float로 변환
            from decimal import Decimal
            def convert_decimal(value):
                if value is None:
                    return None
                if isinstance(value, Decimal):
                    return float(value)
                if isinstance(value, (int, float)):
                    return float(value)
                return value
            
            max_temp_float = convert_decimal(max_temp)
            min_temp_float = convert_decimal(min_temp)
            avg_temp_float = convert_decimal(avg_temp)
            
            # INSERT 쿼리 (ON DUPLICATE KEY UPDATE로 중복 방지)
            query = """
                INSERT INTO tic_data 
                (DAMNAME, DAMCD, DATE_TIME, MAX_TEMP, MIN_TEMP, AVG_TEMP, ALERT_NUM, FILE_PATH, FILE_NAME, NUM_IMAGES)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                MAX_TEMP = VALUES(MAX_TEMP),
                MIN_TEMP = VALUES(MIN_TEMP),
                AVG_TEMP = VALUES(AVG_TEMP),
                ALERT_NUM = VALUES(ALERT_NUM),
                FILE_PATH = VALUES(FILE_PATH),
                FILE_NAME = VALUES(FILE_NAME),
                NUM_IMAGES = VALUES(NUM_IMAGES)
            """
            
            values = (
                MSDB_DAMNAME,  # DAMNAME
                int(MSDB_CODE),  # DAMCD
                now,  # DATE_TIME
                max_temp_float,  # MAX_TEMP
                min_temp_float,  # MIN_TEMP
                avg_temp_float,  # AVG_TEMP
                int(alert_level),  # ALERT_NUM
                file_path,  # FILE_PATH
                file_name,  # FILE_NAME
                3  # NUM_IMAGES (고정값)
            )
            
            cursor.execute(query, values)
            cursor.close()
            # logger.info(f"tic_data INSERT 성공: DAMCD={MSDB_CODE}, ALERT_NUM={alert_level}, FILE_NAME={file_name}")
            return True
            
        except Exception as e:
            logger.error(f"tic_data INSERT 오류: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    def create_sftp_connection(self):
        """SFTP 서버 연결"""
        try:
            logger.info(f"SFTP 서버 연결 시도: {SFTP_USER}@{SFTP_IP}:{SFTP_PORT}")
            
            # SSH 클라이언트 생성
            ssh_client = paramiko.SSHClient()
            ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # SSH 연결
            ssh_client.connect(
                hostname=SFTP_IP,
                port=SFTP_PORT,
                username=SFTP_USER,
                password=SFTP_PASSWORD,
                timeout=10
            )
            
            # SFTP 클라이언트 생성
            sftp_client = ssh_client.open_sftp()
            
            # logger.info("SFTP 서버 연결 성공")
            return ssh_client, sftp_client
            
        except Exception as e:
            logger.error(f"SFTP 서버 연결 실패: {e}")
            return None, None

    def close_sftp_connection(self, ssh_client, sftp_client):
        """SFTP 연결 종료"""
        try:
            if sftp_client:
                sftp_client.close()
            if ssh_client:
                ssh_client.close()
            # logger.info("SFTP 연결 종료 완료")
        except Exception as e:
            logger.warning(f"SFTP 연결 종료 중 오류: {e}")

    def create_remote_directory_tree(self, sftp_client, root_path, year, month, day):
        """원격 서버에 년/월/일 폴더 구조 생성"""
        try:
            logger.info(f"폴더 구조 생성 시작: {root_path}")
            
            # 년/월/일 폴더 경로 생성
            year_path = f"{root_path}/{year}"
            month_path = f"{year_path}/{month:02d}"
            day_path = f"{month_path}/{day:02d}"
            
            # 각 폴더를 순차적으로 생성
            paths_to_create = [year_path, month_path, day_path]
            
            for path in paths_to_create:
                try:
                    sftp_client.stat(path)
                    logger.debug(f"폴더 이미 존재: {path}")
                except FileNotFoundError:
                    try:
                        sftp_client.mkdir(path)
                        logger.info(f"폴더 생성 완료: {path}")
                    except Exception as mkdir_error:
                        if "Failure" in str(mkdir_error) or "already exists" in str(mkdir_error).lower():
                            logger.debug(f"폴더가 이미 존재함: {path}")
                        else:
                            logger.error(f"폴더 생성 실패 {path}: {mkdir_error}")
                            return None
            
            return day_path
            
        except Exception as e:
            logger.error(f"원격 폴더 생성 실패: {e}")
            return None

    def upload_image_to_sftp(self, image_base64, filename):
        """이미지를 SFTP 서버에 업로드 (파일명: YYYYMMDDHHmmss_코드.jpg)"""
        try:
            # SFTP 연결
            ssh_client, sftp_client = self.create_sftp_connection()
            if not sftp_client:
                logger.error("SFTP 연결 실패")
                return None
            
            try:
                # root_path 처리
                root_path = SFTP_ROOT_PATH
                
                # 홈 디렉토리 기반 경로 처리
                if root_path.startswith('~/'):
                    relative_path = root_path[2:]  # ~/ 제거
                    possible_home_dirs = [
                        f"/home/{SFTP_USER}",
                        f"/home/akj",
                        "/home",
                        "/tmp"
                    ]
                    
                    home_dir = None
                    for possible_home in possible_home_dirs:
                        try:
                            sftp_client.stat(possible_home)
                            home_dir = possible_home
                            logger.info(f"홈 디렉토리 확인: {home_dir}")
                            break
                        except:
                            continue
                    
                    if home_dir:
                        root_path = f"{home_dir}/{relative_path}"
                    else:
                        root_path = relative_path
                
                # root_path 폴더 확인 및 생성
                try:
                    sftp_client.stat(root_path)
                except FileNotFoundError:
                    try:
                        sftp_client.mkdir(root_path)
                        logger.info(f"폴더 생성 완료: {root_path}")
                    except Exception as e:
                        logger.error(f"폴더 생성 실패: {e}")
                        return None
                
                # root_path에 직접 파일 업로드 (날짜 폴더 생성 없이)
                remote_file_path = f"{root_path}/{filename}"
                
                # Base64 이미지를 바이너리로 변환
                image_data = base64.b64decode(image_base64)
                
                # 임시 파일에 저장
                with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
                    temp_file.write(image_data)
                    temp_file_path = temp_file.name
                
                try:
                    # SFTP로 파일 업로드
                    sftp_client.put(temp_file_path, remote_file_path)
                    logger.info(f"이미지 SFTP 업로드 완료: {remote_file_path}")
                    
                    # 업로드된 파일 크기 확인
                    remote_file_stat = sftp_client.stat(remote_file_path)
                    logger.info(f"업로드된 파일 크기: {remote_file_stat.st_size} bytes")
                    
                    return filename
                    
                finally:
                    # 임시 파일 삭제
                    try:
                        os.unlink(temp_file_path)
                    except Exception as e:
                        logger.warning(f"임시 파일 삭제 실패: {e}")
            
            finally:
                # SFTP 연결 종료
                self.close_sftp_connection(ssh_client, sftp_client)
                
        except Exception as e:
            logger.error(f"SFTP 업로드 실패: {e}")
            import traceback
            logger.error(traceback.format_exc())
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
            
            logger.info(f"DB에서 조회된 ROI 레코드 수: {len(results)}개")
            for idx, row in enumerate(results):
                logger.info(f"  [{idx+1}] zone_type: {row['zone_type']}, zone_segment_json 길이: {len(row['zone_segment_json']) if row['zone_segment_json'] else 0}")
            
            zone_segments = []
            for row in results:
                if row['zone_segment_json']:
                    try:
                        # JSON 파싱하여 zone_segment_json 내용을 리스트로 변환
                        segment_data = json.loads(row['zone_segment_json'])
                        zone_type = row['zone_type']
                        
                        # DB에서 zone_type은 숫자로 저장되어 있음
                        # 숫자 타입 확인 및 로깅
                        if isinstance(zone_type, (int, float)):
                            zone_type = int(zone_type)  # 정수로 변환
                        elif isinstance(zone_type, str) and zone_type.isdigit():
                            zone_type = int(zone_type)  # 숫자 문자열을 정수로 변환
                        
                        # logger.info(f"zone_type={zone_type} (타입: {type(zone_type).__name__})의 segment_data 타입: {type(segment_data)}")
                        # if isinstance(segment_data, (list, dict)):
                        #     logger.info(f"zone_type={zone_type}의 segment_data 내용 (처음 200자): {str(segment_data)[:200]}")
                        
                        if isinstance(segment_data, list):
                            # 리스트인 경우 각 항목에 zone_type 추가하고 좌표 변환
                            # logger.info(f"zone_type={zone_type}: 리스트로 {len(segment_data)}개 항목 발견")
                            for idx, segment in enumerate(segment_data):
                                if isinstance(segment, dict):
                                    segment['zone_type'] = zone_type
                                    # start_point_x/y, end_point_x/y 형식을 left/top/right/bottom으로 변환
                                    segment = self._convert_roi_coordinates(segment)
                                    # logger.info(f"zone_type={zone_type}: [{idx+1}] ROI 추가 - left={segment.get('left')}, top={segment.get('top')}, right={segment.get('right')}, bottom={segment.get('bottom')}")
                                zone_segments.append(segment)
                        elif isinstance(segment_data, dict):
                            # 딕셔너리인 경우 zone_type 추가하고 좌표 변환
                            segment_data['zone_type'] = zone_type
                            segment_data = self._convert_roi_coordinates(segment_data)
                            # logger.info(f"zone_type={zone_type}: 단일 딕셔너리 ROI 추가 - left={segment_data.get('left')}, top={segment_data.get('top')}, right={segment_data.get('right')}, bottom={segment_data.get('bottom')}")
                            zone_segments.append(segment_data)
                        else:
                            # 기타 타입인 경우 zone_type과 함께 딕셔너리로 변환
                            logger.warning(f"zone_type={zone_type}: 알 수 없는 타입의 segment_data - {type(segment_data)}")
                            zone_segments.append({
                                'data': segment_data,
                                'zone_type': zone_type
                            })
                    except json.JSONDecodeError as e:
                        logger.error(f"zone_segment_json 파싱 오류: {str(e)}, data: {row['zone_segment_json']}")
                        continue
            
            self.zone_list = zone_segments
            # logger.info(f"Zone segments 조회 완료: 총 {len(zone_segments)}개 ROI")
            # for idx, seg in enumerate(zone_segments):
            #     logger.info(f"  [{idx+1}] zone_type={seg.get('zone_type', 'unknown')}, left={seg.get('left', 'N/A')}, top={seg.get('top', 'N/A')}, right={seg.get('right', 'N/A')}, bottom={seg.get('bottom', 'N/A')}")
            return zone_segments

        except Exception as e:
            logger.error(f"Zone list 조회 오류: {str(e)}")
            return []
        finally:
            if cursor:
                cursor.close()

    def _convert_roi_coordinates(self, segment):
        """
        ROI 좌표를 표준 형식(left, top, right, bottom)으로 변환
        start_point_x/y, end_point_x/y 형식을 지원
        """
        try:
            if not isinstance(segment, dict):
                return segment
            
            # 이미 left, top, right, bottom 형식이 있으면 좌표를 검증하고 반환
            if all(key in segment for key in ['left', 'top', 'right', 'bottom']):
                left = int(segment['left'])
                top = int(segment['top'])
                right = int(segment['right'])
                bottom = int(segment['bottom'])
                
                # 좌표 검증: left < right, top < bottom
                if left >= right or top >= bottom:
                    logger.warning(f"ROI 좌표 검증 실패: left={left} >= right={right} 또는 top={top} >= bottom={bottom}, 원본 segment: {segment}")
                    # 좌표를 교정 (더 작은 값을 left/top으로, 더 큰 값을 right/bottom으로)
                    if left >= right:
                        left, right = min(left, right), max(left, right)
                    if top >= bottom:
                        top, bottom = min(top, bottom), max(top, bottom)
                    segment['left'] = left
                    segment['top'] = top
                    segment['right'] = right
                    segment['bottom'] = bottom
                    logger.info(f"ROI 좌표 교정: left={left}, top={top}, right={right}, bottom={bottom}")
                
                logger.info(f"ROI 좌표 확인: left={left}, top={top}, right={right}, bottom={bottom} (width={right-left}, height={bottom-top})")
                return segment
            
            # start_point_x/y, end_point_x/y 형식인 경우 변환
            if all(key in segment for key in ['start_point_x', 'start_point_y', 'end_point_x', 'end_point_y']):
                start_x = int(segment['start_point_x'])
                start_y = int(segment['start_point_y'])
                end_x = int(segment['end_point_x'])
                end_y = int(segment['end_point_y'])
                
                # left는 작은 x 값, right는 큰 x 값
                # top은 작은 y 값, bottom은 큰 y 값
                left = min(start_x, end_x)
                right = max(start_x, end_x)
                top = min(start_y, end_y)
                bottom = max(start_y, end_y)
                
                segment['left'] = left
                segment['top'] = top
                segment['right'] = right
                segment['bottom'] = bottom
                
                logger.info(f"ROI 좌표 변환: start_point({start_x}, {start_y}), end_point({end_x}, {end_y}) -> left={left}, top={top}, right={right}, bottom={bottom}")
                
                return segment
            
            # 좌표 정보가 없는 경우
            logger.warning(f"ROI 좌표 정보가 없습니다: {segment}")
            return segment
            
        except Exception as e:
            logger.error(f"ROI 좌표 변환 오류: {str(e)}, segment: {segment}")
            return segment

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
        온도 데이터를 CSV 파일로 저장 (주석처리)
        """
        # try:
        #     if not temperature_data:
        #         logger.warning("저장할 온도 데이터가 없습니다")
        #         return
        #     
        #     # 현재 시간을 파일명에 포함
        #     timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        #     csv_filename = f"temperature_data_{timestamp}.csv"
        #     
        #     # CSV 파일 경로 설정 (bin 디렉토리 내)
        #     csv_path = os.path.join(os.path.dirname(__file__), csv_filename)
        #     
        #     # CSV 파일 생성
        #     with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
        #         # CSV 헤더 작성
        #         fieldnames = ['x', 'y', 'temperature']
        #         writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        #         writer.writeheader()
        #         
        #         # 온도 데이터 작성
        #         for pixel_data in temperature_data:
        #             writer.writerow({
        #                 'x': pixel_data.get('x', 0),
        #                 'y': pixel_data.get('y', 0),
        #                 'temperature': pixel_data.get('temperature', 0.0)
        #             })
        #     
        #     logger.info(f"온도 데이터 CSV 파일 저장 완료: {csv_path}")
        #     print(f"온도 데이터 CSV 파일 저장 완료: {csv_path}")
        #     
        # except Exception as e:
        #     logger.error(f"온도 데이터 CSV 파일 저장 오류: {str(e)}")
        #     print(f"온도 데이터 CSV 파일 저장 오류: {str(e)}")
        pass

    def create_temperature_matrix(self, panorama_data_json, width=1920, height=480):
        """
        panorama_data_json의 colorbarMapping을 사용하여 온도 매트릭스 생성
        파노라마 이미지 크기에 맞게 1920x480으로 변경
        """
        try:
            if not panorama_data_json:
                return None
            
            # panoramaData JSON 파싱
            try:
                if isinstance(panorama_data_json, str):
                    # JSON 문자열 길이 확인
                    json_length = len(panorama_data_json)
                    logger.info(f"panorama_data_json 길이: {json_length} 문자")
                    
                    # JSON 파싱 시도
                    panorama_data = json.loads(panorama_data_json)
                else:
                    panorama_data = panorama_data_json
            except json.JSONDecodeError as e:
                logger.error(f"JSON 파싱 오류: {str(e)}")
                logger.error(f"JSON 데이터 길이: {len(panorama_data_json) if isinstance(panorama_data_json, str) else 'N/A'}")
                # JSON 데이터의 일부를 로그로 출력 (처음 200자)
                if isinstance(panorama_data_json, str):
                    logger.error(f"JSON 데이터 시작 부분: {panorama_data_json[:200]}")
                return None
            except Exception as e:
                logger.error(f"panorama_data_json 파싱 오류: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
                return None
           
            # temperatures 추출 (온도 데이터)
            temperatures = panorama_data.get('temperatures')
            temperatures_compressed = panorama_data.get('temperatures_compressed', False)
            
            if not temperatures:
                # panoramaData의 모든 키 나열
                panorama_keys = list(panorama_data.keys())
                logger.warning(f"temperatures가 없습니다. panoramaData 키 목록: {panorama_keys}")
                return None
            
            # temperatures가 압축되어 있으면 압축 해제
            if temperatures_compressed and isinstance(temperatures, str):
                try:
                    # base64 디코딩
                    zip_data = base64.b64decode(temperatures)
                    
                    # zip 압축 해제
                    with zipfile.ZipFile(io.BytesIO(zip_data), 'r') as zip_file:
                        if 'temperatures.json' in zip_file.namelist():
                            temperatures_json = zip_file.read('temperatures.json').decode('utf-8')
                            temperatures = json.loads(temperatures_json)
                            # logger.info(f"temperatures 압축 해제 완료: {len(temperatures)}개 데이터")
                        else:
                            logger.error("zip 파일에 temperatures.json이 없습니다")
                            return None
                except Exception as e:
                    logger.error(f"temperatures 압축 해제 실패: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
                    return None
            
            # logger.info(f"temperatures 로드 완료: {type(temperatures)}, 길이: {len(temperatures) if isinstance(temperatures, (list, dict)) else 'N/A'}")
            
            # temperatures 크기 확인 (1920x480 = 921,600개)
            expected_count = width * height  # 1920 * 480 = 921,600
            if isinstance(temperatures, list):
                actual_count = len(temperatures)
                if actual_count != expected_count:
                    logger.warning(f"temperatures 크기 불일치: 예상={expected_count}개 (1920x480), 실제={actual_count}개")
                else:
                    logger.info(f"temperatures 크기 확인: {actual_count}개 (1920x480 = {expected_count}개)")
            elif isinstance(temperatures, dict):
                actual_count = len(temperatures)
                logger.warning(f"temperatures가 딕셔너리 형태입니다. 크기: {actual_count}개")
            else:
                logger.warning(f"temperatures가 리스트나 딕셔너리가 아닙니다: {type(temperatures)}")
            
            # temperatures 파일 저장 (주석처리)
            # try:
            #     timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            #     temperatures_file_path = os.path.join(os.path.dirname(__file__), f"temperatures_{timestamp}.json")
            #     
            #     with open(temperatures_file_path, 'w', encoding='utf-8') as f:
            #         json.dump(temperatures, f, ensure_ascii=False, indent=2)
            #     
            #     logger.info(f"temperatures 파일 저장 완료: {temperatures_file_path}")
            # except Exception as e:
            #     logger.error(f"temperatures 파일 저장 실패: {e}")
            #     import traceback
            #     logger.error(traceback.format_exc())
            
            # temperatures를 2D 매트릭스로 변환
            # 2D 매트릭스 초기화 (1920x480 - 파노라마 크기)
            temp_matrix = np.full((height, width), np.nan, dtype=np.float64)
            
            # temperatures 형태에 따라 처리
            if isinstance(temperatures, list):
                if len(temperatures) > 0:
                    # 첫 번째 요소의 형태 확인
                    first_item = temperatures[0]
                    
                    if isinstance(first_item, dict):
                        # 딕셔너리 리스트 형태: [{'x': x, 'y': y, 'temperature': temp}, ...]
                        for item in temperatures:
                            x = item.get('x', 0)
                            y = item.get('y', 0)
                            temp = item.get('temperature', np.nan)
                            
                            if 0 <= x < width and 0 <= y < height:
                                temp_matrix[y, x] = temp
                        logger.info(f"온도 매트릭스 생성 완료: {width}x{height} (딕셔너리 리스트 형태, {len(temperatures)}개 데이터)")
                    elif isinstance(first_item, list):
                        # 2D 리스트 형태: [[temp, temp, ...], [temp, temp, ...], ...]
                        for y, row in enumerate(temperatures):
                            if y < height:
                                for x, temp in enumerate(row):
                                    if x < width:
                                        temp_matrix[y, x] = temp
                        logger.info(f"온도 매트릭스 생성 완료: {width}x{height} (2D 리스트 형태, {len(temperatures)}x{len(temperatures[0]) if temperatures else 0})")
                    else:
                        # 1D 리스트 형태: [temp, temp, ...] (플랫한 형태)
                        # 이미지 크기로 변환 (가정: row-major 순서)
                        for idx, temp in enumerate(temperatures):
                            y = idx // width
                            x = idx % width
                            if y < height and x < width:
                                temp_matrix[y, x] = temp
                        logger.info(f"온도 매트릭스 생성 완료: {width}x{height} (1D 리스트 형태, {len(temperatures)}개 데이터)")
                else:
                    logger.warning("temperatures 리스트가 비어있습니다")
                    return None
            elif isinstance(temperatures, dict):
                # 딕셔너리 형태: {'x_y': temp, ...} 또는 다른 형태
                logger.warning(f"temperatures가 딕셔너리 형태입니다. 지원하지 않는 형식입니다. 키: {list(temperatures.keys())[:5]}")
                return None
            else:
                logger.warning(f"temperatures가 지원하지 않는 형태입니다: {type(temperatures)}")
                return None
            
            # 생성된 온도 매트릭스 크기 확인 (1920x480)
            actual_height, actual_width = temp_matrix.shape
            if actual_width != width or actual_height != height:
                logger.warning(f"생성된 온도 매트릭스 크기 불일치: 예상={width}x{height}, 실제={actual_width}x{actual_height}")
            else:
                logger.info(f"생성된 온도 매트릭스 크기 확인: {actual_width}x{actual_height} (1920x480)")
            
            return temp_matrix
            
        except Exception as e:
            logger.error(f"온도 매트릭스 생성 오류: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return None

    def save_temperature_matrix_to_csv(self, temp_matrix, width, height):
        """
        온도 매트릭스를 CSV 파일로 저장 (2D 그리드 형태) (주석처리)
        """
        # try:
        #     if temp_matrix is None:
        #         logger.warning("저장할 온도 매트릭스가 없습니다")
        #         return
        #     
        #     # 온도 매트릭스 크기 확인 (1920x480)
        #     expected_width = 1920
        #     expected_height = 480
        #     actual_height, actual_width = temp_matrix.shape
        #     
        #     if actual_width != expected_width or actual_height != expected_height:
        #         logger.warning(f"CSV 저장 전 온도 매트릭스 크기 불일치: 예상={expected_width}x{expected_height}, 실제={actual_width}x{actual_height}")
        #     else:
        #         logger.info(f"CSV 저장 전 온도 매트릭스 크기 확인: {actual_width}x{actual_height} (1920x480)")
        #     
        #     # 현재 시간을 파일명에 포함
        #     timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        #     csv_filename = f"temperature_matrix_{timestamp}.csv"
        #     
        #     # CSV 파일 경로 설정 (bin 디렉토리 내)
        #     csv_path = os.path.join(os.path.dirname(__file__), csv_filename)
        #     
        #     # CSV 파일 생성 (1920x480 크기로 저장)
        #     with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
        #         # CSV 헤더 작성 (x 좌표)
        #         header = ['y\\x'] + [str(i) for i in range(width)]
        #         writer = csv.writer(csvfile)
        #         writer.writerow(header)
        #         
        #         # 온도 매트릭스 데이터 작성 (height x width 크기)
        #         for y in range(height):
        #             row = [str(y)]  # y 좌표
        #             for x in range(width):
        #                 temp_value = temp_matrix[y, x]
        #                 if np.isnan(temp_value):
        #                     row.append('NaN')
        #                 else:
        #                     row.append(f"{temp_value:.2f}")
        #             writer.writerow(row)
        #     
        #     logger.info(f"온도 매트릭스 CSV 파일 저장 완료: {csv_path} (크기: {width}x{height})")
        #     print(f"온도 매트릭스 CSV 파일 저장 완료: {csv_path} (크기: {width}x{height})")
        #     
        # except Exception as e:
        #     logger.error(f"온도 매트릭스 CSV 파일 저장 오류: {str(e)}")
        #     print(f"온도 매트릭스 CSV 파일 저장 오류: {str(e)}")
        pass

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
                    left = int(zone_info['left'])
                    right = int(zone_info['right'])
                    top = int(zone_info['top'])
                    bottom = int(zone_info['bottom'])
                    
                    # 좌표 검증
                    if left >= right or top >= bottom:
                        logger.warning(f"extract_roi_temperature_data: 좌표 검증 실패 - left={left} >= right={right} 또는 top={top} >= bottom={bottom}")
                        if left >= right:
                            left, right = min(left, right), max(left, right)
                        if top >= bottom:
                            top, bottom = min(top, bottom), max(top, bottom)
                    
                    width = right - left
                    height = bottom - top
                    rect = [left, top, width, height]
                    logger.info(f"extract_roi_temperature_data: 좌표 변환 - left={left}, top={top}, right={right}, bottom={bottom} -> rect=[{left}, {top}, {width}, {height}]")
                    logger.info(f"extract_roi_temperature_data: 실제 영역 - x: {left}~{right} ({width}px), y: {top}~{bottom} ({height}px)")
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

    def insert_roi_temperature_data(self, roi_data, zone_info):
        """
        ROI 온도 측정 결과를 tb_video_receive_data 테이블에 INSERT
        data_value는 JSON 형태로 최대온도, 최소온도, 평균온도가 포함됨
        roiNumber는 별도 컬럼에 저장
        """
        cursor = None
        try:
            if not roi_data or not zone_info:
                logger.warning("ROI 온도 데이터 또는 zone_info가 없어 DB 삽입을 건너뜁니다")
                return False
            
            # ROI 번호 추출 (zone_type)
            zone_type = zone_info.get('zone_type', 'unknown')
            
            # zone_type에서 ROI 번호 추출 ("Z1" -> 1, "Z001" -> 1, "1" -> 1)
            # zone_type의 숫자를 그대로 roiNumber로 사용
            roi_number = None
            if isinstance(zone_type, str):
                # "Z1", "Z001", "Z01" 등의 형식 처리
                match = re.match(r'Z?0*(\d+)', zone_type)
                if match:
                    try:
                        roi_number = int(match.group(1))  # Z1 -> 1, Z2 -> 2, ...
                    except ValueError:
                        logger.warning(f"zone_type에서 ROI 번호 추출 실패: {zone_type}")
                else:
                    # 숫자만 있는 경우
                    try:
                        roi_number = int(zone_type)  # 1 -> 1, 2 -> 2, ...
                    except ValueError:
                        logger.warning(f"zone_type에서 ROI 번호 추출 실패: {zone_type}")
            elif isinstance(zone_type, int):
                roi_number = zone_type  # 1 -> 1, 2 -> 2, ...
            
            if roi_number is None or roi_number < 0:
                logger.warning(f"ROI 번호를 추출할 수 없습니다. zone_type: {zone_type}, roi_number: {roi_number}")
                return False
            
            # 온도 데이터 추출 및 소수점 1자리로 반올림
            max_temp = round(roi_data.get('max_temp', 0.0), 1)
            min_temp = round(roi_data.get('min_temp', 0.0), 1)
            avg_temp = round(roi_data.get('avg_temp', 0.0), 1)
            
            # JSON 형태로 data_value 생성 (roi_number는 제외하고 별도 컬럼에 저장)
            data_value = {
                'max_temp': max_temp,
                'min_temp': min_temp,
                'avg_temp': avg_temp
            }
            
            # DB 커서 획득
            cursor = self.get_db_cursor()
            if not cursor:
                logger.error("DB 커서 획득 실패")
                return False
            
            # 현재 시간
            create_date = datetime.now()
            
            # INSERT 쿼리 실행 (roiNumber 컬럼 추가)
            sql = """
                INSERT INTO tb_video_receive_data (fk_camera_id, create_date, roiNumber, data_value)
                VALUES (%s, %s, %s, %s)
            """
            
            cursor.execute(sql, (
                1,  # fk_camera_id (기본값 1)
                create_date,
                roi_number,  # roiNumber 컬럼에 저장
                json.dumps(data_value, ensure_ascii=False)
            ))
            
            # 커밋 (autocommit이 True로 설정되어 있지만 명시적으로 커밋)
            if nvrdb:
                nvrdb.commit()
            
            logger.info(f"ROI 온도 데이터 DB 삽입 성공: ROI={roi_number}, "
                       f"최대온도={max_temp:.1f}°C, 최소온도={min_temp:.1f}°C, 평균온도={avg_temp:.1f}°C")
            return True
            
        except Exception as e:
            logger.error(f"ROI 온도 데이터 DB 삽입 오류: {str(e)}")
            logger.error(traceback.format_exc())
            return False
        finally:
            if cursor:
                cursor.close()

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
                    
                    # 경보 레벨 결정 (1~4단계)
                    # 10% 이상: Level 1, 15% 이상: Level 2, 20% 이상: Level 3, 25% 이상: Level 4
                    alert_level = None
                    for level, threshold in enumerate(threshold_levels):
                        if temp_diff >= threshold:
                            alert_level = level + 1  # 1~4 레벨로 변환
                    
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
                        
                        # logger.info(f"박스 {box_info['box_id']} 경보 감지: 온도차 {temp_diff:.1f}°C >= {threshold_levels[alert_level]}°C (Level {alert_level}), 절대 좌표 폴리곤: {polygon}")
            
            # logger.info(f"총 {len(alert_boxes)}개의 20x20 박스에서 경보 조건 감지")
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
                    # logger.info(f"20x20 박스 분석 결과 구조:")
                    # logger.info(f"  - 메인 ROI: {roi_polygon_data['main_roi']['zone_type']}")
                    # logger.info(f"  - 총 경보 박스: {roi_polygon_data['total_alert_boxes']}개")
                    
                    for i, box in enumerate(roi_polygon_data['alert_boxes'][:5]):  # 처음 5개만
                        # logger.info(f"  - 박스 {i+1}: ID={box['box_id']}, 온도차={box['temp_diff']:.1f}°C, 폴리곤={len(box['polygon'])}개 좌표")
                        if box['polygon']:
                            logger.info(f"    폴리곤 좌표: {box['polygon']}")
                else:
                    # logger.info("단일 ROI 구조")
                    logger.info(f"  - 폴리곤 좌표: {roi_polygon_data}")
            # elif isinstance(roi_polygon_data, list):
            #     logger.info(f"리스트 구조: {len(roi_polygon_data)}개 좌표")
            #     logger.info(f"  - 폴리곤 좌표: {roi_polygon_data}")
            # else:
            #     logger.info(f"알 수 없는 구조: {type(roi_polygon_data)}")
            #     logger.info(f"  - 내용: {roi_polygon_data}")
            
            # logger.info("=== ROI_POLYGON 구조 분석 완료 ===")
            
        except Exception as e:
            logger.error(f"ROI_POLYGON 구조 분석 오류: {str(e)}")

    def draw_roi_on_panorama(self, panorama_data_json, zone_info, output_filename=None):
        """
        파노라마 이미지에 ROI 박스 영역을 그려서 저장
        """
        try:
            if not panorama_data_json:
                logger.warning("파노라마 데이터가 없어 ROI를 그릴 수 없습니다")
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
            
            # 파노라마 이미지 크기를 1920x480으로 강제 리사이즈
            height, width = image.shape[:2]
            target_width = 1920
            target_height = 480
            if width != target_width or height != target_height:
                logger.info(f"draw_roi_on_panorama: 파노라마 이미지 크기 조정: {width}x{height} -> {target_width}x{target_height}")
                image = cv2.resize(image, (target_width, target_height), interpolation=cv2.INTER_LINEAR)
                logger.info(f"draw_roi_on_panorama: 파노라마 이미지 크기 조정 완료: {target_width}x{target_height}")
            else:
                logger.info(f"draw_roi_on_panorama: 파노라마 이미지 크기 확인: {width}x{height} (정상)")
            
            # ROI 좌표 추출 (우선순위: zone_segment_coords > left/top/right/bottom > actual_rect)
            left = None
            top = None
            right = None
            bottom = None
            
            # 1순위: zone_segment_coords (DB에서 가져온 원본 좌표 - 가장 정확함)
            if 'zone_segment_coords' in zone_info:
                coords = zone_info['zone_segment_coords']
                left = int(coords.get('left', 0))
                top = int(coords.get('top', 0))
                right = int(coords.get('right', 0))
                bottom = int(coords.get('bottom', 0))
                logger.info(f"draw_roi_on_panorama: zone_segment_coords 사용 - left={left}, top={top}, right={right}, bottom={bottom}")
            # 2순위: left, top, right, bottom 직접
            elif all(key in zone_info for key in ['left', 'top', 'right', 'bottom']):
                left = int(zone_info['left'])
                top = int(zone_info['top'])
                right = int(zone_info['right'])
                bottom = int(zone_info['bottom'])
                logger.info(f"draw_roi_on_panorama: left/top/right/bottom 사용 - left={left}, top={top}, right={right}, bottom={bottom}")
            # 3순위: actual_rect (변환된 좌표)
            elif 'actual_rect' in zone_info:
                x, y, w, h = zone_info['actual_rect']
                left = x
                top = y
                right = x + w
                bottom = y + h
                logger.info(f"draw_roi_on_panorama: actual_rect 사용 - left={left}, top={top}, right={right}, bottom={bottom} (원본: x={x}, y={y}, w={w}, h={h})")
            else:
                logger.error(f"ROI 좌표 정보를 찾을 수 없습니다. zone_info 키: {list(zone_info.keys())}")
                return None
            
            # 좌표 검증
            if left is None or top is None or right is None or bottom is None:
                logger.error(f"ROI 좌표가 None입니다: left={left}, top={top}, right={right}, bottom={bottom}")
                return None
                
            if left >= right or top >= bottom:
                logger.warning(f"ROI 좌표 검증 실패: left={left}, top={top}, right={right}, bottom={bottom}")
                return None
            
            # logger.info(f"최종 ROI 좌표: left={left}, top={top}, right={right}, bottom={bottom} (width={right-left}, height={bottom-top})")
            
            # ROI 박스 그리기 (사각형)
            # BGR 색상: 주황색 (0, 165, 255)
            color = (0, 165, 255)  # 주황색
            thickness = 3  # 선 두께
            
            # 메인 ROI 박스 그리기
            cv2.rectangle(image, (left, top), (right, bottom), color, thickness)
            
            # ROI 영역에 텍스트 추가
            zone_type = zone_info.get('zone_type', 'unknown')
            label = f"ROI-{zone_type}"
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.8
            text_color = (0, 165, 255)  # 주황색
            text_thickness = 2
            
            # 텍스트 배경 (반투명)
            (text_width, text_height), baseline = cv2.getTextSize(label, font, font_scale, text_thickness)
            cv2.rectangle(image, (left, top - text_height - 10), (left + text_width, top), (0, 0, 0), -1)
            cv2.putText(image, label, (left, top - 5), font, font_scale, text_color, text_thickness)
            
            # 좌표 정보 텍스트 추가
            coord_text = f"({left},{top})-({right},{bottom})"
            (coord_width, coord_height), _ = cv2.getTextSize(coord_text, font, 0.5, 1)
            cv2.rectangle(image, (left, bottom + 5), (left + coord_width + 10, bottom + coord_height + 15), (0, 0, 0), -1)
            cv2.putText(image, coord_text, (left + 5, bottom + coord_height + 10), font, 0.5, (255, 255, 255), 1)
            
            # 격자형 박스 그리기 (AlertStatus.vue처럼)
            # ROI 영역을 20x20 박스로 분할하여 모든 격자를 그림
            box_size = 20
            roi_width = right - left
            roi_height = bottom - top
            
            # 모든 20x20 격자 박스 그리기
            for box_y in range(0, roi_height, box_size):
                for box_x in range(0, roi_width, box_size):
                    # 박스의 실제 크기 계산 (경계 처리)
                    box_w = min(box_size, roi_width - box_x)
                    box_h = min(box_size, roi_height - box_y)
                    
                    # 절대 좌표 계산
                    abs_x = left + box_x
                    abs_y = top + box_y
                    abs_right = abs_x + box_w
                    abs_bottom = abs_y + box_h
                    
                    # 기본 격자 박스 (연한 회색 테두리)
                    grid_color = (100, 100, 100)  # 회색 (BGR)
                    grid_thickness = 1
                    cv2.rectangle(image, (abs_x, abs_y), (abs_right, abs_bottom), grid_color, grid_thickness)
            
            # alert_boxes가 있으면 경보 조건을 만족하는 박스는 다른 색상으로 강조
            if isinstance(zone_info, dict) and 'roi_polygon' in zone_info:
                roi_polygon_data = zone_info['roi_polygon']
                if isinstance(roi_polygon_data, dict) and 'alert_boxes' in roi_polygon_data:
                    alert_boxes = roi_polygon_data['alert_boxes']
                    for box in alert_boxes:
                        # polygon 좌표에서 박스 영역 추출
                        if 'polygon' in box and isinstance(box['polygon'], list) and len(box['polygon']) >= 4:
                            # polygon의 첫 번째와 세 번째 좌표로 사각형 영역 계산
                            poly = box['polygon']
                            box_left = int(poly[0][0])
                            box_top = int(poly[0][1])
                            box_right = int(poly[2][0])
                            box_bottom = int(poly[2][1])
                            
                            # 온도차에 따른 색상 결정 (AlertStatus.vue의 getTemperatureColor 로직 참고)
                            temp_diff = box.get('temp_diff', 0)
                            alert_level = box.get('alert_level', 0)
                            
                            # 온도차에 따른 색상: 노란색 -> 주황색 -> 붉은색
                            if temp_diff <= 2:
                                alert_color = (0, 255, 255)  # 연한 노란색 (BGR)
                                opacity = 0.3
                            elif temp_diff <= 5:
                                alert_color = (0, 255, 255)  # 노란색 (BGR)
                                opacity = 0.5
                            elif temp_diff <= 8:
                                alert_color = (0, 165, 255)  # 주황색 (BGR)
                                opacity = 0.6
                            elif temp_diff <= 10:
                                alert_color = (0, 69, 255)   # 붉은 주황색 (BGR)
                                opacity = 0.7
                            else:
                                alert_color = (0, 0, 255)    # 붉은색 (BGR)
                                opacity = 0.8
                            
                            # 반투명 박스 그리기 (overlay 방식)
                            overlay = image.copy()
                            cv2.rectangle(overlay, (box_left, box_top), (box_right, box_bottom), alert_color, -1)  # 채워진 사각형
                            cv2.addWeighted(overlay, opacity, image, 1 - opacity, 0, image)
                            
                            # 테두리 그리기
                            border_color = (255, 255, 255)  # 흰색 테두리
                            border_thickness = 1
                            cv2.rectangle(image, (box_left, box_top), (box_right, box_bottom), border_color, border_thickness)
                        elif 'rect' in box:
                            # 기존 rect 방식 지원
                            box_x, box_y, box_w, box_h = box['rect']
                            temp_diff = box.get('temp_diff', 0)
                            
                            # 온도차에 따른 색상
                            if temp_diff <= 2:
                                alert_color = (0, 255, 255)  # 연한 노란색
                                opacity = 0.3
                            elif temp_diff <= 5:
                                alert_color = (0, 255, 255)  # 노란색
                                opacity = 0.5
                            elif temp_diff <= 8:
                                alert_color = (0, 165, 255)  # 주황색
                                opacity = 0.6
                            elif temp_diff <= 10:
                                alert_color = (0, 69, 255)   # 붉은 주황색
                                opacity = 0.7
                            else:
                                alert_color = (0, 0, 255)    # 붉은색
                                opacity = 0.8
                            
                            # 반투명 박스 그리기
                            overlay = image.copy()
                            cv2.rectangle(overlay, (box_x, box_y), (box_x + box_w, box_y + box_h), alert_color, -1)
                            cv2.addWeighted(overlay, opacity, image, 1 - opacity, 0, image)
                            
                            # 테두리 그리기
                            cv2.rectangle(image, (box_x, box_y), (box_x + box_w, box_y + box_h), (255, 255, 255), 1)
            
            # 시나리오2: alert_region 또는 bar_region에 수직 빨간색 바 그리기
            scenario = zone_info.get('scenario', '')
            alert_region = zone_info.get('alert_region') or zone_info.get('bar_region')
            
            if scenario == 'scenario2' or alert_region:
                if alert_region:
                    # alert_region 좌표 추출
                    start_x = alert_region.get('start_x') or alert_region.get('min_x', 0)
                    end_x = alert_region.get('end_x') or alert_region.get('max_x', 0)
                    start_y = alert_region.get('start_y') or alert_region.get('min_y', 0)
                    end_y = alert_region.get('end_y') or alert_region.get('max_y', 480)
                    
                    # 수직 빨간색 바 그리기
                    bar_color = (0, 0, 255)  # 빨간색 (BGR)
                    bar_thickness = 3  # 선 두께
                    
                    # 수직 막대 그리기 (start_x부터 end_x까지)
                    if start_x < end_x:
                        # 반투명 빨간색 배경
                        overlay = image.copy()
                        cv2.rectangle(overlay, (start_x, start_y), (end_x, end_y), bar_color, -1)  # 채워진 사각형
                        cv2.addWeighted(overlay, 0.6, image, 0.4, 0, image)
                        
                        # 흰색 테두리
                        border_color = (255, 255, 255)  # 흰색
                        cv2.rectangle(image, (start_x, start_y), (end_x, end_y), border_color, bar_thickness)
                        
                        logger.info(f"시나리오2: 수직 빨간색 바 그리기 완료 - ({start_x}, {start_y}) ~ ({end_x}, {end_y})")
            
            # 저장할 파일명 생성
            if output_filename is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                zone_type_str = zone_info.get('zone_type', 'unknown')
                output_filename = f"panorama_roi_{zone_type_str}_{timestamp}.jpg"
            
            # 이미지 파일 경로 설정
            snapshots_dir = os.path.join(os.path.dirname(__file__), 'snapshots')
            os.makedirs(snapshots_dir, exist_ok=True)
            
            output_path = os.path.join(snapshots_dir, output_filename)
            
            # 이미지 저장
            cv2.imwrite(output_path, image)
            
            logger.info(f"ROI 박스가 그려진 파노라마 이미지 저장 완료: {output_path}")
            logger.info(f"ROI 영역: left={left}, top={top}, right={right}, bottom={bottom}")
            
            return output_path
            
        except Exception as e:
            logger.error(f"파노라마 이미지에 ROI 그리기 오류: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return None

    def draw_roi_on_panorama_and_get_base64(self, panorama_data_json, zone_info, alert_segments=None):
        """
        파노라마 이미지를 base64로 반환 (파일 저장 없음)
        alert_segments가 제공되면 각 등분을 신뢰도에 따라 색상으로 표시 (노란색->붉은색)
        """
        try:
            if not panorama_data_json:
                logger.warning("파노라마 데이터가 없어 ROI를 그릴 수 없습니다")
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
            
            # 파노라마 이미지 크기를 1920x480으로 강제 리사이즈
            height, width = image.shape[:2]
            target_width = 1920
            target_height = 480
            if width != target_width or height != target_height:
                # logger.info(f"draw_roi_on_panorama_and_get_base64: 파노라마 이미지 크기 조정: {width}x{height} -> {target_width}x{target_height}")
                image = cv2.resize(image, (target_width, target_height), interpolation=cv2.INTER_LINEAR)
                # logger.info(f"draw_roi_on_panorama_and_get_base64: 파노라마 이미지 크기 조정 완료: {target_width}x{target_height}")
            else:
                logger.info(f"draw_roi_on_panorama_and_get_base64: 파노라마 이미지 크기 확인: {width}x{height} (정상)")
            
            # ROI 좌표 추출 (우선순위: zone_segment_coords > left/top/right/bottom > actual_rect)
            left = None
            top = None
            right = None
            bottom = None
            
            # 1순위: zone_segment_coords (DB에서 가져온 원본 좌표 - 가장 정확함)
            if 'zone_segment_coords' in zone_info:
                coords = zone_info['zone_segment_coords']
                left = int(coords.get('left', 0))
                top = int(coords.get('top', 0))
                right = int(coords.get('right', 0))
                bottom = int(coords.get('bottom', 0))
                # logger.info(f"draw_roi_on_panorama_and_get_base64: zone_segment_coords 사용 - left={left}, top={top}, right={right}, bottom={bottom}")
            # 2순위: left, top, right, bottom 직접
            elif all(key in zone_info for key in ['left', 'top', 'right', 'bottom']):
                left = int(zone_info['left'])
                top = int(zone_info['top'])
                right = int(zone_info['right'])
                bottom = int(zone_info['bottom'])
                # logger.info(f"draw_roi_on_panorama_and_get_base64: left/top/right/bottom 사용 - left={left}, top={top}, right={right}, bottom={bottom}")
            # 3순위: actual_rect (변환된 좌표)
            elif 'actual_rect' in zone_info:
                x, y, w, h = zone_info['actual_rect']
                left = x
                top = y
                right = x + w
                bottom = y + h
                # logger.info(f"draw_roi_on_panorama_and_get_base64: actual_rect 사용 - left={left}, top={top}, right={right}, bottom={bottom} (원본: x={x}, y={y}, w={w}, h={h})")
            else:
                # logger.error(f"ROI 좌표 정보를 찾을 수 없습니다. zone_info 키: {list(zone_info.keys())}")
                return None
            
            # 좌표 검증
            if left is None or top is None or right is None or bottom is None:
                logger.error(f"ROI 좌표가 None입니다: left={left}, top={top}, right={right}, bottom={bottom}")
                return None
                
            if left >= right or top >= bottom:
                logger.warning(f"ROI 좌표 검증 실패: left={left}, top={top}, right={right}, bottom={bottom}")
                return None
            
            # logger.info(f"최종 ROI 좌표: left={left}, top={top}, right={right}, bottom={bottom} (width={right-left}, height={bottom-top})")
            
            # 시나리오1: 격자형 박스 그리기 (alert_boxes가 있는 경우)
            if isinstance(zone_info, dict) and 'roi_polygon' in zone_info:
                roi_polygon_data = zone_info['roi_polygon']
                if isinstance(roi_polygon_data, dict) and 'alert_boxes' in roi_polygon_data:
                    # 격자형 박스 그리기 (AlertStatus.vue처럼)
                    # ROI 영역을 20x20 박스로 분할하여 모든 격자를 그림
                    box_size = 20
                    roi_width = right - left
                    roi_height = bottom - top
                    
                    # 모든 20x20 격자 박스 그리기
                    for box_y in range(0, roi_height, box_size):
                        for box_x in range(0, roi_width, box_size):
                            # 박스의 실제 크기 계산 (경계 처리)
                            box_w = min(box_size, roi_width - box_x)
                            box_h = min(box_size, roi_height - box_y)
                            
                            # 절대 좌표 계산
                            abs_x = left + box_x
                            abs_y = top + box_y
                            abs_right = abs_x + box_w
                            abs_bottom = abs_y + box_h
                            
                            # 기본 격자 박스 (연한 회색 테두리)
                            grid_color = (100, 100, 100)  # 회색 (BGR)
                            grid_thickness = 1
                            cv2.rectangle(image, (abs_x, abs_y), (abs_right, abs_bottom), grid_color, grid_thickness)
                    
                    # alert_boxes가 있으면 경보 조건을 만족하는 박스는 다른 색상으로 강조
                    alert_boxes = roi_polygon_data['alert_boxes']
                    for box in alert_boxes:
                        # polygon 좌표에서 박스 영역 추출
                        if 'polygon' in box and isinstance(box['polygon'], list) and len(box['polygon']) >= 4:
                            # polygon의 첫 번째와 세 번째 좌표로 사각형 영역 계산
                            poly = box['polygon']
                            box_left = int(poly[0][0])
                            box_top = int(poly[0][1])
                            box_right = int(poly[2][0])
                            box_bottom = int(poly[2][1])
                            
                            # 온도차에 따른 색상 결정 (AlertStatus.vue의 getTemperatureColor 로직 참고)
                            temp_diff = box.get('temp_diff', 0)
                            alert_level = box.get('alert_level', 0)
                            
                            # 온도차에 따른 색상: 노란색 -> 주황색 -> 붉은색
                            if temp_diff <= 2:
                                alert_color = (0, 255, 255)  # 연한 노란색 (BGR)
                                opacity = 0.3
                            elif temp_diff <= 5:
                                alert_color = (0, 255, 255)  # 노란색 (BGR)
                                opacity = 0.5
                            elif temp_diff <= 8:
                                alert_color = (0, 165, 255)  # 주황색 (BGR)
                                opacity = 0.6
                            elif temp_diff <= 10:
                                alert_color = (0, 69, 255)   # 붉은 주황색 (BGR)
                                opacity = 0.7
                            else:
                                alert_color = (0, 0, 255)    # 붉은색 (BGR)
                                opacity = 0.8
                            
                            # 반투명 박스 그리기 (overlay 방식)
                            overlay = image.copy()
                            cv2.rectangle(overlay, (box_left, box_top), (box_right, box_bottom), alert_color, -1)  # 채워진 사각형
                            cv2.addWeighted(overlay, opacity, image, 1 - opacity, 0, image)
                            
                            # 테두리 그리기
                            border_color = (255, 255, 255)  # 흰색 테두리
                            border_thickness = 1
                            cv2.rectangle(image, (box_left, box_top), (box_right, box_bottom), border_color, border_thickness)
                        elif 'rect' in box:
                            # 기존 rect 방식 지원
                            box_x, box_y, box_w, box_h = box['rect']
                            box_left = left + box_x
                            box_top = top + box_y
                            box_right = box_left + box_w
                            box_bottom = box_top + box_h
                            temp_diff = box.get('temp_diff', 0)
                            
                            # 온도차에 따른 색상
                            if temp_diff <= 2:
                                alert_color = (0, 255, 255)  # 연한 노란색
                                opacity = 0.3
                            elif temp_diff <= 5:
                                alert_color = (0, 255, 255)  # 노란색
                                opacity = 0.5
                            elif temp_diff <= 8:
                                alert_color = (0, 165, 255)  # 주황색
                                opacity = 0.6
                            elif temp_diff <= 10:
                                alert_color = (0, 69, 255)   # 붉은 주황색
                                opacity = 0.7
                            else:
                                alert_color = (0, 0, 255)    # 붉은색
                                opacity = 0.8
                            
                            # 반투명 박스 그리기
                            overlay = image.copy()
                            cv2.rectangle(overlay, (box_left, box_top), (box_right, box_bottom), alert_color, -1)
                            cv2.addWeighted(overlay, opacity, image, 1 - opacity, 0, image)
                            
                            # 테두리 그리기
                            border_color = (255, 255, 255)
                            border_thickness = 1
                            cv2.rectangle(image, (box_left, box_top), (box_right, box_bottom), border_color, border_thickness)
            
            # alert_segments가 있으면 각 등분을 신뢰도에 따라 색상으로 표시 (노란색->붉은색) - 시나리오2
            if alert_segments and len(alert_segments) > 0:
                # 최소 신뢰도 계산 (색상 결정용)
                min_confidence = min(seg['confidence_percent'] for seg in alert_segments)
                max_confidence = max(seg['confidence_percent'] for seg in alert_segments)
                
                # 각 등분별로 색상 표시
                for seg in alert_segments:
                    seg_left = seg['left']
                    seg_top = seg['top']
                    seg_right = seg['right']
                    seg_bottom = seg['bottom']
                    seg_confidence = seg['confidence_percent']
                    
                    # 신뢰도에 따라 색상 결정 (노란색 → 붉은색)
                    # 신뢰도 범위: 0~100%
                    # 신뢰도가 낮을수록 붉은색 (0% = 빨간색, 100% = 노란색)
                    # 노란색 (BGR: 0, 255, 255) → 빨간색 (BGR: 0, 0, 255)
                    confidence_ratio = min(seg_confidence / 100.0, 1.0)  # 0.0 ~ 1.0
                    
                    # BGR 색상 계산
                    # G: 255 → 0 (녹색 성분 감소)
                    # R: 255 → 255 (빨간색 성분 유지)
                    # B: 0 → 0 (파란색 성분 유지)
                    g_value = int(255 * confidence_ratio)  # 녹색 성분 (신뢰도가 높을수록 높음)
                    r_value = 255  # 빨간색 성분 (고정)
                    b_value = 0  # 파란색 성분 (고정)
                    
                    seg_color = (b_value, g_value, r_value)  # BGR 형식
                    
                    # 등분 영역을 반투명 색상으로 채우기
                    overlay = image.copy()
                    cv2.rectangle(overlay, (seg_left, seg_top), (seg_right, seg_bottom), seg_color, -1)
                    opacity = 0.5  # 반투명도
                    cv2.addWeighted(overlay, opacity, image, 1 - opacity, 0, image)
                    
                    # 등분 테두리 그리기
                    border_color = (255, 255, 255)  # 흰색 테두리
                    border_thickness = 2
                    cv2.rectangle(image, (seg_left, seg_top), (seg_right, seg_bottom), border_color, border_thickness)
                
                logger.info(f"시나리오2: {len(alert_segments)}개 등분에 색상 표시 완료 "
                           f"(신뢰도 범위: {min_confidence:.1f}% ~ {max_confidence:.1f}%)")
            
            # 이미지를 JPEG 형식으로 인코딩하여 base64로 변환
            _, buffer = cv2.imencode('.jpg', image)
            roi_image_base64 = base64.b64encode(buffer).decode('utf-8')
            
            logger.info(f"파노라마 이미지 생성 완료 (base64, 크기: {len(roi_image_base64)} 문자)")
            logger.info(f"ROI 영역: left={left}, top={top}, right={right}, bottom={bottom}")
            
            return roi_image_base64
            
        except Exception as e:
            logger.error(f"파노라마 이미지에 ROI 그리기 오류: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return None

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
            
            # logger.info(f"파노라마 이미지 저장 완료: {image_path} (크기: {len(image_data)} bytes)")
            
            # RAW 이미지 파일도 저장 (원본 base64 디코딩 데이터를 .raw 파일로)
            raw_filename = f"panorama_{timestamp}.raw"
            raw_image_path = os.path.join(snapshots_dir, raw_filename)
            with open(raw_image_path, 'wb') as f:
                f.write(image_data)
            
            # logger.info(f"파노라마 RAW 이미지 저장 완료: {raw_image_path} (크기: {len(image_data)} bytes)")
            
            # 스냅샷 데이터 형태로 반환
            snapshot_data = {
                'panorama_image': True,
                'image_type': 'panorama',
                'timestamp': datetime.now().isoformat(),
                'image_data': image_base64,
                'file_path': image_path,
                'filename': filename
            }
            
            # logger.info(f"파노라마 스냅샷 데이터 생성 완료: {filename}")
            return snapshot_data
            
        except Exception as e:
            logger.error(f"파노라마 이미지 추출 오류: {str(e)}")
            logger.error(f"예외 상세: {traceback.format_exc()}")
            return None

    def capture_visible_camera_snapshot(self):
        """
        실화상 카메라(videoType=2)의 스트림 이미지만 캡처
        """
        snapshot_image = None
        
        if not hasattr(self, 'camera_info_list') or not self.camera_info_list:
            logger.warning("카메라 정보가 없어 실화상 카메라 스냅샷을 캡처할 수 없습니다")
            return None
        
        # 실화상 카메라(videoType=2) 찾기
        visible_camera = None
        for camera_info in self.camera_info_list:
            video_type = camera_info.get('video_type')
            # videoType이 2이거나, 문자열인 경우 '2' 또는 'visible' 체크
            if video_type == 2 or str(video_type) == '2' or str(video_type).lower() == 'visible':
                visible_camera = camera_info
                break
        
        if not visible_camera:
            logger.warning("실화상 카메라(videoType=2)를 찾을 수 없습니다")
            return None
        
        try:
            rtsp_url = visible_camera['rtsp_url']
            video_type = visible_camera['video_type']
            camera_name = visible_camera.get('camera_name', 'unknown')
            
            # RTSP URL 유효성 검사
            if not rtsp_url or not isinstance(rtsp_url, str) or rtsp_url.strip() == '':
                logger.warning(f"유효하지 않은 RTSP URL: {rtsp_url}")
                return None
            
            rtsp_url = rtsp_url.strip()
            
            # RTSP 프로토콜 확인
            if not rtsp_url.startswith(('rtsp://', 'http://', 'https://')):
                logger.warning(f"RTSP URL에 유효하지 않은 프로토콜: {rtsp_url}")
                return None
            
            logger.info(f"실화상 카메라 스냅샷 캡처 중: {rtsp_url}")
            
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
                    
                    # 타임스탬프 생성 (JPG와 RAW에 동일한 타임스탬프 사용)
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    
                    # 스냅샷 이미지를 파일로 저장 (JPG와 RAW 모두)
                    filename, file_path = self.save_snapshot_to_file(stdout_data, camera_name, video_type, timestamp)
                    
                    # RAW 이미지도 저장
                    if file_path:
                        self.save_raw_image(stdout_data, camera_name, video_type, timestamp)
                    
                    snapshot_image = {
                        'rtsp_url': rtsp_url,
                        'video_type': video_type,
                        'camera_name': camera_name,
                        'timestamp': datetime.now().isoformat(),
                        'image_data': img_base64,
                        'file_path': file_path if file_path else '',
                        'image_type': 'visible_stream'
                    }
                    logger.info(f"실화상 카메라 스냅샷 캡처 성공: {rtsp_url} (Type: {video_type}, Camera: {camera_name})")
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
            logger.error(f"실화상 카메라 스냅샷 캡처 오류: {str(e)}")
            logger.error(f"예외 상세: {traceback.format_exc()}")
        
        return snapshot_image

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
                        
                        # 타임스탬프 생성 (JPG와 RAW에 동일한 타임스탬프 사용)
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        
                        # 스냅샷 이미지를 파일로 저장 (JPG와 RAW 모두)
                        filename, file_path = self.save_snapshot_to_file(stdout_data, camera_name, video_type, timestamp)
                        
                        # RAW 이미지도 저장
                        if file_path:
                            self.save_raw_image(stdout_data, camera_name, video_type, timestamp)
                        
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

    def save_snapshot_to_file(self, image_data, camera_name, video_type, timestamp=None):
        """
        스냅샷 이미지를 파일로 저장
        """
        try:
            if not image_data:
                logger.warning("저장할 이미지 데이터가 없습니다")
                return
            
            # 타임스탬프 생성
            if not timestamp:
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

    def save_raw_image(self, image_data, camera_name, video_type, timestamp=None):
        """
        RAW 이미지 파일 저장 (원본 바이너리 데이터)
        """
        try:
            if not image_data:
                logger.warning("저장할 RAW 이미지 데이터가 없습니다")
                return None, None
            
            # 타임스탬프 생성
            if not timestamp:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # 카메라 이름과 비디오 타입을 파일명에 포함
            safe_camera_name = "".join(c for c in camera_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
            safe_camera_name = safe_camera_name.replace(' ', '_')
            
            # RAW 파일명 생성: 카메라명_비디오타입_날짜시간.raw
            raw_filename = f"{safe_camera_name}_{video_type}_{timestamp}.raw"
            
            # 이미지 파일 경로 설정 (bin 디렉토리 내 snapshots 폴더)
            snapshots_dir = os.path.join(os.path.dirname(__file__), 'snapshots')
            os.makedirs(snapshots_dir, exist_ok=True)
            
            raw_image_path = os.path.join(snapshots_dir, raw_filename)
            
            # RAW 이미지 파일 저장 (원본 바이너리 데이터)
            with open(raw_image_path, 'wb') as f:
                f.write(image_data)
            
            logger.info(f"RAW 이미지 저장 완료: {raw_image_path} (크기: {len(image_data)} bytes)")
            print(f"RAW 이미지 저장 완료: {raw_image_path}")
            
            return raw_filename, raw_image_path
            
        except Exception as e:
            logger.error(f"RAW 이미지 저장 오류: {str(e)}")
            print(f"RAW 이미지 저장 오류: {str(e)}")
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
                # logger.info("강제 종료 요청됨, 시나리오1 중단")
                return False
            
            # 최신 파노라마 데이터 조회
            panorama_data_record = self.get_latest_temperature_data()
            if not panorama_data_record:
                # logger.info("시나리오1: 파노라마 데이터가 없습니다")
                return False
            
            # 온도 매트릭스 생성 (1920x480 파노라마 크기)
            # panorama_data_json의 colorbarMapping을 사용하여 온도 매트릭스 생성
            temp_matrix = self.create_temperature_matrix(panorama_data_record['panoramaData'])
            if temp_matrix is None:
                logger.error("시나리오1: 온도 매트릭스 생성 실패")
                return False
            
            # 온도 매트릭스 크기 확인 (1920x480)
            expected_width = 1920
            expected_height = 480
            actual_height, actual_width = temp_matrix.shape
            if actual_width != expected_width or actual_height != expected_height:
                logger.warning(f"시나리오1: 온도 매트릭스 크기 불일치: 예상={expected_width}x{expected_height}, 실제={actual_width}x{actual_height}")
            else:
                logger.info(f"시나리오1: 온도 매트릭스 크기 확인: {actual_width}x{actual_height} (1920x480)")
            
            # self.save_temperature_matrix_to_csv(temp_matrix, 1920, 480)  # CSV 파일 저장 주석처리
            # zone_type 리스트 가져오기
            if not self.zone_list:
                # logger.warning("시나리오1: zone_list가 없어 기본 ROI 영역을 사용합니다")
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
            # logger.info(f"시나리오1 기준값: {levels}")
            # 4단계 기준값: [2, 5, 8, 10]

            # 스냅샷을 한 번만 캡처 (모든 경보에서 재사용)
            panorama_snapshot = None
            visible_stream_snapshot = None
            
            # 파노라마 이미지 추출
            panorama_snapshot = self.extract_panorama_image(panorama_data_record['panoramaData'])
            # if panorama_snapshot:
            #     logger.info("시나리오1: 파노라마 이미지 추출 성공")
            # else:
            #     logger.warning("시나리오1: 파노라마 이미지 추출 실패")
            
            # 실화상 카메라 스트림 스냅샷 이미지 캡처 (videoType=2) - 한 번만
            visible_stream_snapshot = self.capture_visible_camera_snapshot()
            # if visible_stream_snapshot:
            #     logger.info("시나리오1: 실화상 카메라 스냅샷 캡처 완료")
            # else:
            #     logger.warning("시나리오1: 실화상 카메라 스냅샷 캡처 실패")
            
            # 업로드된 파노라마 스냅샷 사용 (run 메서드에서 업로드됨)
            if self.uploaded_panorama_snapshot:
                panorama_snapshot = self.uploaded_panorama_snapshot
                if self.uploaded_panorama_filename:
                    panorama_snapshot['filename'] = self.uploaded_panorama_filename
                    # logger.info(f"시나리오1: 업로드된 파노라마 스냅샷 사용: {self.uploaded_panorama_filename}")
            
            # 각 ROI 영역을 20x20 박스로 분할하여 검사
            alert_detected = False
            # logger.info(f"시나리오1: 총 {len(zones_to_check)}개 ROI 영역 처리 시작")
            for idx, zone_info in enumerate(zones_to_check, 1):
                # logger.info(f"시나리오1: [{idx}/{len(zones_to_check)}] Zone {zone_info.get('zone_type', 'unknown')} 처리 시작")
                # 강제 종료 체크
                if self.force_exit:
                    logger.info("강제 종료 요청됨, 시나리오1 중단")
                    return False
                
                # zone_segment_json에서 실제 ROI 좌표 추출
                if 'left' in zone_info and 'top' in zone_info and 'right' in zone_info and 'bottom' in zone_info:
                    # zone_segment_json의 실제 좌표 사용
                    left = int(zone_info['left'])
                    top = int(zone_info['top'])
                    right = int(zone_info['right'])
                    bottom = int(zone_info['bottom'])
                    
                    # 좌표 검증 및 로깅
                    # logger.info(f"Zone {zone_info.get('zone_type', 'unknown')}: 원본 좌표 - left={left}, top={top}, right={right}, bottom={bottom}")
                    
                    # 실제 rect 형식: [x, y, width, height]
                    actual_rect = [
                        left,           # x 좌표
                        top,            # y 좌표
                        right - left,   # width (너비)
                        bottom - top    # height (높이)
                    ]
                    
                    # logger.info(f"Zone {zone_info.get('zone_type', 'unknown')}: 변환된 rect - [x={actual_rect[0]}, y={actual_rect[1]}, w={actual_rect[2]}, h={actual_rect[3]}]")
                    # logger.info(f"Zone {zone_info.get('zone_type', 'unknown')}: 실제 영역 범위 - x: {left}~{right} ({actual_rect[2]}px), y: {top}~{bottom} ({actual_rect[3]}px)")
                else:
                    # 기존 rect 정보 사용 (fallback)
                    actual_rect = zone_info.get('rect', [0, 0, 320, 240])
                    # logger.info(f"Zone {zone_info.get('zone_type', 'unknown')}: 기존 rect 좌표 사용 - {actual_rect}")
                
                # ROI 영역을 20x20 박스로 분할 (절대 좌표로)
                boxes = self.create_20x20_boxes(actual_rect, box_size=20)
                
                if not boxes:
                    # logger.warning(f"Zone {zone_info.get('zone_type', 'unknown')}: 20x20 박스 생성 실패")
                    continue
                
                # 20x20 박스들의 온도차 분석
                alert_boxes = self.analyze_20x20_boxes(temp_matrix, boxes, levels)
                
                # logger.info(f"Zone {zone_info.get('zone_type', 'unknown')}: 20x20 박스 분석 완료, 총 {len(boxes)}개 박스 중 {len(alert_boxes) if alert_boxes else 0}개에서 경보 조건 감지")
                
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
                    
                    # alert_boxes 중 가장 높은 alert_level 사용 (1~4)
                    max_alert_level = max([box.get('alert_level', 1) for box in alert_boxes]) if alert_boxes else 1
                    
                    self.create_scenario1_alert(
                        panorama_data_record['id'],
                        zone_info,
                        'S001',
                        len(alert_boxes),  # 경보 조건을 만족하는 박스 개수
                        max_alert_level,  # alert_boxes 중 가장 높은 alert_level (1~4)
                        alert_boxes,  # 20x20 박스 분석 결과
                        panorama_snapshot,  # 재사용할 파노라마 스냅샷
                        visible_stream_snapshot  # 재사용할 실화상 스트림 스냅샷
                    )
                    alert_detected = True

            # 전체 영역 온도차 변화율 검사 (25% 이상) - OR 조건으로 추가
            # zone_type이 0인 ROI는 제외하고 검사
            valid_zones = [z for z in zones_to_check if z.get('zone_type') != 0 and z.get('zone_type') != '0']
            if len(valid_zones) > 1:
                logger.info(f"시나리오1: 전체 영역 검사 시작 (유효한 ROI: {len(valid_zones)}개, 전체: {len(zones_to_check)}개)")
                # 강제 종료 체크
                if self.force_exit:
                    # logger.info("강제 종료 요청됨, 시나리오1 중단")
                    return False
                    
                # 전체 영역의 온도 데이터 수집 (zone_type 0 제외)
                all_temps = []
                for zone_info in valid_zones:
                    roi_data = self.extract_roi_temperature_data(temp_matrix, zone_info)
                    if roi_data and roi_data['temperatures']:
                        all_temps.extend(roi_data['temperatures'])
                
                # 전체 영역 온도차 변화율 계산
                if len(all_temps) > 0:
                    overall_temp_diff = max(all_temps) - min(all_temps)
                    overall_avg_temp = np.mean(all_temps)
                    
                    if overall_avg_temp > 0:
                        temp_change_percent = (overall_temp_diff / overall_avg_temp) * 100
                        # logger.info(f"전체 영역 온도차 변화율: {temp_change_percent:.1f}% (최대: {max(all_temps):.1f}°C, 최소: {min(all_temps):.1f}°C)")
                        
                        # DB 설정값(levels)에 따라 경보 레벨 결정 (1~4단계)
                        # levels는 온도차 변화율(%) 기준값 배열 (예: [10, 15, 20, 25])
                        # 10% 이상: Level 1, 15% 이상: Level 2, 20% 이상: Level 3, 25% 이상: Level 4
                        alert_level = None
                        for level, threshold in enumerate(levels):
                            if temp_change_percent >= threshold:
                                alert_level = level + 1  # 1~4 레벨로 변환
                        
                        # 경보 조건을 만족하는 경우 경보 생성
                        if alert_level is not None:
                            threshold_index = alert_level - 1  # 로그 출력용 인덱스
                            logger.info(f"시나리오1 경보 감지: 전체 영역 온도차 변화율 {temp_change_percent:.1f}% >= {levels[threshold_index]}% (Level {alert_level})")
                            
                            # 전체 영역 ROI 데이터 생성 (파노라마 크기)
                            overall_zone_info = {
                                'zone_type': 'overall',
                                'rect': [0, 0, 1920, 480]  # 1920x480 파노라마 전체 영역
                            }
                            
                            # 경보 생성 (DB 설정값에 따른 alert_level 사용)
                            self.create_scenario1_alert(
                                panorama_data_record['id'],
                                overall_zone_info,
                                'S002',
                                temp_change_percent,
                                alert_level,  # DB 설정값에 따라 결정된 레벨 (1~4)
                                None,  # alert_boxes는 없음
                                panorama_snapshot,  # 재사용할 파노라마 스냅샷
                                visible_stream_snapshot  # 재사용할 실화상 스트림 스냅샷
                            )
                            alert_detected = True

            if not alert_detected:
                # logger.info("시나리오1: 경보 조건을 만족하지 않습니다")
                pass
            
            return alert_detected
            
        except Exception as e:
            logger.error(f"시나리오1 판단 오류: {str(e)}")
            logger.error(traceback.format_exc())
            return False

    def _convert_zone_type_to_int(self, zone_type):
        """
        zone_type을 정수로 변환
        'overall' 또는 다른 문자열인 경우 기본값 1 반환
        """
        try:
            if isinstance(zone_type, (int, float)):
                return int(zone_type)
            elif isinstance(zone_type, str):
                # 문자열이 숫자인지 확인
                if zone_type.isdigit():
                    return int(zone_type)
                else:
                    # 'overall' 등 문자열인 경우 기본값 1 반환
                    logger.warning(f"zone_type이 숫자가 아닌 문자열입니다: '{zone_type}', 기본값 1 사용")
                    return 1
            else:
                logger.warning(f"zone_type이 예상하지 못한 타입입니다: {type(zone_type)}, 기본값 1 사용")
                return 1
        except Exception as e:
            logger.error(f"zone_type 변환 오류: {e}, 기본값 1 사용")
            return 1

    def create_scenario1_alert(self, video_data_id, zone_info, alert_type, threshold_value, alert_level=1, alert_boxes=None, panorama_snapshot=None, visible_stream_snapshot=None):
        """
        시나리오1 경보 생성 및 DB 저장 (20x20 박스 분석 결과 포함)
        panorama_snapshot과 visible_stream_snapshot이 제공되면 재사용, 없으면 새로 캡처
        """
        try:
            cursor = self.get_db_cursor()
            if not cursor:
                return False
            
            # 파노라마 데이터 조회 (ROI 그리기용)
            panorama_data_record = None
            if panorama_snapshot is None:
                panorama_data_record = self.get_latest_temperature_data()
                if panorama_data_record:
                    # logger.info(f"시나리오1: 파노라마 데이터 조회 및 이미지 추출 (새로 캡처)")
                    panorama_snapshot = self.extract_panorama_image(panorama_data_record['panoramaData'])
                else:
                    # logger.warning("시나리오1: 파노라마 데이터 조회 실패 - 데이터가 없습니다")
                    pass
            else:
                # logger.info("시나리오1: 파노라마 스냅샷 재사용")
                # ROI 그리기를 위해 파노라마 데이터 조회
                panorama_data_record = self.get_latest_temperature_data()
            
            if visible_stream_snapshot is None:
                # logger.info("시나리오1: 실화상 카메라 스트림 스냅샷 캡처 (새로 캡처)")
                visible_stream_snapshot = self.capture_visible_camera_snapshot()
            else:
                # logger.info("시나리오1: 실화상 스트림 스냅샷 재사용")
                pass
            
            # 스냅샷 이미지 구성 (파노라마 1개 + 실화상 스트림 1개)
            snapshot_images = []
            
            # 파노라마 이미지 추가
            if panorama_snapshot:
                snapshot_images.append(panorama_snapshot)
                # logger.info("파노라마 이미지가 snapshot_images에 추가됨")
            else:
                # logger.warning("파노라마 이미지가 없어 snapshot_images에 추가되지 않음")
                pass
            
            # 실화상 스트림 이미지 추가 (1개만)
            if visible_stream_snapshot:
                snapshot_images.append(visible_stream_snapshot)
                # logger.info("실화상 스트림 이미지가 snapshot_images에 추가됨")
            else:
                # logger.warning("실화상 스트림 이미지가 없음")
                pass
            
            # logger.info(f"총 {len(snapshot_images)}개의 스냅샷 이미지 준비 완료 (파노라마: {1 if panorama_snapshot else 0}개, 실화상 스트림: {1 if visible_stream_snapshot else 0}개)")
            
            # 디버깅: snapshot_images 내용 확인
            # for i, img in enumerate(snapshot_images):
            #     img_type = img.get('image_type', 'stream')
            #     logger.info(f"스냅샷 {i+1}: 타입={img_type}, 파일명={img.get('filename', 'N/A')}")
            
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
                    # logger.info(f"zone_segment_json 실제 좌표로 main_roi 생성: {main_rect}")
                else:
                    main_rect = zone_info.get('rect', [0, 0, 640, 240])  # 파노라마 기본 크기로 변경
                    main_polygon = self.create_roi_polygon(main_rect)
                    # logger.info(f"기존 rect 좌표로 main_roi 생성: {main_rect}")
                
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
                # logger.info(f"alert_info에 zone_segment_json 실제 좌표 사용: {alert_rect}")
            else:
                alert_rect = zone_info.get('rect', [0, 0, 640, 240])  # 파노라마 기본 크기로 변경
                # logger.info(f"alert_info에 기존 rect 좌표 사용: {alert_rect}")
            
            # ROI 박스를 파노라마 이미지에 그려서 저장하고 DB 저장용 이미지로 사용
            roi_drawn_image_base64 = None
            if panorama_data_record and panorama_data_record.get('panoramaData'):
                try:
                    # zone_info에 roi_polygon 정보 추가 (이미 생성된 경우)
                    zone_info_with_polygon = zone_info.copy()
                    if isinstance(roi_polygon_data, dict):
                        zone_info_with_polygon['roi_polygon'] = roi_polygon_data
                    
                    # 좌표 정보 로깅 (디버깅용)
                    # logger.info(f"ROI 박스 그리기 전 zone_info 좌표 확인:")
                    # logger.info(f"  - left: {zone_info_with_polygon.get('left', 'N/A')}")
                    # logger.info(f"  - top: {zone_info_with_polygon.get('top', 'N/A')}")
                    # logger.info(f"  - right: {zone_info_with_polygon.get('right', 'N/A')}")
                    # logger.info(f"  - bottom: {zone_info_with_polygon.get('bottom', 'N/A')}")
                    # logger.info(f"  - actual_rect: {zone_info_with_polygon.get('actual_rect', 'N/A')}")
                    # logger.info(f"  - zone_segment_coords: {zone_info_with_polygon.get('zone_segment_coords', 'N/A')}")
                    
                    # ROI 박스가 그려진 이미지를 base64로 반환
                    roi_drawn_image_base64 = self.draw_roi_on_panorama_and_get_base64(
                        panorama_data_record['panoramaData'],
                        zone_info_with_polygon
                    )
                    if roi_drawn_image_base64:
                        # logger.info("ROI 박스가 그려진 파노라마 이미지 생성 완료 (base64)")
                        
                        # ROI 박스가 그려진 이미지로 panorama_snapshot 교체
                        if panorama_snapshot:
                            panorama_snapshot['image_data'] = roi_drawn_image_base64
                            panorama_snapshot['roi_drawn'] = True
                            # logger.info("snapshot_images의 파노라마 이미지를 ROI 박스가 그려진 이미지로 교체")
                        else:
                            # panorama_snapshot이 없는 경우 새로 생성
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            panorama_snapshot = {
                                'panorama_image': True,
                                'image_type': 'panorama',
                                'timestamp': datetime.now().isoformat(),
                                'image_data': roi_drawn_image_base64,
                                'roi_drawn': True,
                                'filename': f"panorama_roi_{timestamp}.jpg"
                            }
                            snapshot_images.insert(0, panorama_snapshot)  # 맨 앞에 추가
                            # logger.info("ROI 박스가 그려진 파노라마 이미지를 snapshot_images에 추가")
                    else:
                        # logger.warning("ROI 박스가 그려진 이미지 생성 실패 - 원본 이미지 사용")
                        pass
                except Exception as e:
                    logger.error(f"ROI 박스 그리기 오류: {str(e)}")
                    import traceback
                    logger.error(traceback.format_exc())
            
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
            # logger.info(f"경보 정보 구성 완료: roi_polygon 구조 = {type(roi_polygon_data)}")
            # if isinstance(roi_polygon_data, dict) and 'alert_boxes' in roi_polygon_data:
            #     logger.info(f"20x20 박스 분석 결과: {len(roi_polygon_data['alert_boxes'])}개 박스")
            #     for i, box in enumerate(roi_polygon_data['alert_boxes'][:3]):  # 처음 3개만 로그
            #         logger.info(f"박스 {i+1}: ID={box['box_id']}, 온도차={box['temp_diff']:.1f}°C, 폴리곤={len(box['polygon'])}개 좌표")
            # else:
            #     logger.info(f"단일 ROI 폴리곤: {len(roi_polygon_data)}개 좌표")
            
            # alert_info를 JSON으로 직렬화하여 크기 확인
            alert_info_json = json.dumps(alert_info, ensure_ascii=False)
            # logger.info(f"alert_info JSON 크기: {len(alert_info_json)} 문자")
            
            # DB에 경보 저장
            query = """
                INSERT INTO tb_alert_history 
                (fk_camera_id, alert_accur_time, alert_type, alert_level, 
                alert_status, alert_info_json, fk_detect_zone_id, 
                fk_process_user_id, create_date, update_date, fk_video_receive_data_id, snapshotImages, popup_close)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            now = datetime.now()
            values = (
                1,  # fk_camera_id
                now,  # alert_accur_time
                alert_type,  # alert_type
                alert_level,  # alert_level (1~4)
                'P001',  # alert_status
                alert_info_json,  # alert_info_json (이미 직렬화됨)
                self._convert_zone_type_to_int(zone_info.get('zone_type', 1)),  # fk_detect_zone_id
                0,  # fk_process_user_id
                now,  # create_date
                now,  # update_date
                video_data_id,  # fk_video_receive_data_id
                json.dumps(snapshot_images, ensure_ascii=False) if snapshot_images else None,  # snapshotImages
                0  # popup_close (고정값 0)
            )
            
            cursor.execute(query, values)
            logger.info(f"시나리오1 경보 생성 완료: Zone {zone_info.get('zone_type', 'unknown')}, {alert_type}: {threshold_value}, Level: {alert_level}, Alert Boxes: {len(alert_boxes) if alert_boxes else 0}")
            
            # MSDB에 tic_data INSERT
            try:
                # 온도 정보 추출
                max_temp = None
                min_temp = None
                avg_temp = None
                
                if 'temperature_stats' in alert_info:
                    max_temp = alert_info['temperature_stats'].get('max')
                    min_temp = alert_info['temperature_stats'].get('min')
                    avg_temp = alert_info['temperature_stats'].get('average')
                
                # 온도 정보가 없으면 alert_boxes에서 추출
                if max_temp is None and alert_boxes and len(alert_boxes) > 0:
                    all_temps = []
                    for box_data in alert_boxes:
                        all_temps.extend(box_data.get('temperatures', []))
                    if all_temps:
                        max_temp = max(all_temps)
                        min_temp = min(all_temps)
                        avg_temp = np.mean(all_temps)
                
                # 파일 경로와 파일 이름 (SFTP 업로드된 파일명 사용)
                # SFTP root_path 사용 (~/ftp_data -> ftp_data로 변환)
                file_path = SFTP_ROOT_PATH.replace('~/', '').replace('~', '')  # ~ 제거
                
                # panorama_snapshot에서 업로드된 파일명 사용
                if panorama_snapshot and panorama_snapshot.get('filename'):
                    file_name = panorama_snapshot['filename']
                    logger.info(f"업로드된 파일명 사용: {file_name}")
                else:
                    # 파일명이 없으면 타임스탬프로 생성 (fallback)
                    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                    file_name = f"{timestamp}_{MSDB_CODE}.jpg"
                    logger.warning(f"업로드된 파일명이 없어 새로 생성: {file_name}")
                
                # 온도 정보가 있으면 MSDB에 INSERT
                if max_temp is not None and min_temp is not None and avg_temp is not None:
                    self.insert_tic_data(max_temp, min_temp, avg_temp, alert_level, file_path, file_name)
                else:
                    logger.warning("온도 정보가 없어 MSDB INSERT 건너뜀")
            except Exception as e:
                logger.error(f"MSDB tic_data INSERT 오류: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
            
            # DB 저장 후 roi_polygon 구조 재확인
            # self.log_roi_polygon_structure(roi_polygon_data)
            
            return True
            
        except Exception as e:
            logger.error(f"시나리오1 경보 생성 오류: {str(e)}")
            return False
        finally:
            if cursor:
                cursor.close()

    def collect_roi_hourly_average_temperatures(self, zone_info, hours=1):
        """
        시나리오2: ROI 영역별로 과거 1시간 평균 온도 데이터 수집
        tb_video_receive_data 테이블에서 data_value의 avg_temp를 사용
        """
        try:
            cursor = self.get_db_cursor()
            if not cursor:
                return None
            
            # zone_info에서 ROI 번호 추출 (zone_type)
            zone_type = zone_info.get('zone_type', 'unknown')
            
            # zone_type에서 ROI 번호 추출 ("Z1" -> 1, "Z001" -> 1, "1" -> 1)
            roi_number = None
            if isinstance(zone_type, str):
                # "Z1", "Z001", "Z01" 등의 형식 처리
                match = re.match(r'Z?0*(\d+)', zone_type)
                if match:
                    try:
                        roi_number = int(match.group(1))  # Z1 -> 1, Z2 -> 2, ...
                    except ValueError:
                        logger.warning(f"시나리오2: zone_type에서 ROI 번호 추출 실패: {zone_type}")
                else:
                    # 숫자만 있는 경우
                    try:
                        roi_number = int(zone_type)  # 1 -> 1, 2 -> 2, ...
                    except ValueError:
                        logger.warning(f"시나리오2: zone_type에서 ROI 번호 추출 실패: {zone_type}")
            elif isinstance(zone_type, int):
                roi_number = zone_type  # 1 -> 1, 2 -> 2, ...
            
            if roi_number is None or roi_number < 0:
                logger.warning(f"시나리오2: ROI 번호를 추출할 수 없습니다. zone_type: {zone_type}")
                return None
            
            # rect 정보 추출 (로깅용)
            rect = None
            if isinstance(zone_info, dict):
                if 'rect' in zone_info:
                    rect = zone_info['rect']
                elif all(key in zone_info for key in ['left', 'right', 'top', 'bottom']):
                    left = zone_info['left']
                    right = zone_info['right']
                    top = zone_info['top']
                    bottom = zone_info['bottom']
                    width = right - left
                    height = bottom - top
                    rect = [left, top, width, height]
            
            # 최근 hours 시간 동안의 tb_video_receive_data 조회
            query = """
                SELECT data_value, create_date 
                FROM tb_video_receive_data 
                WHERE roiNumber = %s
                  AND create_date >= DATE_SUB(NOW(), INTERVAL %s HOUR)
                ORDER BY create_date ASC
            """
            cursor.execute(query, (roi_number, hours))
            results = cursor.fetchall()
            
            if not results:
                logger.warning(f"시나리오2: ROI {zone_info.get('zone_type', 'unknown')} (roiNumber={roi_number}) - 최근 {hours}시간 데이터가 없습니다")
                return None
            
            roi_temps = []
            
            for row in results:
                try:
                    # data_value JSON 파싱
                    data_value_json = row['data_value']
                    if not data_value_json:
                        continue
                    
                    data_value = json.loads(data_value_json) if isinstance(data_value_json, str) else data_value_json
                    
                    # avg_temp 추출
                    avg_temp = data_value.get('avg_temp')
                    if avg_temp is None:
                        logger.warning(f"시나리오2: data_value에 avg_temp가 없습니다: {data_value}")
                        continue
                    
                    avg_temp = float(avg_temp)
                    
                    roi_temps.append({
                        'timestamp': row['create_date'],
                        'average_temperature': avg_temp,
                        'zone_type': zone_info.get('zone_type', 'unknown'),
                        'rect': rect
                    })
                        
                except json.JSONDecodeError as e:
                    logger.error(f"시나리오2: data_value JSON 파싱 오류: {str(e)}, data_value: {data_value_json[:100] if data_value_json else 'None'}")
                    continue
                except Exception as e:
                    logger.error(f"시나리오2: ROI 온도 데이터 추출 오류: {str(e)}")
                    import traceback
                    logger.error(traceback.format_exc())
                    continue
            
            if roi_temps:
                logger.info(f"시나리오2: ROI {zone_info.get('zone_type', 'unknown')} (roiNumber={roi_number}) - {len(roi_temps)}개의 평균온도 데이터 수집 완료")
                return roi_temps
            else:
                logger.warning(f"시나리오2: ROI {zone_info.get('zone_type', 'unknown')} (roiNumber={roi_number}) - 유효한 온도 데이터가 없습니다")
                return None
                
        except Exception as e:
            logger.error(f"시나리오2: ROI 평균온도 데이터 수집 오류: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return None
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

    def analyze_roi_normal_distribution(self, roi_hourly_temps):
        """
        시나리오2: ROI 영역별 정규분포 분석 및 신뢰 구간 계산
        """
        try:
            if not roi_hourly_temps or len(roi_hourly_temps) < 1:
                logger.warning("시나리오2: ROI 영역에 충분한 데이터가 없어 정규분포 분석을 수행할 수 없습니다")
                return None
            
            # 온도 데이터 추출
            temperatures = [temp['average_temperature'] for temp in roi_hourly_temps]
            temps_array = np.array(temperatures)
            
            # 데이터가 1개인 경우, 해당 값 기준으로 신뢰 구간 설정
            if len(temperatures) == 1:
                mean_temp = temperatures[0]
                # 1장의 경우 표준편차를 평균의 5%로 설정 (임시)
                std_temp = mean_temp * 0.05
                if std_temp < 0.5:
                    std_temp = 0.5  # 최소 0.5도
                logger.info(f"시나리오2: 데이터가 1개이므로 표준편차를 평균의 5%({std_temp:.2f}°C)로 설정")
            else:
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
                'max_temp': np.max(temps_array),
                'zone_type': roi_hourly_temps[0].get('zone_type', 'unknown'),
                'rect': roi_hourly_temps[0].get('rect', [0, 0, 0, 0])
            }
            
            logger.info(f"시나리오2: ROI 영역 {distribution_info['zone_type']} 정규분포 분석 완료")
            logger.info(f"  평균온도: {mean_temp:.2f}°C")
            logger.info(f"  표준편차: {std_temp:.2f}°C")
            logger.info(f"  기준라인: {baseline_line:.2f}°C")
            logger.info(f"  95% 신뢰구간: {confidence_interval[0]:.2f}°C ~ {confidence_interval[1]:.2f}°C")
            
            return distribution_info
            
        except Exception as e:
            logger.error(f"시나리오2: ROI 정규분포 분석 오류: {str(e)}")
            return None

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

    def detect_roi_alert_segments(self, temp_matrix, zone_info, roi_distribution):
        """
        시나리오2: ROI 영역을 세로 10등분하여 각 등분의 평균온도와 신뢰도 % 차이 계산
        """
        try:
            if not roi_distribution:
                logger.error("시나리오2: ROI 분포 정보가 없어 등분 검사를 수행할 수 없습니다")
                return []
            
            # zone_info에서 rect 정보 추출
            rect = None
            if isinstance(zone_info, dict):
                if 'rect' in zone_info:
                    rect = zone_info['rect']
                elif all(key in zone_info for key in ['left', 'right', 'top', 'bottom']):
                    left = zone_info['left']
                    right = zone_info['right']
                    top = zone_info['top']
                    bottom = zone_info['bottom']
                    width = right - left
                    height = bottom - top
                    rect = [left, top, width, height]
                else:
                    logger.warning(f"시나리오2: 유효하지 않은 zone_info 형식: {zone_info}")
                    return []
            
            if rect is None:
                logger.warning(f"시나리오2: rect 정보를 추출할 수 없습니다: {zone_info}")
                return []
            
            x, y, w, h = rect
            
            # ROI 영역 추출
            roi_temp = temp_matrix[y:y+h, x:x+w]
            
            # 신뢰 구간 및 통계 정보 가져오기
            confidence_lower, confidence_upper = roi_distribution['confidence_interval']
            baseline_line = roi_distribution['baseline_line']
            mean_temp = roi_distribution['mean']
            std_temp = roi_distribution['std']
            
            # ROI를 수직(세로)으로 10등분 (x축 방향으로 나누기)
            num_segments = 10
            segment_width = w / num_segments
            alert_segments = []
            all_segment_temps = []  # 모든 등분의 평균온도 저장
            
            for seg_idx in range(num_segments):
                # 각 등분의 x 범위 계산 (수직으로 나누기)
                seg_left = int(x + seg_idx * segment_width)
                seg_right = int(x + (seg_idx + 1) * segment_width)
                
                # 마지막 등분은 남은 영역 모두 포함
                if seg_idx == num_segments - 1:
                    seg_right = x + w
                
                # 등분 영역 추출 (수직 세그먼트: 전체 높이, x 범위만)
                segment_temp = roi_temp[:, seg_left - x:seg_right - x]
                valid_temps = segment_temp[~np.isnan(segment_temp)]
                
                if len(valid_temps) == 0:
                    all_segment_temps.append(None)  # 유효한 데이터가 없는 등분
                    continue
                
                # 등분의 평균온도 계산
                segment_avg_temp = float(np.mean(valid_temps))
                all_segment_temps.append(segment_avg_temp)  # 모든 등분의 평균온도 저장
                
                # 정규분포에서의 신뢰도 계산 (Z-score 기반)
                # Z-score = (값 - 평균) / 표준편차
                if std_temp > 0:
                    z_score = (segment_avg_temp - mean_temp) / std_temp
                    # 신뢰도 = 1 - (Z-score의 절대값에 따른 확률)
                    # 95% 신뢰구간 기준: |Z| > 1.96이면 신뢰도 95% 이하
                    from scipy import stats
                    # 양측 검정: P(|Z| > |z_score|)
                    confidence_prob = 2 * (1 - stats.norm.cdf(abs(z_score)))
                    # 신뢰도 % = confidence_prob * 100
                    confidence_percent = confidence_prob * 100
                else:
                    # 표준편차가 0이면 신뢰도 100%로 설정
                    confidence_percent = 100.0
                    z_score = 0.0
                
                # 신뢰도가 낮으면 경보 등분
                if segment_avg_temp < confidence_lower or segment_avg_temp > confidence_upper:
                    alert_segment = {
                        'segment_index': seg_idx,
                        'left': seg_left,
                        'top': y,
                        'right': seg_right,
                        'bottom': y + h,
                        'avg_temperature': segment_avg_temp,
                        'baseline_line': baseline_line,
                        'mean_temp': mean_temp,
                        'confidence_lower': confidence_lower,
                        'confidence_upper': confidence_upper,
                        'confidence_percent': confidence_percent,
                        'z_score': z_score,
                        'temperature_diff': segment_avg_temp - mean_temp
                    }
                    alert_segments.append(alert_segment)
            
            # 10등분 평균온도 리스트 로그 출력
            segment_temps_str = ', '.join([f"{temp:.2f}°C" if temp is not None else "N/A" for temp in all_segment_temps])
            logger.info(f"시나리오2: ROI 영역 {zone_info.get('zone_type', 'unknown')} 10등분 평균온도 리스트: [{segment_temps_str}]")
            
            logger.info(f"시나리오2: ROI 영역 {zone_info.get('zone_type', 'unknown')}에서 "
                       f"신뢰 구간을 벗어난 등분 {len(alert_segments)}개 감지 "
                       f"(신뢰구간: {confidence_lower:.2f}°C ~ {confidence_upper:.2f}°C)")
            
            return alert_segments
            
        except Exception as e:
            logger.error(f"시나리오2: ROI 등분 검사 오류: {str(e)}")
            logger.error(traceback.format_exc())
            return []

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
        시나리오2: ROI 영역별 신뢰 구간 기반 픽셀별 경보
        - 관리자가 설정한 ROI 영역별로 기준선 설정
        - ROI 영역의 1시간(1장) 평균 온도값으로 신뢰 구간 계산
        - ROI 영역 내 픽셀별로 신뢰 구간과 대조
        - 기준을 벗어난 픽셀에 경보 표시
        """
        try:
            logger.info("시나리오2 판단 시작 (ROI 영역별 신뢰 구간 기반 픽셀별 경보)")
            
            # 강제 종료 체크
            if self.force_exit:
                # logger.info("강제 종료 요청됨, 시나리오2 중단")
                return False
            
            # zone_list가 없으면 종료
            if not self.zone_list:
                # logger.warning("시나리오2: zone_list가 없어 처리를 수행할 수 없습니다")
                return False
            
            # 현재 파노라마 데이터에서 온도 매트릭스 생성 (모든 ROI에 공통 사용)
            panorama_data_record = self.get_latest_temperature_data()
            if not panorama_data_record:
                # logger.warning("시나리오2: 현재 파노라마 데이터가 없습니다")
                return False
            
            # 현재 스냅샷 데이터 ID를 인스턴스 변수로 저장
            self.current_snapshot_data_id = panorama_data_record['id']
            
            # 온도 매트릭스 생성 (1920x480 파노라마 크기)
            # panorama_data_json의 colorbarMapping을 사용하여 온도 매트릭스 생성
            temp_matrix = self.create_temperature_matrix(panorama_data_record['panoramaData'])
            if temp_matrix is None:
                logger.error("시나리오2: 온도 매트릭스 생성 실패")
                return False
            
            # 온도 매트릭스 크기 확인 (1920x480)
            expected_width = 1920
            expected_height = 480
            actual_height, actual_width = temp_matrix.shape
            if actual_width != expected_width or actual_height != expected_height:
                logger.warning(f"시나리오2: 온도 매트릭스 크기 불일치: 예상={expected_width}x{expected_height}, 실제={actual_width}x{actual_height}")
            else:
                logger.info(f"시나리오2: 온도 매트릭스 크기 확인: {actual_width}x{actual_height} (1920x480)")
            
            # 스냅샷을 한 번만 캡처 (모든 경보에서 재사용)
            panorama_snapshot = None
            visible_stream_snapshot = None
            
            # 파노라마 이미지 추출
            panorama_snapshot = self.extract_panorama_image(panorama_data_record['panoramaData'])
            # if panorama_snapshot:
            #     logger.info("시나리오2: 파노라마 이미지 추출 성공")
            # else:
            #     logger.warning("시나리오2: 파노라마 이미지 추출 실패")
            
            # 실화상 카메라 스트림 스냅샷 이미지 캡처 (videoType=2) - 한 번만
            visible_stream_snapshot = self.capture_visible_camera_snapshot()
            # if visible_stream_snapshot:
            #     logger.info("시나리오2: 실화상 카메라 스냅샷 캡처 완료")
            # else:
            #     logger.warning("시나리오2: 실화상 카메라 스냅샷 캡처 실패")
            
            # 업로드된 파노라마 스냅샷 사용 (run 메서드에서 업로드됨)
            if self.uploaded_panorama_snapshot:
                panorama_snapshot = self.uploaded_panorama_snapshot
                if self.uploaded_panorama_filename:
                    panorama_snapshot['filename'] = self.uploaded_panorama_filename
                    # logger.info(f"시나리오2: 업로드된 파노라마 스냅샷 사용: {self.uploaded_panorama_filename}")
            
            # 각 ROI 영역별로 처리
            alert_detected = False
            # logger.info(f"시나리오2: 총 {len(self.zone_list)}개 ROI 영역 처리 시작")
            for idx, zone_info in enumerate(self.zone_list, 1):
                # logger.info(f"시나리오2: [{idx}/{len(self.zone_list)}] Zone {zone_info.get('zone_type', 'unknown')} 처리 시작")
                # 강제 종료 체크
                if self.force_exit:
                    logger.info("강제 종료 요청됨, 시나리오2 중단")
                    return False
                
                try:
                    # zone_segment_json에서 실제 ROI 좌표 추출
                    if 'left' in zone_info and 'top' in zone_info and 'right' in zone_info and 'bottom' in zone_info:
                        left = int(zone_info['left'])
                        top = int(zone_info['top'])
                        right = int(zone_info['right'])
                        bottom = int(zone_info['bottom'])
                        
                        # 좌표 검증 및 로깅
                        logger.info(f"시나리오2: Zone {zone_info.get('zone_type', 'unknown')} - 원본 좌표 - left={left}, top={top}, right={right}, bottom={bottom}")
                        
                        # 실제 rect 형식: [x, y, width, height]
                        actual_rect = [
                            left,           # x 좌표
                            top,            # y 좌표
                            right - left,   # width (너비)
                            bottom - top    # height (높이)
                        ]
                        
                        logger.info(f"시나리오2: Zone {zone_info.get('zone_type', 'unknown')} - 변환된 rect - [x={actual_rect[0]}, y={actual_rect[1]}, w={actual_rect[2]}, h={actual_rect[3]}]")
                        logger.info(f"시나리오2: Zone {zone_info.get('zone_type', 'unknown')} - 실제 영역 범위 - x: {left}~{right} ({actual_rect[2]}px), y: {top}~{bottom} ({actual_rect[3]}px)")
                    else:
                        actual_rect = zone_info.get('rect', [0, 0, 320, 240])
                        logger.info(f"시나리오2: Zone {zone_info.get('zone_type', 'unknown')} - 기존 rect 좌표 사용: {actual_rect}")
                    
                    # zone_info에 actual_rect 추가
                    zone_info_copy = zone_info.copy()
                    zone_info_copy['actual_rect'] = actual_rect
                    
                    # 1단계: ROI 영역별로 1시간(1장) 평균 온도 데이터 수집
                    roi_hourly_temps = self.collect_roi_hourly_average_temperatures(zone_info_copy, hours=1)
                    if not roi_hourly_temps:
                        logger.warning(f"시나리오2: Zone {zone_info.get('zone_type', 'unknown')} - ROI 평균 온도 데이터 수집 실패")
                        continue
                    
                    # 2단계: ROI 영역별 신뢰 구간 계산
                    roi_distribution = self.analyze_roi_normal_distribution(roi_hourly_temps)
                    if not roi_distribution:
                        logger.warning(f"시나리오2: Zone {zone_info.get('zone_type', 'unknown')} - ROI 신뢰 구간 계산 실패")
                        continue
                    
                    # 3단계: ROI 영역을 세로 10등분하여 각 등분의 평균온도와 신뢰도 % 차이 계산
                    alert_segments = self.detect_roi_alert_segments(temp_matrix, zone_info_copy, roi_distribution)
                    
                    # 4단계: 벗어난 등분이 있으면 경보 생성
                    if alert_segments:
                        logger.info(f"시나리오2: Zone {zone_info.get('zone_type', 'unknown')}에서 "
                                   f"신뢰 구간을 벗어난 등분 {len(alert_segments)}개 감지")
                        
                        # alert_settings에서 시나리오2 레벨 기준값 가져오기
                        if not self.alert_settings:
                            self.get_alert_settings()
                        
                        if not self.alert_settings or 'alarmLevels' not in self.alert_settings or 'scenario2' not in self.alert_settings['alarmLevels']:
                            logger.error("시나리오2: alert_setting_json의 alarmLevels.scenario2를 찾을 수 없습니다")
                            alert_level = 1  # 기본 레벨
                        else:
                            levels = self.alert_settings['alarmLevels']['scenario2']
                            # levels는 [10, 15, 20, 25] 형식 (온도 차이 °C)
                            
                            # 경보 레벨 결정 (최대 온도 차이에 따라)
                            # 각 등분의 평균온도와 기준선(mean_temp)의 차이 계산
                            max_temp_diff = max(
                                abs(seg['temperature_diff']) for seg in alert_segments
                            )
                            
                            # DB 설정값에 따라 레벨 결정 (온도 차이가 threshold °C 이상이면 해당 레벨)
                            alert_level = None
                            for level, threshold in enumerate(levels):
                                if max_temp_diff >= threshold:
                                    alert_level = level + 1  # 1~4 레벨로 변환
                            
                            if alert_level is None:
                                alert_level = 1  # 기본 레벨 (신뢰 구간을 벗어났으므로)
                            else:
                                threshold_index = alert_level - 1  # 로그 출력용 인덱스
                                logger.info(f"시나리오2 경보 감지: 최대 온도차 {max_temp_diff:.1f}°C >= {levels[threshold_index]}°C (Level {alert_level})")
                        
                        # 기존 평균 온도와 벗어난 정도 로그 기록
                        if roi_distribution:
                            baseline_temp = roi_distribution.get('baseline_line', roi_distribution.get('mean', 0))
                            mean_temp = roi_distribution.get('mean', baseline_temp)
                            
                            # 경보 등분들의 온도 정보 수집
                            alert_temps = [seg['avg_temperature'] for seg in alert_segments]
                            alert_temp_diffs = [abs(seg['temperature_diff']) for seg in alert_segments]
                            
                            if alert_temps:
                                min_alert_temp = min(alert_temps)
                                max_alert_temp = max(alert_temps)
                                avg_alert_temp = sum(alert_temps) / len(alert_temps)
                                max_temp_diff = max(alert_temp_diffs)
                                
                                logger.info(f"시나리오2 경보 발생 - Zone {zone_info.get('zone_type', 'unknown')}: "
                                           f"기존 평균 온도={mean_temp:.2f}°C (기준선={baseline_temp:.2f}°C), "
                                           f"경보 등분 평균 온도={avg_alert_temp:.2f}°C (최소={min_alert_temp:.2f}°C, 최대={max_alert_temp:.2f}°C), "
                                           f"최대 온도 차이={max_temp_diff:.2f}°C, "
                                           f"벗어난 등분 수={len(alert_segments)}개")
                        
                        # 전체 ROI 영역의 온도 통계 계산 (temperature_stats용)
                        roi_temperature_stats = None
                        try:
                            # ROI 영역 추출
                            if 'actual_rect' in zone_info_copy:
                                x, y, w, h = zone_info_copy['actual_rect']
                            else:
                                x, y, w, h = zone_info_copy.get('rect', [0, 0, 640, 240])
                            
                            # 경계 체크
                            if x + w <= temp_matrix.shape[1] and y + h <= temp_matrix.shape[0]:
                                roi_temp = temp_matrix[y:y+h, x:x+w]
                                # NaN 값 제거하고 유효한 온도 데이터만 추출
                                valid_temps = roi_temp[~np.isnan(roi_temp)]
                                
                                if len(valid_temps) > 0:
                                    roi_temperature_stats = {
                                        'min': float(np.min(valid_temps)),
                                        'max': float(np.max(valid_temps)),
                                        'average': float(np.mean(valid_temps)),
                                        'difference': float(np.max(valid_temps) - np.min(valid_temps)),
                                        'total_pixels': len(valid_temps)
                                    }
                                    # logger.info(f"시나리오2: ROI 전체 온도 통계 계산 완료 - "
                                    #           f"min={roi_temperature_stats['min']:.1f}°C, "
                                    #           f"max={roi_temperature_stats['max']:.1f}°C, "
                                    #           f"avg={roi_temperature_stats['average']:.1f}°C")
                        except Exception as e:
                            logger.error(f"시나리오2: ROI 온도 통계 계산 오류: {str(e)}")
                        
                        # 경보 생성
                        self.create_scenario2_alert(
                            panorama_data_record['id'],
                            zone_info_copy,
                            'S002',
                            len(alert_segments),
                            alert_level,
                            alert_segments,  # alert_segments 전달
                            roi_distribution,
                            panorama_snapshot,  # 재사용할 파노라마 스냅샷
                            visible_stream_snapshot,  # 재사용할 실화상 스트림 스냅샷
                            roi_temperature_stats  # 전체 ROI 온도 통계 추가
                        )
                        alert_detected = True
                        
                        logger.info(f"시나리오2 경보 감지: Zone {zone_info.get('zone_type', 'unknown')}, 벗어난 등분 {len(alert_segments)}개")
                    else:
                        # logger.info(f"시나리오2: Zone {zone_info.get('zone_type', 'unknown')}에서 "
                        #            f"신뢰 구간을 벗어난 픽셀이 없습니다")
                        pass
                        
                except Exception as e:
                    logger.error(f"시나리오2: Zone {zone_info.get('zone_type', 'unknown')} 처리 오류: {str(e)}")
                    logger.error(traceback.format_exc())
                    continue
            
            if not alert_detected:
                # logger.info("시나리오2: 모든 ROI 영역에서 경보 조건을 만족하지 않습니다")
                pass
            
            return alert_detected
            
        except Exception as e:
            logger.error(f"시나리오2 판단 오류: {str(e)}")
            logger.error(traceback.format_exc())
            return False

    def create_scenario2_alert(self, video_data_id, zone_info, alert_type, alert_segment_count, alert_level=1, alert_segments=None, roi_distribution=None, panorama_snapshot=None, visible_stream_snapshot=None, roi_temperature_stats=None):
        """
        시나리오2 경보 생성 및 DB 저장 (ROI 영역을 세로 10등분하여 신뢰 구간 벗어난 등분)
        panorama_snapshot과 visible_stream_snapshot이 제공되면 재사용, 없으면 새로 캡처
        """
        try:
            cursor = self.get_db_cursor()
            if not cursor:
                return False
            
            # 파노라마 데이터 조회 (ROI 그리기용)
            panorama_data_record = None
            if panorama_snapshot is None:
                panorama_data_record = self.get_latest_temperature_data()
                if panorama_data_record:
                    logger.info(f"시나리오2: 파노라마 데이터 조회 및 이미지 추출 (새로 캡처)")
                    panorama_snapshot = self.extract_panorama_image(panorama_data_record['panoramaData'])
                else:
                    logger.warning("시나리오2: 파노라마 데이터 조회 실패 - 데이터가 없습니다")
            else:
                logger.info("시나리오2: 파노라마 스냅샷 재사용")
                # ROI 그리기를 위해 파노라마 데이터 조회
                panorama_data_record = self.get_latest_temperature_data()
            
            if visible_stream_snapshot is None:
                logger.info("시나리오2: 실화상 카메라 스트림 스냅샷 캡처 (새로 캡처)")
                visible_stream_snapshot = self.capture_visible_camera_snapshot()
            else:
                logger.info("시나리오2: 실화상 스트림 스냅샷 재사용")
            
            # 스냅샷 이미지 구성 (파노라마 1개 + 실화상 스트림 1개)
            snapshot_images = []
            
            # 파노라마 이미지 추가
            if panorama_snapshot:
                snapshot_images.append(panorama_snapshot)
                logger.info("파노라마 이미지가 snapshot_images에 추가됨")
            else:
                logger.warning("파노라마 이미지가 없어 snapshot_images에 추가되지 않음")
            
            # 실화상 스트림 이미지 추가 (1개만)
            if visible_stream_snapshot:
                snapshot_images.append(visible_stream_snapshot)
                logger.info("실화상 스트림 이미지가 snapshot_images에 추가됨")
            else:
                logger.warning("실화상 스트림 이미지가 없음")
            
            logger.info(f"총 {len(snapshot_images)}개의 스냅샷 이미지 준비 완료 (파노라마: {1 if panorama_snapshot else 0}개, 실화상 스트림: {1 if visible_stream_snapshot else 0}개)")
            
            # 시나리오1처럼 ROI 박스를 파노라마 이미지에 그리기
            if panorama_data_record and panorama_snapshot:
                try:
                    # zone_info에 좌표 정보 추가 (시나리오1과 동일한 방식)
                    zone_info_with_polygon = zone_info.copy()
                    
                    # 좌표 변환 (시나리오1과 동일)
                    if 'zone_segment_coords' not in zone_info_with_polygon:
                        # zone_segment_coords가 없으면 추가
                        if 'actual_rect' in zone_info_with_polygon:
                            x, y, w, h = zone_info_with_polygon['actual_rect']
                            zone_info_with_polygon['zone_segment_coords'] = {
                                'left': x,
                                'top': y,
                                'right': x + w,
                                'bottom': y + h
                            }
                            logger.info(f"시나리오2: actual_rect에서 zone_segment_coords 생성 - left={x}, top={y}, right={x+w}, bottom={y+h}")
                        elif all(key in zone_info_with_polygon for key in ['left', 'top', 'right', 'bottom']):
                            zone_info_with_polygon['zone_segment_coords'] = {
                                'left': zone_info_with_polygon['left'],
                                'top': zone_info_with_polygon['top'],
                                'right': zone_info_with_polygon['right'],
                                'bottom': zone_info_with_polygon['bottom']
                            }
                            logger.info(f"시나리오2: left/top/right/bottom에서 zone_segment_coords 생성")
                    
                    logger.info(f"시나리오2: ROI 박스 그리기 시작")
                    logger.info(f"  - zone_type: {zone_info_with_polygon.get('zone_type', 'N/A')}")
                    logger.info(f"  - left: {zone_info_with_polygon.get('left', 'N/A')}")
                    logger.info(f"  - top: {zone_info_with_polygon.get('top', 'N/A')}")
                    logger.info(f"  - right: {zone_info_with_polygon.get('right', 'N/A')}")
                    logger.info(f"  - bottom: {zone_info_with_polygon.get('bottom', 'N/A')}")
                    logger.info(f"  - actual_rect: {zone_info_with_polygon.get('actual_rect', 'N/A')}")
                    logger.info(f"  - zone_segment_coords: {zone_info_with_polygon.get('zone_segment_coords', 'N/A')}")
                    logger.info(f"  - alert_region: {zone_info_with_polygon.get('alert_region', 'N/A')}")
                    
                    # ROI 박스가 그려진 이미지를 base64로 반환 (경보 등분 정보 포함)
                    roi_drawn_image_base64 = self.draw_roi_on_panorama_and_get_base64(
                        panorama_data_record['panoramaData'],
                        zone_info_with_polygon,
                        alert_segments=alert_segments  # 시나리오2 경보 등분 정보 전달
                    )
                    if roi_drawn_image_base64:
                        logger.info("시나리오2: ROI 박스가 그려진 파노라마 이미지 생성 완료 (base64)")
                        
                        # ROI 박스가 그려진 이미지로 panorama_snapshot 교체
                        if panorama_snapshot:
                            panorama_snapshot['image_data'] = roi_drawn_image_base64
                            panorama_snapshot['roi_drawn'] = True
                            logger.info("시나리오2: snapshot_images의 파노라마 이미지를 ROI 박스가 그려진 이미지로 교체")
                        else:
                            # panorama_snapshot이 없는 경우 새로 생성
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            panorama_snapshot = {
                                'panorama_image': True,
                                'image_type': 'panorama',
                                'timestamp': datetime.now().isoformat(),
                                'image_data': roi_drawn_image_base64,
                                'roi_drawn': True,
                                'filename': f"panorama_roi_{timestamp}.jpg"
                            }
                            snapshot_images.insert(0, panorama_snapshot)  # 맨 앞에 추가
                            logger.info("시나리오2: ROI 박스가 그려진 파노라마 이미지를 snapshot_images에 추가")
                    else:
                        logger.warning("시나리오2: ROI 박스가 그려진 이미지 생성 실패 - 원본 이미지 사용")
                except Exception as e:
                    logger.error(f"시나리오2: ROI 박스 그리기 오류: {str(e)}")
                    import traceback
                    logger.error(traceback.format_exc())
            
            # ROI 폴리곤 생성
            if 'actual_rect' in zone_info:
                main_rect = zone_info['actual_rect']
                main_polygon = self.create_roi_polygon(main_rect)
            else:
                main_rect = zone_info.get('rect', [0, 0, 640, 240])
                main_polygon = self.create_roi_polygon(main_rect)
            
            # alert_segments가 있는 경우 각 등분의 정보 저장
            
            # 경보 정보 구성
            alert_info = {
                'scenario': 'scenario2',
                'alert_type': alert_type,
                'alert_segment_count': alert_segment_count,
                'alert_level': alert_level,
                'zone_type': zone_info.get('zone_type', 'unknown'),
                'rect': main_rect,
                'detection_time': datetime.now().isoformat(),
                'roi_polygon': {
                    'main_roi': {
                        'zone_type': zone_info.get('zone_type', 'unknown'),
                        'rect': main_rect,
                        'polygon': main_polygon
                    },
                    'alert_segments': alert_segments if alert_segments else [],
                    'total_alert_segments': len(alert_segments) if alert_segments else 0
                },
                'roi_distribution': roi_distribution if roi_distribution else None
            }
            
            # 벗어난 등분 통계 정보 추가
            if alert_segments and len(alert_segments) > 0:
                segment_temps = [seg['avg_temperature'] for seg in alert_segments]
                segment_confidences = [seg['confidence_percent'] for seg in alert_segments]
                alert_info['alert_segment_stats'] = {
                    'min_temp': min(segment_temps),
                    'max_temp': max(segment_temps),
                    'avg_temp': np.mean(segment_temps),
                    'min_confidence': min(segment_confidences),
                    'max_confidence': max(segment_confidences),
                    'avg_confidence': np.mean(segment_confidences),
                    'total_segments': len(alert_segments)
                }
                
                # 신뢰 구간 밖 범위 확인
                below_lower = [seg for seg in alert_segments if seg['avg_temperature'] < seg['confidence_lower']]
                above_upper = [seg for seg in alert_segments if seg['avg_temperature'] > seg['confidence_upper']]
                
                alert_info['alert_segment_stats']['below_lower_count'] = len(below_lower)
                alert_info['alert_segment_stats']['above_upper_count'] = len(above_upper)
                
                # alert_segments를 기반으로 경계 박스(bounding box) 생성 (웹 화면 표시용)
                try:
                    segment_lefts = [seg['left'] for seg in alert_segments]
                    segment_rights = [seg['right'] for seg in alert_segments]
                    segment_tops = [seg['top'] for seg in alert_segments]
                    segment_bottoms = [seg['bottom'] for seg in alert_segments]
                    
                    min_x = min(segment_lefts)
                    max_x = max(segment_rights)
                    min_y = min(segment_tops)
                    max_y = max(segment_bottoms)
                    
                    # 경계 박스 정보 저장 (웹 화면 표시용)
                    alert_info['alert_region'] = {
                        'min_x': min_x,
                        'max_x': max_x,
                        'min_y': min_y,
                        'max_y': max_y,
                        'start_x': min_x,
                        'end_x': max_x,
                        'start_y': min_y,
                        'end_y': max_y,
                        'width': max_x - min_x,
                        'height': max_y - min_y
                    }
                    
                    logger.info(f"시나리오2: 경계 박스 생성 완료 - "
                              f"({min_x}, {min_y}) ~ ({max_x}, {max_y}), "
                              f"크기: {max_x - min_x}x{max_y - min_y}")
                except Exception as e:
                    logger.error(f"시나리오2: 경계 박스 생성 오류: {str(e)}")
                    # fallback: ROI 전체 영역 사용
                    alert_info['alert_region'] = {
                        'start_x': main_rect[0],
                        'end_x': main_rect[0] + main_rect[2],
                        'start_y': main_rect[1],
                        'end_y': main_rect[1] + main_rect[3],
                        'width': main_rect[2],
                        'height': main_rect[3]
                    }
            else:
                # alert_segments가 없는 경우 ROI 전체 영역을 경계 박스로 사용
                alert_info['alert_region'] = {
                    'start_x': main_rect[0],
                    'end_x': main_rect[0] + main_rect[2],
                    'start_y': main_rect[1],
                    'end_y': main_rect[1] + main_rect[3],
                    'width': main_rect[2],
                    'height': main_rect[3]
                }
            
            # 전체 ROI 영역의 온도 통계 추가 (시나리오1과 동일한 구조로 저장)
            if roi_temperature_stats:
                alert_info['temperature_stats'] = roi_temperature_stats
                logger.info(f"시나리오2: temperature_stats 저장 완료 - "
                          f"min={roi_temperature_stats['min']:.1f}°C, "
                          f"max={roi_temperature_stats['max']:.1f}°C, "
                          f"average={roi_temperature_stats['average']:.1f}°C")
            else:
                logger.warning("시나리오2: ROI 온도 통계가 없어 temperature_stats를 저장하지 않습니다")
            
            # DB에 경보 저장
            query = """
                INSERT INTO tb_alert_history 
                (fk_camera_id, alert_accur_time, alert_type, alert_level, 
                alert_status, alert_info_json, fk_detect_zone_id, 
                fk_process_user_id, create_date, update_date, fk_video_receive_data_id, snapshotImages, popup_close)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            now = datetime.now()
            values = (
                1,  # fk_camera_id
                now,  # alert_accur_time
                alert_type,  # alert_type
                alert_level,  # alert_level (1~4)
                'P001',  # alert_status
                json.dumps(alert_info, ensure_ascii=False),  # alert_info_json
                self._convert_zone_type_to_int(zone_info.get('zone_type', 1)),  # fk_detect_zone_id
                0,  # fk_process_user_id
                now,  # create_date
                now,  # update_date
                video_data_id,  # fk_video_receive_data_id
                json.dumps(snapshot_images, ensure_ascii=False) if snapshot_images else None,  # snapshotImages
                0  # popup_close (고정값 0)
            )
            
            cursor.execute(query, values)
            logger.info(f"시나리오2 경보 생성 완료: Zone {zone_info.get('zone_type', 'unknown')}, "
                       f"벗어난 등분 {alert_segment_count}개, 레벨={alert_level}")
            
            # MSDB에 tic_data INSERT
            try:
                # 온도 정보 추출
                max_temp = None
                min_temp = None
                avg_temp = None
                
                if 'temperature_stats' in alert_info:
                    max_temp = alert_info['temperature_stats'].get('max')
                    min_temp = alert_info['temperature_stats'].get('min')
                    avg_temp = alert_info['temperature_stats'].get('average')
                
                # roi_temperature_stats에서 추출
                if max_temp is None and roi_temperature_stats:
                    max_temp = roi_temperature_stats.get('max')
                    min_temp = roi_temperature_stats.get('min')
                    avg_temp = roi_temperature_stats.get('average')
                
                # 파일 경로와 파일 이름 (SFTP 업로드된 파일명 사용)
                # SFTP root_path 사용 (~/ftp_data -> ftp_data로 변환)
                file_path = SFTP_ROOT_PATH.replace('~/', '').replace('~', '')  # ~ 제거
                
                # panorama_snapshot에서 업로드된 파일명 사용
                if panorama_snapshot and panorama_snapshot.get('filename'):
                    file_name = panorama_snapshot['filename']
                    logger.info(f"업로드된 파일명 사용: {file_name}")
                else:
                    # 파일명이 없으면 타임스탬프로 생성 (fallback)
                    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                    file_name = f"{timestamp}_{MSDB_CODE}.jpg"
                    logger.warning(f"업로드된 파일명이 없어 새로 생성: {file_name}")
                
                # 온도 정보가 있으면 MSDB에 INSERT
                if max_temp is not None and min_temp is not None and avg_temp is not None:
                    self.insert_tic_data(max_temp, min_temp, avg_temp, alert_level, file_path, file_name)
                else:
                    logger.warning("온도 정보가 없어 MSDB INSERT 건너뜀")
            except Exception as e:
                logger.error(f"MSDB tic_data INSERT 오류: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
            
            return True
            
        except Exception as e:
            logger.error(f"시나리오2 경보 생성 오류: {str(e)}")
            logger.error(traceback.format_exc())
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
                    
                    # 파노라마 데이터 조회 및 SFTP 업로드 (시나리오 체크 전 한 번만)
                    panorama_data_record = self.get_latest_temperature_data()
                    uploaded_filename = None
                    if panorama_data_record:
                        # 파노라마 이미지 추출
                        panorama_snapshot = self.extract_panorama_image(panorama_data_record['panoramaData'])
                        if panorama_snapshot and panorama_snapshot.get('image_data'):
                            # 파일명 생성: YYYYMMDDHHmmss_코드.jpg
                            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                            filename = f"{timestamp}_{SFTP_CODE}.jpg"
                            
                            # SFTP 업로드
                            uploaded_filename = self.upload_image_to_sftp(panorama_snapshot['image_data'], filename)
                            if uploaded_filename:
                                logger.info(f"파노라마 이미지 SFTP 업로드 완료: {uploaded_filename}")
                                # 업로드된 파일명을 인스턴스 변수에 저장
                                self.uploaded_panorama_filename = uploaded_filename
                                self.uploaded_panorama_snapshot = panorama_snapshot
                            else:
                                logger.warning("파노라마 이미지 SFTP 업로드 실패")
                                self.uploaded_panorama_filename = None
                                self.uploaded_panorama_snapshot = None
                        else:
                            self.uploaded_panorama_filename = None
                            self.uploaded_panorama_snapshot = None
                    else:
                        self.uploaded_panorama_filename = None
                        self.uploaded_panorama_snapshot = None
                    
                    # ROI 온도 데이터 추출 및 DB 삽입 (시나리오1,2 실행 전에 모든 ROI에 대해 실행)
                    if panorama_data_record:
                        try:
                            # 온도 매트릭스 생성
                            temp_matrix = self.create_temperature_matrix(panorama_data_record['panoramaData'])
                            if temp_matrix is not None:
                                # 모든 ROI에 대해 온도 데이터 추출 및 DB 삽입
                                for zone_info in self.zone_list:
                                    roi_data = self.extract_roi_temperature_data(temp_matrix, zone_info)
                                    if roi_data:
                                        self.insert_roi_temperature_data(roi_data, zone_info)
                        except Exception as e:
                            logger.error(f"ROI 온도 데이터 DB 삽입 오류: {str(e)}")
                            import traceback
                            logger.error(traceback.format_exc())
                    
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

