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
import pymysql.err
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
import zipfile
import subprocess
import tempfile
import hashlib
import random
import string
import pickle

# 컬러바 분석 함수 직접 구현
def analyze_colorbar(colorbar_image_path, temp_min, temp_max, num_steps=256):
    """컬러바 이미지를 분석하여 색상-온도 매핑 생성"""
    colorbar_img = cv2.imread(colorbar_image_path)
    if colorbar_img is None:
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
    return color_to_temp_map

def get_temperature_from_color_with_map(pixel_color_bgr, color_map, temp_min, temp_max):
    """픽셀 색상으로부터 온도 추정 (가장 가까운 색상 매핑 사용)"""
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

def create_digest_auth(username, password, method, uri, realm, nonce, qop, nc, cnonce):
    """Digest 인증 헤더 생성"""
    # HA1 = MD5(username:realm:password)
    ha1 = hashlib.md5(f"{username}:{realm}:{password}".encode('utf-8')).hexdigest()
    
    # HA2 = MD5(method:uri)
    ha2 = hashlib.md5(f"{method}:{uri}".encode('utf-8')).hexdigest()
    
    # response = MD5(HA1:nonce:nc:cnonce:qop:HA2)
    response = hashlib.md5(f"{ha1}:{nonce}:{nc}:{cnonce}:{qop}:{ha2}".encode('utf-8')).hexdigest()
    
    return f'Digest username="{username}", realm="{realm}", nonce="{nonce}", uri="{uri}", qop={qop}, nc={nc}, cnonce="{cnonce}", response="{response}"'

def make_digest_request(url, username, password, timeout=10):
    """Digest 인증을 사용한 HTTP 요청"""
    try:
        logger.info(f"[인증] 요청 시작: {url}")
        
        # 먼저 Basic 인증 시도
        logger.info("[인증] Basic 인증 시도")
        response = requests.get(url, auth=(username, password), timeout=timeout)
        
        if response.status_code == 200:
            logger.info(f"[인증] Basic 인증 성공: {response.status_code}")
            return response
        elif response.status_code == 401:
            logger.info(f"[인증] Basic 인증 실패: {response.status_code}")
            
            # Digest 인증 시도
            www_authenticate = response.headers.get('www-authenticate')
            logger.info(f"[인증] WWW-Authenticate 헤더: {www_authenticate}")
            
            if www_authenticate and www_authenticate.startswith('Digest'):
                # Digest 인증 파라미터 파싱
                import re
                realm_match = re.search(r'realm="([^"]+)"', www_authenticate)
                nonce_match = re.search(r'nonce="([^"]+)"', www_authenticate)
                qop_match = re.search(r'qop="([^"]+)"', www_authenticate)
                
                logger.info(f"[인증] Digest 파싱 결과 - realm: {realm_match.group(1) if realm_match else None}, nonce: {nonce_match.group(1) if nonce_match else None}, qop: {qop_match.group(1) if qop_match else None}")
                
                if realm_match and nonce_match and qop_match:
                    realm = realm_match.group(1)
                    nonce = nonce_match.group(1)
                    qop = qop_match.group(1)
                    
                    # cnonce와 nc 생성
                    cnonce = ''.join(random.choices(string.ascii_letters + string.digits, k=32))
                    nc = '00000001'
                    
                    # URI 추출
                    from urllib.parse import urlparse
                    parsed_url = urlparse(url)
                    uri = parsed_url.path + (f"?{parsed_url.query}" if parsed_url.query else "")
                    
                    logger.info(f"[인증] Digest URI: {uri}, cnonce: {cnonce}, nc: {nc}")
                    
                    # Digest 인증 헤더 생성
                    auth_header = create_digest_auth(username, password, 'GET', uri, realm, nonce, qop, nc, cnonce)
                    logger.info(f"[인증] Digest 헤더: {auth_header}")
                    
                    # Digest 인증으로 두 번째 요청
                    logger.info("[인증] Digest 인증 요청 시작")
                    try:
                        return requests.get(url, headers={'Authorization': auth_header}, timeout=timeout)
                    except requests.exceptions.RequestException as digest_error:
                        logger.error(f"[인증] Digest 인증 요청 실패: {digest_error}")
                        raise digest_error
                else:
                    logger.error(f"[인증] Digest 파라미터 파싱 실패 - realm: {bool(realm_match)}, nonce: {bool(nonce_match)}, qop: {bool(qop_match)}")
                    raise requests.exceptions.HTTPError(f"Digest 파라미터 파싱 실패")
            else:
                logger.error(f"[인증] Digest 인증이 아닙니다: {www_authenticate}")
                raise requests.exceptions.HTTPError(f"Digest 인증이 아닙니다: {www_authenticate}")
        else:
            # 401이 아닌 다른 오류
            response.raise_for_status()
    except Exception as e:
        logger.error(f"[인증] 요청 실패: {e}")
        raise

def load_config():
    """설정 파일 로드"""
    config = ConfigParser()
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.ini')
    
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    config.read(config_path, encoding='utf-8')
    return config

def read_ptz_info_ini(preset_number):
    """ptz_info.ini 파일에서 프리셋 값 읽기"""
    try:
        # ptz_info.ini 파일 경로
        ptz_info_path = os.path.join(os.path.dirname(__file__), 'ptz_info.ini')
        
        if not os.path.exists(ptz_info_path):
            logger.error(f"ptz_info.ini 파일을 찾을 수 없습니다: {ptz_info_path}")
            return None
        
        # INI 파일 읽기
        config = ConfigParser()
        config.read(ptz_info_path, encoding='utf-8')
        
        section_name = f'PRESET_{preset_number}'
        if not config.has_section(section_name):
            logger.error(f"프리셋 {preset_number} 섹션을 찾을 수 없습니다")
            return None
        
        # 프리셋 값 읽기
        pan = config.getfloat(section_name, 'pan')
        tilt = config.getfloat(section_name, 'tilt')
        zoom = config.getfloat(section_name, 'zoom')
        
        logger.info(f"프리셋 {preset_number} 값 읽기 성공: Pan={pan}, Tilt={tilt}, Zoom={zoom}")
        return {'pan': pan, 'tilt': tilt, 'zoom': zoom}
        
    except Exception as e:
        logger.error(f"ptz_info.ini 읽기 실패: {e}")
        return None

