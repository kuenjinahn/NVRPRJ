'use-strict';

import * as StatisticController from './statistic.controller.js';
import * as PaginationMiddleware from '../../middlewares/pagination.middleware.js';
import * as PermissionMiddleware from '../../middlewares/auth.permission.middleware.js';
import * as ValidationMiddleware from '../../middlewares/auth.validation.middleware.js';
import express from 'express';

/**
 * @swagger
 * tags:
 *  name: Statistics
 */

export const routesConfig = (app) => {
  // 디버깅 로그 추가
  console.log('Configuring statistic routes...');

  /**
   * @swagger
   * /api/statistic/realtime-temp:
   *   get:
   *     tags: [Statistics]
   *     security:
   *       - bearerAuth: []
   *     summary: Get real-time temperature data
   *     parameters:
   *       - in: query
   *         name: cameraId
   *         schema:
   *           type: integer
   *         description: Optional camera ID for filtering data
   *     responses:
   *       200:
   *         description: Successful
   *       401:
   *         description: Unauthorized
   *       500:
   *         description: Internal server error
   */
  app.get('/api/statistic/realtime-temp', [
    ValidationMiddleware.validJWTNeeded,
    PermissionMiddleware.minimumPermissionLevelRequired('statistic:access'),
    StatisticController.getRealtimeTemp,
  ]);

  // getDailyRoiAvgTemp 함수가 controller에 없으므로 주석 처리
  // app.get('/api/statistic/daily-roi-avg-temp', [
  //   ValidationMiddleware.validJWTNeeded,
  //   PermissionMiddleware.minimumPermissionLevelRequired('statistic:access'),
  //   StatisticController.getDailyRoiAvgTemp,
  // ]);

  app.get('/api/statistic/daily-roi-min-change', [
    ValidationMiddleware.validJWTNeeded,
    PermissionMiddleware.minimumPermissionLevelRequired('statistic:access'),
    StatisticController.getDailyRoiMinChange,
  ]);

  app.get('/api/statistic/roi-data-list', [
    ValidationMiddleware.validJWTNeeded,
    PermissionMiddleware.minimumPermissionLevelRequired('statistic:access'),
    StatisticController.getRoiDataList,
  ]);

  /**
   * @swagger
   * /api/statistic/roi-time-series:
   *   get:
   *     tags: [Statistics]
   *     security:
   *       - bearerAuth: []
   *     summary: Get ROI time series data for a specific ROI number and event date
   *     parameters:
   *       - in: query
   *         name: roiNumber
   *         required: true
   *         schema:
   *           type: integer
   *         description: ROI number (1-10)
   *       - in: query
   *         name: eventDate
   *         required: true
   *         schema:
   *           type: string
   *           format: date-time
   *         description: Event date and time (ISO format)
   *     responses:
   *       200:
   *         description: Successful
   *         content:
   *           application/json:
   *             schema:
   *               type: object
   *               properties:
   *                 success:
   *                   type: boolean
   *                 result:
   *                   type: object
   *                   properties:
   *                     roiNumber:
   *                       type: integer
   *                     eventDate:
   *                       type: string
   *                     timeRange:
   *                       type: object
   *                       properties:
   *                         start:
   *                           type: string
   *                         end:
   *                           type: string
   *                     statistics:
   *                       type: object
   *                       properties:
   *                         maxTemp:
   *                           type: string
   *                         minTemp:
   *                           type: string
   *                         avgTemp:
   *                           type: string
   *                         dataCount:
   *                           type: integer
   *                     timeSeriesData:
   *                       type: array
   *                       items:
   *                         type: object
   *                         properties:
   *                           time:
   *                             type: string
   *                           min:
   *                             type: string
   *                           max:
   *                             type: string
   *                           avg:
   *                             type: string
   *                           roiNumber:
   *                             type: integer
   *       400:
   *         description: Bad request - missing parameters or invalid date format
   *       401:
   *         description: Unauthorized
   *       500:
   *         description: Internal server error
   */
  app.get('/api/statistic/roi-time-series', [
    ValidationMiddleware.validJWTNeeded,
    PermissionMiddleware.minimumPermissionLevelRequired('statistic:access'),
    StatisticController.getRoiTimeSeriesData,
  ]);

  app.get('/api/statistic/roi-temperature-time-series', [
    ValidationMiddleware.validJWTNeeded,
    PermissionMiddleware.minimumPermissionLevelRequired('statistic:access'),
    StatisticController.getRoiTemperatureTimeSeries,
  ]);

  const routes = app._router.stack
    .filter(r => r.route)
    .map(r => ({
      path: r.route.path,
      method: Object.keys(r.route.methods)[0].toUpperCase()
    }));
  console.log('Registered statistic routes:', routes);
}; 