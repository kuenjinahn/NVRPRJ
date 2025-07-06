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

def load_config():
    config = ConfigParser()
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.ini')
    
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    config.read(config_path, encoding='utf-8')
    return config

# 설정 로드
config = load_config()

# 카메라 설정
CAMERA_IP = config.get('CAMERA', 'ip')
CAMERA_PORT = config.getint('CAMERA', 'port')


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

                                # --- 데이터 파싱 및 DB 저장 ---
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

                                # 해석값 변환 (예시: signed, /10)
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
                                import json
                                data_raw_json = {f"data_{i+1}": v for i, v in enumerate(data_raw_list)}
                                data_value_json = {f"data_{i+1}": v for i, v in enumerate(data_value_list)}
                                data_raw_str = json.dumps(data_raw_json, ensure_ascii=False)
                                data_value_str = json.dumps(data_value_json, ensure_ascii=False)

                                # DB Insert
                                try:
                                    cursor = self.get_db_cursor()
                                    if not cursor:
                                        logger.error("DB 커서 획득 실패")
                                        continue
                                    sql = """
                                        INSERT INTO tb_video_receive_data (fk_camera_id, create_date, data_raw, data_value)
                                        VALUES (1, NOW(), %s, %s)
                                    """
                                    cursor.execute(sql, (data_raw_str, data_value_str))
                                    nvrdb.commit()
                                    logger.info("DB Insert 성공 (JSON)")
                                except Exception as e:
                                    logger.error(f"DB Insert 실패: {e}")
                                    logger.error(traceback.format_exc())

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
        self.send_command_and_receive(cmd,data)


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

