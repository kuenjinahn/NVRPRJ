#!/bin/bash

sudo pkill -9 node
sudo pkill -9 camera.ui
sudo pkill -9 npm
nohup sudo npm run watch:server > server.log 2>&1 &
(cd /home/user/NVRPRj/ui && nohup sudo npm start > web.log 2>&1) &


