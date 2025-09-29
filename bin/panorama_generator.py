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
import hashlib
import random
import string
import paramiko

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

def create_sftp_connection():
    """SFTP 서버 연결"""
    try:
        # SFTP 설정 읽기
        sftp_ip = config.get('SFTP', 'ip')
        sftp_port = config.getint('SFTP', 'port')
        sftp_user = config.get('SFTP', 'user')
        sftp_password = config.get('SFTP', 'password')
        
        logger.info(f"SFTP 서버 연결 시도: {sftp_user}@{sftp_ip}:{sftp_port}")
        
        # SSH 클라이언트 생성
        ssh_client = paramiko.SSHClient()
        ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        # SSH 연결
        ssh_client.connect(
            hostname=sftp_ip,
            port=sftp_port,
            username=sftp_user,
            password=sftp_password,
            timeout=10
        )
        
        # SFTP 클라이언트 생성
        sftp_client = ssh_client.open_sftp()
        
        logger.info("SFTP 서버 연결 성공")
        return ssh_client, sftp_client
        
    except Exception as e:
        logger.error(f"SFTP 서버 연결 실패: {e}")
        return None, None

def close_sftp_connection(ssh_client, sftp_client):
    """SFTP 연결 종료"""
    try:
        if sftp_client:
            sftp_client.close()
        if ssh_client:
            ssh_client.close()
        logger.info("SFTP 연결 종료 완료")
    except Exception as e:
        logger.warning(f"SFTP 연결 종료 중 오류: {e}")

def create_remote_directory_tree(sftp_client, root_path, year, month, day):
    """원격 서버에 년/월/일 폴더 구조 생성"""
    try:
        logger.info(f"폴더 구조 생성 시작: {root_path}")
        
        # 년/월/일 폴더 경로 생성
        year_path = f"{root_path}/{year}"
        month_path = f"{year_path}/{month:02d}"
        day_path = f"{month_path}/{day:02d}"
        
        logger.info(f"생성할 경로들: {[year_path, month_path, day_path]}")
        
        # 각 폴더를 순차적으로 생성 (상위 폴더부터)
        paths_to_create = [year_path, month_path, day_path]
        
        for i, path in enumerate(paths_to_create):
            logger.info(f"폴더 생성 시도 {i+1}/{len(paths_to_create)}: {path}")
            
            # 폴더가 이미 존재하는지 확인
            try:
                sftp_client.stat(path)
                logger.info(f"폴더 이미 존재: {path}")
                continue
            except FileNotFoundError:
                logger.info(f"폴더가 존재하지 않음, 생성 시도: {path}")
            except Exception as stat_error:
                logger.warning(f"폴더 확인 중 오류: {stat_error}")
            
            # 폴더 생성 시도
            try:
                sftp_client.mkdir(path)
                logger.info(f"폴더 생성 성공: {path}")
            except Exception as mkdir_error:
                logger.error(f"폴더 생성 실패 {path}: {mkdir_error}")
                
                # 폴더가 이미 존재하는 경우 (Failure 오류)
                if "Failure" in str(mkdir_error):
                    logger.info(f"폴더가 이미 존재함 (Failure 무시): {path}")
                    # 폴더가 실제로 존재하는지 다시 확인
                    try:
                        sftp_client.stat(path)
                        logger.info(f"폴더 존재 확인됨: {path}")
                        continue  # 다음 폴더로 진행
                    except FileNotFoundError:
                        logger.error(f"폴더가 실제로 존재하지 않음: {path}")
                        return None
                # 상위 디렉토리가 없어서 실패한 경우, 단계별로 생성
                elif "No such file" in str(mkdir_error) or "No such file or directory" in str(mkdir_error):
                    logger.info(f"상위 디렉토리부터 단계별 생성 시도: {path}")
                    if not create_directories_step_by_step(sftp_client, path):
                        logger.error(f"단계별 생성 실패: {path}")
                        return None
                    # 단계별 생성 후 다시 시도
                    try:
                        sftp_client.mkdir(path)
                        logger.info(f"폴더 생성 완료 (재시도): {path}")
                    except Exception as retry_error:
                        if "Failure" in str(retry_error):
                            logger.info(f"재시도 시에도 폴더가 이미 존재함: {path}")
                            continue
                        else:
                            logger.error(f"폴더 생성 재시도 실패 {path}: {retry_error}")
                            return None
                elif "Permission denied" in str(mkdir_error):
                    logger.error(f"폴더 생성 권한 없음 {path}: {mkdir_error}")
                    return None
                else:
                    logger.error(f"폴더 생성 실패 (기타 오류) {path}: {mkdir_error}")
                    return None
        
        # 최종 확인
        try:
            sftp_client.stat(day_path)
            logger.info(f"폴더 구조 생성 완료: {day_path}")
            return day_path
        except Exception as final_error:
            logger.error(f"최종 폴더 확인 실패: {day_path}, 오류: {final_error}")
            return None
        
    except Exception as e:
        logger.error(f"원격 폴더 생성 실패: {e}")
        return None

