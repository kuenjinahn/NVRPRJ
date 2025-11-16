/* eslint-disable unicorn/explicit-length-check */
'use-strict';

import checkDiskSpace from 'check-disk-space';
import getFolderSize from 'get-folder-size';
import { Server } from 'socket.io';
import jwt from 'jsonwebtoken';
import systeminformation from 'systeminformation';

import LoggerService from '../services/logger/logger.service.js';

import Database from './database.js';

import CameraController from '../controller/camera/camera.controller.js';
import MotionController from '../controller/motion/motion.controller.js';

const { log } = LoggerService;

export default class Socket {
  #streamTimeouts = new Map();

  static #uptime = {
    systemTime: '0m',
    processTime: '0m',
  };

  static #cpuLoadHistory = [];
  static #cpuTempHistory = [];
  static #memoryUsageHistory = [];
  static #diskSpaceHistory = [];

  static diskSpace = {
    free: null,
    total: null,
    used: null,
    usedRecordings: null,
  };

  static io;

  static create = (server) => new Socket(server);

  constructor(server) {
    Socket.io = LoggerService.socket = new Server(server, {
      cors: {
        origin: '*',
      },
    });

    // this 바인딩을 위한 참조 저장
    const self = this;

    // 토큰과 관계없이 모든 연결 허용
    Socket.io.use(async (socket, next) => {
      try {
        // Authorization 헤더에서 토큰 추출 (Bearer 토큰 형식)
        let token = null;
        const authHeader = socket.handshake?.headers?.authorization || socket.handshake?.headers?.Authorization;
        if (authHeader && authHeader.startsWith('Bearer ')) {
          token = authHeader.substring(7);
        } else {
          // query나 auth에서도 토큰 확인
          token = socket.handshake?.auth?.token || socket.handshake?.query?.token;
        }

        // 토큰이 있으면 디코딩만 시도 (검증 없이)
        if (token) {
          try {
            // 검증 없이 디코딩만 수행 (만료된 토큰도 디코딩 가능)
            const decoded = jwt.decode(token);
            socket.encoded_token = token;
            socket.decoded_token = decoded;
          } catch (decodeError) {
            // 디코딩 실패해도 연결 허용
            socket.encoded_token = token;
            socket.decoded_token = null;
          }
        } else {
          socket.encoded_token = null;
          socket.decoded_token = null;
        }

        next();
      } catch (error) {
        // 예상치 못한 오류도 연결 허용
        console.error('[Socket] Unexpected error in middleware:', error);
        socket.encoded_token = null;
        socket.decoded_token = null;
        next();
      }
    });

    Socket.io.on('connection', async (socket) => {
      try {
        // 토큰과 관계없이 모든 연결 허용
        const username = socket.decoded_token?.username || socket.decoded_token?.userId || 'unknown';
        const remoteAddress = socket.conn?.remoteAddress || 'unknown';
        log.debug(`${username} (${remoteAddress}) connected to socket`);

        // 권한 체크 없이 항상 알림 데이터 전송
        // const notifications = await Database.interfaceDB?.chain.get('notifications').cloneDeep().value();
        // const systemNotifications = Database.notificationsDB?.chain.get('notifications').cloneDeep().value();

        // if (notifications && systemNotifications) {
        //   const size = notifications.length + systemNotifications.length;
        //   socket.emit('notification_size', size);
        // }
        socket.on('join_stream', (data) => {
          try {
            if (data?.feed) {
              socket.join(`stream/${data.feed}`);
              const username = socket.decoded_token?.username || 'unknown';
              const remoteAddress = socket.conn?.remoteAddress || 'unknown';
              log.debug(`${username} (${remoteAddress}) joined stream: ${data.feed}`);
            }
          } catch (error) {
            log.error(`Error in join_stream handler: ${error.message}`, 'Socket');
          }
        });
        socket.on('leave_stream', (data) => {
          try {
            if (data?.feed) {
              socket.leave(`stream/${data.feed}`);
              const username = socket.decoded_token?.username || 'unknown';
              const remoteAddress = socket.conn?.remoteAddress || 'unknown';
              log.debug(`${username} (${remoteAddress}) left stream: ${data.feed}`);
            }
          } catch (error) {
            log.error(`Error in leave_stream handler: ${error.message}`, 'Socket');
          }
        });
        socket.on('rejoin_stream', (data) => {
          try {
            if (data?.feed) {
              socket.leave(`stream/${data.feed}`);
              socket.join(`stream/${data.feed}`);

              const username = socket.decoded_token?.username || 'unknown';
              const remoteAddress = socket.conn?.remoteAddress || 'unknown';
              log.debug(`${username} (${remoteAddress}) re-joined stream: ${data.feed}`);
            }
          } catch (error) {
            log.error(`Error in rejoin_stream handler: ${error.message}`, 'Socket');
          }
        });
        socket.on('refresh_stream', (data) => {
          try {
            if (data?.feed) {
              const username = socket.decoded_token?.username || 'unknown';
              const remoteAddress = socket.conn?.remoteAddress || 'unknown';
              log.debug(`${username} (${remoteAddress}) requested to restart stream: ${data.feed}`);
              self.#handleStream(data.feed, 'restart').catch((error) => {
                log.error(`Error restarting stream for ${data.feed}: ${error.message}`, 'Socket');
              });
            }
          } catch (error) {
            log.error(`Error in refresh_stream handler: ${error.message}`, 'Socket');
          }
        });

        socket.on('getUptime', () => {
          try {
            Socket.io.emit('uptime', Socket.#uptime);
          } catch (error) {
            log.error(`Error in getUptime handler: ${error.message}`, 'Socket');
          }
        });

        socket.on('getCpuLoad', () => {
          try {
            Socket.io.emit('cpuLoad', Socket.#cpuLoadHistory);
          } catch (error) {
            log.error(`Error in getCpuLoad handler: ${error.message}`, 'Socket');
          }
        });

        socket.on('getCpuTemp', () => {
          try {
            Socket.io.emit('cpuTemp', Socket.#cpuTempHistory);
          } catch (error) {
            log.error(`Error in getCpuTemp handler: ${error.message}`, 'Socket');
          }
        });

        socket.on('getMemory', () => {
          try {
            Socket.io.emit('memory', Socket.#memoryUsageHistory);
          } catch (error) {
            log.error(`Error in getMemory handler: ${error.message}`, 'Socket');
          }
        });

        socket.on('getDiskSpace', () => {
          try {
            Socket.io.emit('diskSpace', Socket.#diskSpaceHistory);
          } catch (error) {
            log.error(`Error in getDiskSpace handler: ${error.message}`, 'Socket');
          }
        });

        socket.on('getMotionServerStatus', () => {
          try {
            const ftpStatus = MotionController.ftpServer?.server?.listening;
            const httpStatus = MotionController.httpServer?.listening;
            const mqttStatus = MotionController.mqttClient?.connected;
            const smtpStatus = MotionController.smtpServer?.server?.listening;

            Socket.io.emit('motionServerStatus', {
              ftpStatus: ftpStatus ? 'online' : 'offline',
              httpStatus: httpStatus ? 'online' : 'offline',
              mqttStatus: mqttStatus ? 'online' : 'offline',
              smtpStatus: smtpStatus ? 'online' : 'offline',
            });

            Socket.io.emit('ftpStatus', {
              status: ftpStatus ? 'online' : 'offline',
            });

            Socket.io.emit('httpStatus', {
              status: httpStatus ? 'online' : 'offline',
            });

            Socket.io.emit('mqttStatus', {
              status: mqttStatus ? 'online' : 'offline',
            });

            Socket.io.emit('smtpStatus', {
              status: smtpStatus ? 'online' : 'offline',
            });
          } catch (error) {
            log.error(`Error in getMotionServerStatus handler: ${error.message}`, 'Socket');
          }
        });

        socket.on('getCameraPrebufferSatus', (cameras) => {
          try {
            if (!Array.isArray(cameras)) {
              cameras = [cameras];
            }

            for (const cameraName of cameras) {
              const controller = CameraController.cameras.get(cameraName);
              const state = controller?.prebuffer?.prebufferSession?.isActive();

              socket.emit('prebufferStatus', {
                camera: cameraName,
                status: state ? 'active' : 'inactive',
              });
            }
          } catch (error) {
            log.error(`Error in getCameraPrebufferSatus handler: ${error.message}`, 'Socket');
          }
        });

        socket.on('getCameraVideoanalysisSatus', (cameras) => {
          try {
            if (!Array.isArray(cameras)) {
              cameras = [cameras];
            }

            for (const cameraName of cameras) {
              const controller = CameraController.cameras.get(cameraName);
              const state = controller?.videoanalysis?.videoanalysisSession?.isActive();

              socket.emit('videoanalysisStatus', {
                camera: cameraName,
                status: state ? 'active' : 'inactive',
              });
            }
          } catch (error) {
            log.error(`Error in getCameraVideoanalysisSatus handler: ${error.message}`, 'Socket');
          }
        });

        socket.on('disconnect', () => {
          try {
            const username = socket.decoded_token?.username || socket.decoded_token?.userId || 'unknown';
            const remoteAddress = socket.conn?.remoteAddress || 'unknown';
            log.debug(`${username} (${remoteAddress}) disconnected from socket`);
          } catch (error) {
            log.error(`Error in disconnect handler: ${error.message}`, 'Socket');
          }
        });
      } catch (error) {
        log.error(`Error in connection handler: ${error.message}`, 'Socket');
      }
    });

    Socket.io.of('/').adapter.on('join-room', (room) => {
      try {
        if (room?.startsWith('stream/')) {
          const cameraName = room.split('/')[1];
          if (!cameraName) return;

          const clients = Socket.io.sockets.adapter.rooms.get(`stream/${cameraName}`)?.size || 0;

          log.debug(`Active sockets in room (stream/${cameraName}): ${clients}`);

          let streamTimeout = self.#streamTimeouts.get(cameraName);

          if (streamTimeout) {
            clearTimeout(streamTimeout);
            self.#streamTimeouts.delete(cameraName);
          } else if (clients < 2) {
            self.#handleStream(cameraName, 'start').catch((error) => {
              log.error(`Error starting stream for ${cameraName}: ${error.message}`, 'Socket');
            });
          }
        }
      } catch (error) {
        log.error(`Error in join-room handler: ${error.message}`, 'Socket');
      }
    });

    Socket.io.of('/').adapter.on('leave-room', (room) => {
      try {
        if (room?.startsWith('stream/')) {
          const cameraName = room.split('/')[1];
          if (!cameraName) return;

          const clients = Socket.io.sockets.adapter.rooms.get(`stream/${cameraName}`)?.size || 0;

          log.debug(`Active sockets in room (stream/${cameraName}): ${clients}`);

          if (!clients) {
            let streamTimeout = self.#streamTimeouts.get(cameraName);

            if (!streamTimeout) {
              log.debug('If no clients connects to the Websocket, the stream will be closed in 15s');

              streamTimeout = setTimeout(() => {
                try {
                  self.#handleStream(cameraName, 'stop').catch((error) => {
                    log.error(`Error stopping stream for ${cameraName}: ${error.message}`, 'Socket');
                  });
                  self.#streamTimeouts.delete(cameraName);
                } catch (error) {
                  log.error(`Error in stream timeout handler for ${cameraName}: ${error.message}`, 'Socket');
                  self.#streamTimeouts.delete(cameraName);
                }
              }, 15000);

              self.#streamTimeouts.set(cameraName, streamTimeout);
            }
          }
        }
      } catch (error) {
        log.error(`Error in leave-room handler: ${error.message}`, 'Socket');
      }
    });

    Socket.io.of('/').adapter.on('delete-room', (room) => {
      try {
        if (room?.startsWith('stream/')) {
          const cameraName = room.split('/')[1];
          if (!cameraName) return;

          let streamTimeout = self.#streamTimeouts.get(cameraName);

          if (!streamTimeout) {
            log.debug('If no clients connects to the Websocket, the stream will be closed in 15s');

            streamTimeout = setTimeout(() => {
              try {
                self.#handleStream(cameraName, 'stop').catch((error) => {
                  log.error(`Error stopping stream for ${cameraName}: ${error.message}`, 'Socket');
                });
                self.#streamTimeouts.delete(cameraName);
              } catch (error) {
                log.error(`Error in stream timeout handler for ${cameraName}: ${error.message}`, 'Socket');
                self.#streamTimeouts.delete(cameraName);
              }
            }, 15000);

            self.#streamTimeouts.set(cameraName, streamTimeout);
          }
        }
      } catch (error) {
        log.error(`Error in delete-room handler: ${error.message}`, 'Socket');
      }
    });

    return Socket.io;
  }

  async #handleStream(cameraName, target) {
    try {
      if (!cameraName) {
        log.error('handleStream called with invalid cameraName', 'Socket');
        return;
      }

      const controller = CameraController.cameras.get(cameraName);

      if (controller?.stream) {
        switch (target) {
          case 'start':
            await controller.stream.start();
            break;
          case 'stop':
            await controller.stream.stop();
            break;
          case 'restart':
            await controller.stream.restart();
            break;
          default:
            log.error(`Invalid stream target: ${target}`, 'Socket');
        }
      } else {
        log.debug(`Camera controller not found for: ${cameraName}`, 'Socket');
      }
    } catch (error) {
      log.error(`Error in handleStream for ${cameraName} (${target}): ${error.message}`, 'Socket');
      throw error;
    }
  }

  static async watchSystem() {
    await Socket.#handleUptime();
    await Socket.#handleCpuLoad();
    await Socket.#handleCpuTemperature();
    await Socket.#handleMemoryUsage();
    await Socket.handleDiskUsage();

    setTimeout(() => {
      Socket.watchSystem();
    }, 30000);
  }

  static async #handleUptime() {
    try {
      const humaniseDuration = (seconds) => {
        if (seconds < 50) {
          return '0m';
        }
        if (seconds < 3600) {
          return Math.round(seconds / 60) + 'm';
        }
        if (seconds < 86400) {
          return Math.round(seconds / 60 / 60) + 'h';
        }
        return Math.floor(seconds / 60 / 60 / 24) + 'd';
      };

      const systemTime = await systeminformation.time();
      const processUptime = process.uptime();

      Socket.#uptime = {
        systemTime: humaniseDuration(systemTime ? systemTime.uptime : 0),
        processTime: humaniseDuration(processUptime),
      };
    } catch (error) {
      log.error(error, 'Socket');
    }

    Socket.io.emit('uptime', Socket.#uptime);
  }

  static async #handleCpuLoad() {
    try {
      const cpuLoad = await systeminformation.currentLoad();
      let processLoad = await systeminformation.processLoad(process.title);

      if (processLoad?.length && !processLoad[0].pid && !processLoad[0].cpu && !processLoad[0].mem) {
        // can not find through process.title, try again with process.pid
        const processes = await systeminformation.processes();
        const processByPID = processes.list.find((p) => p.pid === process.pid);

        if (processByPID) {
          processLoad = [
            {
              cpu: processByPID.cpu,
            },
          ];
        }
      }

      Socket.#cpuLoadHistory = Socket.#cpuLoadHistory.slice(-60);
      Socket.#cpuLoadHistory.push({
        time: new Date(),
        value: cpuLoad ? cpuLoad.currentLoad : 0,
        value2: processLoad?.length ? processLoad[0].cpu || 0 : 0,
      });
    } catch (error) {
      log.error(error, 'Socket');
    }

    Socket.io.emit('cpuLoad', Socket.#cpuLoadHistory);
  }

  static async #handleCpuTemperature() {
    try {
      const cpuTemperatureData = await systeminformation.cpuTemperature();

      Socket.#cpuTempHistory = Socket.#cpuTempHistory.slice(-60);
      Socket.#cpuTempHistory.push({
        time: new Date(),
        value: cpuTemperatureData ? cpuTemperatureData.main : 0,
      });
    } catch (error) {
      log.error(error, 'Socket');
    }

    Socket.io.emit('cpuTemp', Socket.#cpuTempHistory);
  }

  static async #handleMemoryUsage() {
    try {
      const mem = await systeminformation.mem();
      const memoryFreePercent = mem ? ((mem.total - mem.available) / mem.total) * 100 : 50;
      let processLoad = await systeminformation.processLoad(process.title);

      if (!processLoad.pid && !processLoad.cpu && !processLoad.mem) {
        // can not find through process.title, try again with process.pid
        const processes = await systeminformation.processes();
        const processByPID = processes.list.find((p) => p.pid === process.pid);

        if (processByPID) {
          processLoad = [
            {
              mem: processByPID.mem,
            },
          ];
        }
      }

      Socket.#memoryUsageHistory = Socket.#memoryUsageHistory.slice(-60);
      Socket.#memoryUsageHistory.push({
        time: new Date(),
        value: memoryFreePercent,
        value2: processLoad?.length ? processLoad[0].mem || 0 : 0,
        available: mem ? (mem.available / 1024 / 1024 / 1024).toFixed(2) : 4,
        total: mem ? (mem.total / 1024 / 1024 / 1024).toFixed(2) : 8,
      });
    } catch (error) {
      log.error(error, 'Socket');
    }

    Socket.io.emit('memory', Socket.#memoryUsageHistory);
  }

  static async handleDiskUsage() {
    try {
      const settingsDatabase = await Database.interfaceDB.chain.get('settings').cloneDeep().value();
      const recordingsPath = settingsDatabase?.recordings.path;

      if (!recordingsPath) {
        return;
      }

      const diskSpace = await checkDiskSpace(recordingsPath);
      const recordingsSpace = await getFolderSize.loose(recordingsPath);

      Socket.diskSpace = {
        available: diskSpace.free / 1e9,
        total: diskSpace.size / 1e9,
        used: (diskSpace.size - diskSpace.free) / 1e9,
        usedRecordings: recordingsSpace / 1e9,
        recordingsPath: recordingsPath,
      };

      const usedPercent = Socket.diskSpace.used / Socket.diskSpace.total;
      const usedRecordingsPercent = Socket.diskSpace.usedRecordings / Socket.diskSpace.total;

      Socket.#diskSpaceHistory = Socket.#diskSpaceHistory.slice(-60);
      Socket.#diskSpaceHistory.push({
        time: new Date(),
        value: usedPercent * 100,
        value2: usedRecordingsPercent * 100,
        available: Socket.diskSpace.available.toFixed(2),
        total: Socket.diskSpace.total.toFixed(2),
      });
    } catch (error) {
      log.error(error, 'Socket');
    }

    Socket.io.emit('diskSpace', Socket.#diskSpaceHistory);
  }
}
