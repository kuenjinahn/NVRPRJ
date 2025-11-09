# -*- coding:utf-8 -*-
# 한글 주석 처리
__author__ = 'bychem'

import logging
import time
import json
import os
import sys
from logging.handlers import RotatingFileHandler
from configparser import ConfigParser
from pathlib import Path
import pymysql
from datetime import datetime, timedelta

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
    def __init__(self):
        self.config = config

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
            table_name = 'dubhrdamtif'
            
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
                FROM `{table_name}` 
                WHERE `DAMCD` = %s 
                AND `obsdh` > DATE_FORMAT(DATE_SUB(NOW(), INTERVAL 1 HOUR), '%%Y%%m%%d%%H')
                ORDER BY `obsdh` DESC
                LIMIT 1
            """
            
            logger.info(f"MSDB (MariaDB) 쿼리 실행: DAMCD = {MSDB_CODE}, 테이블 = {table_name}")
            cursor.execute(query, (MSDB_CODE,))
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

    def run(self):
        """메인 실행 루프 - 1분마다 댐 데이터 조회 및 업데이트"""
        logger.info("VideoDataReceiver 시작 (1분 간격 댐 데이터 업데이트)")
        
        while True:
            try:
                # 댐 데이터 조회 및 업데이트
                self.process_dam_data()
                
                # 1분 대기
                logger.info("1분 대기 중...")
                time.sleep(60)
                
            except KeyboardInterrupt:
                logger.info("사용자에 의해 중단됨")
                break
            except Exception as e:
                logger.error(f"메인 루프 오류: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
                time.sleep(60)  # 오류 발생 시 1분 대기 후 재시도
            finally:
                # 연결 종료
                self.disconnect_msdb()
                self.disconnect_nvrdb()


if __name__ == "__main__":
    try:
        dataReceiver = VideoDataReceiver()
        dataReceiver.run()
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