def create_directories_step_by_step(sftp_client, target_path):
    """단계별로 디렉토리 생성 (더 안전한 방법)"""
    try:
        logger.info(f"단계별 디렉토리 생성 시작: {target_path}")
        
        # 경로를 '/'로 분할
        path_parts = target_path.split('/')
        path_parts = [part for part in path_parts if part]  # 빈 문자열 제거
        
        logger.info(f"경로 분할 결과: {path_parts}")
        
        current_path = ''
        
        for i, part in enumerate(path_parts):
            if i == 0 and target_path.startswith('/'):
                # 절대 경로의 첫 번째 부분
                current_path = f"/{part}"
            else:
                # 상대 경로이거나 절대 경로의 나머지 부분
                current_path = f"{current_path}/{part}" if current_path else part
            
            logger.info(f"현재 처리 중인 경로: {current_path}")
            
            try:
                # 현재 경로가 존재하는지 확인
                sftp_client.stat(current_path)
                logger.debug(f"디렉토리 이미 존재: {current_path}")
            except FileNotFoundError:
                # 존재하지 않으면 생성
                try:
                    sftp_client.mkdir(current_path)
                    logger.info(f"디렉토리 생성 완료: {current_path}")
                except Exception as mkdir_error:
                    logger.error(f"디렉토리 생성 실패 {current_path}: {mkdir_error}")
                    return False
            except Exception as stat_error:
                logger.error(f"디렉토리 확인 실패 {current_path}: {stat_error}")
                return False
        
        logger.info(f"단계별 디렉토리 생성 완료: {target_path}")
        return True
        
    except Exception as e:
        logger.error(f"단계별 디렉토리 생성 실패: {e}")
        return False

def create_parent_directories(sftp_client, target_path):
    """상위 디렉토리들을 재귀적으로 생성"""
    try:
        logger.info(f"상위 디렉토리 생성 시작: {target_path}")
        
        # 절대 경로인지 확인하고 적절히 처리
        is_absolute = target_path.startswith('/')
        
        # 경로를 '/'로 분할하여 각 단계별로 생성
        path_parts = target_path.split('/')
        
        # 빈 문자열 제거 (split으로 인한 빈 요소들)
        path_parts = [part for part in path_parts if part]
        
        current_path = ''
        
        for i, part in enumerate(path_parts):
            if is_absolute and i == 0:
                # 절대 경로의 첫 번째 부분 (루트)
                current_path = f"/{part}"
            else:
                # 상대 경로이거나 절대 경로의 나머지 부분
                current_path = f"{current_path}/{part}" if current_path else part
            
            try:
                # 현재 경로가 존재하는지 확인
                sftp_client.stat(current_path)
                logger.debug(f"상위 폴더 이미 존재: {current_path}")
            except FileNotFoundError:
                # 존재하지 않으면 생성
                try:
                    sftp_client.mkdir(current_path)
                    logger.info(f"상위 폴더 생성 완료: {current_path}")
                except Exception as mkdir_error:
                    logger.error(f"상위 폴더 생성 실패 {current_path}: {mkdir_error}")
                    # 권한 오류인 경우 더 자세한 정보 출력
                    if "Permission denied" in str(mkdir_error):
                        logger.error(f"권한 없음: {current_path}")
                    elif "Failure" in str(mkdir_error):
                        logger.error(f"SFTP 서버 오류: {current_path}")
                    return False
            except Exception as stat_error:
                logger.error(f"경로 확인 실패 {current_path}: {stat_error}")
                return False
        
        logger.info(f"상위 디렉토리 생성 완료: {target_path}")
        return True
        
    except Exception as e:
        logger.error(f"상위 디렉토리 생성 실패: {e}")
        return False

