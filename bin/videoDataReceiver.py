# -*- coding:utf-8 -*-
# 한글 주석 처리
__author__ = 'bychem'

import logging
import time
import json
import os
import sys
import subprocess
from logging.handlers import RotatingFileHandler
from configparser import ConfigParser
from pathlib import Path
import pymysql
from datetime import datetime, timedelta
try:
    import urllib.request
    import urllib.error
except ImportError:
    import urllib2 as urllib

def load_config():
    config = ConfigParser()
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.ini')
    
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    config.read(config_path, encoding='utf-8')
    return config

# 설정 로드
config = load_config()

### MSDB 연결정보 ####
MSDB_IP = config.get('MSDB', 'ip')
MSDB_PORT = config.getint('MSDB', 'port')
MSDB_USER = config.get('MSDB', 'user')
MSDB_PASSWORD = config.get('MSDB', 'password')
MSDB_DB = config.get('MSDB', 'dbname')
MSDB_CODE = config.get('MSDB', 'code')
msdb_conn = None
########################

### nvrdb 연결정보 (tb_event_setting 업데이트용) ####
DBSERVER_IP = config.get('DATABASE', 'host')
DBSERVER_PORT = config.getint('DATABASE', 'port')
DBSERVER_USER = config.get('DATABASE', 'user')
DBSERVER_PASSWORD = config.get('DATABASE', 'password')
DBSERVER_DB = config.get('DATABASE', 'database')
DBSERVER_CHARSET = config.get('DATABASE', 'charset')
nvrdb = None
########################

### Health Check 설정 ####
WEB_IP = config.get('WEB', 'ip', fallback='localhost')
WEB_PORT = config.getint('WEB', 'port', fallback=9091)
UI_PORT = 9092  # UI 서버 포트 (기본값)
ALIVE_URL = "http://{}:{}/api/system/alive".format(WEB_IP, WEB_PORT)
UI_PING_URL = "http://{}:{}/ping".format(WEB_IP, UI_PORT)
HEALTH_CHECK_INTERVAL = 5  # 5초마다 체크
HEALTH_CHECK_TIMEOUT = 3  # 3초 타임아웃
MAX_FAIL_COUNT = 2  # 2회 연속 실패 시 재시작
health_check_fail_count = 0
ui_health_check_fail_count = 0  # UI 서버 실패 카운트
last_health_check_log_time = 0  # 마지막 health check 로그 시간
HEALTH_CHECK_LOG_INTERVAL = 60  # 성공 시 60초마다 한 번씩만 로그 기록
########################

