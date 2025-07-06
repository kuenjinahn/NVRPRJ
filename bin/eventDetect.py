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
import cv2
import numpy as np
import traceback
from pathlib import Path
import subprocess
from ultralytics import YOLO  # YOLOv8 추가
import argparse  # 명령행 인자 처리를 위해 추가
import threading
import queue
import ffmpeg
import pymysql
import zipfile

# 로깅 설정
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)
log_file = log_dir / "event_detecter.log"

handler = RotatingFileHandler(
    log_file, maxBytes=10*1024*1024, backupCount=5, encoding='utf-8'
)
handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
))

logger = logging.getLogger("EventDetecter")
logger.setLevel(logging.INFO)
logger.addHandler(handler)

# 콘솔 출력을 위한 핸들러 추가
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
))
logger.addHandler(console_handler)

def load_config():
    config = ConfigParser()
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.ini')
    
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")
    
    config.read(config_path, encoding='utf-8')
    return config

# 설정 로드
config = load_config()

### mariadb 연결정보 ####
DBSERVER_IP = config.get('DATABASE', 'host')
DBSERVER_PORT = config.getint('DATABASE', 'port')
DBSERVER_USER = config.get('DATABASE', 'user')
DBSERVER_PASSWORD = config.get('DATABASE', 'password')
DBSERVER_DB = config.get('DATABASE', 'database')
DBSERVER_CHARSET = config.get('DATABASE', 'charset')
nvrdb = None

CAMERA_NAME = config.get('EVENT_DETECT', 'camera_name')
DETECTED_MOVE_DIR = config.get('EVENT_DETECT', 'detected_move_dir')
########################

def parse_cameras_from_json():
    """
    ../test/camera.ui/database/dababase.json 파일에서 cameras 키값을 파싱하여 반환합니다.
    """
    json_path = '../test/camera.ui/database/database.json'
    try:
        # JSON 파일 경로
        json_path = json_path
        
        # JSON 파일 읽기
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # cameras 키값 추출
        if 'cameras' in data:
            return data['cameras']
        else:
            logger.warning("'cameras' key not found in JSON file")
            return None
            
    except FileNotFoundError:
        logger.error(f"File not found at {json_path}")
        return None
    except json.JSONDecodeError:
        logger.error("Invalid JSON format")
        return None
    except Exception as e:
        logger.error(f"Error parsing JSON: {str(e)}")
        return None

