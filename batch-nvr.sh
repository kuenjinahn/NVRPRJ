#!/usr/bin/env bash

# 스크립트 실행 위치 확인
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="$SCRIPT_DIR/logs"
LOG_ROTATOR="$SCRIPT_DIR/bin/log_rotator.py"

# logs 폴더 생성
mkdir -p "$LOG_DIR"

# batch-nvr.sh 자체 로그를 logs 폴더에 기록 (로그 로테이터 사용)
echo "=== batch-nvr.sh started at $(date) ===" | python3 "$LOG_ROTATOR" "$LOG_DIR/batch-nvr.log"

PYTHON=/home/user/miniconda3/envs/nvr/bin/python   # which python 에서 나온 값으로 변경

# Python 스크립트들은 자체적으로 logs 폴더에 로그를 기록하므로 리다이렉션 제거
# 필요시 로그 로테이터를 사용하여 추가 로그 기록 가능
nohup $PYTHON "$SCRIPT_DIR/bin/videoDataReceiver.py" > /dev/null 2>&1 &
nohup $PYTHON "$SCRIPT_DIR/bin/videoAlertCheck.py" > /dev/null 2>&1 &
nohup $PYTHON "$SCRIPT_DIR/bin/panorama_generator.py" > /dev/null 2>&1 &
nohup $PYTHON "$SCRIPT_DIR/bin/videoRecoder.py" > /dev/null 2>&1 &
