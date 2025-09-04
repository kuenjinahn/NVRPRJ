'use strict';

import * as SchedulesController from './schedules.controller.js';
import LoggerService from '../../../services/logger/logger.service.js';
// import ScheduleChecker from '../../../services/schedule/schedule.checker.js';
// import RecordingProcess from '../../../services/recording/recording.process.js';

const { log } = LoggerService;

export const routesConfig = (app) => {
  log.info('Registering schedules routes...', 'Schedules');

  // 녹화 프로세스는 Python으로 이동됨 - Node 서버에서는 제거
  // RecordingProcess.start();
  // ScheduleChecker.startChecking(60); // 1분 간격으로 체크

  // 레코딩 관련 API는 Python으로 이동됨 - 제거
  // app.get('/api/schedules/recording', ...)
  // app.get('/api/schedules/recording-status', ...)

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