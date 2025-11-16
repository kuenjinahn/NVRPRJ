#!/usr/bin/env bash

echo "=== batch-nvr.sh started at $(date) ===" >> /home/user/NVRPRj/batch-nvr.log 2>&1

PYTHON=/home/user/miniconda3/envs/nvr/bin/python   # which python 에서 나온 값으로 변경

nohup $PYTHON /home/user/NVRPRj/bin/videoDataReceiver.py    >> /home/user/NVRPRj/receive.log            2>&1 &
nohup $PYTHON /home/user/NVRPRj/bin/videoAlertCheck.py      >> /home/user/NVRPRj/alert.log              2>&1 &
nohup $PYTHON /home/user/NVRPRj/bin/panorama_generator.py   >> /home/user/NVRPRj/panorama_generator.log 2>&1 &
nohup $PYTHON /home/user/NVRPRj/bin/videoRecoder.py         >> /home/user/NVRPRj/videoRecoder.log       2>&1 &