class EventDetecter:
    def __init__(self, debug_mode=False):
        self.debug_mode = debug_mode
        self.cameras = parse_cameras_from_json()
        if not self.cameras:
            logger.error("Failed to load cameras from JSON")
            self.cameras = {}
        self.object_setting = None
        self.last_setting_time = 0
        self.setting_lock = threading.Lock()
        self.detection_zones = {}  # {camera_id: [zone, ...]}
        self.yolo_model = None  # Initialize YOLO model as None
        
        # 프레임 처리 간격 설정 (초 단위)
        self.frame_interval = 1.0  # 기본값 1초
        self.last_object_detect_time = 0
        self.last_motion_detect_time = 0
        
        # 스레드 제어를 위한 이벤트
        self.stop_event = threading.Event()
        
        # 프레임 버퍼를 위한 큐
        self.frame_queue = queue.Queue(maxsize=30)  # 최대 30프레임 저장

    def connect_to_db(self):
        global nvrdb
        try:
            if nvrdb is not None:
                try:
                    # 연결 상태 확인을 위한 간단한 쿼리 실행
                    cursor = nvrdb.cursor()
                    cursor.execute('SELECT 1')
                    cursor.close()
                    return True
                except Exception as e:
                    logger.error(f"Connection check failed: {str(e)}")
                    nvrdb = None
            
            # 새로운 연결 생성
            nvrdb = pymysql.connect(
                host=DBSERVER_IP,
                port=DBSERVER_PORT,
                user=DBSERVER_USER,
                password=DBSERVER_PASSWORD,
                db=DBSERVER_DB,
                charset='utf8',
                autocommit=True,
                cursorclass=pymysql.cursors.DictCursor,
                connect_timeout=5
            )
            logger.info("Database connected successfully")
            return True
        except Exception as e:
            logger.error(f'Database connection failed: {str(e)}')
            logger.error(f'Connection params: host={DBSERVER_IP}, port={DBSERVER_PORT}, user={DBSERVER_USER}, db={DBSERVER_DB}')
            onixdb = None
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

    def draw_detections(self, image, results):
        annotated = image.copy()
        for box, conf, cls in zip(results.boxes.xyxy.cpu().numpy(), results.boxes.conf.cpu().numpy(), results.boxes.cls.cpu().numpy()):
            x1, y1, x2, y2 = map(int, box)
            label = f"{results.names[int(cls)]} {conf:.2f}"
            color = (0, 255, 0)
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
            cv2.putText(annotated, label, (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
        return annotated

    def drain_stderr(self,stderr):
        while True:
            if stderr.closed:
                break
            stderr.read(1024)

    def insert_event_history(self, camera_name, detected_image_url, event_data_json, event_accur_time=None):
        if event_accur_time is None:
            event_accur_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        create_date = event_accur_time
        try:
            cursor = self.get_db_cursor()
            if cursor:
                sql = ("""
                    INSERT INTO tb_event_history 
                    (fk_camera_id, camera_name, event_accur_time, event_type, event_data_json, detected_image_url, create_date)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """)
                cursor.execute(sql, (
                    4, camera_name, event_accur_time, 'E001', event_data_json,detected_image_url, create_date
                ))
                cursor.close()
                logger.info(f"DB Insert: {camera_name}, {event_data_json}, {detected_image_url}")
                return True
            else:
                logger.error("DB cursor is None. Insert failed.")
                return False
        except Exception as e:
            logger.error(f"DB Insert Error: {str(e)}")
            return False

    def insert_motion_event_history(self, camera_name, detected_image_url, zone_id, event_accur_time=None):
        """움직임 감지 이벤트를 DB에 저장"""
        if event_accur_time is None:
            event_accur_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        create_date = event_accur_time
        
        # 이벤트 데이터 JSON 생성
        event_data = {
            "label": "온도이상",
            "zone_id": zone_id,
            "detection_time": event_accur_time
        }
        event_data_json = json.dumps(event_data, ensure_ascii=False)
        
        try:
            cursor = self.get_db_cursor()
            if cursor:
                sql = ("""
                    INSERT INTO tb_event_history 
                    (fk_camera_id, camera_name, event_accur_time, event_type, event_data_json, fk_detect_zone_id, detected_image_url, create_date)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """)
                cursor.execute(sql, (
                    4, camera_name, event_accur_time, 'E002', event_data_json, zone_id, detected_image_url, create_date
                ))
                cursor.close()
                logger.info(f"Motion Event DB Insert: {camera_name}, Zone: {zone_id}, {detected_image_url}")
                return True
            else:
                logger.error("DB cursor is None. Motion event insert failed.")
                return False
        except Exception as e:
            logger.error(f"Motion Event DB Insert Error: {str(e)}")
            return False

    def get_Event_Config(self):
        try:
            cursor = self.get_db_cursor()
            if cursor:
                # tb_event_setting 테이블에서 object_json 조회
                sql = "SELECT object_json FROM tb_event_setting ORDER BY id DESC LIMIT 1"
                cursor.execute(sql)
                result = cursor.fetchone()
                cursor.close()
                
                if result and result.get('object_json'):
                    return json.loads(result['object_json']), None
                else:
                    logger.warning("No event setting found in database")
                    return None, None
            else:
                logger.error("Failed to get database cursor")
                return None, None

        except Exception as e:
            logger.error(f'Error getting event setting from database: {e}')
            return None, None

    def setting_updater(self):
        while True:
            new_setting,new_detection_zone = self.get_Event_Config()
            with self.setting_lock:
                self.object_setting = new_setting
                self.detection_zones = new_detection_zone
                self.last_setting_time = time.time()
            time.sleep(10)

    def save_detected_image(self, camera_name, frame, base_dir):
        try:
            # 날짜 폴더 생성
            today = datetime.now().strftime('%Y-%m-%d')
            save_dir = os.path.join(base_dir, today)
            os.makedirs(save_dir, exist_ok=True)
            
            # 타임스탬프 생성
            timestamp = datetime.now().strftime('%H%M%S_%f')
            
            # 이미지 파일명과 경로
            image_filename = f'{camera_name}_{timestamp}.jpg'
            image_path = os.path.join(save_dir, image_filename)
            
            # 이미지 저장
            cv2.imwrite(image_path, frame)
            logger.info(f"Detected image saved: {image_path}")
            
            return image_path
            
        except Exception as e:
            logger.error(f"Error in save_detected_image: {str(e)}")
            return None

    def detect_motion_in_polygon(self, prev_frame, curr_frame, polygon):
        # polygon: [[x1, y1], [x2, y2], ...]
        Threshold = 30
        mask = np.zeros(curr_frame.shape[:2], dtype=np.uint8)
        pts = np.array(polygon, np.int32)
        pts = pts.reshape((-1, 1, 2))
        cv2.fillPoly(mask, [pts], 255)
        gray_prev = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)
        gray_curr = cv2.cvtColor(curr_frame, cv2.COLOR_BGR2GRAY)
        diff = cv2.absdiff(gray_prev, gray_curr)
        masked_diff = cv2.bitwise_and(diff, diff, mask=mask)
        thresh = cv2.threshold(masked_diff, 25, 255, cv2.THRESH_BINARY)[1]
        motion_pixels = cv2.countNonZero(thresh)
        is_motion = motion_pixels > Threshold  # 임계값은 상황에 맞게 조정
        logger.info(f"Motion detection - Pixels changed: {motion_pixels}, Threshold: {Threshold}, Detected: {is_motion}")
        return is_motion

    def process_detection(self, curr_frame):
        camera_name = CAMERA_NAME
        logger.info(f"Processing frame for camera {camera_name}")
        
        # Get current settings for object detection
        with self.setting_lock:
            object_setting = self.object_setting
        
        enable_tracking, detection_labels, confidence_threshold, _ = self.process_settings(object_setting)
        
        # Debug 모드일 때 원본 프레임 표시
        # if self.debug_mode:
        #     cv2.imshow('Original Frame', curr_frame)
        #     cv2.waitKey(1)
        
        # Perform object detection on entire frame if enabled
        if enable_tracking and self.yolo_model is not None:
            frame = curr_frame.copy()
            results, filtered_boxes, annotated, detected_objects = self.run_yolo_and_filter(
                self.yolo_model, frame, detection_labels, confidence_threshold
            )
            
            if filtered_boxes:
                today = datetime.now().strftime('%Y-%m-%d')
                output_dir = os.path.join(DETECTED_MOVE_DIR, today)
                os.makedirs(output_dir, exist_ok=True)
                filename = os.path.join(output_dir, f'{camera_name}_detection_{int(time.time())}.jpg')
                cv2.imwrite(filename, annotated)
                
                # DB 기록
                event_data_json = json.dumps(detected_objects, ensure_ascii=False)
                event_accur_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                self.insert_event_history(camera_name, filename, event_data_json, event_accur_time)
            
            # Debug 모드일 때 감지된 객체가 있는 프레임 표시
            # if self.debug_mode:
            #     cv2.imshow('Object Detection', annotated)
            #     cv2.waitKey(1)

    def run_yolo_and_filter(self, yolo_model, frame, detection_labels, confidence_threshold):
        results = yolo_model(frame)
        filtered_boxes = []
        detected_objects = []
        annotated = frame.copy()
        for box, conf, cls in zip(results[0].boxes.xyxy.cpu().numpy(), results[0].boxes.conf.cpu().numpy(), results[0].boxes.cls.cpu().numpy()):
            label = results[0].names[int(cls)]
            print(f"label: {label}, conf: {conf:.2f}, cls: {cls}")
            if detection_labels and label not in detection_labels:
                logger.info(f"[검출제외] label={label}, conf={conf:.2f} (detectionType={detection_labels}) 대상 아님")
                continue
            if conf < confidence_threshold:
                continue
            filtered_boxes.append((box, conf, cls))
            x1, y1, x2, y2 = map(int, box)
            color = (0, 255, 0)
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
            cv2.putText(annotated, f"{label} {conf:.2f}", (x1, y1 - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
            detected_objects.append({
                'label': label,
                'bbox': [x1, y1, x2, y2],
                'confidence': float(conf)
            })
        return results, filtered_boxes, annotated, detected_objects

    def process_settings(self, object_setting):
        """
        설정값을 처리하여 필요한 파라미터들을 반환합니다.
        
        Args:
            object_setting (dict): 설정 데이터
            
        Returns:
            tuple: (enable_tracking, detection_labels, confidence_threshold, interval)
        """
        if not object_setting:
            return True, None, 0.5, 1.0
            
        enable_tracking = object_setting.get('enableTracking', True)
        detection_type = object_setting.get('detectionType', '사람')
        accuracy = object_setting.get('accuracy', '보통')
        tracking_duration = object_setting.get('trackingDuration', 1)
        
        # 라벨 필터
        if detection_type == '전체':
            detection_labels = None
        elif detection_type == '사람':
            detection_labels = ['person']
        elif detection_type == '차량':
            detection_labels = ['car', 'truck']
        elif detection_type == '동물':
            detection_labels = ['animal']
        else:
            detection_labels = [detection_type]
            
        # 정확도 임계값
        if accuracy == '높음':
            confidence_threshold = 0.7
        elif accuracy == '보통':
            confidence_threshold = 0.5
        else:
            confidence_threshold = 0.3
            
        # interval
        try:
            interval = float(tracking_duration)
        except:
            interval = 1.0
            
        logger.info(f"[설정] enableTracking={enable_tracking}, detectionType={detection_type}, accuracy={accuracy}, interval={interval}")
        return enable_tracking, detection_labels, confidence_threshold, interval

    def object_detection_thread(self, yolo_model, camera_name):
        """객체 감지 스레드"""
        while not self.stop_event.is_set():
            try:
                current_time = time.time()
                time_since_last = current_time - self.last_object_detect_time
                
                if time_since_last >= self.frame_interval:
                    # 설정값 읽기
                    with self.setting_lock:
                        object_setting = self.object_setting
                    
                    enable_tracking, detection_labels, confidence_threshold, _ = self.process_settings(object_setting)
                    
                    if enable_tracking and not self.frame_queue.empty():
                        frame = self.frame_queue.get()
                        results, filtered_boxes, annotated, detected_objects = self.run_yolo_and_filter(
                            yolo_model, frame, detection_labels, confidence_threshold
                        )
                        
                        if filtered_boxes:
                            today = datetime.now().strftime('%Y-%m-%d')
                            output_dir = os.path.join(DETECTED_MOVE_DIR, today)
                            os.makedirs(output_dir, exist_ok=True)
                            filename = os.path.join(output_dir, f'{camera_name}_detection_{int(time.time())}.jpg')
                            cv2.imwrite(filename, annotated)
                            
                            # DB 기록
                            event_data_json = json.dumps(detected_objects, ensure_ascii=False)
                            event_accur_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                            self.insert_event_history(camera_name, filename, event_data_json, event_accur_time)

                        
                        self.last_object_detect_time = current_time
                        logger.debug(f"Object detection processed at {current_time:.2f}, interval: {time_since_last:.2f}s")
                
                # 남은 시간만큼 대기
                sleep_time = max(0, self.frame_interval - (time.time() - current_time))
                if sleep_time > 0:
                    time.sleep(sleep_time)
                
            except Exception as e:
                logger.error(f"Object detection error: {str(e)}")
                time.sleep(1)

    def motion_detection_thread(self, camera_name, base_dir):
        """움직임 감지 스레드"""
        prev_frame = None
        while not self.stop_event.is_set():
            try:
                current_time = time.time()
                time_since_last = current_time - self.last_motion_detect_time
                
                if time_since_last >= self.frame_interval:
                    logger.info(f"self.frame_queue count: {self.frame_queue.qsize()}")
                    if not self.frame_queue.empty():
                        curr_frame = self.frame_queue.get()
                        logger.info("Got frame from queue")
                        self.process_detection(curr_frame)
                        self.last_motion_detect_time = current_time
                        logger.debug(f"Motion detection processed at {current_time:.2f}, interval: {time_since_last:.2f}s")
                
                # 남은 시간만큼 대기
                sleep_time = max(0, self.frame_interval - (time.time() - current_time))
                if sleep_time > 0:
                    time.sleep(sleep_time)
                
            except Exception as e:
                logger.error(f"Motion detection error: {str(e)}")
                time.sleep(1)

    def frame_capture_thread(self, rtsp_url):
        """프레임 캡처 스레드"""
        logger.info(f"Frame capture thread started : rtsp_url={rtsp_url}")
        
        while not self.stop_event.is_set():
            try:
                probe = ffmpeg.probe(rtsp_url, rtsp_transport='tcp')
                video_stream = next(s for s in probe['streams'] if s['codec_type'] == 'video')
                w = int(video_stream['width'])
                h = int(video_stream['height'])
                pix_fmt = video_stream['pix_fmt']
                fps = float(eval(video_stream['r_frame_rate']))
                
                process = (
                    ffmpeg
                    .input(rtsp_url, rtsp_transport='tcp')
                    .output('pipe:', format='rawvideo', pix_fmt=pix_fmt, s=f'{w}x{h}', r=fps)
                    .run_async(pipe_stdout=True, pipe_stderr=True)
                )
                
                threading.Thread(target=self.drain_stderr, args=(process.stderr,), daemon=True).start()
                frame_size = w * h * 3 // 2  # YUV420p
                
                last_capture_time = 0
                while not self.stop_event.is_set():
                    try:
                        now = time.time()
                        if now - last_capture_time < 1.0:
                            time.sleep(0.01)
                            continue
                        last_capture_time = now

                        in_bytes = process.stdout.read(frame_size)
                        if not in_bytes or len(in_bytes) < frame_size:
                            break

                        yuv = np.frombuffer(in_bytes, np.uint8).reshape((h * 3 // 2, w))
                        bgr = cv2.cvtColor(yuv, cv2.COLOR_YUV2BGR_I420)

                        if self.frame_queue.full():
                            try:
                                self.frame_queue.get_nowait()
                            except queue.Empty:
                                pass
                        self.frame_queue.put(bgr)

                    except Exception as e:
                        logger.error(f"Frame capture error: {str(e)}")
                        break
                        
                process.stdout.close()
                process.wait()
                
            except Exception as e:
                logger.error(f"Stream connection error: {str(e)}")
                time.sleep(5)  # 재연결 전 대기

            # 스레드 종료 시 창 닫기
            if self.debug_mode:
                cv2.destroyWindow('Frame Capture (Debug)')

    def get_all_cameras(self):
        try:
            cursor = self.get_db_cursor()
            if cursor:
                cursor.execute('SELECT * FROM tb_cameras')
                self.cameras = cursor.fetchall()
                cursor.close()
                return True
            else:
                logger.error("DB cursor is None. Insert failed.")
                return False
        except Exception as e:
            logger.error(f"DB Search Error: {str(e)}")
            return False
                
    def run(self):
        try:
            self.get_all_cameras()
            print("CAMERA_NAME : ", CAMERA_NAME)
            rtsp_url = None
            for cam in self.cameras:
                if cam.get('name') == CAMERA_NAME:
                    if 'videoConfig' in cam and 'source' in cam['videoConfig']:
                        src = json.loads(cam['videoConfig'])['source']
                        if 'rtsp://' in src:
                            rtsp_url = src[src.find('rtsp://'):].strip('"')
                            break
                        
            if not rtsp_url:
                logger.error(f"Camera with name '{CAMERA_NAME}' not found in self.cameras.")
                return

            # 설정 갱신 스레드 시작
            threading.Thread(target=self.setting_updater, daemon=True).start()
            
            # YOLO 모델 초기화
            self.yolo_model = YOLO('yolov8n.pt')

           
            # 스레드 시작
            threads = [
                threading.Thread(target=self.frame_capture_thread, args=(rtsp_url,), daemon=True),
                threading.Thread(target=self.motion_detection_thread, args=(CAMERA_NAME, DETECTED_MOVE_DIR), daemon=True)
            ]
            
            for thread in threads:
                thread.start()
            
            # 메인 스레드에서 키보드 입력 대기
            while not self.stop_event.is_set():
                if self.debug_mode and cv2.waitKey(1) & 0xFF == ord('q'):
                    self.stop_event.set()
                    break
                time.sleep(0.1)
            
            # 스레드 종료 대기
            for thread in threads:
                thread.join(timeout=1.0)
            
            cv2.destroyAllWindows()
            
        except Exception as e:
            logger.error(f"Error in main: {str(e)}")
            logger.error(traceback.format_exc())
        finally:
            self.stop_event.set()
            cv2.destroyAllWindows()

if __name__ == "__main__":
    try:
        # 명령행 인자 파싱
        parser = argparse.ArgumentParser(description='Event Detection with RTSP Stream')
        parser.add_argument('--debug', action='store_true', help='Enable debug mode with UI')
        args = parser.parse_args()
        
        detecter = EventDetecter(debug_mode=args.debug)
        detecter.run()

    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
        logger.error(traceback.format_exc())

