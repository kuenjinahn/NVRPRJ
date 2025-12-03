#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import locale

# 출력 버퍼링 비활성화 (실시간 로그 출력을 위해)
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

# 시스템 인코딩 설정
if sys.platform.startswith('win'):
    # Windows에서 한글 출력을 위한 인코딩 설정
    try:
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.detach())
        # 버퍼링 비활성화 재적용
        sys.stdout.reconfigure(line_buffering=True)
        sys.stderr.reconfigure(line_buffering=True)
    except:
        pass
    
    # 로케일 설정
    try:
        locale.setlocale(locale.LC_ALL, 'ko_KR.UTF-8')
    except:
        try:
            locale.setlocale(locale.LC_ALL, 'Korean_Korea.UTF8')
        except:
            pass

import shlex
import signal
import subprocess
import threading
import time
import json
import logging
from logging.handlers import RotatingFileHandler
import pymysql
from configparser import ConfigParser
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional


def load_config():
    config = ConfigParser()
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.ini')
    
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    config.read(config_path, encoding='utf-8')
    return config

# 설정 로드
config = load_config()

# 데이터베이스 연결 정보
DBSERVER_IP = config.get('DATABASE', 'host')
DBSERVER_PORT = config.getint('DATABASE', 'port')
DBSERVER_USER = config.get('DATABASE', 'user')
DBSERVER_PASSWORD = config.get('DATABASE', 'password')
DBSERVER_DB = config.get('DATABASE', 'database')
DBSERVER_CHARSET = config.get('DATABASE', 'charset')

# 로깅 설정 - 프로젝트 루트의 ./logs 폴더에 로그 파일 생성
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)  # bin의 상위 디렉토리 (프로젝트 루트)
log_dir = Path(project_root) / 'logs'

# 로그 디렉토리 생성 (상세한 오류 처리)
try:
    log_dir.mkdir(exist_ok=True)
    if not log_dir.exists():
        raise OSError(f"로그 디렉토리 생성 실패: {log_dir}")
    if not os.access(log_dir, os.W_OK):
        raise OSError(f"로그 디렉토리 쓰기 권한 없음: {log_dir}")
except Exception as e:
    # 로그 디렉토리 생성 실패 시 stderr에 출력
    import sys
    sys.stderr.write(f"ERROR: 로그 디렉토리 생성 실패: {e}\n")
    sys.stderr.write(f"  project_root: {project_root}\n")
    sys.stderr.write(f"  script_dir: {script_dir}\n")
    sys.stderr.write(f"  log_dir: {log_dir}\n")
    sys.stderr.flush()
    # 기본 경로로 폴백 (프로젝트 루트)
    log_dir = Path(project_root)
    log_dir.mkdir(exist_ok=True)

log_file = log_dir / 'video_recorder.log'
log_file_str = str(log_file)

# 로그 파일 핸들러 생성 (상세한 오류 처리)
handler = None
try:
    handler = RotatingFileHandler(
        log_file_str,
        maxBytes=1024 * 1024,  # 1MB
        backupCount=5,  # 5개까지 생성, 이후 덮어쓰기
        encoding='utf-8'
    )
    handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
except Exception as e:
    import sys
    sys.stderr.write(f"ERROR: RotatingFileHandler 생성 실패: {e}\n")
    sys.stderr.write(f"  log_file_str: {log_file_str}\n")
    sys.stderr.flush()
    raise

logger = logging.getLogger("VideoRecorder")
logger.setLevel(logging.INFO)

# 기존 핸들러 제거 (중복 방지)
for h in logger.handlers[:]:
    logger.removeHandler(h)

logger.addHandler(handler)

# 로그 파일 생성 확인을 위한 초기 메시지 기록 및 테스트
try:
    # 첫 로그 메시지 기록 (이 시점에 파일이 생성됨)
    logger.info("=" * 80)
    handler.flush()  # 버퍼 강제 플러시
    
    # 파일 생성 확인
    import time
    time.sleep(0.1)  # 파일 시스템 동기화 대기
    
    if log_file.exists():
        logger.info(f"VideoRecorder 로깅 시작 - 로그 파일: {log_file_str}")
        logger.info(f"로그 디렉토리: {log_dir}")
        logger.info(f"프로젝트 루트: {project_root}")
        logger.info(f"스크립트 디렉토리: {script_dir}")
        logger.info("=" * 80)
        handler.flush()
    else:
        # 파일이 생성되지 않은 경우 강제 생성 시도
        import sys
        sys.stderr.write(f"WARNING: 로그 파일이 자동 생성되지 않음: {log_file_str}\n")
        sys.stderr.write(f"  로그 디렉토리 존재: {log_dir.exists()}\n")
        sys.stderr.write(f"  로그 디렉토리 쓰기 가능: {os.access(log_dir, os.W_OK) if log_dir.exists() else False}\n")
        sys.stderr.flush()
        
        try:
            # 강제로 파일 생성
            with open(log_file_str, 'a', encoding='utf-8') as f:
                f.write(f"# Log file created at {datetime.now().isoformat()}\n")
            logger.info(f"VideoRecorder 로깅 시작 - 로그 파일 (강제 생성): {log_file_str}")
            logger.info(f"로그 디렉토리: {log_dir}")
            logger.info(f"프로젝트 루트: {project_root}")
            logger.info(f"스크립트 디렉토리: {script_dir}")
            logger.info("=" * 80)
            handler.flush()
        except Exception as create_error:
            import sys
            import traceback
            sys.stderr.write(f"ERROR: 로그 파일 강제 생성 실패: {create_error}\n")
            sys.stderr.write(traceback.format_exc())
            sys.stderr.flush()
            # 로그 기록은 계속 시도
            logger.error(f"로그 파일 생성 실패, 하지만 로깅은 계속 시도: {create_error}")
except Exception as e:
    # 로그 기록 실패 시 stderr에 출력
    import sys
    import traceback
    sys.stderr.write(f"ERROR: 로그 기록 실패: {e}\n")
    sys.stderr.write(traceback.format_exc())
    sys.stderr.flush()

# print() 출력을 로그 파일에도 기록하도록 래핑
_original_print = print
def print(*args, **kwargs):
    """print() 함수를 래핑하여 콘솔과 로그 파일 모두에 기록"""
    # file 파라미터 확인
    output_file = kwargs.get('file', None)
    # 원본 print() 호출
    _original_print(*args, **kwargs)
    # sys.stdout으로 출력하는 경우에만 로그 파일에도 기록
    # output_file이 None이거나 sys.stdout인 경우 로그에 기록
    if output_file is None or output_file is sys.stdout or (hasattr(output_file, 'name') and output_file.name == '<stdout>'):
        try:
            # sep, end 파라미터 처리
            sep = kwargs.get('sep', ' ')
            end = kwargs.get('end', '\n')
            message = sep.join(str(arg) for arg in args) + (end if end != '\n' else '')
            if message.strip():  # 빈 메시지는 기록하지 않음
                logger.info(message.rstrip())  # 끝의 개행 문자 제거
        except Exception:
            pass  # 로그 기록 실패해도 원본 print는 실행됨

# 🔧 글로벌 설정 변수
# 세그먼트 분할 시간 (초 단위) - DB에서 동적으로 로드됩니다
SPLIT_SECONDS = 600  # 기본값: 600초 (10분) - DB에서 로드 실패 시 사용

# 비트레이트 설정 (DB에서 동적으로 로드됩니다)
DEFAULT_BITRATE = "1024k"  # 기본값 - DB에서 로드 실패 시 사용

print(f"🔧 Global Settings Loaded:")
print(f"  📹 SPLIT_SECONDS: {SPLIT_SECONDS} seconds ({SPLIT_SECONDS/60:.1f} minutes) - Will be updated from DB")
print(f"  📹 DEFAULT_BITRATE: {DEFAULT_BITRATE} - Will be updated from DB")