def upload_panorama_to_sftp(panorama_base64, timestamp):
    """파노라마 이미지를 SFTP 서버에 업로드"""
    try:
        # SFTP 연결
        ssh_client, sftp_client = create_sftp_connection()
        if not sftp_client:
            return False
        
        try:
            # 설정에서 SFTP 정보 읽기
            root_path = config.get('SFTP', 'root_path')
            
            # 타임스탬프에서 년/월/일 추출
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            year = dt.year
            month = dt.month
            day = dt.day
            hour = dt.hour
            minute = dt.minute
            second = dt.second
            
            # 홈 디렉토리 기반 경로 처리
            if root_path.startswith('~/'):
                # 홈 디렉토리 경로를 절대 경로로 변환
                relative_path = root_path[2:]  # ~/ 제거
                
                # 여러 가능한 홈 디렉토리 경로 시도
                possible_home_dirs = [
                    f"/home/{config.get('SFTP', 'user')}",  # 일반적인 홈 디렉토리
                    f"/home/akj",  # 하드코딩된 사용자명
                    "/home",  # 홈 디렉토리 루트
                    "/tmp"  # 임시 디렉토리 (폴백)
                ]
                
                home_dir = None
                for possible_home in possible_home_dirs:
                    try:
                        # 디렉토리가 존재하는지 확인
                        sftp_client.stat(possible_home)
                        home_dir = possible_home
                        logger.info(f"홈 디렉토리 확인: {home_dir}")
                        break
                    except FileNotFoundError:
                        continue
                    except Exception as e:
                        logger.debug(f"홈 디렉토리 확인 실패 {possible_home}: {e}")
                        continue
                
                if home_dir:
                    root_path = f"{home_dir}/{relative_path}"
                    logger.info(f"홈 디렉토리 경로 변환: ~/{relative_path} -> {root_path}")
                else:
                    # 홈 디렉토리를 찾을 수 없는 경우, 상대 경로로 시도
                    logger.warning("홈 디렉토리를 찾을 수 없어 상대 경로로 시도")
                    root_path = relative_path
            
            # ftp_data 폴더가 없으면 생성
            try:
                sftp_client.stat(root_path)
                logger.info(f"폴더 존재 확인: {root_path}")
            except FileNotFoundError:
                logger.info(f"폴더가 없어서 생성 시도: {root_path}")
                try:
                    sftp_client.mkdir(root_path)
                    logger.info(f"폴더 생성 완료: {root_path}")
                except Exception as e:
                    logger.error(f"폴더 생성 실패: {e}")
                    return False
            except Exception as e:
                logger.error(f"폴더 확인 실패: {e}")
                return False
            
            # 파일명 생성: {date_time}_{댐코드}.jpg 형식
            # config.ini에서 댐코드 읽기
            dam_code = config.get('SFTP', 'code', fallback='1001210')
            
            # 날짜시간 형식: YYYYMMDDHHMMSS
            date_time = f"{year:04d}{month:02d}{day:02d}{hour:02d}{minute:02d}{second:02d}"
            
            # 파일명 생성: {date_time}_{댐코드}.jpg
            filename = f"{date_time}_{dam_code}.jpg"
            # ftp_data 폴더에 직접 저장
            remote_file_path = f"{root_path}/{filename}"
            
            # Base64 이미지를 바이너리로 변환
            image_data = base64.b64decode(panorama_base64)
            
            # 임시 파일에 저장
            with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
                temp_file.write(image_data)
                temp_file_path = temp_file.name
            
            try:
                # SFTP로 파일 업로드
                sftp_client.put(temp_file_path, remote_file_path)
                logger.info(f"파노라마 이미지 SFTP 업로드 완료: {remote_file_path}")
                
                # 업로드된 파일 크기 확인
                remote_file_stat = sftp_client.stat(remote_file_path)
                logger.info(f"업로드된 파일 크기: {remote_file_stat.st_size} bytes")
                
                return True
                
            finally:
                # 임시 파일 삭제
                try:
                    os.unlink(temp_file_path)
                except Exception as e:
                    logger.warning(f"임시 파일 삭제 실패: {e}")
        
        finally:
            # SFTP 연결 종료
            close_sftp_connection(ssh_client, sftp_client)
            
    except Exception as e:
        logger.error(f"SFTP 업로드 실패: {e}")
        return False

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
                    time.sleep(3)  # 카메라 이동 대기
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
                
                # 출력 데이터 수집 (타임아웃 설정)
                stdout_data, stderr_data = process.communicate(timeout=30)
                
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
            
            # 현재 시간 생성
            current_time = datetime.now()
            timestamp = current_time.isoformat()
            
            # 파노라마 데이터 구성 (테이블 구조에 맞게 최적화)
            panorama_data = {
                "type": "panorama",
                "timestamp": timestamp,
                "image": panorama_base64,
                "presets": [2, 1, 3],
                "description": "PTZ 프리셋 투어 파노라마",
                "created_at": current_time.strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # panoramaData 필드에 JSON 데이터 저장
            query = "INSERT INTO tb_video_panorama_data (panoramaData) VALUES (%s)"
            cursor.execute(query, (json.dumps(panorama_data, ensure_ascii=False),))
            cursor.close()
            
            logger.info("파노라마 데이터 저장 완료")
            
            # DB 저장 성공 후 SFTP 업로드 수행
            logger.info("SFTP 업로드 시작...")
            if upload_panorama_to_sftp(panorama_base64, timestamp):
                logger.info("SFTP 업로드 성공")
            else:
                logger.warning("SFTP 업로드 실패 (DB 저장은 완료됨)")
            
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
                
                # 프리셋 간 잠시 대기 (연결 안정화)
                if preset_num < 3:  # 마지막 프리셋이 아닌 경우
                    logger.info("다음 프리셋 처리 전 잠시 대기...")
                    time.sleep(2)
            
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
