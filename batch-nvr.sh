#!/usr/bin/env bash

# 1) conda 셸 hook 불러오기
eval "$(conda shell.bash hook)"

# 2) 환경 활성화
conda activate nvr
# 3) nohup 백그라운드 실행
nohup python /home/user/NVRPRj/bin/videoDataReceiver.py > /home/user/NVRPRj/receive.log 2>&1 &
nohup python /home/user/NVRPRj/bin/videoAlertCheck.py   > /home/user/NVRPRj/alert.log   2>&1 &