# 로깅 설정 - 실행 파일의 현재 폴더에 로그 기록
project_root = os.path.dirname(os.path.dirname(__file__))
log_dir = Path(project_root)
log_dir.mkdir(exist_ok=True)
log_file_name = config.get('LOGGING', 'log_file', fallback='video_data_receiver.log')
log_file = log_dir / log_file_name

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
    def __init__(self):
        self.config = config
        self.project_dir = os.path.dirname(os.path.dirname(__file__))

    def connect_to_msdb(self):
        """MSDB에 연결"""
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

    def connect_to_nvrdb(self):
        """nvrdb에 연결 (tb_event_setting 업데이트용)"""
        global nvrdb
        try:
            if nvrdb is not None:
                try:
                    cursor = nvrdb.cursor()
                    cursor.execute('SELECT 1')
                    cursor.close()
                    return True
                except Exception as e:
                    logger.error(f"nvrdb connection check failed: {str(e)}")
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
            logger.info("nvrdb connected successfully")
            return True
        except Exception as e:
            logger.error(f'nvrdb connection failed: {str(e)}')
            logger.error(f'Connection params: host={DBSERVER_IP}, port={DBSERVER_PORT}, user={DBSERVER_USER}, db={DBSERVER_DB}')
            nvrdb = None
            return False

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

    def disconnect_nvrdb(self):
        """nvrdb 연결 종료"""
        global nvrdb
        try:
            if nvrdb:
                nvrdb.close()
                nvrdb = None
                logger.info("nvrdb disconnected")
        except Exception as e:
            logger.error(f'Error disconnecting nvrdb: {str(e)}')

    def get_dam_data_from_msdb(self):
        """MSDB에서 댐 데이터 조회"""
        try:
            if not self.connect_to_msdb():
                logger.error("MSDB 연결 실패")
                return None

            cursor = msdb_conn.cursor(pymysql.cursors.DictCursor)
            
            # 현재 데이터베이스 확인
            cursor.execute("SELECT DATABASE() as current_db")
            current_db = cursor.fetchone()
            logger.info(f"현재 데이터베이스: {current_db.get('current_db') if current_db else 'None'}")
            
            # 테이블명은 소문자로 처리
            table_name = 'dubhrdamtif_vw'
            
            # 테이블 존재 여부 확인
            try:
                check_query = f"SHOW TABLES LIKE '{table_name}'"
                cursor.execute(check_query)
                if not cursor.fetchone():
                    # 모든 테이블 목록 확인 (디버깅용)
                    try:
                        cursor.execute("SHOW TABLES")
                        tables = cursor.fetchall()
                        logger.warning(f"사용 가능한 테이블 목록: {[list(t.values())[0] for t in tables]}")
                    except:
                        pass
                    logger.error(f"{table_name} 테이블을 찾을 수 없습니다")
                    cursor.close()
                    return None
                logger.info(f"테이블 발견: {table_name}")
            except Exception as e:
                logger.error(f"테이블 확인 실패: {str(e)}")
                cursor.close()
                return None
            
            # MariaDB 형식으로 쿼리 작성 (Oracle의 to_char(sysdate - 1/24, 'yyyymmddhh24')를 MariaDB로 변환)
            # 1시간 전의 날짜시간을 YYYYMMDDHH 형식으로 변환
            # %를 %%로 이스케이프 처리 (pymysql이 %를 플레이스홀더로 인식하므로)
            # 테이블명은 소문자, 필드명은 대문자
            query = f"""
                SELECT `RWL`, `DAMBSARF`, `DQTY` 
                FROM dubhrdamtif_vw 
                WHERE `DAMCD` = {MSDB_CODE}
                AND `obsdh` > DATE_FORMAT(DATE_SUB(NOW(), INTERVAL 1 HOUR), '%%Y%%m%%d%%H')
                ORDER BY `obsdh` DESC
                LIMIT 1
            """
            
            logger.info(f"MSDB (MariaDB) 쿼리 실행: DAMCD = {MSDB_CODE}, 테이블 = {table_name}")
            cursor.execute(query)
            result = cursor.fetchone()
            cursor.close()
            
            if result:
                logger.info(f"댐 데이터 조회 성공: {result}")
                return result
            else:
                logger.warning("조회된 데이터가 없습니다")
                return None
                
        except Exception as e:
            logger.error(f"MSDB 데이터 조회 오류: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return None

    def update_event_setting_system_json(self, dam_data):
        """tb_event_setting의 system_json에 댐 데이터 추가하여 업데이트"""
        try:
            if not self.connect_to_nvrdb():
                logger.error("nvrdb 연결 실패")
                return False

            cursor = nvrdb.cursor(pymysql.cursors.DictCursor)
            
            # 기존 system_json 조회
            select_query = """
                SELECT system_json 
                FROM tb_event_setting 
                ORDER BY id DESC 
                LIMIT 1
            """
            cursor.execute(select_query)
            result = cursor.fetchone()
            
            if not result:
                logger.error("tb_event_setting에 데이터가 없습니다")
                cursor.close()
                return False
            
            # 기존 system_json 파싱
            try:
                system_json = json.loads(result['system_json']) if result['system_json'] else {}
            except json.JSONDecodeError:
                logger.warning("기존 system_json 파싱 실패, 빈 객체로 시작")
                system_json = {}
            
            # 댐 데이터 추가/업데이트
            # RWL: 댐수위, DAMBSARF: 우량, DQTY: 방류량
            if dam_data:
                # Decimal 타입을 float로 변환하여 JSON 직렬화 가능하도록 처리
                from decimal import Decimal
                
                def convert_decimal(value):
                    """Decimal 타입을 float로 변환"""
                    if value is None:
                        return None
                    if isinstance(value, Decimal):
                        return float(value)
                    return value
                
                # 실제 컬럼명: RWL, DAMBSARF, DQTY (대문자)
                rwl_value = dam_data.get('RWL') or dam_data.get('rwl')
                dambasrf_value = dam_data.get('DAMBSARF') or dam_data.get('dambasrf')
                dqty_value = dam_data.get('DQTY') or dam_data.get('dqty')
                
                system_json['rwl'] = convert_decimal(rwl_value)
                system_json['dambasrf'] = convert_decimal(dambasrf_value)
                system_json['dqty'] = convert_decimal(dqty_value)
                
                logger.info(f"댐 데이터 추가: rwl={system_json.get('rwl')}, dambasrf={system_json.get('dambasrf')}, dqty={system_json.get('dqty')}")
            
            # system_json 업데이트
            update_query = """
                UPDATE tb_event_setting 
                SET system_json = %s, update_date = NOW()
                WHERE id = (SELECT id FROM (SELECT id FROM tb_event_setting ORDER BY id DESC LIMIT 1) AS tmp)
            """
            
            system_json_str = json.dumps(system_json, ensure_ascii=False)
            cursor.execute(update_query, (system_json_str,))
            nvrdb.commit()
            cursor.close()
            
            logger.info("tb_event_setting system_json 업데이트 성공")
            return True
            
        except Exception as e:
            logger.error(f"tb_event_setting 업데이트 오류: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False

    def process_dam_data(self):
        """댐 데이터 조회 및 업데이트 처리"""
        try:
            logger.info("댐 데이터 조회 시작")
            
            # MSDB에서 댐 데이터 조회
            dam_data = self.get_dam_data_from_msdb()
            
            if dam_data:
                # tb_event_setting 업데이트
                if self.update_event_setting_system_json(dam_data):
                    logger.info("댐 데이터 업데이트 완료")
                else:
                    logger.error("댐 데이터 업데이트 실패")
            else:
                logger.warning("댐 데이터 조회 실패 또는 데이터 없음")
                
        except Exception as e:
            logger.error(f"댐 데이터 처리 중 오류: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())

    def check_ui_server_health(self):
        """UI 서버 health check"""
        global ui_health_check_fail_count, last_health_check_log_time
        start_time = time.time()
        current_time = time.time()
        try:
            if sys.version_info[0] >= 3:
                # Python 3
                req = urllib.request.Request(UI_PING_URL)
                req.add_header('User-Agent', 'HealthCheck/1.0')
                try:
                    response = urllib.request.urlopen(req, timeout=HEALTH_CHECK_TIMEOUT)
                    response_time = round((time.time() - start_time) * 1000, 2)  # ms
                    status_code = response.getcode()
                    
                    if status_code == 200:
                        # 응답 본문 읽기
                        try:
                            response_data = response.read().decode('utf-8')
                            response_json = json.loads(response_data)
                            ui_port = response_json.get('port', 'N/A')
                        except:
                            ui_port = 'N/A'
                        
                        # 서버 정상
                        if ui_health_check_fail_count > 0:
                            logger.info("[UI Health Check] UI 서버 복구됨 (이전 실패 횟수: {}, 응답시간: {}ms, 포트: {})".format(
                                ui_health_check_fail_count, response_time, ui_port))
                            last_health_check_log_time = current_time
                        elif current_time - last_health_check_log_time >= HEALTH_CHECK_LOG_INTERVAL:
                            # 60초마다 한 번씩 성공 로그 기록
                            logger.info("[UI Health Check] UI 서버 정상 (응답시간: {}ms, 포트: {}, URL: {})".format(
                                response_time, ui_port, UI_PING_URL))
                            last_health_check_log_time = current_time
                        ui_health_check_fail_count = 0
                        return True
                    else:
                        ui_health_check_fail_count += 1
                        logger.warning("[UI Health Check] UI 서버 응답 오류 (HTTP {}, 응답시간: {}ms, 실패 횟수: {}/{}, URL: {})".format(
                            status_code, response_time, ui_health_check_fail_count, MAX_FAIL_COUNT, UI_PING_URL))
                        return False
                except urllib.error.URLError as e:
                    response_time = round((time.time() - start_time) * 1000, 2)  # ms
                    ui_health_check_fail_count += 1
                    logger.warning("[UI Health Check] UI 서버 연결 실패 (응답시간: {}ms, 실패 횟수: {}/{}, URL: {}, 오류: {})".format(
                        response_time, ui_health_check_fail_count, MAX_FAIL_COUNT, UI_PING_URL, str(e)))
                    return False
                except Exception as e:
                    response_time = round((time.time() - start_time) * 1000, 2)  # ms
                    ui_health_check_fail_count += 1
                    logger.error("[UI Health Check] 예외 발생 (응답시간: {}ms, 실패 횟수: {}/{}, URL: {}, 오류: {})".format(
                        response_time, ui_health_check_fail_count, MAX_FAIL_COUNT, UI_PING_URL, str(e)))
                    return False
            else:
                # Python 2
                try:
                    response = urllib.urlopen(UI_PING_URL, timeout=HEALTH_CHECK_TIMEOUT)
                    response_time = round((time.time() - start_time) * 1000, 2)  # ms
                    status_code = response.getcode()
                    
                    if status_code == 200:
                        try:
                            response_data = response.read()
                            response_json = json.loads(response_data)
                            ui_port = response_json.get('port', 'N/A')
                        except:
                            ui_port = 'N/A'
                        
                        if ui_health_check_fail_count > 0:
                            logger.info("[UI Health Check] UI 서버 복구됨 (이전 실패 횟수: {}, 응답시간: {}ms, 포트: {})".format(
                                ui_health_check_fail_count, response_time, ui_port))
                            last_health_check_log_time = current_time
                        elif current_time - last_health_check_log_time >= HEALTH_CHECK_LOG_INTERVAL:
                            logger.info("[UI Health Check] UI 서버 정상 (응답시간: {}ms, 포트: {}, URL: {})".format(
                                response_time, ui_port, UI_PING_URL))
                            last_health_check_log_time = current_time
                        ui_health_check_fail_count = 0
                        return True
                    else:
                        ui_health_check_fail_count += 1
                        logger.warning("[UI Health Check] UI 서버 응답 오류 (HTTP {}, 응답시간: {}ms, 실패 횟수: {}/{}, URL: {})".format(
                            status_code, response_time, ui_health_check_fail_count, MAX_FAIL_COUNT, UI_PING_URL))
                        return False
                except Exception as e:
                    response_time = round((time.time() - start_time) * 1000, 2)  # ms
                    ui_health_check_fail_count += 1
                    logger.warning("[UI Health Check] UI 서버 연결 실패 (응답시간: {}ms, 실패 횟수: {}/{}, URL: {}, 오류: {})".format(
                        response_time, ui_health_check_fail_count, MAX_FAIL_COUNT, UI_PING_URL, str(e)))
                    return False
        except Exception as e:
            response_time = round((time.time() - start_time) * 1000, 2)  # ms
            ui_health_check_fail_count += 1
            logger.error("[UI Health Check] Health check 오류 (응답시간: {}ms, 실패 횟수: {}/{}, URL: {}, 오류: {})".format(
                response_time, ui_health_check_fail_count, MAX_FAIL_COUNT, UI_PING_URL, str(e)))
            import traceback
            logger.error(traceback.format_exc())
            return False

    def check_server_health(self):
        """Node 서버 health check"""
        global health_check_fail_count, last_health_check_log_time
        start_time = time.time()
        current_time = time.time()
        try:
            if sys.version_info[0] >= 3:
                # Python 3
                req = urllib.request.Request(ALIVE_URL)
                req.add_header('User-Agent', 'HealthCheck/1.0')
                try:
                    response = urllib.request.urlopen(req, timeout=HEALTH_CHECK_TIMEOUT)
                    response_time = round((time.time() - start_time) * 1000, 2)  # ms
                    status_code = response.getcode()
                    
                    if status_code == 200:
                        # 응답 본문 읽기 (선택적)
                        try:
                            response_data = response.read().decode('utf-8')
                            response_json = json.loads(response_data)
                            uptime = response_json.get('uptime', 'N/A')
                        except:
                            uptime = 'N/A'
                        
                        # 서버 정상
                        if health_check_fail_count > 0:
                            logger.info("[Health Check] 서버 복구됨 (이전 실패 횟수: {}, 응답시간: {}ms, uptime: {}초)".format(
                                health_check_fail_count, response_time, uptime))
                            last_health_check_log_time = current_time
                        elif current_time - last_health_check_log_time >= HEALTH_CHECK_LOG_INTERVAL:
                            # 60초마다 한 번씩 성공 로그 기록
                            logger.info("[Health Check] 서버 정상 (응답시간: {}ms, uptime: {}초, URL: {})".format(
                                response_time, uptime, ALIVE_URL))
                            last_health_check_log_time = current_time
                        health_check_fail_count = 0
                        return True
                    else:
                        health_check_fail_count += 1
                        logger.warning("[Health Check] 서버 응답 오류 (HTTP {}, 응답시간: {}ms, 실패 횟수: {}/{}, URL: {})".format(
                            status_code, response_time, health_check_fail_count, MAX_FAIL_COUNT, ALIVE_URL))
                        return False
                except urllib.error.URLError as e:
                    response_time = round((time.time() - start_time) * 1000, 2)  # ms
                    health_check_fail_count += 1
                    logger.warning("[Health Check] 서버 연결 실패 (응답시간: {}ms, 실패 횟수: {}/{}, URL: {}, 오류: {})".format(
                        response_time, health_check_fail_count, MAX_FAIL_COUNT, ALIVE_URL, str(e)))
                    return False
                except Exception as e:
                    response_time = round((time.time() - start_time) * 1000, 2)  # ms
                    health_check_fail_count += 1
                    logger.error("[Health Check] 예외 발생 (응답시간: {}ms, 실패 횟수: {}/{}, URL: {}, 오류: {})".format(
                        response_time, health_check_fail_count, MAX_FAIL_COUNT, ALIVE_URL, str(e)))
                    return False
            else:
                # Python 2
                try:
                    response = urllib.urlopen(ALIVE_URL, timeout=HEALTH_CHECK_TIMEOUT)
                    response_time = round((time.time() - start_time) * 1000, 2)  # ms
                    status_code = response.getcode()
                    
                    if status_code == 200:
                        # 응답 본문 읽기 (선택적)
                        try:
                            response_data = response.read()
                            response_json = json.loads(response_data)
                            uptime = response_json.get('uptime', 'N/A')
                        except:
                            uptime = 'N/A'
                        
                        if health_check_fail_count > 0:
                            logger.info("[Health Check] 서버 복구됨 (이전 실패 횟수: {}, 응답시간: {}ms, uptime: {}초)".format(
                                health_check_fail_count, response_time, uptime))
                            last_health_check_log_time = current_time
                        elif current_time - last_health_check_log_time >= HEALTH_CHECK_LOG_INTERVAL:
                            # 60초마다 한 번씩 성공 로그 기록
                            logger.info("[Health Check] 서버 정상 (응답시간: {}ms, uptime: {}초, URL: {})".format(
                                response_time, uptime, ALIVE_URL))
                            last_health_check_log_time = current_time
                        health_check_fail_count = 0
                        return True
                    else:
                        health_check_fail_count += 1
                        logger.warning("[Health Check] 서버 응답 오류 (HTTP {}, 응답시간: {}ms, 실패 횟수: {}/{}, URL: {})".format(
                            status_code, response_time, health_check_fail_count, MAX_FAIL_COUNT, ALIVE_URL))
                        return False
                except Exception as e:
                    response_time = round((time.time() - start_time) * 1000, 2)  # ms
                    health_check_fail_count += 1
                    logger.warning("[Health Check] 서버 연결 실패 (응답시간: {}ms, 실패 횟수: {}/{}, URL: {}, 오류: {})".format(
                        response_time, health_check_fail_count, MAX_FAIL_COUNT, ALIVE_URL, str(e)))
                    return False
        except Exception as e:
            response_time = round((time.time() - start_time) * 1000, 2)  # ms
            health_check_fail_count += 1
            logger.error("[Health Check] Health check 오류 (응답시간: {}ms, 실패 횟수: {}/{}, URL: {}, 오류: {})".format(
                response_time, health_check_fail_count, MAX_FAIL_COUNT, ALIVE_URL, str(e)))
            import traceback
            logger.error(traceback.format_exc())
            return False

    def restart_nvr_services(self):
        """NVR 서비스 재시작"""
        global health_check_fail_count, ui_health_check_fail_count
        try:
            logger.info("=" * 50)
            logger.info("NVR 서비스 재시작 시작")
            logger.info("=" * 50)
            
            # start-nvr.sh 실행
            logger.info("NVR 서버 시작 중...")
            start_script = os.path.join(self.project_dir, 'start-nvr.sh')
            if os.path.exists(start_script):
                try:
                    if hasattr(subprocess, 'run'):
                        # Python 3.5+
                        subprocess.run(['sudo', start_script], cwd=self.project_dir, check=False)
                    else:
                        # Python 2
                        subprocess.call(['sudo', start_script], cwd=self.project_dir)
                except Exception as e:
                    logger.error("start-nvr.sh 실행 오류: {}".format(str(e)))
                time.sleep(3)
            else:
                logger.warning("start-nvr.sh 파일을 찾을 수 없습니다: {}".format(start_script))
            
            # batch-nvr.sh 실행
            logger.info("배치 프로세스 시작 중...")
            batch_script = os.path.join(self.project_dir, 'batch-nvr.sh')
            if os.path.exists(batch_script):
                try:
                    if hasattr(subprocess, 'run'):
                        # Python 3.5+
                        subprocess.run(['sudo', batch_script], cwd=self.project_dir, check=False)
                    else:
                        # Python 2
                        subprocess.call(['sudo', batch_script], cwd=self.project_dir)
                except Exception as e:
                    logger.error("batch-nvr.sh 실행 오류: {}".format(str(e)))
            else:
                logger.warning("batch-nvr.sh 파일을 찾을 수 없습니다: {}".format(batch_script))
            
            logger.info("NVR 서비스 재시작 완료")
            logger.info("=" * 50)
            
            # 실패 카운트 리셋
            health_check_fail_count = 0
            ui_health_check_fail_count = 0
            
        except Exception as e:
            logger.error("NVR 서비스 재시작 오류: {}".format(str(e)))
            import traceback
            logger.error(traceback.format_exc())

    def run(self):
        """메인 실행 루프 - 1분마다 댐 데이터 조회 및 업데이트, 5초마다 health check"""
        global health_check_fail_count, ui_health_check_fail_count
        
        logger.info("VideoDataReceiver 시작")
        logger.info("  - 댐 데이터 업데이트: 1분 간격")
        logger.info("  - Node 서버 Health check: {}초 간격 (URL: {})".format(HEALTH_CHECK_INTERVAL, ALIVE_URL))
        logger.info("  - UI 서버 Health check: {}초 간격 (URL: {})".format(HEALTH_CHECK_INTERVAL, UI_PING_URL))
        logger.info("  - Health check 타임아웃: {}초".format(HEALTH_CHECK_TIMEOUT))
        logger.info("  - 최대 실패 횟수: {}회".format(MAX_FAIL_COUNT))
        logger.info("  - Health check 시작 대기: 10초")
        
        last_dam_data_time = 0
        dam_data_interval = 60  # 1분
        health_check_start_time = time.time()
        health_check_initial_delay = 10  # 처음 시작 시 10초 대기
        health_check_enabled = False  # Health check 활성화 여부
        
        while True:
            try:
                current_time = time.time()
                
                # Health check 시작 여부 확인 (10초 후 시작)
                if not health_check_enabled:
                    if current_time - health_check_start_time >= health_check_initial_delay:
                        health_check_enabled = True
                        logger.info("[Health Check] Health check 시작 (10초 대기 완료)")
                    else:
                        # Health check 시작 전에는 댐 데이터만 처리
                        if current_time - last_dam_data_time >= dam_data_interval:
                            self.process_dam_data()
                            last_dam_data_time = current_time
                        time.sleep(HEALTH_CHECK_INTERVAL)
                        continue
                
                # Health check (5초마다) - Node 서버와 UI 서버 모두 체크
                node_health_ok = self.check_server_health()
                ui_health_ok = self.check_ui_server_health()
                
                # Node 서버 또는 UI 서버 중 하나라도 실패하면 재시작
                if not node_health_ok:
                    if health_check_fail_count >= MAX_FAIL_COUNT:
                        logger.error("Node 서버 응답 없음이 {}회 연속 발생. NVR 서비스 재시작 실행".format(MAX_FAIL_COUNT))
                        self.restart_nvr_services()
                        # 재시작 후 다시 10초 대기
                        health_check_enabled = False
                        health_check_start_time = time.time()
                
                if not ui_health_ok:
                    if ui_health_check_fail_count >= MAX_FAIL_COUNT:
                        logger.error("UI 서버 응답 없음이 {}회 연속 발생. NVR 서비스 재시작 실행".format(MAX_FAIL_COUNT))
                        self.restart_nvr_services()
                        # 재시작 후 다시 10초 대기
                        health_check_enabled = False
                        health_check_start_time = time.time()
                        ui_health_check_fail_count = 0  # 재시작 후 카운트 리셋
                
                # 댐 데이터 조회 및 업데이트 (1분마다)
                if current_time - last_dam_data_time >= dam_data_interval:
                    self.process_dam_data()
                    last_dam_data_time = current_time
                
                # 5초 대기
                time.sleep(HEALTH_CHECK_INTERVAL)
                
            except KeyboardInterrupt:
                logger.info("사용자에 의해 중단됨")
                break
            except Exception as e:
                logger.error(f"메인 루프 오류: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
                time.sleep(HEALTH_CHECK_INTERVAL)  # 오류 발생 시 5초 대기 후 재시도
            finally:
                # 연결 종료 (주기적으로 정리)
                pass


if __name__ == "__main__":
    try:
        dataReceiver = VideoDataReceiver()
        dataReceiver.run()
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
