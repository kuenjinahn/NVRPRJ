'use-strict';

import * as AlertsController from './alerts.controller.js';

import * as PaginationMiddleware from '../../middlewares/pagination.middleware.js';
import * as PermissionMiddleware from '../../middlewares/auth.permission.middleware.js';
import * as ValidationMiddleware from '../../middlewares/auth.validation.middleware.js';

/**
 * @swagger
 * tags:
 *  name: Alerts
 */

export const routesConfig = (app) => {
  // 디버깅 로그 추가
  console.log('Configuring alert routes...');

  // 먼저 settings 관련 라우트를 등록 (더 명확한 경로명 사용)
  console.log('Registering alert settings routes');

  /**
   * @swagger
   * /api/alerts/settings:
   *   get:
   *     tags: [Alerts]
   *     security:
   *       - bearerAuth: []
   *     summary: Get alert settings
   *     parameters:
   *       - in: query
   *         name: userId
   *         schema:
   *           type: integer
   *         description: Optional user ID for retrieving settings
   *     responses:
   *       200:
   *         description: Successful
   *       401:
   *         description: Unauthorized
   *       500:
   *         description: Internal server error
   */
  app.get('/api/alerts/settings', [
    ValidationMiddleware.validJWTNeeded,
    PermissionMiddleware.minimumPermissionLevelRequired('alerts:access'),
    AlertsController.getAlertSettings,
  ]);

  /**
   * @swagger
   * /api/alerts/settings:
   *   post:
   *     tags: [Alerts]
   *     security:
   *       - bearerAuth: []
   *     summary: Save or update alert settings
   *     requestBody:
   *       required: true
   *       content:
   *         application/json:
   *          schema:
   *            type: object
   *            properties:
   *              alert_setting_json:
   *                type: string
   *                description: JSON string containing alert settings
   *              fk_user_id:
   *                type: integer
   *                description: User ID to associate with these settings
   *     responses:
   *       200:
   *         description: Successful
   *       400:
   *         description: Bad request
   *       401:
   *         description: Unauthorized
   *       500:
   *         description: Internal server error
   */
  app.post('/api/alerts/settings', [
    ValidationMiddleware.validJWTNeeded,
    PermissionMiddleware.minimumPermissionLevelRequired('alerts:update'),
    AlertsController.saveAlertSettings,
  ]);

  /**
   * @swagger
   * /api/alerts/settings/{userId}:
   *   get:
   *     tags: [Alerts]
   *     security:
   *       - bearerAuth: []
   *     summary: Get alert settings for a specific user
   *     parameters:
   *       - in: path
   *         name: userId
   *         schema:
   *           type: integer
   *         required: true
   *         description: ID of the user
   *     responses:
   *       200:
   *         description: Successful
   *       401:
   *         description: Unauthorized
   *       500:
   *         description: Internal server error
   */
  app.get('/api/alerts/settings/:userId', [
    ValidationMiddleware.validJWTNeeded,
    PermissionMiddleware.minimumPermissionLevelRequired('alerts:access'),
    AlertsController.getAlertSettings,
  ]);

  /**
   * @swagger
   * /api/alerts/settings/{userId}:
   *   post:
   *     tags: [Alerts]
   *     security:
   *       - bearerAuth: []
   *     summary: Save or update alert settings for a specific user
   *     parameters:
   *       - in: path
   *         name: userId
   *         schema:
   *           type: integer
   *         required: true
   *         description: ID of the user
   *     requestBody:
   *       required: true
   *       content:
   *         application/json:
   *          schema:
   *            type: object
   *            properties:
   *              alert_setting_json:
   *                type: string
   *                description: JSON string containing alert settings
   *     responses:
   *       200:
   *         description: Successful
   *       400:
   *         description: Bad request
   *       401:
   *         description: Unauthorized
   *       500:
   *         description: Internal server error
   */
  app.post('/api/alerts/settings/:userId', [
    ValidationMiddleware.validJWTNeeded,
    PermissionMiddleware.minimumPermissionLevelRequired('alerts:update'),
    AlertsController.saveAlertSettings,
  ]);

  // 테스트용 라우트 추가 (인증 없이 접근 가능)
  app.get('/api/alerts/settings-test', (req, res) => {
    res.json({ message: 'Settings test route works!' });
  });

  console.log('Registering other alert routes');

  /**
   * @swagger
   * /api/alerts:
   *   get:
   *     tags: [Alerts]
   *     security:
   *       - bearerAuth: []
   *     summary: Get all alerts
   *     parameters:
   *       - in: query
   *         name: start
   *         schema:
   *           type: number
   *         description: Start index
   *       - in: query
   *         name: page
   *         schema:
   *           type: number
   *         description: Page
   *       - in: query
   *         name: pageSize
   *         schema:
   *           type: number
   *         description: Page size
   *     responses:
   *       200:
   *         description: Successful
   *       401:
   *         description: Unauthorized
   *       500:
   *         description: Internal server error
   */
  app.get('/api/alerts', [
    ValidationMiddleware.validJWTNeeded,
    PermissionMiddleware.minimumPermissionLevelRequired('alerts:access'),
    AlertsController.list,
    PaginationMiddleware.pages,
  ]);

  /**
   * @swagger
   * /api/alerts:
   *   post:
   *     tags: [Alerts]
   *     security:
   *       - bearerAuth: []
   *     summary: Create new alert
   *     requestBody:
   *       required: true
   *       content:
   *         application/json:
   *          schema:
   *            type: object
   *            properties:
   *              fk_camera_id:
   *                type: integer
   *              alert_type:
   *                type: string
   *              alert_level:
   *                type: string
   *              alert_status:
   *                type: string
   *              alert_description:
   *                type: string
   *     responses:
   *       201:
   *         description: Successful
   *       400:
   *         description: Bad request
   *       401:
   *         description: Unauthorized
   *       500:
   *         description: Internal server error
   */
  app.post('/api/alerts', [
    ValidationMiddleware.validJWTNeeded,
    PermissionMiddleware.minimumPermissionLevelRequired('alerts:create'),
    AlertsController.insert,
  ]);

  /**
   * @swagger
   * /api/alerts/camera/{cameraId}:
   *   get:
   *     tags: [Alerts]
   *     security:
   *       - bearerAuth: []
   *     summary: Get alerts by camera ID
   *     parameters:
   *       - in: path
   *         name: cameraId
   *         schema:
   *           type: integer
   *         required: true
   *         description: ID of the camera
   *     responses:
   *       200:
   *         description: Successful
   *       401:
   *         description: Unauthorized
   *       500:
   *         description: Internal server error
   */
  app.get('/api/alerts/camera/:cameraId', [
    ValidationMiddleware.validJWTNeeded,
    PermissionMiddleware.minimumPermissionLevelRequired('alerts:access'),
    AlertsController.getByCamera,
  ]);

  /**
   * @swagger
   * /api/alerts/status/{status}:
   *   get:
   *     tags: [Alerts]
   *     security:
   *       - bearerAuth: []
   *     summary: Get alerts by status
   *     parameters:
   *       - in: path
   *         name: status
   *         schema:
   *           type: string
   *         required: true
   *         description: Status of the alert
   *     responses:
   *       200:
   *         description: Successful
   *       401:
   *         description: Unauthorized
   *       500:
   *         description: Internal server error
   */
  app.get('/api/alerts/status/:status', [
    ValidationMiddleware.validJWTNeeded,
    PermissionMiddleware.minimumPermissionLevelRequired('alerts:access'),
    AlertsController.getByStatus,
  ]);

  /**
   * @swagger
   * /api/alerts/recent_alert:
   *   get:
   *     tags: [Alerts]
   *     summary: 최근 7일간의 알림 건수 집계
   *     responses:
   *       200:
   *         description: Successful
   *       500:
   *         description: Internal server error
   */
  app.get('/api/alerts/recent_alert', [
    AlertsController.recentAlertCount
  ]);

  /**
   * @swagger
   * /api/alerts/{id}:
   *   get:
   *     tags: [Alerts]
   *     security:
   *       - bearerAuth: []
   *     summary: Get specific alert by id
   *     parameters:
   *       - in: path
   *         name: id
   *         schema:
   *           type: integer
   *         required: true
   *         description: ID of the alert
   *     responses:
   *       200:
   *         description: Successful
   *       401:
   *         description: Unauthorized
   *       404:
   *         description: Not found
   *       500:
   *         description: Internal server error
   */
  app.get('/api/alerts/:id', [
    ValidationMiddleware.validJWTNeeded,
    PermissionMiddleware.minimumPermissionLevelRequired('alerts:access'),
    AlertsController.getById,
  ]);

  /**
   * @swagger
   * /api/alerts/{id}:
   *   patch:
   *     tags: [Alerts]
   *     security:
   *       - bearerAuth: []
   *     summary: Update alert by id
   *     parameters:
   *       - in: path
   *         name: id
   *         schema:
   *           type: integer
   *         required: true
   *         description: ID of the alert
   *     requestBody:
   *       required: true
   *       content:
   *         application/json:
   *          schema:
   *            type: object
   *            properties:
   *              alert_status:
   *                type: string
   *              fk_process_user_id:
   *                type: integer
   *              alert_process_time:
   *                type: string
   *              alert_description:
   *                type: string
   *     responses:
   *       204:
   *         description: Successful
   *       400:
   *         description: Bad request
   *       401:
   *         description: Unauthorized
   *       404:
   *         description: Not found
   *       500:
   *         description: Internal server error
   */
  app.patch('/api/alerts/:id', [
    ValidationMiddleware.validJWTNeeded,
    PermissionMiddleware.minimumPermissionLevelRequired('alerts:update'),
    AlertsController.patchById,
  ]);

  /**
   * @swagger
   * /api/alerts/{id}:
   *   delete:
   *     tags: [Alerts]
   *     security:
   *       - bearerAuth: []
   *     summary: Delete alert by id
   *     parameters:
   *       - in: path
   *         name: id
   *         schema:
   *           type: integer
   *         required: true
   *         description: ID of the alert
   *     responses:
   *       204:
   *         description: Successful
   *       401:
   *         description: Unauthorized
   *       404:
   *         description: Not found
   *       500:
   *         description: Internal server error
   */
  app.delete('/api/alerts/:id', [
    ValidationMiddleware.validJWTNeeded,
    PermissionMiddleware.minimumPermissionLevelRequired('alerts:delete'),
    AlertsController.removeById,
  ]);

  /**
   * @swagger
   * /api/alerts/weekly-stats:
   *   get:
   *     tags: [Alerts]
   *     summary: Get weekly alert stats (recent 7 days, grouped by date and alert_level)
   *     responses:
   *       200:
   *         description: Successful
   *       500:
   *         description: Internal server error
   */
  app.get('/api/alerts/weekly-stats', [
    ValidationMiddleware.validJWTNeeded,
    PermissionMiddleware.minimumPermissionLevelRequired('alerts:access'),
    AlertsController.getWeeklyStats,
  ]);

  const routes = app._router.stack
    .filter(r => r.route)
    .map(r => ({
      path: r.route.path,
      method: Object.keys(r.route.methods)[0].toUpperCase()
    }));
  console.log('Registered alert routes:', routes);
}; 