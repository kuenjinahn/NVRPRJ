#!/bin/bash

# 프로젝트 경로 설정
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
echo "Project directory: $PROJECT_DIR"

# 프로세스 종료
echo "Stopping existing processes..."
sudo pkill -9 node 2>/dev/null || true
sudo pkill -9 camera.ui 2>/dev/null || true
sudo pkill -9 npm 2>/dev/null || true

# 환경 변수 설정
export NODE_ENV=production

# 백엔드 서버 시작
echo "Starting backend server..."
cd "$PROJECT_DIR"
nohup npm run watch:server > server.log 2>&1 &
BACKEND_PID=$!
echo "Backend started with PID: $BACKEND_PID"

# 잠시 대기
sleep 3

# UI 서버 시작
echo "Starting UI server..."
cd "$PROJECT_DIR/ui"
nohup npm start > web.log 2>&1 &
UI_PID=$!
echo "UI started with PID: $UI_PID"

# 프로세스 상태 확인
sleep 2
echo "Checking process status..."
ps aux | grep -E "(node|npm)" | grep -v grep

echo "NVR services started:"
echo "Backend PID: $BACKEND_PID (server.log)"
echo "UI PID: $UI_PID (web.log)"
echo "Logs: $PROJECT_DIR/server.log, $PROJECT_DIR/ui/web.log"