def load_event_settings():
    """tb_event_setting에서 object_json을 조회하여 녹화 설정을 로드"""
    global SPLIT_SECONDS, DEFAULT_BITRATE
    
    try:
        print("\n" + "=" * 80, flush=True)
        print("🔍 LOADING EVENT SETTINGS FROM DATABASE", flush=True)
        print("=" * 80, flush=True)
        print(f"📊 DB Connection: {DBSERVER_IP}:{DBSERVER_PORT}/{DBSERVER_DB}", flush=True)
        print(f"📊 DB User: {DBSERVER_USER}", flush=True)
        
        # DB 연결
        db_connection = pymysql.connect(
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
        print("✅ Database connection successful", flush=True)
        
        cursor = db_connection.cursor()
        
        # tb_event_setting에서 object_json 조회
        query = "SELECT object_json FROM tb_event_setting LIMIT 1"
        cursor.execute(query)
        result = cursor.fetchone()
        
        if result and result['object_json']:
            print("✅ Found event settings in database", flush=True)
            object_json = json.loads(result['object_json'])
            
            # recording 설정 확인
            recording_config = object_json.get('recording', {})
            print(f"📋 Recording configuration found: {len(recording_config)} settings", flush=True)
            
            # enabled 값에 따라 레코딩 여부 결정
            recording_enabled = recording_config.get('enabled', True)
            status_text = "🟢 ENABLED" if recording_enabled else "🔴 DISABLED"
            print(f"📹 Recording Status: {status_text}", flush=True)
            
            if recording_enabled:
                # recordingSegment 값에 따라 SPLIT_SECONDS 설정
                recording_segment = recording_config.get('recordingSegment', '10')  # 기본값: 10분
                
                # 분 단위를 초 단위로 변환
                segment_mapping = {
                    '1': 60,     # 1분 = 60초
                    '2': 120,    # 2분 = 120초
                    '5': 300,    # 5분 = 300초
                    '10': 600,   # 10분 = 600초
                    '30': 1800,  # 30분 = 1800초
                    '60': 3600   # 1시간 = 3600초
                }
                
                old_split_seconds = SPLIT_SECONDS
                SPLIT_SECONDS = segment_mapping.get(recording_segment, 600)  # 기본값: 10분
                print(f"📹 Segment Duration: {recording_segment}min → {SPLIT_SECONDS}s ({SPLIT_SECONDS/60:.1f} minutes)", flush=True)
                if old_split_seconds != SPLIT_SECONDS:
                    print(f"   🔄 Changed from {old_split_seconds}s to {SPLIT_SECONDS}s", flush=True)
                
                # recodingBitrate 값 설정
                old_bitrate = DEFAULT_BITRATE
                recoding_bitrate = recording_config.get('recodingBitrate', '1024k')
                DEFAULT_BITRATE = recoding_bitrate
                print(f"📹 Video Bitrate: {recoding_bitrate}", flush=True)
                if old_bitrate != DEFAULT_BITRATE:
                    print(f"   🔄 Changed from {old_bitrate} to {DEFAULT_BITRATE}", flush=True)
                
                # 파일 삭제 설정
                delete_days = recording_config.get('recodingFileDeleteDays', 30)
                print(f"📹 File Auto-Delete: {delete_days} days", flush=True)
                
                print("✅ All recording settings loaded successfully", flush=True)
            else:
                print("⚠️ Recording is disabled, using default values", flush=True)
                print(f"   📹 Default SPLIT_SECONDS: {SPLIT_SECONDS}s", flush=True)
                print(f"   📹 Default DEFAULT_BITRATE: {DEFAULT_BITRATE}", flush=True)
            
        else:
            print("⚠️ No object_json found in tb_event_setting", flush=True)
            print("🔄 Using default values:", flush=True)
            print(f"   📹 SPLIT_SECONDS: {SPLIT_SECONDS}s ({SPLIT_SECONDS/60:.1f} minutes)", flush=True)
            print(f"   📹 DEFAULT_BITRATE: {DEFAULT_BITRATE}", flush=True)
            
        cursor.close()
        db_connection.close()
        print("✅ Database connection closed", flush=True)
        
    except Exception as e:
        print(f"❌ Error loading event settings: {e}", flush=True)
        print("🔄 Using default values:", flush=True)
        print(f"   📹 SPLIT_SECONDS: {SPLIT_SECONDS}s ({SPLIT_SECONDS/60:.1f} minutes)", flush=True)
        print(f"   📹 DEFAULT_BITRATE: {DEFAULT_BITRATE}", flush=True)
        print("⚠️ Please check database connection and settings", flush=True)
    
    print("=" * 80, flush=True)
    print("🎯 CURRENT SETTINGS SUMMARY:", flush=True)
    print(f"   📹 SPLIT_SECONDS: {SPLIT_SECONDS} seconds ({SPLIT_SECONDS/60:.1f} minutes)", flush=True)
    print(f"   📹 DEFAULT_BITRATE: {DEFAULT_BITRATE}", flush=True)
    print("=" * 80 + "\n", flush=True)

# 설정 로드 실행
load_event_settings()

@dataclass
class RecorderConfig:
    rtsp_url: str = "rtsp://210.99.70.120:1935/live/cctv005.stream"
    camera_name: str = "unknown"
    segment_seconds: int = SPLIT_SECONDS
    output_dir: Path = Path("./outputs/nvr/recordings")
    reencode_video: bool = False
    video_bitrate: str = DEFAULT_BITRATE
    gop_seconds: Optional[int] = None
    rtsp_transport: str = "tcp"
    analyzeduration: str = "10M"
    probesize: str = "10M"
    ffmpeg_path: str = "ffmpeg"
    reconnect_delay_sec: int = 5
    max_muxing_queue_size: int = 1024
    filename_pattern: str = "{name}/{date}/{time}.mp4"
    video_type: int = 2  # 카메라 타입 (1: 열화상, 2: 실화상)

    # 🔧 타임아웃 옵션 (빌드에 따라 미지원일 수 있음)
    use_timeouts: bool = True            # 타임아웃 활성화
    timeout_mode: str = "timeout"        # 'timeout' 모드 사용 (초 단위)
    timeout_value_us: int = 30           # 30초 타임아웃


class RTSPRecorder:
    def __init__(self, config: RecorderConfig):
        self.cfg = config
        self.process: Optional[subprocess.Popen] = None
        self._stop = threading.Event()
        self._monitor_thread: Optional[threading.Thread] = None
        self._ensure_output_dir()
        self.recording_start_time = None
        self.original_camera_name = None  # tb_cameras의 원본 이름 저장
        self._processed_segments = set()  # 처리된 세그먼트 추적
        self._filtered_dts_warnings = 0  # 필터링된 DTS 경고 수 추적

    def _ensure_output_dir(self):
        """출력 디렉토리 생성"""
        try:
            # 절대 경로로 변환하여 확인
            abs_output_dir = self.cfg.output_dir.resolve()
            print(f"[Recorder-{self.cfg.camera_name}] Output directory:")
            print(f"  Relative: {self.cfg.output_dir}")
            print(f"  Absolute: {abs_output_dir}")
            
            # 디렉토리 생성
            self.cfg.output_dir.mkdir(parents=True, exist_ok=True)
            
            # 생성 후 권한 확인
            if self.cfg.output_dir.exists():
                print(f"[Recorder-{self.cfg.camera_name}] Output directory created/verified successfully")
                # 쓰기 권한 테스트
                test_file = self.cfg.output_dir / "test_write.tmp"
                try:
                    test_file.write_text("test")
                    test_file.unlink()
                    print(f"[Recorder-{self.cfg.camera_name}] Write permission test: PASSED")
                except Exception as e:
                    print(f"[Recorder-{self.cfg.camera_name}] ⚠️ Write permission test: FAILED - {e}")
            else:
                print(f"[Recorder-{self.cfg.camera_name}] ⚠️ Failed to create output directory")
                
        except Exception as e:
            print(f"[Recorder-{self.cfg.camera_name}] Error creating output directory: {e}")
            raise

    def _get_output_path(self) -> str:
        """출력 파일 경로 생성 - segment 분할을 위한 패턴 (유니크 숫자 사용)
        
        날짜가 변경되면 자동으로 새로운 날짜 폴더에 저장되도록 strftime 형식 사용
        """
        # 현재 날짜로 초기 날짜별 폴더 생성 (FFmpeg 시작 시)
        current_date = datetime.now().strftime("%Y-%m-%d")
        camera_date_dir = self.cfg.output_dir / self.cfg.camera_name / current_date
        camera_date_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"[Recorder-{self.cfg.camera_name}] Created initial date directory: {camera_date_dir}")
        
        # 유니크 숫자 기반 파일명 패턴 (타임스탬프 사용)
        # 날짜 폴더도 strftime 형식으로 변경하여 날짜가 바뀌면 자동으로 새 폴더에 저장
        # %Y-%m-%d 형식: 년-월-일 (날짜 변경 시 자동으로 새 폴더 생성)
        # %Y%m%d_%H%M%S 형식: 년월일_시분초 (파일명에 타임스탬프 포함)
        # FFmpeg의 -strftime 1 옵션과 함께 사용하면 날짜가 변경될 때 자동으로 새 날짜 폴더에 저장됨
        pattern = f"./outputs/nvr/recordings/{self.cfg.camera_name}/%Y-%m-%d/segment_%Y%m%d_%H%M%S.mp4"
        
        print(f"[Recorder-{self.cfg.camera_name}] Generated pattern: {pattern}")
        print(f"[Recorder-{self.cfg.camera_name}] Note: Using strftime-based date folder - will auto-create new folder when date changes")
        return pattern

    def _cleanup_recording_status_records(self):
        """DB에서 status가 'recording'인 항목들을 모두 삭제"""
        try:
            current_date = datetime.now().strftime("%Y-%m-%d")
            camera_name = self.original_camera_name or self.cfg.camera_name
            
            print(f"[Recorder-{self.cfg.camera_name}] 🗑️ Cleaning up 'recording' status records from DB...")
            print(f"[Recorder-{self.cfg.camera_name}]   Camera: {camera_name}")
            print(f"[Recorder-{self.cfg.camera_name}]   Date: {current_date}")
            
            db_connection = pymysql.connect(
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
            
            cursor = db_connection.cursor()
            
            # status가 'recording'인 레코드 조회
            select_query = """
                SELECT id, file_path 
                FROM tb_recording_history 
                WHERE camera_name = %s 
                  AND status = 'recording'
                  AND DATE(create_date) = %s
            """
            
            cursor.execute(select_query, (camera_name, current_date))
            recording_records = cursor.fetchall()
            
            if recording_records:
                print(f"[Recorder-{self.cfg.camera_name}]   Found {len(recording_records)} 'recording' status records to delete")
                
                # 삭제 쿼리 실행
                delete_query = """
                    DELETE FROM tb_recording_history 
                    WHERE camera_name = %s 
                      AND status = 'recording'
                      AND DATE(create_date) = %s
                """
                
                cursor.execute(delete_query, (camera_name, current_date))
                deleted_count = cursor.rowcount
                
                db_connection.commit()
                print(f"[Recorder-{self.cfg.camera_name}] ✅ Deleted {deleted_count} 'recording' status records from DB")
                
                # 삭제된 레코드 정보 출력
                for record in recording_records:
                    file_path = record.get('file_path', 'N/A')
                    print(f"[Recorder-{self.cfg.camera_name}]   - Deleted: {file_path}")
            else:
                print(f"[Recorder-{self.cfg.camera_name}] ℹ️ No 'recording' status records found, nothing to delete")
            
            cursor.close()
            db_connection.close()
            
        except Exception as e:
            print(f"[Recorder-{self.cfg.camera_name}] ⚠️ Error cleaning up 'recording' status records: {e}")
            import traceback
            traceback.print_exc()

    def _cleanup_existing_segments(self):
        """유니크 숫자 기반 파일명은 매번 새로운 파일명이 생성되므로 cleanup 불필요"""
        try:
            # 유니크 숫자 기반 파일명 (segment_20240112_183045_123456.mp4)은
            # FFmpeg가 자동으로 타임스탬프 기반으로 생성하므로
            # 같은 이름의 파일이 생성될 가능성이 거의 없음
            # 따라서 cleanup 로직은 불필요
            print(f"[Recorder-{self.cfg.camera_name}] ℹ️ Unique timestamp-based naming: cleanup not needed (each segment has unique filename)")
            return
                
        except Exception as e:
            print(f"[Recorder-{self.cfg.camera_name}] ⚠️ Error during cleanup: {e}")
            import traceback
            traceback.print_exc()

    def _wait_and_check_file(self, file_path: str):
        """파일 생성 대기 및 확인"""
        import time
        
        if not file_path:
            return
            
        print(f"[Recorder-{self.cfg.camera_name}] Waiting for file creation: {file_path}")
        
        # 최대 10초까지 대기
        for i in range(10):
            time.sleep(1)
            if os.path.exists(file_path):
                print(f"[Recorder-{self.cfg.camera_name}] File created after {i+1} seconds: {file_path}")
                
                # 파일 크기 확인 (0바이트 파일 체크)
                file_size = os.path.getsize(file_path)
                if file_size == 0:
                    print(f"[Recorder-{self.cfg.camera_name}] ⚠️⚠️⚠️ 0바이트 파일 발견: {file_path}")
                    print(f"[Recorder-{self.cfg.camera_name}] ⚠️ RTSP 스트림 연결 실패 또는 데이터 수신 실패로 인한 빈 파일")
                    try:
                        # 0바이트 파일 삭제
                        os.remove(file_path)
                        print(f"[Recorder-{self.cfg.camera_name}] ✅ 0바이트 파일 삭제 완료: {file_path}")
                    except Exception as e:
                        print(f"[Recorder-{self.cfg.camera_name}] ❌ 0바이트 파일 삭제 실패: {e}")
                    
                    # 재연결 트리거를 위해 에러 플래그 설정
                    print(f"[Recorder-{self.cfg.camera_name}] 🔄 재연결이 필요합니다 (RTSP 스트림 연결 실패)")
                    return
                
                # 이미 처리된 세그먼트인지 확인
                if file_path in self._processed_segments:
                    print(f"[Recorder-{self.cfg.camera_name}] ⚠️ Already processed segment: {file_path}")
                    return
                
                # 파일 수정 시간 확인 - 녹화 시작 시간 이후에 생성된 파일만 처리
                if self.recording_start_time:
                    file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                    if file_mtime < self.recording_start_time:
                        print(f"[Recorder-{self.cfg.camera_name}] ⚠️ 파일이 녹화 시작 전에 생성됨 - 건너뜀: {os.path.basename(file_path)} (생성: {file_mtime}, 녹화 시작: {self.recording_start_time})")
                        # 처리된 목록에 추가하여 다시 체크하지 않도록 함
                        self._processed_segments.add(file_path)
                        return
                
                # 새 세그먼트 파일 감지 - 이전 세그먼트를 DB에 insert
                print(f"[Recorder-{self.cfg.camera_name}] 🎯 New segment file detected: {os.path.basename(file_path)}")
                
                # 이전 세그먼트 파일 찾기
                file_dir = os.path.dirname(file_path)
                prev_segment_path = self._find_previous_segment_file(file_dir, file_path)
                
                if prev_segment_path and os.path.exists(prev_segment_path):
                    # 이전 세그먼트를 'completed' 상태로 DB에 insert
                    print(f"[Recorder-{self.cfg.camera_name}] 🗄️ Inserting previous segment to DB: {os.path.basename(prev_segment_path)}")
                    self._insert_recording_history(prev_segment_path, None, force_completed=True)
                
                # 현재 세그먼트는 처리 목록에만 추가 (다음 세그먼트 시작 시 insert됨)
                self._processed_segments.add(file_path)
                return
        
        print(f"[Recorder-{self.cfg.camera_name}] ⚠️ File not created after 10 seconds: {file_path}")

    def _analyze_error(self, error_line: str):
        """에러 로그 분석 및 해결 방안 제시"""
        error_line_lower = error_line.lower()
        
        if "conversion failed" in error_line_lower:
            print(f"[Recorder-{self.cfg.camera_name}] 🔍 Conversion failed 분석:")
            print(f"  - 가능한 원인: RTSP 스트림 연결 실패, 코덱 문제, 파일 권한 문제")
            print(f"  - 해결 방안: RTSP URL 확인, 네트워크 연결 상태 점검")
        elif "could not get segment filename with strftime" in error_line_lower:
            print(f"[Recorder-{self.cfg.camera_name}] 🔍 strftime 패턴 오류 분석:")
            print(f"  - 가능한 원인: 파일명 패턴의 strftime 형식 오류")
            print(f"  - 해결 방안: 파일명 패턴 단순화, 경로 구분자 통일")
        elif "could not open" in error_line_lower or "no such file" in error_line_lower:
            print(f"[Recorder-{self.cfg.camera_name}] 🔍 파일/디렉토리 접근 오류 분석:")
            print(f"  - 가능한 원인: 출력 디렉토리 생성 실패, 권한 문제, 경로 오류")
            print(f"  - 해결 방안: 디렉토리 권한 확인, 경로 구분자 통일, 상대경로 사용")
        elif "invalid argument" in error_line_lower:
            print(f"[Recorder-{self.cfg.camera_name}] 🔍 잘못된 인수 오류 분석:")
            print(f"  - 가능한 원인: FFmpeg 옵션 오류, 경로 형식 문제")
            print(f"  - 해결 방안: FFmpeg 명령어 옵션 확인, 경로 패턴 단순화")
        elif "monotonic dts" in error_line_lower or "incorrect timestamps" in error_line_lower:
            print(f"[Recorder-{self.cfg.camera_name}] 🔍 DTS 타임스탬프 문제 분석:")
            print(f"  - 가능한 원인: RTSP 스트림의 타임스탬프 손상, 네트워크 지연")
            print(f"  - 해결 방안: -fflags +genpts+igndts, -avoid_negative_ts make_zero 옵션 추가")
            print(f"  - 추가 옵션: -use_wallclock_as_timestamps 1, -copyts 사용")
        elif "dts" in error_line_lower and "error" in error_line_lower:
            print(f"[Recorder-{self.cfg.camera_name}] 🔍 DTS 오류 분석:")
            print(f"  - 가능한 원인: 타임스탬프 불일치, 스트림 동기화 문제")
            print(f"  - 해결 방안: 타임스탬프 관련 FFmpeg 옵션 조정")
        elif "non-monotonic dts" in error_line_lower:
            print(f"[Recorder-{self.cfg.camera_name}] 🔍 Non-monotonic DTS 경고 분석:")
            print(f"  - 가능한 원인: RTSP 스트림의 타임스탬프 손상, 네트워크 지연, 프레임 순서 변경")
            print(f"  - 해결 방안: 현재 적용된 옵션들이 자동으로 처리 중")
            print(f"  - 추가 개선: 네트워크 안정성 향상, 카메라 설정 최적화")
            print(f"  - 참고: 이 경고는 일반적으로 무시해도 됨 (자동 수정됨)")
        elif "could not write header" in error_line_lower:
            print(f"[Recorder-{self.cfg.camera_name}] 🔍 헤더 쓰기 실패 분석:")
            print(f"  - 가능한 원인: 코덱 파라미터 불일치, 타임스탬프 문제")
            print(f"  - 해결 방안: -avoid_negative_ts make_zero 옵션 추가, 코덱 설정 확인")
        elif "rtsp" in error_line_lower and "failed" in error_line_lower:
            print(f"[Recorder-{self.cfg.camera_name}] 🔍 RTSP 연결 실패 분석:")
            print(f"  - 가능한 원인: 카메라 IP/포트 오류, 네트워크 타임아웃")
            print(f"  - 해결 방안: 카메라 설정 확인, 방화벽 설정 점검")
        elif "invalid data found when processing input" in error_line_lower or ("error opening input" in error_line_lower and "invalid data" in error_line_lower):
            print(f"[Recorder-{self.cfg.camera_name}] 🔍 입력 스트림 처리 오류 분석:")
            print(f"  - 가능한 원인: RTSP 스트림 데이터 손상, 입력 옵션 오류, 스트림 형식 불일치")
            print(f"  - 해결 방안: 입력 옵션 최소화(-fflags 제거), 타임아웃 설정 확인, RTSP 스트림 상태 점검")
            print(f"  - 참고: -fflags는 입력 옵션으로 사용하면 안 됩니다 (출력 옵션에서만 사용)")
        elif "error opening input" in error_line_lower:
            print(f"[Recorder-{self.cfg.camera_name}] 🔍 입력 파일 열기 오류 분석:")
            print(f"  - 가능한 원인: RTSP URL 오류, 네트워크 연결 실패, 인증 실패")
            print(f"  - 해결 방안: RTSP URL 확인, 카메라 접근 가능 여부 점검, 인증 정보 확인")
        elif "segment" in error_line_lower and "failed" in error_line_lower:
            print(f"[Recorder-{self.cfg.camera_name}] 🔍 세그먼트 분할 실패 분석:")
            print(f"  - 가능한 원인: 출력 디렉토리 권한 문제, 디스크 공간 부족")
            print(f"  - 해결 방안: 디렉토리 권한 확인, 디스크 공간 점검")
        elif "permission" in error_line_lower:
            print(f"[Recorder-{self.cfg.camera_name}] 🔍 권한 문제 분석:")
            print(f"  - 가능한 원인: 출력 디렉토리 쓰기 권한 없음")
            print(f"  - 해결 방안: 디렉토리 권한 설정 확인")
        elif "no space" in error_line_lower or "disk full" in error_line_lower:
            print(f"[Recorder-{self.cfg.camera_name}] 🔍 디스크 공간 문제 분석:")
            print(f"  - 가능한 원인: 디스크 공간 부족")
            print(f"  - 해결 방안: 불필요한 파일 정리, 디스크 공간 확보")

    def _convert_to_relative_path(self, absolute_path: str) -> str:
        """절대경로를 상대경로로 변환"""
        try:
            # 현재 작업 디렉토리 (videoRecoder.py가 실행되는 위치)
            current_dir = os.getcwd()
            
            print(f"[Recorder-{self.cfg.camera_name}] Path conversion debug:")
            print(f"  Current directory: {current_dir}")
            print(f"  Absolute path: {absolute_path}")
            
            # 절대경로가 현재 디렉토리를 포함하는지 확인
            if absolute_path.startswith(current_dir):
                # 현재 디렉토리 부분을 제거하고 상대경로로 변환
                relative_path = os.path.relpath(absolute_path, current_dir)
                # Windows 경로 구분자를 /로 통일
                relative_path = relative_path.replace('\\', '/')
                print(f"  Converted (current dir): {relative_path}")
                return relative_path
            else:
                # 현재 디렉토리에 포함되지 않는 경우, outputs 폴더 기준으로 상대경로 생성
                # 예: C:\D\project\nvr\src\nvr\outputs\nvr\recordings\camera1\2025-09-01\file.mp4
                # → ./outputs/nvr/recordings/camera1/2025-09-01/file.mp4
                
                # outputs 폴더 위치 찾기
                if 'outputs' in absolute_path:
                    outputs_index = absolute_path.find('outputs')
                    if outputs_index != -1:
                        relative_path = './' + absolute_path[outputs_index:].replace('\\', '/')
                        print(f"  Converted (outputs): {relative_path}")
                        return relative_path
                
                # 기본적으로 원본 경로 반환 (변환 실패 시)
                fallback_path = absolute_path.replace('\\', '/')
                print(f"  Fallback path: {fallback_path}")
                return fallback_path
                
        except Exception as e:
            print(f"[Recorder-{self.cfg.camera_name}] Error converting to relative path: {e}")
            # 에러 발생 시 원본 경로 반환
            return absolute_path.replace('\\', '/')

    def _check_segment_files(self):
        """세그먼트 파일 상태 확인"""
        try:
            camera_dir = self.cfg.output_dir / self.cfg.camera_name
            if camera_dir.exists():
                # 날짜별 폴더 확인
                date_dirs = [d for d in camera_dir.iterdir() if d.is_dir()]
                total_files = 0
                
                # 날짜별 폴더에 segment_000.mp4, segment_001.mp4 등
                # 모든 날짜 폴더를 검색
                date_dirs = [d for d in camera_dir.iterdir() if d.is_dir()]
                for date_dir in date_dirs:
                    if date_dir.name.replace('-', '').isdigit():  # 날짜 폴더인지 확인
                        mp4_files = list(date_dir.glob("segment_*.mp4"))
                        total_files += len(mp4_files)
                        if mp4_files:
                            # 파일명 정렬 (순번 순서대로)
                            mp4_files.sort(key=lambda x: x.name)
                            print(f"[Recorder-{self.cfg.camera_name}] {date_dir.name}: {len(mp4_files)} files")
                            # 첫 번째와 마지막 파일명 표시
                            if len(mp4_files) > 0:
                                print(f"  First: {mp4_files[0].name}")
                                if len(mp4_files) > 1:
                                    print(f"  Last: {mp4_files[-1].name}")
                
                print(f"[Recorder-{self.cfg.camera_name}] Total segment files: {total_files}")
        except Exception as e:
            print(f"[Recorder-{self.cfg.camera_name}] Error checking segment files: {e}")

    def _manual_segment_check(self):
        """수동으로 세그먼트 파일을 확인하고 DB에 INSERT 시도"""
        try:
            print(f"[Recorder-{self.cfg.camera_name}] 🔍 Manual segment check started...")
            
            camera_dir = self.cfg.output_dir / self.cfg.camera_name
            if not camera_dir.exists():
                print(f"[Recorder-{self.cfg.camera_name}] ⚠️ Camera directory does not exist: {camera_dir}")
                return
            
            # 날짜별 폴더 확인
            date_dirs = [d for d in camera_dir.iterdir() if d.is_dir()]
            total_processed = 0
            
            for date_dir in date_dirs:
                if date_dir.name.replace('-', '').isdigit():  # 날짜 폴더인지 확인
                    print(f"[Recorder-{self.cfg.camera_name}] Checking date directory: {date_dir.name}")
                    
                    mp4_files = list(date_dir.glob("segment_*.mp4"))
                    if mp4_files:
                        print(f"[Recorder-{self.cfg.camera_name}] Found {len(mp4_files)} segment files in {date_dir.name}")
                        
                        for mp4_file in mp4_files:
                            file_path = str(mp4_file.absolute())
                            
                            # 이미 처리된 세그먼트인지 확인
                            if file_path in self._processed_segments:
                                print(f"[Recorder-{self.cfg.camera_name}] ⚠️ Already processed: {mp4_file.name}")
                                continue
                            
                            print(f"[Recorder-{self.cfg.camera_name}] 🎯 Processing segment: {mp4_file.name}")
                            
                            # 이전 세그먼트 파일 찾기
                            file_dir = os.path.dirname(file_path)
                            prev_segment_path = self._find_previous_segment_file(file_dir, file_path)
                            
                            if prev_segment_path and os.path.exists(prev_segment_path):
                                # 이전 세그먼트를 'completed' 상태로 DB에 insert
                                print(f"[Recorder-{self.cfg.camera_name}] 🗄️ Inserting previous segment to DB: {os.path.basename(prev_segment_path)}")
                                self._insert_recording_history(prev_segment_path, None, force_completed=True)
                            
                            # 현재 세그먼트는 처리 목록에만 추가
                            self._processed_segments.add(file_path)
                            total_processed += 1
            
            if total_processed > 0:
                print(f"[Recorder-{self.cfg.camera_name}] ✅ Manual check completed: {total_processed} segments processed")
            else:
                print(f"[Recorder-{self.cfg.camera_name}] ℹ️ Manual check completed: No new segments found")
                
        except Exception as e:
            print(f"[Recorder-{self.cfg.camera_name}] Error in manual segment check: {e}")
            import traceback
            traceback.print_exc()

    def _check_rtsp_connection(self):
        """RTSP 연결 상태 확인"""
        check_start_time = datetime.now()
        try:
            print(f"[Recorder-{self.cfg.camera_name}] 🔍 Checking RTSP connection status...")
            print(f"[Recorder-{self.cfg.camera_name}] ⏰ 연결 체크 시작 시간: {check_start_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
            
            # RTSP URL에서 IP 주소 추출
            rtsp_url = self.cfg.rtsp_url
            if "rtsp://" in rtsp_url:
                # rtsp://210.99.70.120:1935/live/cctv014.stream
                ip_start = rtsp_url.find("rtsp://") + 7
                ip_end = rtsp_url.find(":", ip_start)
                if ip_end == -1:
                    ip_end = rtsp_url.find("/", ip_start)
                
                if ip_end != -1:
                    ip_address = rtsp_url[ip_start:ip_end]
                    port_start = rtsp_url.find(":", ip_start) + 1
                    port_end = rtsp_url.find("/", port_start)
                    port = rtsp_url[port_start:port_end] if port_end != -1 else "554"
                    
                    print(f"[Recorder-{self.cfg.camera_name}] 📋 RTSP 연결 정보:")
                    print(f"[Recorder-{self.cfg.camera_name}]   - IP 주소: {ip_address}")
                    print(f"[Recorder-{self.cfg.camera_name}]   - 포트: {port}")
                    print(f"[Recorder-{self.cfg.camera_name}]   - 전체 URL: {rtsp_url}")
                    
                    # ping 테스트
                    import subprocess
                    ping_start_time = datetime.now()
                    try:
                        result = subprocess.run(
                            ["ping", "-n", "1", ip_address], 
                            capture_output=True, 
                            text=True, 
                            timeout=5
                        )
                        ping_elapsed = (datetime.now() - ping_start_time).total_seconds()
                        if result.returncode == 0:
                            print(f"[Recorder-{self.cfg.camera_name}] ✅ Ping to {ip_address}: SUCCESS (소요 시간: {ping_elapsed:.2f}초)")
                            return True
                        else:
                            print(f"[Recorder-{self.cfg.camera_name}] ❌ Ping to {ip_address}: FAILED (소요 시간: {ping_elapsed:.2f}초)")
                            print(f"[Recorder-{self.cfg.camera_name}] ⚠️ 네트워크 연결 문제 가능성")
                            return False
                    except subprocess.TimeoutExpired:
                        ping_elapsed = (datetime.now() - ping_start_time).total_seconds()
                        print(f"[Recorder-{self.cfg.camera_name}] ❌ Ping to {ip_address}: TIMEOUT (소요 시간: {ping_elapsed:.2f}초)")
                        print(f"[Recorder-{self.cfg.camera_name}] ⚠️ 네트워크 타임아웃 - 카메라에 접근할 수 없습니다")
                        return False
                    except Exception as e:
                        ping_elapsed = (datetime.now() - ping_start_time).total_seconds()
                        print(f"[Recorder-{self.cfg.camera_name}] ⚠️ Ping test failed: {e} (소요 시간: {ping_elapsed:.2f}초)")
                        return False
                else:
                    print(f"[Recorder-{self.cfg.camera_name}] ⚠️ Could not extract IP from RTSP URL")
                    return False
            else:
                print(f"[Recorder-{self.cfg.camera_name}] ⚠️ Invalid RTSP URL format")
                return False
                
        except Exception as e:
            check_elapsed = (datetime.now() - check_start_time).total_seconds()
            print(f"[Recorder-{self.cfg.camera_name}] ❌ Error checking RTSP connection: {e} (소요 시간: {check_elapsed:.2f}초)")
            return False
        finally:
            check_elapsed = (datetime.now() - check_start_time).total_seconds()
            print(f"[Recorder-{self.cfg.camera_name}] ⏰ 전체 연결 체크 소요 시간: {check_elapsed:.2f}초")

    def _monitor_segment_files(self):
        """파일 시스템을 직접 모니터링하여 새 세그먼트 파일 감지 및 이전 세그먼트 DB insert"""
        try:
            # 녹화 시작 시간이 없으면 처리하지 않음
            if not self.recording_start_time:
                return
            
            # 현재 날짜 폴더 경로
            current_date = datetime.now().strftime("%Y-%m-%d")
            camera_date_dir = self.cfg.output_dir / self.cfg.camera_name / current_date
            
            if not camera_date_dir.exists():
                return
            
            # 기존에 처리된 파일 목록과 현재 파일 목록 비교
            current_files = set()
            for mp4_file in camera_date_dir.glob("segment_*.mp4"):
                current_files.add(str(mp4_file.absolute()))
            
            # 새로운 파일 찾기 (아직 처리되지 않은 파일)
            new_files = current_files - self._processed_segments
            
            if new_files:
                # 생성 시간 순으로 정렬 (오래된 것부터)
                new_files_with_time = []
                for file_path in new_files:
                    if os.path.exists(file_path):
                        file_mtime = os.path.getmtime(file_path)
                        # 녹화 시작 시간 이후에 생성된 파일만 처리
                        if self.recording_start_time:
                            file_mtime_dt = datetime.fromtimestamp(file_mtime)
                            if file_mtime_dt < self.recording_start_time:
                                continue
                        new_files_with_time.append((file_path, file_mtime))
                
                # 생성 시간 순으로 정렬
                new_files_with_time.sort(key=lambda x: x[1])
                
                for file_path, file_mtime in new_files_with_time:
                    # 파일 크기 확인
                    file_size = os.path.getsize(file_path)
                    if file_size == 0:
                        print(f"[Recorder-{self.cfg.camera_name}] ⚠️⚠️⚠️ 0바이트 파일 발견: {os.path.basename(file_path)}")
                        try:
                            os.remove(file_path)
                            print(f"[Recorder-{self.cfg.camera_name}] ✅ 0바이트 파일 삭제 완료: {os.path.basename(file_path)}")
                        except Exception as e:
                            print(f"[Recorder-{self.cfg.camera_name}] ❌ 0바이트 파일 삭제 실패: {e}")
                        continue
                    
                    # 새 세그먼트 파일 감지 - 이전 세그먼트를 DB에 insert
                    print(f"[Recorder-{self.cfg.camera_name}] 🎯 New segment file detected: {os.path.basename(file_path)}")
                    
                    # 이전 세그먼트 파일 찾기
                    file_dir = os.path.dirname(file_path)
                    prev_segment_path = self._find_previous_segment_file(file_dir, file_path)
                    
                    if prev_segment_path and os.path.exists(prev_segment_path):
                        # 이전 세그먼트 파일이 정상적인 동영상인지 확인
                        if self._validate_video_file(prev_segment_path):
                            # 이전 세그먼트를 'completed' 상태로 DB에 insert
                            print(f"[Recorder-{self.cfg.camera_name}] 🗄️ Inserting previous segment to DB: {os.path.basename(prev_segment_path)}")
                            self._insert_recording_history(prev_segment_path, None, force_completed=True)
                        else:
                            print(f"[Recorder-{self.cfg.camera_name}] ⚠️ Skipping invalid video file: {os.path.basename(prev_segment_path)}")
                            # 비정상 파일은 처리 목록에 추가하여 다시 체크하지 않도록 함
                            self._processed_segments.add(prev_segment_path)
                    
                    # 현재 세그먼트는 처리 목록에만 추가 (다음 세그먼트 시작 시 insert됨)
                    self._processed_segments.add(file_path)
                        
        except Exception as e:
            print(f"[Recorder-{self.cfg.camera_name}] Error monitoring segment files: {e}")
            import traceback
            traceback.print_exc()

    def _continuous_monitor_segments(self, interval_seconds: int):
        """지속적으로 세그먼트 파일을 모니터링하는 메서드"""
        try:
            print(f"[Recorder-{self.cfg.camera_name}] 🔍 Continuous segment monitoring started (interval: {interval_seconds}s)")
            
            while not self._stop.is_set() and self.process and self.process.poll() is None:
                try:
                    # 세그먼트 파일 확인 (새 파일 감지 및 이전 파일 DB insert)
                    self._monitor_segment_files()
                    
                    # 짧은 간격으로 체크 (1초)
                    import time
                    time.sleep(1)
                    
                except Exception as e:
                    print(f"[Recorder-{self.cfg.camera_name}] Error in continuous monitoring: {e}")
                    time.sleep(5)  # 에러 발생 시 5초 대기 후 재시도
            
            print(f"[Recorder-{self.cfg.camera_name}] 🔍 Continuous segment monitoring stopped")
            
        except Exception as e:
            print(f"[Recorder-{self.cfg.camera_name}] Fatal error in continuous monitoring: {e}")
            import traceback
            traceback.print_exc()

    def _handle_segment_complete(self, line: str):
        """세그먼트 완료 시 데이터베이스에 기록"""
        try:
            print(f"[Recorder-{self.cfg.camera_name}] 🔍 Handling segment complete for line: {line.rstrip()}")
            
            # 파일 경로 추출 (더 유연하게)
            file_path = self._extract_file_path_from_line(line)
            if file_path:
                print(f"[Recorder-{self.cfg.camera_name}] ✅ File path extracted: {file_path}")
                
                # 파일 존재 및 크기 확인
                if not os.path.exists(file_path):
                    print(f"[Recorder-{self.cfg.camera_name}] ⚠️ 파일이 존재하지 않습니다: {file_path}")
                    return
                
                file_size = os.path.getsize(file_path)
                if file_size == 0:
                    print(f"[Recorder-{self.cfg.camera_name}] ⚠️⚠️⚠️ 0바이트 파일 발견: {file_path}")
                    print(f"[Recorder-{self.cfg.camera_name}] ⚠️ RTSP 스트림 연결 실패로 인한 빈 파일 - DB INSERT 건너뜀")
                    try:
                        os.remove(file_path)
                        print(f"[Recorder-{self.cfg.camera_name}] ✅ 0바이트 파일 삭제 완료: {file_path}")
                    except Exception as e:
                        print(f"[Recorder-{self.cfg.camera_name}] ❌ 0바이트 파일 삭제 실패: {e}")
                    return
                
                # 이미 처리된 세그먼트인지 확인
                if file_path in self._processed_segments:
                    print(f"[Recorder-{self.cfg.camera_name}] ⚠️ Already processed segment: {file_path}")
                    return
                
                # 파일 수정 시간 확인 - 녹화 시작 시간 이후에 생성된 파일만 처리
                if self.recording_start_time:
                    file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                    if file_mtime < self.recording_start_time:
                        print(f"[Recorder-{self.cfg.camera_name}] ⚠️ 파일이 녹화 시작 전에 생성됨 - 건너뜀: {os.path.basename(file_path)} (생성: {file_mtime}, 녹화 시작: {self.recording_start_time})")
                        # 처리된 목록에 추가하여 다시 체크하지 않도록 함
                        self._processed_segments.add(file_path)
                        return
                
                # 새 세그먼트 파일 감지 - 이전 세그먼트를 DB에 insert
                print(f"[Recorder-{self.cfg.camera_name}] 🎯 New segment file detected: {os.path.basename(file_path)}")
                
                # 이전 세그먼트 파일 찾기
                file_dir = os.path.dirname(file_path)
                prev_segment_path = self._find_previous_segment_file(file_dir, file_path)
                
                if prev_segment_path and os.path.exists(prev_segment_path):
                    # 이전 세그먼트를 'completed' 상태로 DB에 insert
                    print(f"[Recorder-{self.cfg.camera_name}] 🗄️ Inserting previous segment to DB: {os.path.basename(prev_segment_path)}")
                    self._insert_recording_history(prev_segment_path, None, force_completed=True)
                
                # 현재 세그먼트는 처리 목록에만 추가 (다음 세그먼트 시작 시 insert됨)
                self._processed_segments.add(file_path)
            else:
                print(f"[Recorder-{self.cfg.camera_name}] ⚠️ Could not extract file path from line: {line.rstrip()}")
                
        except Exception as e:
            print(f"[Recorder-{self.cfg.camera_name}] Error handling segment complete: {e}")
            import traceback
            traceback.print_exc()

    def _extract_file_path_from_line(self, line: str) -> Optional[str]:
        """FFmpeg 로그에서 파일 경로 추출"""
        try:
            print(f"[Recorder-{self.cfg.camera_name}] 🔍 Extracting file path from: {line.rstrip()}")
            
            # "Opening 'file_path' for writing" 형태에서 파일 경로 추출
            if "Opening '" in line and "' for writing" in line:
                start = line.find("Opening '") + 9
                end = line.find("' for writing")
                if start > 8 and end > start:
                    file_path = line[start:end]
                    print(f"[Recorder-{self.cfg.camera_name}] Found path (quotes): {file_path}")
                    # 절대 경로로 변환
                    if not os.path.isabs(file_path):
                        file_path = os.path.abspath(file_path)
                    print(f"[Recorder-{self.cfg.camera_name}] Absolute path: {file_path}")
                    return file_path
                    
            # "Opening file_path for writing" 형태도 지원
            elif "Opening " in line and " for writing" in line:
                start = line.find("Opening ") + 8
                end = line.find(" for writing")
                if start > 7 and end > start:
                    file_path = line[start:end].strip()
                    print(f"[Recorder-{self.cfg.camera_name}] Found path (no quotes): {file_path}")
                    # 따옴표 제거
                    if file_path.startswith("'") and file_path.endswith("'"):
                        file_path = file_path[1:-1]
                        print(f"[Recorder-{self.cfg.camera_name}] Removed quotes: {file_path}")
                    # 절대 경로로 변환
                    if not os.path.isabs(file_path):
                        file_path = os.path.abspath(file_path)
                    print(f"[Recorder-{self.cfg.camera_name}] Absolute path: {file_path}")
                    return file_path
                    
            # "segment" 관련 로그에서 파일 경로 추출 시도
            elif "segment" in line.lower() and ".mp4" in line:
                print(f"[Recorder-{self.cfg.camera_name}] Segment line detected, trying to extract path...")
                # 파일 경로가 포함된 부분 찾기
                if "./outputs" in line:
                    start = line.find("./outputs")
                    end = line.find(".mp4") + 4
                    if start != -1 and end > start:
                        file_path = line[start:end]
                        print(f"[Recorder-{self.cfg.camera_name}] Extracted from segment line: {file_path}")
                        # 절대 경로로 변환
                        if not os.path.isabs(file_path):
                            file_path = os.path.abspath(file_path)
                        print(f"[Recorder-{self.cfg.camera_name}] Absolute path: {file_path}")
                        return file_path
                        
            # 더 일반적인 패턴: .mp4 파일이 포함된 모든 라인에서 경로 추출 시도
            elif ".mp4" in line:
                print(f"[Recorder-{self.cfg.camera_name}] MP4 file detected, trying to extract path...")
                # ./outputs로 시작하는 경로 찾기
                if "./outputs" in line:
                    start = line.find("./outputs")
                    end = line.find(".mp4") + 4
                    if start != -1 and end > start:
                        file_path = line[start:end]
                        print(f"[Recorder-{self.cfg.camera_name}] Extracted from general MP4 line: {file_path}")
                        # 절대 경로로 변환
                        if not os.path.isabs(file_path):
                            file_path = os.path.abspath(file_path)
                        print(f"[Recorder-{self.cfg.camera_name}] Absolute path: {file_path}")
                        return file_path
                        
            print(f"[Recorder-{self.cfg.camera_name}] ⚠️ No valid file path found in line")
            
        except Exception as e:
            print(f"[Recorder-{self.cfg.camera_name}] Error extracting file path: {e}")
        return None

    def _validate_video_file(self, file_path: str) -> bool:
        """동영상 파일이 정상적으로 재생 가능한지 확인 (FFprobe 사용)"""
        try:
            import subprocess
            
            # FFprobe 경로 (FFmpeg와 같은 디렉토리에 있음)
            ffprobe_path = self.cfg.ffmpeg_path.replace("ffmpeg", "ffprobe")
            if not os.path.exists(ffprobe_path):
                # Windows에서는 .exe 확장자 추가
                if os.name == "nt":
                    ffprobe_path = ffprobe_path + ".exe"
                if not os.path.exists(ffprobe_path):
                    # 경로를 찾을 수 없으면 ffprobe만 시도
                    ffprobe_path = "ffprobe"
            
            # FFprobe로 파일 정보 확인
            cmd = [
                ffprobe_path,
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                file_path
            ]
            
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=5,
                text=True
            )
            
            if result.returncode == 0:
                # duration이 있고 0보다 크면 정상 파일
                duration = result.stdout.strip()
                if duration and float(duration) > 0:
                    print(f"[Recorder-{self.cfg.camera_name}] ✅ Video file validated: {os.path.basename(file_path)} (duration: {float(duration):.2f}s)")
                    return True
                else:
                    print(f"[Recorder-{self.cfg.camera_name}] ⚠️ Invalid video file (duration=0): {os.path.basename(file_path)}")
                    return False
            else:
                print(f"[Recorder-{self.cfg.camera_name}] ⚠️ FFprobe validation failed: {os.path.basename(file_path)}")
                print(f"[Recorder-{self.cfg.camera_name}]   Error: {result.stderr[:200]}")
                return False
                
        except subprocess.TimeoutExpired:
            print(f"[Recorder-{self.cfg.camera_name}] ⚠️ Video validation timeout: {os.path.basename(file_path)}")
            return False
        except Exception as e:
            print(f"[Recorder-{self.cfg.camera_name}] ⚠️ Error validating video file: {e}")
            return False

    def _find_previous_segment_file(self, file_dir: str, current_file_path: str) -> Optional[str]:
        """이전 세그먼트 파일 찾기 - 현재 파일보다 이전에 생성된 가장 최근 파일"""
        try:
            from pathlib import Path
            
            if not os.path.exists(current_file_path):
                return None
            
            current_file_mtime = os.path.getmtime(current_file_path)
            dir_path = Path(file_dir)
            segment_files = list(dir_path.glob("segment_*.mp4"))
            
            prev_file = None
            prev_file_mtime = 0
            
            for segment_file in segment_files:
                file_path = str(segment_file.absolute())
                if file_path == current_file_path:
                    continue
                    
                if os.path.exists(file_path):
                    file_mtime = os.path.getmtime(file_path)
                    # 현재 파일보다 이전에 생성된 파일 중 가장 최근 파일
                    if file_mtime < current_file_mtime and file_mtime > prev_file_mtime:
                        prev_file = file_path
                        prev_file_mtime = file_mtime
            
            if prev_file:
                print(f"[Recorder-{self.cfg.camera_name}] ✅ Found previous segment: {os.path.basename(prev_file)}")
            else:
                print(f"[Recorder-{self.cfg.camera_name}] ℹ️ No previous segment found (first segment)")
            
            return prev_file
            
        except Exception as e:
            print(f"[Recorder-{self.cfg.camera_name}] ❌ Error finding previous segment: {e}")
            return None

    def _extract_segment_number(self, file_path: str) -> Optional[int]:
        """파일 경로에서 세그먼트 번호 추출 (유니크 숫자 기반)"""
        try:
            # 파일명만 추출 (경로 제거)
            filename = os.path.basename(file_path)
            
            # segment_유니크숫자.mp4 패턴에서 유니크 숫자 추출
            # segment_20240112_183045_123456.mp4 형식 (년월일_시분초_마이크로초)
            if filename.startswith("segment_") and filename.endswith(".mp4"):
                segment_part = filename[8:-4]  # "segment_" 제거하고 ".mp4" 제거
                # 유니크 숫자 추출: 타임스탬프 문자열을 숫자로 변환
                # segment_20240112_183045_123456 -> 숫자 부분만 추출하여 유니크 ID 생성
                if "_" in segment_part:
                    # 날짜+시간+마이크로초 형식: 숫자만 추출하여 하나의 숫자로 변환
                    digits_only = ''.join(filter(str.isdigit, segment_part))
                    if digits_only:
                        segment_num = int(digits_only)
                        print(f"[Recorder-{self.cfg.camera_name}] Extracted segment number (unique): {segment_num} from {filename}")
                        return segment_num
                elif segment_part.isdigit():
                    # 단순 숫자 형식도 지원 (하위 호환성)
                    segment_num = int(segment_part)
                    print(f"[Recorder-{self.cfg.camera_name}] Extracted segment number (unique): {segment_num} from {filename}")
                    return segment_num
            
            # 기존 패턴도 지원 (segment_000.mp4 형식 - 하위 호환성)
            if "_" in filename and filename.endswith(".mp4"):
                parts = filename[:-4].split("_")  # .mp4 제거하고 _로 분할
                if len(parts) >= 2 and parts[-1].isdigit():
                    segment_num = int(parts[-1])
                    print(f"[Recorder-{self.cfg.camera_name}] Extracted segment number: {segment_num} from {filename}")
                    return segment_num
                    
        except Exception as e:
            print(f"[Recorder-{self.cfg.camera_name}] Error extracting segment number: {e}")
        
        return None

    def _check_file_completed(self, file_path: str, segment_number: int = None) -> bool:
        """파일이 완료되었는지 확인 (다음 segment 파일이 생성되면 이전 segment는 완료된 것으로 간주)"""
        try:
            if not os.path.exists(file_path):
                return False
            
            file_size = os.path.getsize(file_path)
            if file_size == 0:
                return False
            
            # segment 번호가 없으면 완료 여부를 판단할 수 없음
            if segment_number is None:
                return False
            
            # 다음 segment 파일 경로 생성
            # segment_000.mp4 -> segment_001.mp4
            file_dir = os.path.dirname(file_path)
            next_segment_number = segment_number + 1
            next_segment_filename = f"segment_{next_segment_number:03d}.mp4"
            next_segment_path = os.path.join(file_dir, next_segment_filename)
            
            # 다음 segment 파일이 존재하면 현재 segment는 완료된 것으로 간주
            if os.path.exists(next_segment_path):
                next_file_size = os.path.getsize(next_segment_path)
                # 다음 segment 파일이 0바이트가 아니면 완료된 것으로 간주
                if next_file_size > 0:
                    print(f"[Recorder-{self.cfg.camera_name}] ✅ Segment #{segment_number} completed (next segment #{next_segment_number} exists)")
                    return True
            
            return False
        except Exception as e:
            print(f"[Recorder-{self.cfg.camera_name}] Error checking file completion: {e}")
            return False

    def _update_recording_status(self, file_path: str, status: str):
        """레코딩 기록의 status를 업데이트"""
        try:
            relative_file_path = self._convert_to_relative_path(file_path)
            
            db_connection = pymysql.connect(
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
            
            cursor = db_connection.cursor()
            
            # file_path로 레코딩 기록 찾아서 status 업데이트
            query = """
                UPDATE tb_recording_history 
                SET status = %s, update_date = %s
                WHERE file_path = %s
            """
            
            cursor.execute(query, (status, datetime.now(), relative_file_path))
            db_connection.commit()
            
            cursor.close()
            db_connection.close()
            
            print(f"[Recorder-{self.cfg.camera_name}] ✅ Recording status updated to '{status}' for: {relative_file_path}")
            
        except Exception as e:
            print(f"[Recorder-{self.cfg.camera_name}] Error updating recording status: {e}")

    def _insert_recording_history(self, file_path: str, segment_number: int = None, force_completed: bool = False):
        """tb_recording_history 테이블에 녹화 기록 insert
        
        Args:
            file_path: 파일 경로
            segment_number: 세그먼트 번호
            force_completed: True이면 무조건 'completed' 상태로 insert
        """
        try:
            print(f"[Recorder-{self.cfg.camera_name}] 🗄️ Starting database INSERT for: {file_path}")
            
            # DB 연결 테스트
            print(f"[Recorder-{self.cfg.camera_name}] 🔍 Testing database connection...")
            print(f"[Recorder-{self.cfg.camera_name}] DB Config: {DBSERVER_IP}:{DBSERVER_PORT}, User: {DBSERVER_USER}, DB: {DBSERVER_DB}")
            
            # 파일 정보 수집 및 0바이트 파일 검증
            if not os.path.exists(file_path):
                print(f"[Recorder-{self.cfg.camera_name}] ❌ 파일이 존재하지 않습니다: {file_path}")
                return
                
            file_size = os.path.getsize(file_path)
            
            # 0바이트 파일 체크 및 처리
            if file_size == 0:
                print(f"[Recorder-{self.cfg.camera_name}] ⚠️⚠️⚠️ 0바이트 파일 - DB INSERT 건너뜀: {file_path}")
                print(f"[Recorder-{self.cfg.camera_name}] ⚠️ RTSP 스트림 연결 실패로 인한 빈 파일입니다")
                try:
                    # 0바이트 파일 삭제
                    os.remove(file_path)
                    print(f"[Recorder-{self.cfg.camera_name}] ✅ 0바이트 파일 삭제 완료: {file_path}")
                except Exception as e:
                    print(f"[Recorder-{self.cfg.camera_name}] ❌ 0바이트 파일 삭제 실패: {e}")
                return
            
            # 세그먼트 시간 계산 - 파일 생성 시간 기준
            file_mtime = os.path.getmtime(file_path)
            segment_end_time = datetime.fromtimestamp(file_mtime)
            segment_start_time = segment_end_time - timedelta(seconds=self.cfg.segment_seconds)
            segment_duration = self.cfg.segment_seconds
            
            print(f"[Recorder-{self.cfg.camera_name}] Time calculation:")
            print(f"  Segment start: {segment_start_time}")
            print(f"  Segment end: {segment_end_time}")
            print(f"  Duration: {segment_duration} seconds")
            
            # 절대경로를 상대경로로 변환
            relative_file_path = self._convert_to_relative_path(file_path)
            
            # 데이터베이스 직접 연결
            print(f"[Recorder-{self.cfg.camera_name}] 🔍 Attempting database connection...")
            db_connection = pymysql.connect(
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
            print(f"[Recorder-{self.cfg.camera_name}] ✅ Database connection successful")
            
            cursor = db_connection.cursor()
            
            # DB 중복 체크: 같은 file_path가 이미 존재하는지 확인
            check_query = "SELECT id, status FROM tb_recording_history WHERE file_path = %s LIMIT 1"
            cursor.execute(check_query, (relative_file_path,))
            existing_record = cursor.fetchone()
            
            if existing_record:
                existing_id = existing_record.get('id')
                existing_status = existing_record.get('status')
                
                # force_completed가 True이고 기존 레코드가 'recording' 상태이면 'completed'로 업데이트
                if force_completed and existing_status == 'recording':
                    update_query = """
                        UPDATE tb_recording_history 
                        SET status = 'completed', update_date = %s
                        WHERE id = %s
                    """
                    cursor.execute(update_query, (datetime.now(), existing_id))
                    db_connection.commit()
                    print(f"[Recorder-{self.cfg.camera_name}] ✅ Updated existing record (ID: {existing_id}) from 'recording' to 'completed'")
                    cursor.close()
                    db_connection.close()
                    return
                else:
                    print(f"[Recorder-{self.cfg.camera_name}] ⚠️⚠️⚠️ Duplicate record found in DB - skipping INSERT: {relative_file_path}")
                    print(f"[Recorder-{self.cfg.camera_name}]   Existing record ID: {existing_id}, Status: {existing_status}")
                    cursor.close()
                    db_connection.close()
                    return
            
            # force_completed가 True이면 무조건 'completed' 상태로 insert
            initial_status = 'completed' if force_completed else 'recording'
            print(f"[Recorder-{self.cfg.camera_name}] 📊 Status: {initial_status}")
            
            # tb_recording_history에 insert
            query = """
                INSERT INTO tb_recording_history 
                (fk_camera_id, fk_schedule_id, camera_name, start_time, end_time, duration, 
                 file_path, file_size, record_type, status, resolution, bitrate, framerate, 
                 codec, create_date, update_date)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            values = (
                0,  # fk_camera_id
                0,  # fk_schedule_id
                self.original_camera_name or self.cfg.camera_name,  # camera_name
                segment_start_time,  # start_time (세그먼트별 시작 시간)
                segment_end_time,  # end_time (세그먼트별 종료 시간)
                segment_duration,  # duration (세그먼트별 길이 - 초 단위)
                relative_file_path,  # file_path (상대경로)
                file_size,  # file_size
                'continuous',  # record_type
                initial_status,  # status (파일 완료 여부에 따라 결정)
                None,  # resolution
                None,  # bitrate
                None,  # framerate
                None,  # codec
                datetime.now(),  # create_date
                datetime.now()   # update_date
            )
            
            print(f"[Recorder-{self.cfg.camera_name}] 🔍 Executing INSERT query...")
            print(f"[Recorder-{self.cfg.camera_name}]   Query: {query[:100]}...")
            print(f"[Recorder-{self.cfg.camera_name}]   Values: fk_schedule_id={values[1]}, status={values[9]}, file_path={values[6][:50]}...")
            cursor.execute(query, values)
            inserted_id = cursor.lastrowid
            print(f"[Recorder-{self.cfg.camera_name}] ✅ INSERT query executed successfully (ID: {inserted_id})")
            
            db_connection.commit()
            print(f"[Recorder-{self.cfg.camera_name}] ✅ Database commit successful")
            
            cursor.close()
            db_connection.close()
            print(f"[Recorder-{self.cfg.camera_name}] ✅ Database connection closed")
            
            print(f"[Recorder-{self.cfg.camera_name}] 🎉 Recording history inserted successfully:")
            print(f"  Start time: {segment_start_time}")
            print(f"  End time: {segment_end_time}")
            print(f"  Duration: {segment_duration} seconds")
            print(f"  File: {os.path.basename(file_path)}")
            print(f"  Status: {initial_status}")
            
        except Exception as e:
            print(f"[Recorder-{self.cfg.camera_name}] ❌❌❌ Error inserting recording history: {e}")
            import traceback
            traceback.print_exc()
            print(f"[Recorder-{self.cfg.camera_name}]   File path: {file_path}")
            print(f"[Recorder-{self.cfg.camera_name}]   Segment number: {segment_number}")
            print(f"[Recorder-{self.cfg.camera_name}]   Force completed: {force_completed}")

    def build_ffmpeg_cmd(self) -> List[str]:
        out_pattern = self._get_output_path()

        cmd = [
            self.cfg.ffmpeg_path,
            "-hide_banner", "-loglevel", "error",  # error 레벨로 설정
            "-nostats",  # 진행 상황 통계 출력 완전 비활성화
            "-rtsp_transport", self.cfg.rtsp_transport,
        ]

        # ❗ 타임아웃 옵션 추가
        if self.cfg.use_timeouts:
            if self.cfg.timeout_mode == "timeout":
                # timeout 모드 (초 단위)
                cmd += ["-timeout", str(self.cfg.timeout_value_us)]
                print(f"[Recorder-{self.cfg.camera_name}] Added timeout option: -timeout {self.cfg.timeout_value_us}")
            elif self.cfg.timeout_mode == "rw_timeout":
                # rw_timeout 모드 (마이크로초 단위)
                cmd += ["-rw_timeout", str(self.cfg.timeout_value_us * 1_000_000)]
                print(f"[Recorder-{self.cfg.camera_name}] Added rw_timeout option: -rw_timeout {self.cfg.timeout_value_us * 1_000_000}")
            elif self.cfg.timeout_mode == "stimeout":
                # stimeout 모드 (마이크로초 단위)
                cmd += ["-stimeout", str(self.cfg.timeout_value_us * 1_000_000)]
                print(f"[Recorder-{self.cfg.camera_name}] Added stimeout option: -stimeout {self.cfg.timeout_value_us * 1_000_000}")

        # 입력 옵션 (RTSP 스트림 처리용)
        # 주의: -fflags는 입력 옵션으로 사용하면 안 됩니다. RTSP 스트림을 열 때 문제를 일으킬 수 있습니다.
        cmd += [
            "-analyzeduration", self.cfg.analyzeduration,
            "-probesize", self.cfg.probesize,
            # RTSP 스트림 연결 옵션만 사용 (타임스탬프 처리는 출력 옵션에서 수행)
            "-i", self.cfg.rtsp_url,
            "-map", "0:v",  # 비디오 스트림만 매핑 (오디오 제외)
        ]

        if self.cfg.reencode_video:
            gop = self.cfg.gop_seconds or self.cfg.segment_seconds
            cmd += [
                "-c:v", "libx264", "-preset", "veryfast", "-tune", "zerolatency",
                "-profile:v", "high", "-level", "4.1",
                "-b:v", self.cfg.video_bitrate,
                "-maxrate", self.cfg.video_bitrate, "-bufsize", self.cfg.video_bitrate,
                "-force_key_frames", f"expr:gte(t,n_forced*{gop})",
            ]
            
            # 열화상 카메라(video_type=1)인 경우 해상도와 프레임레이트 강제
            if self.cfg.video_type == 1:
                cmd += [
                    "-vf", "scale=640:480",  # 해상도 강제: 640x480
                    "-r", "29.97",  # 프레임레이트 강제: 29.97fps
                ]
                print(f"[Recorder-{self.cfg.camera_name}] 🔧 열화상 카메라: 해상도 640x480, 프레임레이트 29.97fps로 강제 설정")
        else:
            # 스트림 복사 모드
            cmd += [
                "-c:v", "copy",
            ]

        # 출력 옵션 (세그먼트 파일 생성용)
        # 주의: -map 0:v로 비디오만 매핑했으므로 -an은 필요 없지만 안전을 위해 유지
        cmd += [
            "-an",  # 오디오 제거 (이중 방어)
            "-f", "segment",
            "-segment_time", str(SPLIT_SECONDS),  # 문자열로 변환
            "-reset_timestamps", "1",
            "-segment_format", "mp4",
            "-movflags", "+faststart",
            "-max_muxing_queue_size", str(self.cfg.max_muxing_queue_size),
            "-strftime", "1",  # strftime 형식 사용 (유니크 숫자 기반 파일명)
            "-segment_list_size", "0",  # 세그먼트 리스트 파일 생성 안함
            "-segment_list_flags", "live",  # 라이브 스트리밍용 플래그
            # 출력 파일 처리 옵션 (세그먼트 파일의 타임스탬프 문제 해결)
            "-fflags", "+genpts+igndts+discardcorrupt",  # 타임스탬프 생성 + 손상된 DTS 무시 + 손상된 프레임 제거
            "-avoid_negative_ts", "make_zero",  # 음수 타임스탬프 방지
            "-max_interleave_delta", "0",  # 인터리브 델타 최대값 제한
            out_pattern,
        ]
        return cmd

    def start(self):
        if self._monitor_thread and self._monitor_thread.is_alive():
            print(f"[Recorder-{self.cfg.camera_name}] Already running.")
            return
        self._stop.clear()
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        
        # 녹화 시작 시간 기록
        self.recording_start_time = datetime.now()
        print(f"[Recorder-{self.cfg.camera_name}] Started at {self.recording_start_time}.")

        if not self.cfg.reencode_video and self.cfg.video_bitrate:
            print(f"[Recorder-{self.cfg.camera_name}] NOTE: video_bitrate is ignored when reencode_video=False (stream copy mode).")

    def _monitor_loop(self):
        while not self._stop.is_set():
            try:
                # RTSP 스트림 연결 전 검증 및 대기
                connection_prep_start = datetime.now()
                print(f"[Recorder-{self.cfg.camera_name}] 🔍 RTSP 스트림 연결 준비 시작...")
                print(f"[Recorder-{self.cfg.camera_name}] ⏰ 준비 시작 시간: {connection_prep_start.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
                print(f"[Recorder-{self.cfg.camera_name}] 📋 RTSP URL: {self.cfg.rtsp_url}")
                print(f"[Recorder-{self.cfg.camera_name}] 📋 RTSP Transport: {self.cfg.rtsp_transport}")
                print(f"[Recorder-{self.cfg.camera_name}] 📋 Analyzeduration: {self.cfg.analyzeduration}")
                print(f"[Recorder-{self.cfg.camera_name}] 📋 Probesize: {self.cfg.probesize}")
                
                # RTSP URL 검증
                if not self.cfg.rtsp_url or not self.cfg.rtsp_url.strip():
                    print(f"[Recorder-{self.cfg.camera_name}] ❌ RTSP URL이 비어있습니다")
                    print(f"[Recorder-{self.cfg.camera_name}] 🔄 재연결 대기 중... ({self.cfg.reconnect_delay_sec}초)")
                    time.sleep(self.cfg.reconnect_delay_sec)
                    continue
                
                if not self.cfg.rtsp_url.startswith(('rtsp://', 'http://', 'https://')):
                    print(f"[Recorder-{self.cfg.camera_name}] ❌ RTSP URL 형식 오류: {self.cfg.rtsp_url}")
                    print(f"[Recorder-{self.cfg.camera_name}] ⚠️ RTSP URL은 'rtsp://' 또는 'http://' 또는 'https://'로 시작해야 합니다")
                    print(f"[Recorder-{self.cfg.camera_name}] 🔄 재연결 대기 중... ({self.cfg.reconnect_delay_sec}초)")
                    time.sleep(self.cfg.reconnect_delay_sec)
                    continue
                
                # RTSP 연결 테스트 (선택적)
                connection_test_start = datetime.now()
                connection_test_result = self._check_rtsp_connection()
                connection_test_elapsed = (datetime.now() - connection_test_start).total_seconds()
                if connection_test_result:
                    print(f"[Recorder-{self.cfg.camera_name}] ✅ RTSP 연결 테스트 성공 (소요 시간: {connection_test_elapsed:.2f}초)")
                else:
                    print(f"[Recorder-{self.cfg.camera_name}] ⚠️ RTSP 연결 테스트 실패 또는 건너뜀 (소요 시간: {connection_test_elapsed:.2f}초)")
                    print(f"[Recorder-{self.cfg.camera_name}] ⚠️ FFmpeg가 직접 연결을 시도합니다")
                
                # 타이밍 문제 해결을 위한 대기 시간 추가 (카메라 준비 시간)
                print(f"[Recorder-{self.cfg.camera_name}] ⏳ 스트림 연결 전 준비 대기 중... (2초)")
                time.sleep(2)  # 카메라가 준비될 시간 제공
                prep_elapsed = (datetime.now() - connection_prep_start).total_seconds()
                print(f"[Recorder-{self.cfg.camera_name}] ⏰ 전체 준비 소요 시간: {prep_elapsed:.2f}초")
                
                # DB에서 status가 'recording'인 항목들을 모두 삭제
                self._cleanup_recording_status_records()
                
                cmd = self.build_ffmpeg_cmd()
                print(f"[Recorder-{self.cfg.camera_name}] 🚀 FFmpeg 명령어 실행 시작...")
                print(f"[Recorder-{self.cfg.camera_name}] Launch FFmpeg:", " ".join(shlex.quote(c) for c in cmd))
                
                # FFmpeg 명령어에서 출력 경로 확인
                output_path_index = -1
                for i, arg in enumerate(cmd):
                    if arg.endswith('.mp4'):
                        output_path_index = i
                        break
                
                if output_path_index != -1:
                    print(f"[Recorder-{self.cfg.camera_name}] Output path: {cmd[output_path_index]}")
                    print(f"[Recorder-{self.cfg.camera_name}] Pattern contains strftime: {'%' in cmd[output_path_index]}")

                ffmpeg_start_time = datetime.now()
                print(f"[Recorder-{self.cfg.camera_name}] ⏰ FFmpeg 프로세스 시작 시간: {ffmpeg_start_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
                
                self.process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    universal_newlines=True,
                )
                
                ffmpeg_process_elapsed = (datetime.now() - ffmpeg_start_time).total_seconds() * 1000
                print(f"[Recorder-{self.cfg.camera_name}] ✅ FFmpeg 프로세스 생성 완료 (PID: {self.process.pid})")
                print(f"[Recorder-{self.cfg.camera_name}] ⏰ 프로세스 생성 소요 시간: {ffmpeg_process_elapsed:.2f}ms")

                # FFmpeg 실행 중 실시간 세그먼트 모니터링을 위한 별도 스레드 시작
                import threading
                monitor_thread = threading.Thread(
                    target=self._continuous_monitor_segments,
                    daemon=True,
                    args=(self.cfg.segment_seconds,)  # 설정값 사용
                )
                monitor_thread.start()
                print(f"[Recorder-{self.cfg.camera_name}] 🔍 Started continuous segment monitoring thread")

                for line in self.process.stdout:
                    # Non-monotonic DTS 및 타임스탬프 관련 경고 메시지 필터링
                    line_lower = line.lower()
                    if any(keyword in line_lower for keyword in [
                        "non-monotonic dts",
                        "this may result in incorrect timestamps",
                        "changing to",
                        "vost#0:0/copy",
                        "previous:",
                        "current:"
                    ]):
                        # DTS 관련 경고는 출력하지 않음 (자동으로 처리됨)
                        self._filtered_dts_warnings += 1
                        continue
                    
                    # 필터링된 메시지만 출력
                    print(f"[Recorder-{self.cfg.camera_name}] {line.rstrip()}")
                    
                    # 에러 및 경고 로그만 처리
                    if "error" in line_lower or "failed" in line_lower:
                        error_time = datetime.now()
                        print(f"[Recorder-{self.cfg.camera_name}] ⚠️⚠️⚠️ ERROR: {line.rstrip()}")
                        print(f"[Recorder-{self.cfg.camera_name}] ⏰ 에러 발생 시간: {error_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
                        if ffmpeg_start_time:
                            error_elapsed = (error_time - ffmpeg_start_time).total_seconds()
                            print(f"[Recorder-{self.cfg.camera_name}] ⏰ FFmpeg 시작 후 에러까지 소요 시간: {error_elapsed:.2f}초")
                        self._analyze_error(line)
                    elif "warning" in line_lower:
                        warning_time = datetime.now()
                        print(f"[Recorder-{self.cfg.camera_name}] ⚠️ WARNING: {line.rstrip()}")
                        print(f"[Recorder-{self.cfg.camera_name}] ⏰ 경고 발생 시간: {warning_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
                    
                    if self._stop.is_set():
                        break

                ret = self.process.poll()
                if ret is None:
                    continue
                
                ffmpeg_end_time = datetime.now()
                if ffmpeg_start_time:
                    total_elapsed = (ffmpeg_end_time - ffmpeg_start_time).total_seconds()
                    print(f"[Recorder-{self.cfg.camera_name}] ⏰ FFmpeg 총 실행 시간: {total_elapsed:.2f}초")
                
                if ret == 0:
                    print(f"[Recorder-{self.cfg.camera_name}] ✅ FFmpeg completed successfully")
                else:
                    print(f"[Recorder-{self.cfg.camera_name}] ❌ FFmpeg exited with code {ret}")
                    print(f"[Recorder-{self.cfg.camera_name}] ⏰ 종료 시간: {ffmpeg_end_time.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]}")
                    print(f"[Recorder-{self.cfg.camera_name}] 🔍 스트림 연결 실패 원인 분석:")
                    print(f"[Recorder-{self.cfg.camera_name}]   1. RTSP URL 확인: {self.cfg.rtsp_url}")
                    print(f"[Recorder-{self.cfg.camera_name}]   2. 네트워크 연결 상태 점검 필요")
                    print(f"[Recorder-{self.cfg.camera_name}]   3. 카메라 접근 가능 여부 확인 필요")
                    print(f"[Recorder-{self.cfg.camera_name}]   4. 인증 정보 확인 필요")
                    print(f"[Recorder-{self.cfg.camera_name}]   5. 타임아웃 설정: {self.cfg.timeout_mode}={self.cfg.timeout_value_us}초")
                    print(f"[Recorder-{self.cfg.camera_name}]   6. RTSP Transport: {self.cfg.rtsp_transport}")
                    print(f"[Recorder-{self.cfg.camera_name}]   7. Analyzeduration: {self.cfg.analyzeduration}, Probesize: {self.cfg.probesize}")
                    
                # 세그먼트 파일 확인
                self._check_segment_files()
                
               
                # RTSP 연결 상태 확인
                self._check_rtsp_connection()
                
                # 필터링된 DTS 경고 수 출력 (100개 이상일 때만)
                if self._filtered_dts_warnings > 0 and self._filtered_dts_warnings % 100 == 0:
                    print(f"[Recorder-{self.cfg.camera_name}] 🔧 Filtered {self._filtered_dts_warnings} DTS warnings (auto-handled)")

            except Exception as e:
                print(f"[Recorder-{self.cfg.camera_name}] Exception: {e}")

            if not self._stop.is_set():
                print(f"[Recorder-{self.cfg.camera_name}] Restarting in {self.cfg.reconnect_delay_sec}s...")
                time.sleep(self.cfg.reconnect_delay_sec)

    def stop(self, timeout: int = 10):
        self._stop.set()
        if self.process and self.process.poll() is None:
            try:
                if os.name == "nt":
                    self.process.terminate()
                else:
                    self.process.send_signal(signal.SIGINT)
                self.process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                print(f"[Recorder-{self.cfg.camera_name}] Force killing FFmpeg...")
                self.process.kill()

        if self._monitor_thread:
            self._monitor_thread.join(timeout=timeout)
        print(f"[Recorder-{self.cfg.camera_name}] Stopped.")


class MultiCameraRecorder:
    def __init__(self):
        self.recorders = {}
        self.db_connection = None
        self.running = False

    def connect_to_db(self):
        """데이터베이스 연결"""
        try:
            if self.db_connection is not None:
                try:
                    cursor = self.db_connection.cursor()
                    cursor.execute('SELECT 1')
                    cursor.close()
                    return True
                except Exception as e:
                    print(f"Connection check failed: {str(e)}")
                    self.db_connection = None
            
            self.db_connection = pymysql.connect(
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
            print("Database connected successfully")
            return True
        except Exception as e:
            print(f'Database connection failed: {str(e)}')
            print(f'Connection params: host={DBSERVER_IP}, port={DBSERVER_PORT}, user={DBSERVER_USER}, db={DBSERVER_DB}')
            self.db_connection = None
            return False

    def disconnect_db(self):
        """데이터베이스 연결 해제"""
        try:
            if self.db_connection:
                self.db_connection.close()
                self.db_connection = None
                print("Database disconnected")
        except Exception as e:
            print(f'Error disconnecting database: {str(e)}')

    def _generate_camera_name(self, index: int) -> str:
        """순차적인 카메라 이름 생성 (camera1, camera2, ...)"""
        return f"camera{index}"

    def _is_recording_enabled(self):
        """DB에서 레코딩 활성화 상태 확인"""
        try:
            if not self.connect_to_db():
                print("⚠️ DB connection failed, defaulting to recording enabled")
                return True  # DB 연결 실패 시 기본적으로 활성화
            
            cursor = self.db_connection.cursor()
            query = "SELECT object_json FROM tb_event_setting LIMIT 1"
            cursor.execute(query)
            result = cursor.fetchone()
            
            if result and result['object_json']:
                object_json = json.loads(result['object_json'])
                recording_config = object_json.get('recording', {})
                recording_enabled = recording_config.get('enabled', True)
                status_icon = "🟢" if recording_enabled else "🔴"
                print(f"📹 Recording Status Check: {status_icon} {'ENABLED' if recording_enabled else 'DISABLED'}")
                return recording_enabled
            else:
                print("📹 No object_json found, defaulting to recording enabled")
                return True
                
        except Exception as e:
            print(f"❌ Error checking recording status: {e}")
            return True  # 에러 시 기본적으로 활성화

    def get_camera_list(self):
        """tb_cameras 테이블에서 카메라 정보 조회"""
        try:
            if not self.connect_to_db():
                return []

            cursor = self.db_connection.cursor()
            query = """
                SELECT name, videoConfig 
                FROM tb_cameras 
                WHERE videoConfig IS NOT NULL 
                AND videoConfig != ''
            """
            cursor.execute(query)
            results = cursor.fetchall()
            
            camera_list = []
            camera_index = 1
            for row in results:
                try:
                    if row['videoConfig']:
                        video_config = json.loads(row['videoConfig'])
                        if 'source' in video_config:
                            # RTSP URL에서 -i 파라미터 제거
                            rtsp_url = video_config['source']
                            
                            # URL이 문자열인지 확인
                            if not isinstance(rtsp_url, str):
                                print(f"Invalid source type: {type(rtsp_url)}, value: {rtsp_url}")
                                continue
                            
                            # 빈 문자열 체크
                            if not rtsp_url.strip():
                                print(f"Empty source URL: {rtsp_url}")
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
                                            print(f"No valid protocol found in URL: {rtsp_url}")
                                            continue
                            
                            # URL 정리 (앞뒤 공백 제거 및 끝에 붙은 점 제거)
                            rtsp_url = rtsp_url.strip()
                            # URL 끝에 붙은 점(.) 제거 (DB에서 잘못 저장된 경우 대비)
                            original_url = rtsp_url
                            if rtsp_url.endswith('.'):
                                rtsp_url = rtsp_url.rstrip('.')
                                print(f"[ConfigLoader] ⚠️ URL 끝의 점(.) 제거: '{original_url}' -> '{rtsp_url}'")
                            
                            # 순차적인 카메라 이름 생성 (camera1, camera2, ...)
                            camera_name = self._generate_camera_name(camera_index)
                            
                            # videoType 추출 (열화상: 1, 실화상: 2)
                            video_type = video_config.get('videoType', 2)  # 기본값: 실화상(2)
                            if not isinstance(video_type, int):
                                try:
                                    video_type = int(video_type)
                                except (ValueError, TypeError):
                                    video_type = 2  # 기본값: 실화상
                            
                            camera_info = {
                                'name': row['name'],
                                'camera_name': camera_name,
                                'rtsp_url': rtsp_url,
                                'video_config': video_config,
                                'video_type': video_type
                            }
                            camera_list.append(camera_info)
                            
                            # 순차적인 이름으로 출력
                            print(f"Found camera - Name: {camera_name} (Original: {row['name']}), RTSP: {rtsp_url}")
                            
                            camera_index += 1
                            
                except json.JSONDecodeError as e:
                    print(f"Error parsing videoConfig JSON: {str(e)}")
                except Exception as e:
                    print(f"Error processing videoConfig: {str(e)}")
            
            cursor.close()
            print(f"Retrieved {len(camera_list)} camera configurations")
            return camera_list

        except Exception as e:
            print(f"Error getting camera list: {str(e)}")
            return []

    def start_all_recorders(self):
        """모든 카메라 녹화 시작"""
        # 시작 전에 설정을 다시 로드 (30초마다 업데이트)
        load_event_settings()
        
        # 레코딩이 비활성화되었는지 확인
        if not self._is_recording_enabled():
            print("📹 Recording is disabled in settings, skipping recorder startup")
            print("📹 Program will continue running and check settings every 30 seconds")
            return
        
        camera_list = self.get_camera_list()
        if not camera_list:
            print("⚠️ No cameras found in database")
            return

        print(f"🎬 Starting recorders for {len(camera_list)} cameras...", flush=True)
        print(f"📹 Using SPLIT_SECONDS: {SPLIT_SECONDS} seconds ({SPLIT_SECONDS/60:.1f} minutes)", flush=True)
        print(f"📹 Using DEFAULT_BITRATE: {DEFAULT_BITRATE}", flush=True)
        print("-" * 60, flush=True)
        
        for camera_info in camera_list:
            try:
                video_type = camera_info.get('video_type', 2)  # 기본값: 실화상(2)
                # 열화상 카메라(video_type=1)인 경우 reencode_video를 True로 설정하여 해상도/프레임레이트 강제
                is_thermal = (video_type == 1)
                
                config = RecorderConfig(
                    rtsp_url=camera_info['rtsp_url'],
                    camera_name=camera_info['camera_name'],  # 순차적인 이름 사용
                    output_dir=Path("./outputs/nvr/recordings"),
                    segment_seconds=SPLIT_SECONDS,  # DB에서 로드된 세그먼트 분할 시간
                    video_bitrate=DEFAULT_BITRATE,  # DB에서 로드된 비트레이트
                    reencode_video=is_thermal,  # 열화상 카메라는 인코딩 필요 (해상도/프레임레이트 강제)
                    rtsp_transport="tcp",
                    use_timeouts=True,  # 타임아웃 활성화
                    timeout_mode="timeout",  # timeout 옵션 사용
                    timeout_value_us=10_000_000,  # 10초 타임아웃
                    video_type=video_type
                )
                
                recorder = RTSPRecorder(config)
                # 원본 카메라 이름 설정 (tb_recording_history용)
                recorder.original_camera_name = camera_info['name']
                
                self.recorders[camera_info['camera_name']] = recorder  # 순차적인 이름을 키로 사용
                recorder.start()
                print(f"✅ Started recorder: {camera_info['camera_name']} ({camera_info['name']})", flush=True)
                
            except Exception as e:
                print(f"❌ Error starting recorder for {camera_info['camera_name']}: {e}", flush=True)

        if self.recorders:
            self.running = True
            print("-" * 60, flush=True)
            print(f"🎉 Successfully started {len(self.recorders)} recorders", flush=True)
            for name in self.recorders.keys():
                print(f"   📹 - {name}", flush=True)
        else:
            print("⚠️ No recorders started (recording may be disabled)", flush=True)

    def stop_all_recorders(self):
        """모든 녹화 중지"""
        if not self.recorders:
            print("📹 No active recorders to stop")
            return
            
        print("\n" + "=" * 80)
        print("⏹️ STOPPING ALL RECORDERS")
        print("=" * 80)
        print(f"📹 Stopping {len(self.recorders)} active recorders...")
        print("-" * 60)
        
        for name, recorder in self.recorders.items():
            try:
                print(f"⏹️ Stopping recorder: {name}")
                recorder.stop()
                print(f"✅ Recorder {name} stopped successfully")
            except Exception as e:
                print(f"❌ Error stopping recorder {name}: {e}")
        
        self.recorders.clear()
        # self.running = False  # 프로그램이 계속 실행되도록 주석 처리
        
        print("-" * 60)
        print("🎯 RECORDING STATUS: ALL RECORDERS STOPPED")
        print("📹 Program continues running and monitoring settings...")
        print("=" * 80 + "\n")

    def run(self):
        """메인 실행 루프"""
        try:
            # 초기 설정 로드 및 녹화기 시작 시도
            self.start_all_recorders()
            
            # 프로그램이 계속 실행되도록 self.running을 True로 설정
            self.running = True
            
            print("\n" + "=" * 80, flush=True)
            print("🚀 MULTI-CAMERA RECORDER STARTED", flush=True)
            print("=" * 80, flush=True)
            print("📹 Program will continue running even if recording is disabled.", flush=True)
            print("📹 Settings will be checked every 30 seconds for changes.", flush=True)
            print("📹 Press Ctrl+C to stop the program.", flush=True)
            print("=" * 80 + "\n", flush=True)
            
            last_settings_reload = time.time()
            settings_reload_interval = 30  # 30초마다 설정 다시 로드
            
            while self.running:
                current_time = time.time()
                
                # 30초마다 설정 다시 로드
                if current_time - last_settings_reload >= settings_reload_interval:
                    print("🔄 RELOADING SETTINGS FROM DATABASE...", flush=True)
                    load_event_settings()
                    last_settings_reload = current_time
                    
                    # 설정이 변경되었는지 확인하고 필요시 녹화기 재시작
                    self._check_and_restart_recorders_if_needed()
                
                time.sleep(1)
                
        except KeyboardInterrupt:
            print("\n" + "=" * 80, flush=True)
            print("⏹️ PROGRAM INTERRUPTED BY USER", flush=True)
            print("=" * 80, flush=True)
        finally:
            self.stop_all_recorders()
            self.disconnect_db()
    
    def _check_and_restart_recorders_if_needed(self):
        """설정 변경 시 녹화기 재시작이 필요한지 확인"""
        try:
            print("\n" + "-" * 60)
            print("🔍 CHECKING RECORDING STATUS AND SETTINGS")
            print("-" * 60)
            recording_enabled = self._is_recording_enabled()
            
            # 레코딩이 비활성화된 경우
            if not recording_enabled:
                if self.recorders:
                    print("🔴 Recording disabled, stopping all recorders...")
                    self.stop_all_recorders()
                else:
                    print("🔴 Recording is disabled. No recorders running.")
                print("-" * 60 + "\n")
                return
            
            # 레코딩이 활성화된 경우
            if recording_enabled:
                # 녹화기가 없는 경우 시작
                if not self.recorders:
                    print("🟢 Recording enabled, starting recorders...")
                    self.start_all_recorders()
                    print("-" * 60 + "\n")
                    return
                
                # 현재 실행 중인 녹화기들의 설정과 새로운 설정 비교
                settings_changed = False
                for name, recorder in self.recorders.items():
                    current_segment_seconds = recorder.cfg.segment_seconds
                    current_bitrate = recorder.cfg.video_bitrate
                    
                    # 설정이 변경되었으면 재시작
                    if (current_segment_seconds != SPLIT_SECONDS or 
                        current_bitrate != DEFAULT_BITRATE):
                        
                        settings_changed = True
                        print(f"🔄 Settings changed for {name}, restarting recorder...")
                        print(f"   📹 Segment: {current_segment_seconds}s → {SPLIT_SECONDS}s")
                        print(f"   📹 Bitrate: {current_bitrate} → {DEFAULT_BITRATE}")
                        
                        # 기존 녹화기 중지
                        recorder.stop()
                        
                        # 새로운 설정으로 녹화기 재시작
                        config = RecorderConfig(
                            rtsp_url=recorder.cfg.rtsp_url,
                            camera_name=recorder.cfg.camera_name,
                            output_dir=Path("./outputs/nvr/recordings"),
                            segment_seconds=SPLIT_SECONDS,
                            video_bitrate=DEFAULT_BITRATE,
                            reencode_video=False,
                            rtsp_transport="tcp",
                            use_timeouts=True,
                            timeout_mode="timeout",
                            timeout_value_us=10_000_000
                        )
                        
                        new_recorder = RTSPRecorder(config)
                        new_recorder.original_camera_name = recorder.original_camera_name
                        
                        self.recorders[name] = new_recorder
                        new_recorder.start()
                        print(f"✅ Recorder {name} restarted with new settings")
                
                if not settings_changed:
                    print("🟢 Recording enabled. All recorders running with current settings.")
                    print(f"   📹 Active recorders: {len(self.recorders)}")
                    for name in self.recorders.keys():
                        print(f"   📹 - {name}")
            
            print("-" * 60 + "\n")
                    
        except Exception as e:
            print(f"❌ Error checking and restarting recorders: {e}")
            print("-" * 60 + "\n")


if __name__ == "__main__":
    # 단일 카메라 녹화 (기존 방식)
    if len(sys.argv) > 1 and sys.argv[1] == "--single":
        cfg = RecorderConfig(
            rtsp_url="rtsp://210.99.70.120:1935/live/cctv005.stream",
            camera_name="test_camera",
            segment_seconds=SPLIT_SECONDS,               # DB에서 로드된 분할 길이(초)
            output_dir=Path("./outputs/nvr/recordings"),
            reencode_video=False,             # True로 바꾸면 video_bitrate 적용됨
            video_bitrate=DEFAULT_BITRATE,    # DB에서 로드된 비트레이트
            gop_seconds=None,                 # None이면 segment_seconds 사용
            rtsp_transport="tcp",
        )

        rec = RTSPRecorder(cfg)
        try:
            rec.start()
            print("[Recorder] Running. Press Ctrl+C to stop.")
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[Recorder] Interrupted by user.")
        finally:
            rec.stop()
    else:
        # 다중 카메라 녹화 (기본)
        multi_recorder = MultiCameraRecorder()
        multi_recorder.run()
