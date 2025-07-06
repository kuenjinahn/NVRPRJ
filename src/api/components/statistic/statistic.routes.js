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

  app.get('/api/statistic/daily-roi-avg-temp', [
    ValidationMiddleware.validJWTNeeded,
    PermissionMiddleware.minimumPermissionLevelRequired('statistic:access'),
    StatisticController.getDailyRoiAvgTemp,
  ]);

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

  const routes = app._router.stack
    .filter(r => r.route)
    .map(r => ({
      path: r.route.path,
      method: Object.keys(r.route.methods)[0].toUpperCase()
    }));
  console.log('Registered statistic routes:', routes);
}; 