def call_set_position_api(ip, pan, tilt, zoom, preset_number):
    """setPosition 웹 API 호출 (Digest 인증 사용)"""
    try:
        # 웹 API URL 구성
        api_url = f"http://{ip}:80/api/ptz.cgi?PTZNumber={preset_number}&GotoAbsolutePosition={pan},{tilt},{zoom}"
        
        logger.info(f"웹 API 호출: {api_url}")
        
        # Digest 인증을 사용한 HTTP GET 요청
        response = make_digest_request(api_url, 'root', 'cctv1350!!', timeout=10)
        
        if response.status_code == 200:
            logger.info(f"프리셋 {preset_number} 이동 성공: {response.text}")
            return True
        else:
            logger.error(f"프리셋 {preset_number} 이동 실패: HTTP {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"웹 API 호출 실패: {e}")
        return False

# 설정 로드
config = load_config()

# API 설정
API_BASE_URL = config.get('API', 'base_url', fallback='http://localhost:9001')

# 글로벌 상수 설정
PANORAMA_INTERVAL_SECONDS = 600  # 1시간 = 3600초
PANORAMA_INTERVAL_MINUTES = PANORAMA_INTERVAL_SECONDS // 60  # 60분

# PTZ 프리셋 이동 여부 설정
ENABLE_PRESET_MOVEMENT = True  # True: 실제 이동, False: 이동 없이 대기만
PRESET_WAIT_SECONDS = 7  # 프리셋 이동 비활성화 시 대기 시간 (초)

# 컬러바 온도 설정 (컬러바 이미지에 명시된 온도 범위)
TEMP_MIN_GLOBAL = 35.0  # 최저 온도 (도)
TEMP_MAX_GLOBAL = 51.0  # 최고 온도 (도)

# 컬러바 매핑 샘플링 개수 (속도 개선을 위해 줄임: 기본 256 -> 64)
COLORBAR_NUM_STEPS = 32  # 매핑 개수 (낮을수록 빠르지만 정확도 감소)

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

# 컬러바 분석 함수는 직접 구현되어 있음 (별도 확인 불필요)

# =========================
# PNT Protocol Constants (pnt_server.py와 동일)
# =========================
RMID = 0xB8  # 184 - Request Message ID
TMID = 0xAC  # 172 - Response Message ID
PNT_ID = 0x01  # Device Address (fixed)

# Protocol IDs (PNT 프로토콜 매뉴얼 준수)
PID_PRESET_SAVE = 24    # 0x18 - 프리셋 저장
PID_PRESET_RECALL = 25  # 0x19 - 프리셋 호출
PID_ALARM_RESET = 26    # 0x1A - 알람 리셋 (매뉴얼 표준)
PID_AUTO_SCAN_CMD = 27  # 0x1B - 자동 스캔 명령 (매뉴얼 표준)
PID_PRESET_ACK = 32     # 0x20 - 프리셋 호출 응답 (매뉴얼 표준)
PID_TOUR = 46           # 0x2E - 투어 제어 (1 = start, 0 = stop)
PID_SET_EACH_TOUR_DATA = 222  # 0xDE: [D0=preset(1~8), D1~D2= speed(rpm LSB/MSB), D3=delay(1~255s)]

# 매뉴얼 표준 PID (추가)
PID_PRESET_DATA = 200       # 0xC8 - 프리셋 데이터 (Pan, Tilt, Zoom, Focus)
PID_LIMIT_POSI_DATA = 202   # 0xCA - PAN/TILT 제한 위치 데이터

# Response codes (PNT 프로토콜 표준)
RESPONSE_SUCCESS = 0x00
RESPONSE_ERROR = 0xFF
RESPONSE_INVALID_COMMAND = 0x01
RESPONSE_INVALID_PARAMETER = 0x02
RESPONSE_DEVICE_BUSY = 0x03
RESPONSE_NOT_IMPLEMENTED = 0x04

def calculate_checksum(packet):
    """PNT 프로토콜 체크섬 계산 (pnt_server.py와 동일)"""
    return (256 - (sum(packet) & 0xFF)) & 0xFF

def int_to_le16(n):
    """16비트 정수를 little-endian 바이트 배열로 변환"""
    n &= 0xFFFF
    return [n & 0xFF, (n >> 8) & 0xFF]

def create_pnt_packet(pid, data=None):
    """PNT 패킷 생성 (pnt_server.py와 동일)"""
    if data is None:
        data = []
    packet = [RMID, TMID, PNT_ID, pid, len(data)] + data
    checksum = calculate_checksum(packet)
    return bytes(packet + [checksum])

def parse_pnt_response(response_data):
    """PNT 응답 패킷 파싱"""
    if len(response_data) < 6:
        return None
    
    try:
        # [RMID, TMID, PNT_ID, PID, LEN, DATA..., CHECKSUM]
        rm_id = response_data[0]
        tm_id = response_data[1]
        pnt_id = response_data[2]
        pid = response_data[3]
        data_len = response_data[4]
        
        if len(response_data) < 6 + data_len:
            return None
            
        data = response_data[5:5+data_len]
        checksum = response_data[5+data_len]
        
        # 체크섬 검증
        packet_without_checksum = response_data[:-1]
        expected_checksum = calculate_checksum(packet_without_checksum)
        
        if checksum != expected_checksum:
            logger.warning(f"PNT 응답 체크섬 불일치: expected={expected_checksum:02X}, actual={checksum:02X}")
            return None
        
        return {
            'rm_id': rm_id,
            'tm_id': tm_id,
            'pnt_id': pnt_id,
            'pid': pid,
            'data_len': data_len,
            'data': data,
            'checksum': checksum,
            'valid': True
        }
    except Exception as e:
        logger.error(f"PNT 응답 파싱 실패: {e}")
        return None

class PNTClient:
    """PNT 프로토콜 클라이언트 (pnt_server.py 표준 준수)"""
    
    def __init__(self):
        self.sock = None
        self.connected = False

    def connect(self, host: str, port: int, timeout=5.0):
        """PNT 서버에 연결"""
        try:
            self.close()
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(timeout)
            self.sock.connect((host, port))
            self.sock.settimeout(2.0)  # 응답 대기 타임아웃
            self.connected = True
            logger.info(f"PNT 서버 연결 성공: {host}:{port}")
            return True
        except Exception as e:
            logger.error(f"PNT 서버 연결 실패: {e}")
            self.connected = False
            return False

    def close(self):
        """연결 종료"""
        self.connected = False
        if self.sock:
            try:
                self.sock.close()
                logger.debug("PNT 소켓 연결 종료")
            except Exception as e:
                logger.warning(f"PNT 소켓 종료 중 오류: {e}")
        self.sock = None

    def send_command(self, pid: int, data=None, expect_response=True):
        """PNT 명령 전송 및 응답 수신"""
        if not self.connected or not self.sock:
            self.connected = False  # 연결 상태 업데이트
            raise RuntimeError("PNT 서버에 연결되지 않았습니다.")
        
        try:
            # 패킷 생성 및 전송
            packet = create_pnt_packet(pid, data)
            logger.debug(f"PNT 패킷 전송: {packet.hex()}")
            self.sock.sendall(packet)
            
            if not expect_response:
                return {'success': True, 'message': '명령 전송 완료'}
            
            # 응답 수신
            response_data = self.sock.recv(1024)
            if not response_data:
                logger.warning("PNT 서버로부터 응답 데이터가 없습니다. 연결이 끊어졌을 수 있습니다.")
                self.connected = False
                return {'success': False, 'message': '응답 데이터 없음'}
            
            logger.debug(f"PNT 응답 수신: {response_data.hex()}")
            
            # 응답 파싱
            parsed_response = parse_pnt_response(response_data)
            if not parsed_response:
                return {'success': False, 'message': '응답 파싱 실패'}
            
            # 응답 코드 확인
            if parsed_response['data'] and len(parsed_response['data']) > 0:
                response_code = parsed_response['data'][0]
                if response_code == RESPONSE_SUCCESS:
                    return {'success': True, 'message': '명령 실행 성공', 'response': parsed_response}
                else:
                    error_messages = {
                        RESPONSE_ERROR: '일반 오류',
                        RESPONSE_INVALID_COMMAND: '잘못된 명령',
                        RESPONSE_INVALID_PARAMETER: '잘못된 파라미터',
                        RESPONSE_DEVICE_BUSY: '장치 사용 중',
                        RESPONSE_NOT_IMPLEMENTED: '구현되지 않음'
                    }
                    error_msg = error_messages.get(response_code, f'알 수 없는 오류 (코드: {response_code:02X})')
                    return {'success': False, 'message': f'서버 오류: {error_msg}', 'response': parsed_response}
            else:
                return {'success': True, 'message': '명령 실행 성공', 'response': parsed_response}
                
        except socket.timeout:
            logger.error("PNT 명령 응답 타임아웃")
            self.connected = False  # 타임아웃 시 연결 상태 업데이트
            return {'success': False, 'message': '응답 타임아웃'}
        except ConnectionResetError:
            logger.error("PNT 서버 연결이 리셋되었습니다")
            self.connected = False
            return {'success': False, 'message': '연결 리셋'}
        except BrokenPipeError:
            logger.error("PNT 서버 파이프가 끊어졌습니다")
            self.connected = False
            return {'success': False, 'message': '파이프 끊어짐'}
        except Exception as e:
            logger.error(f"PNT 명령 전송 실패: {e}")
            self.connected = False  # 예외 발생 시 연결 상태 업데이트
            return {'success': False, 'message': f'전송 실패: {str(e)}'}

    def preset_recall(self, preset_number: int):
        """프리셋 호출"""
        logger.info(f"프리셋 {preset_number} 호출 요청")
        result = self.send_command(PID_PRESET_RECALL, [preset_number & 0xFF])
        if result['success']:
            logger.info(f"프리셋 {preset_number} 호출 성공")
        else:
            logger.error(f"프리셋 {preset_number} 호출 실패: {result['message']}")
            # 추가 디버깅 정보
            if 'response' in result and result['response']:
                logger.error(f"PNT 응답 상세: {result['response']}")
        return result

    def preset_save(self, preset_number: int):
        """프리셋 저장"""
        logger.info(f"프리셋 {preset_number} 저장 요청")
        result = self.send_command(PID_PRESET_SAVE, [preset_number & 0xFF])
        if result['success']:
            logger.info(f"프리셋 {preset_number} 저장 성공")
        else:
            logger.error(f"프리셋 {preset_number} 저장 실패: {result['message']}")
        return result

    def tour_start(self):
        """투어 시작"""
        logger.info("투어 시작 요청")
        result = self.send_command(PID_TOUR, [1])
        if result['success']:
            logger.info("투어 시작 성공")
        else:
            logger.error(f"투어 시작 실패: {result['message']}")
        return result

    def tour_stop(self):
        """투어 정지"""
        logger.info("투어 정지 요청")
        result = self.send_command(PID_TOUR, [0])
        if result['success']:
            logger.info("투어 정지 성공")
        else:
            logger.error(f"투어 정지 실패: {result['message']}")
        return result

    def set_tour_step(self, preset_number: int, speed_rpm: int, delay_sec: int):
        """투어 스텝 설정"""
        logger.info(f"투어 스텝 설정: 프리셋={preset_number}, 속도={speed_rpm}rpm, 지연={delay_sec}초")
        
        # 속도를 little-endian 16비트로 변환
        speed_bytes = int_to_le16(speed_rpm)
        delay = max(1, min(255, delay_sec))
        
        data = [preset_number & 0xFF] + speed_bytes + [delay]
        result = self.send_command(PID_SET_EACH_TOUR_DATA, data)
        
        if result['success']:
            logger.info(f"투어 스텝 설정 성공: 프리셋 {preset_number}")
        else:
            logger.error(f"투어 스텝 설정 실패: {result['message']}")
        return result

class PanoramaGenerator:
    """파노라마 이미지 생성기"""
    
    def __init__(self, debug_mode=False):
        self.debug_mode = debug_mode
        self.config = config
        self.running = True
        self.thermal_camera_ip = None
        self.thermal_camera_port = None
        
        # 컬러바 관련 설정
        self.colorbar_image_path = None
        self.color_mapping = None
        self.temp_min = TEMP_MIN_GLOBAL
        self.temp_max = TEMP_MAX_GLOBAL
        
        # 컬러바 이미지 경로 설정 (config에서 가져오거나 기본값 사용)
        # config.ini에 COLORBAR 섹션이 있으면 사용, 없으면 기본 경로 시도
        try:
            self.colorbar_image_path = config.get('COLORBAR', 'image_path', fallback=None)
            if self.colorbar_image_path:
                # 상대 경로를 절대 경로로 변환
                if not os.path.isabs(self.colorbar_image_path):
                    base_dir = os.path.dirname(os.path.dirname(__file__))
                    self.colorbar_image_path = os.path.join(base_dir, self.colorbar_image_path)
                
                # 컬러바 온도 범위 설정 (config에서 가져오거나 기본값 사용)
                self.temp_min = config.getfloat('COLORBAR', 'temp_min', fallback=TEMP_MIN_GLOBAL)
                self.temp_max = config.getfloat('COLORBAR', 'temp_max', fallback=TEMP_MAX_GLOBAL)
                
                logger.info(f"컬러바 이미지 경로: {self.colorbar_image_path}")
                logger.info(f"컬러바 온도 범위: {self.temp_min}°C ~ {self.temp_max}°C")
            else:
                logger.error("컬러바 이미지 경로가 설정되지 않았습니다. 컬러바 기반 온도 측정이 불가능합니다.")
                logger.error("프로그램을 종료합니다.")
                sys.exit(1)
        except Exception as e:
            logger.error(f"컬러바 설정 로드 실패: {e}")
            logger.error("컬러바 기반 온도 측정이 불가능합니다. 프로그램을 종료합니다.")
            sys.exit(1)
        
        # PTZ 이동이 활성화된 경우에만 PTZ 클라이언트 생성
        # 디버그 모드일 때는 프리셋 이동을 건너뛰므로 PTZ 클라이언트 생성하지 않음
        if ENABLE_PRESET_MOVEMENT and not self.debug_mode:
            self.ptz_client = PNTClient()
        else:
            self.ptz_client = None
        
        # 신호 핸들러 등록
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        atexit.register(self.cleanup)
        
        if self.debug_mode:
            logger.info("PanoramaGenerator 초기화 완료 (디버그 모드 - 프리셋 이동 건너뜀)")
        else:
            logger.info("PanoramaGenerator 초기화 완료")

    def signal_handler(self, signum, frame):
        """신호 핸들러 (pnt_server.py와 동일)"""
        signal_names = {
            signal.SIGINT: 'SIGINT (Ctrl+C)',
            signal.SIGTERM: 'SIGTERM'
        }
        signal_name = signal_names.get(signum, f'Signal {signum}')
        logger.info(f"신호 {signal_name} 수신, 종료 중...")
        print(f"🛑 {signal_name} 수신, 프로그램 종료 중...")
        self.running = False

    def cleanup(self):
        """정리 작업 (개선된 에러 처리)"""
        try:
            logger.info("정리 작업 시작...")
            
            # PNT 클라이언트 연결 종료
            if ENABLE_PRESET_MOVEMENT and self.ptz_client:
                try:
                    self.ptz_client.close()
                    logger.info("PNT 클라이언트 연결 종료 완료")
                except Exception as e:
                    logger.warning(f"PNT 클라이언트 종료 중 오류: {e}")
            
            # 데이터베이스 연결 종료
            if nvrdb:
                try:
                    nvrdb.close()
                    logger.info("데이터베이스 연결 종료 완료")
                except Exception as e:
                    logger.warning(f"데이터베이스 종료 중 오류: {e}")
            
            logger.info("정리 작업 완료")
            print("✅ 정리 작업 완료")
        except Exception as e:
            logger.error(f"정리 작업 중 오류: {e}")
            print(f"❌ 정리 작업 중 오류: {e}")

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
        """PTZ 카메라 연결 (개선된 에러 처리)"""
        try:
            if not self.thermal_camera_ip or not self.thermal_camera_port:
                logger.error("열화상 카메라 IP/Port가 설정되지 않았습니다")
                return False
            
            # PNT 서버 연결 시도
            success = self.ptz_client.connect(self.thermal_camera_ip, int(self.thermal_camera_port))
            if success:
                logger.info(f"PTZ 카메라 연결 성공: {self.thermal_camera_ip}:{self.thermal_camera_port}")
                return True
            else:
                logger.error(f"PTZ 카메라 연결 실패: {self.thermal_camera_ip}:{self.thermal_camera_port}")
                return False
        except Exception as e:
            logger.error(f"PTZ 카메라 연결 중 예외 발생: {e}")
            return False

    def move_to_preset(self, preset_number):
        """지정된 프리셋으로 이동 (웹 API 방식)"""
        try:
            # 디버그 모드일 때는 프리셋 이동을 건너뜀
            if self.debug_mode:
                logger.info(f"디버그 모드 - 프리셋 {preset_number} 이동 건너뜀")
                time.sleep(1)  # 짧은 대기 시간
                return True
            
            if ENABLE_PRESET_MOVEMENT:
                logger.info(f"프리셋 {preset_number}로 이동 중...")
                
                # 1. ptz_info.ini에서 프리셋 값 읽기
                preset_values = read_ptz_info_ini(preset_number)
                if not preset_values:
                    logger.error(f"프리셋 {preset_number} 값을 읽을 수 없습니다")
                    return False
                
                # 2. 열화상 카메라 IP 가져오기
                if not self.thermal_camera_ip:
                    logger.error("열화상 카메라 IP가 설정되지 않았습니다")
                    return False
                
                # 3. 웹 API로 프리셋 이동
                success = call_set_position_api(
                    self.thermal_camera_ip,
                    preset_values['pan'],
                    preset_values['tilt'],
                    preset_values['zoom'],
                    preset_number
                )
                
                if success:
                    logger.info(f"프리셋 {preset_number} 이동 성공")
                    time.sleep(7)  # 카메라 이동 대기 (간격 단축 시 충분한 안정화 시간 확보)
                    logger.info(f"프리셋 {preset_number} 이동 완료")
                    return True
                else:
                    logger.error(f"프리셋 {preset_number} 이동 실패")
                    return False
            else:
                logger.info(f"프리셋 이동 비활성화됨 - 프리셋 {preset_number} 위치에서 {PRESET_WAIT_SECONDS}초 대기...")
                time.sleep(PRESET_WAIT_SECONDS)
                logger.info(f"프리셋 {preset_number} 위치 대기 완료")
                return True
        except Exception as e:
            if ENABLE_PRESET_MOVEMENT:
                logger.error(f"프리셋 {preset_number} 이동 중 예외 발생: {e}")
                logger.error(traceback.format_exc())
            else:
                logger.error(f"프리셋 {preset_number} 대기 중 예외 발생: {e}")
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
                
                # 출력 데이터 수집 (타임아웃 설정 - 간격 단축 시 안정성을 위해 증가)
                stdout_data, stderr_data = process.communicate(timeout=45)
                
                # 디버깅을 위한 로그
                if stderr_data:
                    stderr_text = stderr_data.decode('utf-8', errors='ignore')
                    logger.debug(f"FFmpeg stderr for {rtsp_url}: {stderr_text}")
                
                if process.returncode == 0 and stdout_data:
                    # base64로 인코딩
                    image_base64 = base64.b64encode(stdout_data).decode('utf-8')
                    
                    # 이미지 오버레이 제거 (시간 정보와 preset 정보 삭제)
                    # 원본 이미지 그대로 사용
                    
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
        """3개 이미지를 수평으로 머지 (각 이미지 640x480, 최종 1920x480)"""
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
            
            # 각 이미지를 640x480으로 리사이즈
            target_width = 640
            target_height = 480
            resized_images = []
            
            for i, img in enumerate(images):
                # 각 이미지를 640x480으로 리사이즈
                resized_img = cv2.resize(img, (target_width, target_height), interpolation=cv2.INTER_LINEAR)
                resized_images.append(resized_img)
                logger.info(f"이미지 {i+1} 리사이즈 완료: {img.shape[1]}x{img.shape[0]} -> {target_width}x{target_height}")
            
            # 수평으로 머지 (640 * 3 = 1920, 높이 480)
            panorama = np.hstack(resized_images)
            
            # 머지된 이미지 크기 확인
            panorama_height, panorama_width = panorama.shape[:2]
            logger.info(f"머지된 이미지 크기: {panorama_width}x{panorama_height} (예상: 1920x480)")
            
            # 머지된 이미지를 base64로 인코딩
            _, buffer = cv2.imencode('.jpg', panorama, [cv2.IMWRITE_JPEG_QUALITY, 90])
            panorama_base64 = base64.b64encode(buffer).decode('utf-8')
            
            logger.info("이미지 머지 완료")
            return panorama_base64
            
        except Exception as e:
            logger.error(f"이미지 머지 실패: {e}")
            return None

    def _load_colorbar_mapping(self):
        """컬러바 매핑 로드 (lazy loading)"""
        if self.color_mapping is not None:
            return self.color_mapping
        
        if not self.colorbar_image_path or not os.path.exists(self.colorbar_image_path):
            logger.error(f"컬러바 이미지 파일을 찾을 수 없습니다: {self.colorbar_image_path}")
            logger.error("컬러바 기반 온도 측정이 불가능합니다. 프로그램을 종료합니다.")
            sys.exit(1)
        
        try:
            logger.info("컬러바 이미지 분석 시작...")
            self.color_mapping = analyze_colorbar(
                self.colorbar_image_path, 
                self.temp_min, 
                self.temp_max,
                num_steps=COLORBAR_NUM_STEPS  # 매핑 개수 제한으로 속도 개선
            )
            
            if self.color_mapping is None:
                logger.error("컬러바 분석에 실패했습니다.")
                logger.error("컬러바 기반 온도 측정이 불가능합니다. 프로그램을 종료합니다.")
                sys.exit(1)
            
            logger.info(f"컬러바 분석 완료: {len(self.color_mapping)}개 색상-온도 매핑 생성")
            return self.color_mapping
            
        except SystemExit:
            raise  # sys.exit(1) 재발생
        except Exception as e:
            logger.error(f"컬러바 분석 오류: {e}")
            logger.error(traceback.format_exc())
            logger.error("컬러바 기반 온도 측정이 불가능합니다. 프로그램을 종료합니다.")
            sys.exit(1)

    def extract_temperature_from_image(self, panorama_base64):
        """파노라마 이미지에서 온도 데이터 추출 및 최고/최저 온도 계산 (컬러바 분석 기반)"""
        try:
            # base64 이미지를 디코딩하여 OpenCV로 로드
            image_data = base64.b64decode(panorama_base64)
            nparr = np.frombuffer(image_data, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if image is None:
                logger.warning("파노라마 이미지 디코딩 실패 - 온도 계산 건너뜀")
                return None, None
            
            # 이미지 크기 확인 및 검증 (1920x480)
            height, width = image.shape[:2]
            target_width = 1920
            target_height = 480
            
            logger.info(f"파노라마 이미지 크기: {width}x{height}")
            
            # 이미지 크기가 1920x480이 아니면 리사이즈
            if width != target_width or height != target_height:
                logger.warning(f"이미지 크기가 1920x480이 아닙니다. 리사이즈: {width}x{height} -> {target_width}x{target_height}")
                image = cv2.resize(image, (target_width, target_height), interpolation=cv2.INTER_LINEAR)
                width = target_width
                height = target_height
                logger.info(f"이미지 리사이즈 완료: {width}x{height}")
            else:
                logger.info(f"이미지 크기 확인: {width}x{height} (정상)")
            
            # 컬러바 매핑 로드 (필수)
            color_mapping = self._load_colorbar_mapping()
            
            if color_mapping is None:
                logger.error("컬러바 매핑을 로드할 수 없습니다.")
                logger.error("컬러바 기반 온도 측정이 불가능합니다. 프로그램을 종료합니다.")
                sys.exit(1)
            
            logger.info("컬러바 분석 기반 온도 추정 사용")
            
            # 온도 데이터 추출 (1920x480 = 921,600개 모든 픽셀 처리)
            temperatures = []
            sample_interval = 1  # 모든 픽셀 샘플링 (1920x480 = 921,600개)
            
            total_pixels = width * height  # 1920 * 480 = 921,600
            processed_pixels = 0
            progress_interval = max(1, total_pixels // 20)  # 5% 간격으로 진행률 표시
            
            logger.info(f"온도 매트릭스 생성 시작: 총 {total_pixels}개 픽셀 처리 예정")
            
            for y in range(0, height, sample_interval):
                for x in range(0, width, sample_interval):
                    # BGR 이미지에서 픽셀 값 추출
                    pixel = image[y, x]
                    pixel_color_bgr = pixel
                    
                    # 컬러바 분석 기반 온도 추정
                    temperature = get_temperature_from_color_with_map(
                        pixel_color_bgr, 
                        color_mapping, 
                        self.temp_min, 
                        self.temp_max
                    )
                    
                    temperatures.append(temperature)
                    processed_pixels += 1
                    
                    # 진행률 표시 (5% 간격)
                    if processed_pixels % progress_interval == 0 or processed_pixels == total_pixels:
                        progress_percent = (processed_pixels / total_pixels) * 100
                        logger.info(f"온도 매트릭스 생성 진행률: {progress_percent:.1f}% ({processed_pixels:,}/{total_pixels:,} 픽셀)")
            
            # temperatures 크기 확인 (1920x480 = 921,600개)
            expected_count = target_width * target_height  # 1920 * 480 = 921,600
            actual_count = len(temperatures)
            if actual_count != expected_count:
                logger.warning(f"temperatures 크기 불일치: 예상={expected_count}개 (1920x480), 실제={actual_count}개")
            else:
                logger.info(f"temperatures 크기 확인: {actual_count}개 (1920x480 = {expected_count}개)")
            
            if not temperatures:
                logger.warning("온도 데이터가 없습니다")
                return None, None, None
            
            # 최고/최저 온도 계산
            min_temp = min(temperatures)
            max_temp = max(temperatures)
            
            logger.info(f"온도 계산 완료 (컬러바 분석): 최저온도={min_temp:.2f}°C, 최고온도={max_temp:.2f}°C (샘플링: {len(temperatures)}개 픽셀)")
            
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
            
            return min_temp, max_temp, temperatures
            
        except Exception as e:
            logger.error(f"온도 추출 오류: {e}")
            logger.error(traceback.format_exc())
            return None, None, None

    def save_panorama_to_db(self, panorama_base64):
        """파노라마 이미지를 데이터베이스에 저장"""
        try:
            cursor = nvrdb.cursor()
            
            # 현재 시간 생성
            current_time = datetime.now()
            timestamp = current_time.isoformat()
            
            # 파노라마 이미지에서 온도 데이터 추출 및 최고/최저 온도 계산
            # extract_temperature_from_image에서 이미 color_mapping을 로드하므로 재사용
            min_temp, max_temp, temperatures = self.extract_temperature_from_image(panorama_base64)
            
            # temperatures 크기 확인 (1920x480 = 921,600개)
            target_width = 1920
            target_height = 480
            expected_count = target_width * target_height
            
            if temperatures is not None:
                actual_count = len(temperatures)
                if actual_count != expected_count:
                    logger.warning(f"DB 저장 전 temperatures 크기 불일치: 예상={expected_count}개, 실제={actual_count}개")
                else:
                    logger.info(f"DB 저장 전 temperatures 크기 확인: {actual_count}개 (1920x480 = {expected_count}개)")
            else:
                logger.warning("temperatures가 None입니다. DB 저장 시 temperatures 필드가 저장되지 않습니다.")
            
            # temperatures를 zip 압축
            temperatures_compressed = None
            if temperatures is not None:
                try:
                    # temperatures를 JSON 문자열로 변환
                    temperatures_json = json.dumps(temperatures, ensure_ascii=False)
                    
                    # zip 압축
                    zip_buffer = io.BytesIO()
                    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                        zip_file.writestr('temperatures.json', temperatures_json.encode('utf-8'))
                    
                    # base64로 인코딩
                    temperatures_compressed = base64.b64encode(zip_buffer.getvalue()).decode('utf-8')
                    
                    original_size = len(temperatures_json.encode('utf-8'))
                    compressed_size = len(temperatures_compressed.encode('utf-8'))
                    compression_ratio = (1 - compressed_size / original_size) * 100 if original_size > 0 else 0
                    
                    logger.info(f"temperatures 압축 완료: 원본={original_size} bytes ({original_size / 1024 / 1024:.2f} MB), "
                              f"압축={compressed_size} bytes ({compressed_size / 1024 / 1024:.2f} MB), "
                              f"압축률={compression_ratio:.1f}%")
                except Exception as e:
                    logger.error(f"temperatures 압축 실패: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
                    # 압축 실패 시 원본 사용
                    temperatures_compressed = None
            
            # 파노라마 데이터 구성 (테이블 구조에 맞게 최적화)
            panorama_data = {
                "type": "panorama",
                "timestamp": timestamp,
                "image": panorama_base64,
                "temperatures": temperatures_compressed if temperatures_compressed else temperatures,  # zip 압축된 데이터 또는 원본
                "temperatures_compressed": temperatures_compressed is not None,  # 압축 여부 플래그
                "presets": [2, 1, 3],
                "description": "PTZ 프리셋 투어 파노라마",
                "created_at": current_time.strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # 온도 데이터가 추출된 경우에만 추가
            if min_temp is not None and max_temp is not None:
                panorama_data["minTemp"] = round(min_temp, 2)
                panorama_data["maxTemp"] = round(max_temp, 2)
                # logger.info(f"온도 데이터 추가: minTemp={panorama_data['minTemp']}, maxTemp={panorama_data['maxTemp']}")
            
            # panoramaData 필드에 JSON 데이터 저장
            panorama_data_json = json.dumps(panorama_data, ensure_ascii=False)
            json_size = len(panorama_data_json.encode('utf-8'))
            
            
            # DB 저장 시도
            query = "INSERT INTO tb_video_panorama_data (panoramaData) VALUES (%s)"
            try:
                cursor.execute(query, (panorama_data_json,))
                cursor.close()
                logger.info(f"파노라마 데이터 저장 완료 (크기: {json_size} bytes, {json_size / 1024 / 1024:.2f} MB)")
            except pymysql.err.OperationalError as e:
                if "max_allowed_packet" in str(e):
                    logger.error(f"max_allowed_packet 오류: {e}")
                    logger.error(f"JSON 데이터 크기: {json_size} bytes ({json_size / 1024 / 1024:.2f} MB)")
                    logger.error("해결 방법: 서버 설정 파일(my.cnf 또는 my.ini)에서 max_allowed_packet을 증가시키거나, 데이터를 압축/분할하여 저장해야 합니다.")
                    cursor.close()
                    return False
                else:
                    raise
            
            # logger.info("파노라마 데이터 저장 완료")
            
            # SFTP 업로드는 videoAlertCheck.py에서 처리됨
            
            return True
            
        except Exception as e:
            logger.error(f"파노라마 데이터 저장 실패: {e}")
            return False

    def generate_panorama(self):
        """파노라마 생성 메인 로직"""
        try:
            logger.info("파노라마 생성 시작")
            
            # 1. 열화상 카메라 설정 조회 (PTZ 이동이 활성화되고 디버그 모드가 아닌 경우에만)
            if ENABLE_PRESET_MOVEMENT and not self.debug_mode:
                if not self.get_thermal_camera_config():
                    return False
                logger.info("웹 API 방식으로 프리셋 이동을 수행합니다")
            elif self.debug_mode:
                logger.info("디버그 모드 - PTZ 설정 조회 및 프리셋 이동을 건너뜁니다")
            else:
                logger.info("프리셋 이동이 비활성화되어 PTZ 설정 조회를 건너뜁니다")
            
            # 3. 3개 프리셋에서 스냅샷 캡처
            snapshots = []
            for preset_num in [2, 1, 3]:
                logger.info(f"=== 프리셋 {preset_num} 처리 시작 ===")
                
                if not self.move_to_preset(preset_num):
                    logger.error(f"프리셋 {preset_num} 이동 실패")
                    return False
                
                snapshot = self.capture_snapshot(preset_num)
                if snapshot:
                    snapshots.append(snapshot)
                    logger.info(f"프리셋 {preset_num} 스냅샷 캡처 성공")
                else:
                    logger.error(f"프리셋 {preset_num} 스냅샷 캡처 실패")
                    return False
                
                logger.info(f"=== 프리셋 {preset_num} 처리 완료 ===")
                
                # 프리셋 간 잠시 대기 (연결 안정화 및 간격 단축 시 충분한 대기 시간)
                if preset_num < 3:  # 마지막 프리셋이 아닌 경우
                    logger.info("다음 프리셋 처리 전 잠시 대기...")
                    time.sleep(3)  # 2초 → 3초로 증가 (연결 안정화)
            
            # 4. 3개 이미지를 수평으로 머지
            panorama_base64 = self.merge_images_horizontally(snapshots)
            if not panorama_base64:
                logger.error("이미지 머지 실패")
                return False
            
            # 5. 데이터베이스에 저장
            if not self.save_panorama_to_db(panorama_base64):
                logger.error("데이터베이스 저장 실패")
                return False
            
            # 6. 파노라마 생성 완료 후 프리셋 1번으로 이동
            if ENABLE_PRESET_MOVEMENT:
                logger.info("파노라마 생성 완료 후 프리셋 1번으로 이동")
                if not self.move_to_preset(1):
                    logger.warning("프리셋 1번 이동 실패 (파노라마 생성은 완료됨)")
                else:
                    logger.info("프리셋 1번 이동 완료")
            else:
                logger.info("프리셋 이동이 비활성화되어 홈 위치 이동을 건너뜁니다")
            
            logger.info("파노라마 생성 완료")
            return True
            
        except Exception as e:
            logger.error(f"파노라마 생성 중 오류: {e}")
            logger.error(traceback.format_exc())
            return False

    def run_scheduler(self):
        """스케줄러 실행 (설정된 간격마다)"""
        if self.debug_mode:
            movement_status = "디버그 모드 (건너뜀)"
        else:
            movement_status = "활성화" if ENABLE_PRESET_MOVEMENT else "비활성화"
        logger.info(f"파노라마 생성 스케줄러 시작 (간격: {PANORAMA_INTERVAL_MINUTES}분, 프리셋 이동: {movement_status})")
        
        # 중복 실행 방지를 위한 플래그
        self.is_generating = False
        
        while self.running:
            try:
                # 이전 파노라마 생성이 진행 중이면 대기
                if self.is_generating:
                    logger.warning("이전 파노라마 생성이 진행 중입니다. 10초 대기 후 다시 확인합니다...")
                    time.sleep(10)
                    continue
                
                current_time = datetime.now()
                logger.info(f"현재 시간: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
                
                # 파노라마 생성 시작 시간 기록
                start_time = time.time()
                self.is_generating = True
                
                try:
                    # 파노라마 생성 실행
                    if self.generate_panorama():
                        logger.info("파노라마 생성 성공")
                    else:
                        logger.error("파노라마 생성 실패")
                finally:
                    # 생성 완료 플래그 해제
                    self.is_generating = False
                
                # 실제 소요 시간 계산
                elapsed_time = time.time() - start_time
                logger.info(f"파노라마 생성 소요 시간: {elapsed_time:.2f}초")
                
                # 다음 실행까지 대기 (생성 시간을 고려하여 조정)
                remaining_time = max(0, PANORAMA_INTERVAL_SECONDS - int(elapsed_time))
                if remaining_time > 0:
                    logger.info(f"다음 실행까지 {remaining_time}초 ({remaining_time // 60}분) 대기...")
                    for i in range(remaining_time):
                        if not self.running:
                            break
                        time.sleep(1)
                else:
                    logger.warning(f"파노라마 생성 시간({elapsed_time:.2f}초)이 설정된 간격({PANORAMA_INTERVAL_SECONDS}초)보다 깁니다. 즉시 다음 실행을 시작합니다.")
                
            except KeyboardInterrupt:
                logger.info("사용자에 의해 중단됨")
                break
            except Exception as e:
                logger.error(f"스케줄러 실행 중 오류: {e}")
                logger.error(traceback.format_exc())
                self.is_generating = False  # 오류 발생 시 플래그 해제
                time.sleep(60)  # 오류 발생 시 1분 대기 후 재시도

def main():
    """메인 함수 (개선된 예외 처리)"""
    parser = argparse.ArgumentParser(description='파노라마 이미지 생성 프로그램')
    parser.add_argument('--debug', action='store_true', help='디버그 모드')
    parser.add_argument('--once', action='store_true', help='한 번만 실행')
    args = parser.parse_args()
    
    generator = None
    try:
        print("🚀 파노라마 생성기 시작...")
        logger.info("파노라마 생성기 프로그램 시작")
        
        generator = PanoramaGenerator(debug_mode=args.debug)
        
        # 데이터베이스 연결
        if not generator.connect_database():
            logger.error("데이터베이스 연결 실패")
            print("❌ 데이터베이스 연결 실패")
            return 1
        
        if args.once:
            # 한 번만 실행
            if args.debug:
                logger.info("한 번만 실행 모드 (디버그)")
                print("🔄 한 번만 실행 모드 (디버그 - 프리셋 이동 건너뜀)")
            else:
                logger.info("한 번만 실행 모드")
                print("🔄 한 번만 실행 모드")
            success = generator.generate_panorama()
            if success:
                print("✅ 파노라마 생성 완료")
                return 0
            else:
                print("❌ 파노라마 생성 실패")
                return 1
        else:
            # 스케줄러 실행
            if args.debug:
                print(f"⏰ 스케줄러 모드 시작 (간격: {PANORAMA_INTERVAL_MINUTES}분, 디버그 - 프리셋 이동 건너뜀)")
            else:
                print(f"⏰ 스케줄러 모드 시작 (간격: {PANORAMA_INTERVAL_MINUTES}분)")
            generator.run_scheduler()
            return 0
            
    except KeyboardInterrupt:
        logger.info("사용자에 의해 중단됨 (Ctrl+C)")
        print("🛑 사용자에 의해 중단됨")
        return 0
    except Exception as e:
        logger.error(f"프로그램 실행 중 오류: {e}")
        logger.error(traceback.format_exc())
        print(f"❌ 프로그램 실행 중 오류: {e}")
        return 1
    finally:
        if generator:
            try:
                generator.cleanup()
            except Exception as e:
                logger.error(f"정리 작업 중 오류: {e}")
                print(f"⚠️ 정리 작업 중 오류: {e}")

if __name__ == "__main__":
    sys.exit(main())
