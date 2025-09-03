'use strict';

import * as SchedulesController from './schedules.controller.js';
import LoggerService from '../../../services/logger/logger.service.js';
import ScheduleChecker from '../../../services/schedule/schedule.checker.js';
import RecordingProcess from '../../../services/recording/recording.process.js';

const { log } = LoggerService;

export const routesConfig = (app) => {
  log.info('Registering schedules routes...', 'Schedules');

  // 녹화 프로세스 시작
  RecordingProcess.start();

  // 스케줄 체커 시작
  ScheduleChecker.startChecking(60); // 1분 간격으로 체크

  // 현재 녹화 중인 스케줄 조회 엔드포인트 추가
  app.get('/api/schedules/recording', async (req, res) => {
    try {
      const recordingSchedules = await ScheduleChecker.getCurrentlyRecordingSchedules();
      res.json(recordingSchedules);
    } catch (error) {
      log.error('Error getting recording schedules:', error);
      res.status(500).json({ error: error.message });
    }
  });

  // 녹화 상태 조회 API
  app.get('/api/schedules/recording-status', async (req, res) => {
    try {
      const activeRecordings = Array.from(RecordingProcess.activeRecordings.entries()).map(([cameraName, info]) => ({
        cameraName,
        scheduleId: info.scheduleId,
        startTime: info.startTime,
        outputPath: info.outputPath
      }));

      res.json({
        status: 'success',
        activeRecordings
      });
    } catch (error) {
      log.error('Error getting recording status:', error);
      res.status(500).json({ error: error.message });
    }
  });

  // Log when routes are being registered
  log.debug('Adding schedules middleware and routes', 'Schedules');

  // Middleware to log all schedules requests
  app.use('/api/schedules', (req, res, next) => {
    log.info(`Incoming ${req.method} request to ${req.originalUrl}`, 'Schedules', {
      body: req.body,
      query: req.query,
      params: req.params,
      headers: req.headers
    });
    next();
  });

  // Get all schedules with optional filters
  app.get('/api/schedules', [
    (req, res, next) => {
      log.debug('Getting all schedules', 'Schedules', { filters: req.query });
      next();
    },
    SchedulesController.getSchedules
  ]);

  // Create a new schedule
  app.post('/api/schedules', [
    (req, res, next) => {
      log.debug('Creating new schedule', 'Schedules', { data: req.body });
      next();
    },
    SchedulesController.createSchedule
  ]);

  // Update an existing schedule
  app.put('/api/schedules/:id', [
    (req, res, next) => {
      log.debug('Updating schedule', 'Schedules', {
        id: req.params.id,
        data: req.body
      });
      next();
    },
    SchedulesController.updateSchedule
  ]);

  // Delete a schedule
  app.delete('/api/schedules/:id', [
    (req, res, next) => {
      log.debug('Deleting schedule', 'Schedules', { id: req.params.id });
      next();
    },
    SchedulesController.deleteSchedule
  ]);

  // Toggle schedule active status
  app.patch('/api/schedules/:id/toggle', [
    (req, res, next) => {
      log.debug('Toggling schedule status', 'Schedules', { id: req.params.id });
      next();
    },
    SchedulesController.toggleSchedule
  ]);

  // 서버 종료 시 녹화 프로세스 정리
  process.on('SIGTERM', () => {
    RecordingProcess.stop();
  });

  process.on('SIGINT', () => {
    RecordingProcess.stop();
  });

  // Log when routes are registered
  log.info('Schedules routes registered successfully', 'Schedules');
}; 