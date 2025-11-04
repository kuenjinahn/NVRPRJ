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
        """출력 파일 경로 생성 - segment 분할을 위한 패턴"""
        # 현재 날짜로 날짜별 폴더 생성
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        # 카메라별 + 날짜별 디렉토리 생성
        camera_date_dir = self.cfg.output_dir / self.cfg.camera_name / current_date
        camera_date_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"[Recorder-{self.cfg.camera_name}] Created date directory: {camera_date_dir}")
        
        # Python에서 동적으로 날짜 폴더를 포함한 패턴 생성
        # FFmpeg의 strftime 처리 문제를 피하면서 날짜별 폴더 구조 유지
        pattern = f"./outputs/nvr/recordings/{self.cfg.camera_name}/{current_date}/segment_%03d.mp4"
        
        print(f"[Recorder-{self.cfg.camera_name}] Generated pattern: {pattern}")
        print(f"[Recorder-{self.cfg.camera_name}] Note: Using Python dynamic date folder creation")
        return pattern

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
                
                # 이미 처리된 세그먼트인지 확인
                if file_path in self._processed_segments:
                    print(f"[Recorder-{self.cfg.camera_name}] ⚠️ Already processed segment: {file_path}")
                    return
                
                # 세그먼트 번호 추출
                segment_number = self._extract_segment_number(file_path)
                if segment_number is not None:
                    # 처리된 세그먼트 목록에 추가
                    self._processed_segments.add(file_path)
                    # 데이터베이스에 INSERT
                    self._insert_recording_history(file_path, segment_number)
                else:
                    print(f"[Recorder-{self.cfg.camera_name}] ⚠️ Could not extract segment number from: {file_path}")
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
                            
                            # 세그먼트 번호 추출
                            segment_number = self._extract_segment_number(file_path)
                            if segment_number is not None:
                                print(f"[Recorder-{self.cfg.camera_name}] 🎯 Processing segment #{segment_number}: {mp4_file.name}")
                                
                                # 처리된 세그먼트 목록에 추가
                                self._processed_segments.add(file_path)
                                
                                # 데이터베이스에 INSERT
                                print(f"[Recorder-{self.cfg.camera_name}] 🗄️ Manual database INSERT...")
                                self._insert_recording_history(file_path, segment_number)
                                total_processed += 1
                            else:
                                print(f"[Recorder-{self.cfg.camera_name}] ⚠️ Could not extract segment number from: {mp4_file.name}")
            
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
        try:
            print(f"[Recorder-{self.cfg.camera_name}] 🔍 Checking RTSP connection status...")
            
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
                    print(f"[Recorder-{self.cfg.camera_name}] RTSP IP: {ip_address}")
                    
                    # ping 테스트
                    import subprocess
                    try:
                        result = subprocess.run(
                            ["ping", "-n", "1", ip_address], 
                            capture_output=True, 
                            text=True, 
                            timeout=5
                        )
                        if result.returncode == 0:
                            print(f"[Recorder-{self.cfg.camera_name}] ✅ Ping to {ip_address}: SUCCESS")
                        else:
                            print(f"[Recorder-{self.cfg.camera_name}] ❌ Ping to {ip_address}: FAILED")
                    except Exception as e:
                        print(f"[Recorder-{self.cfg.camera_name}] ⚠️ Ping test failed: {e}")
                else:
                    print(f"[Recorder-{self.cfg.camera_name}] ⚠️ Could not extract IP from RTSP URL")
            else:
                print(f"[Recorder-{self.cfg.camera_name}] ⚠️ Invalid RTSP URL format")
                
        except Exception as e:
            print(f"[Recorder-{self.cfg.camera_name}] Error checking RTSP connection: {e}")

    def _monitor_segment_files(self):
        """파일 시스템을 직접 모니터링하여 세그먼트 파일 감지"""
        try:
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
                print(f"[Recorder-{self.cfg.camera_name}] 🔍 Found {len(new_files)} new segment files")
                
                for file_path in new_files:
                    # 세그먼트 번호 추출
                    segment_number = self._extract_segment_number(file_path)
                    if segment_number is not None:
                        print(f"[Recorder-{self.cfg.camera_name}] 🎯 Processing new segment #{segment_number}: {os.path.basename(file_path)}")
                        
                        # 처리된 세그먼트 목록에 추가
                        self._processed_segments.add(file_path)
                        
                        # 데이터베이스에 INSERT
                        print(f"[Recorder-{self.cfg.camera_name}] 🗄️ Database INSERT for new segment...")
                        self._insert_recording_history(file_path, segment_number)
                    else:
                        print(f"[Recorder-{self.cfg.camera_name}] ⚠️ Could not extract segment number from: {os.path.basename(file_path)}")
                        
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
                    # 세그먼트 파일 확인
                    self._monitor_segment_files()
                    
                    # 지정된 간격만큼 대기
                    import time
                    time.sleep(interval_seconds)
                    
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
                
                # 이미 처리된 세그먼트인지 확인
                if file_path in self._processed_segments:
                    print(f"[Recorder-{self.cfg.camera_name}] ⚠️ Already processed segment: {file_path}")
                    return
                
                # 세그먼트 번호 추출 (segment_000.mp4 -> 0)
                segment_number = self._extract_segment_number(file_path)
                if segment_number is not None:
                    print(f"[Recorder-{self.cfg.camera_name}] 🎯 New segment #{segment_number} detected: {file_path}")
                    
                    # 처리된 세그먼트 목록에 추가
                    self._processed_segments.add(file_path)
                    print(f"[Recorder-{self.cfg.camera_name}] ✅ Added to processed segments list")
                    
                    # 데이터베이스에 INSERT
                    print(f"[Recorder-{self.cfg.camera_name}] 🗄️ Attempting database INSERT...")
                    self._insert_recording_history(file_path, segment_number)
                else:
                    print(f"[Recorder-{self.cfg.camera_name}] ⚠️ Could not extract segment number from: {file_path}")
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

    def _extract_segment_number(self, file_path: str) -> Optional[int]:
        """파일 경로에서 세그먼트 번호 추출"""
        try:
            # 파일명만 추출 (경로 제거)
            filename = os.path.basename(file_path)
            
            # segment_000.mp4 패턴에서 000 추출 (0부터 시작)
            if filename.startswith("segment_") and filename.endswith(".mp4"):
                segment_part = filename[8:-4]  # "segment_" 제거하고 ".mp4" 제거
                if segment_part.isdigit():
                    segment_num = int(segment_part)
                    print(f"[Recorder-{self.cfg.camera_name}] Extracted segment number: {segment_num} from {filename}")
                    return segment_num
            
            # 다른 패턴도 지원 (예: camera1_000.mp4)
            if "_" in filename and filename.endswith(".mp4"):
                parts = filename[:-4].split("_")  # .mp4 제거하고 _로 분할
                if len(parts) >= 2 and parts[-1].isdigit():
                    segment_num = int(parts[-1])
                    print(f"[Recorder-{self.cfg.camera_name}] Extracted segment number: {segment_num} from {filename}")
                    return segment_num
                    
        except Exception as e:
            print(f"[Recorder-{self.cfg.camera_name}] Error extracting segment number: {e}")
        
        return None

    def _insert_recording_history(self, file_path: str, segment_number: int = None):
        """tb_recording_history 테이블에 녹화 기록 insert"""
        try:
            print(f"[Recorder-{self.cfg.camera_name}] 🗄️ Starting database INSERT for: {file_path}")
            
            # DB 연결 테스트
            print(f"[Recorder-{self.cfg.camera_name}] 🔍 Testing database connection...")
            print(f"[Recorder-{self.cfg.camera_name}] DB Config: {DBSERVER_IP}:{DBSERVER_PORT}, User: {DBSERVER_USER}, DB: {DBSERVER_DB}")
            
            # 파일 정보 수집
            file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
            
            # 세그먼트별 정확한 시작/종료 시간 계산
            if segment_number is not None:
                # 세그먼트 번호가 있는 경우: 정확한 시간 계산
                # segment_000.mp4는 첫 번째 세그먼트 (0부터 시작)
                segment_start_time = self.recording_start_time + timedelta(seconds=segment_number * self.cfg.segment_seconds)
                segment_end_time = segment_start_time + timedelta(seconds=self.cfg.segment_seconds)
                segment_duration = self.cfg.segment_seconds
                
                print(f"[Recorder-{self.cfg.camera_name}] Time calculation for segment #{segment_number}:")
                print(f"  Recording start: {self.recording_start_time}")
                print(f"  Segment start: {segment_start_time}")
                print(f"  Segment end: {segment_end_time}")
                print(f"  Expected duration: {segment_duration} seconds")
            else:
                # 세그먼트 번호가 없는 경우: 전체 녹화 시간 사용
                segment_start_time = self.recording_start_time
                segment_end_time = datetime.now()
                segment_duration = int((segment_end_time - segment_start_time).total_seconds()) if segment_start_time else 0
            
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
                'completed',  # status
                None,  # resolution
                None,  # bitrate
                None,  # framerate
                None,  # codec
                datetime.now(),  # create_date
                datetime.now()   # update_date
            )
            
            print(f"[Recorder-{self.cfg.camera_name}] 🔍 Executing INSERT query...")
            cursor.execute(query, values)
            print(f"[Recorder-{self.cfg.camera_name}] ✅ INSERT query executed successfully")
            
            db_connection.commit()
            print(f"[Recorder-{self.cfg.camera_name}] ✅ Database commit successful")
            
            cursor.close()
            db_connection.close()
            print(f"[Recorder-{self.cfg.camera_name}] ✅ Database connection closed")
            
            print(f"[Recorder-{self.cfg.camera_name}] 🎉 Recording history inserted successfully:")
            print(f"  Segment #{segment_number if segment_number else 'N/A'}")
            print(f"  Start time: {segment_start_time}")
            print(f"  End time: {segment_end_time}")
            print(f"  Duration: {segment_duration} seconds ({segment_duration/60:.1f} minutes)")
            print(f"  Absolute path: {file_path}")
            print(f"  Relative path: {relative_file_path}")
            print(f"  File size: {file_size} bytes")
            
        except Exception as e:
            print(f"[Recorder-{self.cfg.camera_name}] Error inserting recording history: {e}")

    def build_ffmpeg_cmd(self) -> List[str]:
        out_pattern = self._get_output_path()

        cmd = [
            self.cfg.ffmpeg_path,
            "-hide_banner", "-loglevel", "error",  # error 레벨로 설정하여 Non-monotonic DTS 경고 숨김
            "-nostats",  # 진행 상황 통계 출력 완전 비활성화
            "-rtsp_transport", self.cfg.rtsp_transport,
        ]
        
        # 🔧 로그 레벨 설정 안내
        print(f"[Recorder-{self.cfg.camera_name}] 🔧 FFmpeg log level: error (Non-monotonic DTS 경고 숨김)")
        print(f"[Recorder-{self.cfg.camera_name}] 💡 필요시 -loglevel을 'warning' 또는 'info'로 변경 가능")

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
            "-map", "0",
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
        else:
            # 스트림 복사 모드
            cmd += [
                "-c:v", "copy",
            ]

        # 출력 옵션 (세그먼트 파일 생성용)
        cmd += [
            "-an",  # 오디오 제거
            "-f", "segment",
            "-segment_time", str(SPLIT_SECONDS),  # 문자열로 변환
            "-reset_timestamps", "1",
            "-segment_format", "mp4",
            "-movflags", "+faststart",
            "-max_muxing_queue_size", str(self.cfg.max_muxing_queue_size),
            "-segment_start_number", "0",  # 세그먼트 번호 시작
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
                cmd = self.build_ffmpeg_cmd()
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

                self.process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    universal_newlines=True,
                )

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
                        print(f"[Recorder-{self.cfg.camera_name}] ⚠️ ERROR: {line.rstrip()}")
                        self._analyze_error(line)
                    elif "warning" in line_lower:
                        print(f"[Recorder-{self.camera_name}] ⚠️ WARNING: {line.rstrip()}")
                    
                    if self._stop.is_set():
                        break

                ret = self.process.poll()
                if ret is None:
                    continue
                
                if ret == 0:
                    print(f"[Recorder-{self.cfg.camera_name}] FFmpeg completed successfully")
                else:
                    print(f"[Recorder-{self.cfg.camera_name}] FFmpeg exited with code {ret}")
                    
                # 세그먼트 파일 확인
                self._check_segment_files()
                
                # 수동으로 세그먼트 파일 확인 및 DB INSERT 시도
                self._manual_segment_check()
                
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
                            
                            camera_info = {
                                'name': row['name'],
                                'camera_name': camera_name,
                                'rtsp_url': rtsp_url,
                                'video_config': video_config
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
                config = RecorderConfig(
                    rtsp_url=camera_info['rtsp_url'],
                    camera_name=camera_info['camera_name'],  # 순차적인 이름 사용
                    output_dir=Path("./outputs/nvr/recordings"),
                    segment_seconds=SPLIT_SECONDS,  # DB에서 로드된 세그먼트 분할 시간
                    video_bitrate=DEFAULT_BITRATE,  # DB에서 로드된 비트레이트
                    reencode_video=False,
                    rtsp_transport="tcp",
                    use_timeouts=True,  # 타임아웃 활성화
                    timeout_mode="timeout",  # timeout 옵션 사용
                    timeout_value_us=10_000_000  # 10초 타임아웃
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
