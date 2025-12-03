#!/bin/bash

# 스크립트 실행 위치 확인
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$SCRIPT_DIR/logs"
LOG_ROTATOR="$SCRIPT_DIR/bin/log_rotator.py"

# logs 폴더 생성
mkdir -p "$LOG_DIR"

sudo pkill -9 node
sudo pkill -9 camera.ui
sudo pkill -9 npm
sudo pkill -9 ffmpeg

# Python 로그 로테이터를 사용하여 로그 처리 (1MB 단위, 5개까지 로테이션)
nohup sudo npm run watch:server 2>&1 | python3 "$LOG_ROTATOR" "$LOG_DIR/server.log" &
(cd /home/user/NVRPRj/ui && nohup sudo npm start 2>&1 | python3 "$LOG_ROTATOR" "$LOG_DIR/web.log") &


