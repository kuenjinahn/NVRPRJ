import express from 'express';
import { models } from '../../../models/index.js';
import * as ValidationMiddleware from '../../middlewares/auth.validation.middleware.js';
import * as PermissionMiddleware from '../../middlewares/auth.permission.middleware.js';
import LoggerService from '../../../services/logger/logger.service.js';

const { VideoPanoramaData } = models;
const { log } = LoggerService;

const router = express.Router();

/**
 * @swagger
 * tags:
 *  name: Panorama
 */

/**
 * @swagger
 * /api/panorama/data:
 *   get:
 *     tags: [Panorama]
 *     security:
 *       - bearerAuth: []
 *     summary: 파노라마 데이터 조회 (최근 N개)
 *     parameters:
 *       - in: query
 *         name: limit
 *         description: 조회할 데이터 개수
 *         type: number
 *         default: 5
 *     responses:
 *       200:
 *         description: 파노라마 데이터 조회 성공
 *       401:
 *         description: Unauthorized
 *       500:
 *         description: Internal server error
 */
router.get('/data', [
  ValidationMiddleware.validJWTNeeded,
  PermissionMiddleware.minimumPermissionLevelRequired('panorama:access'),
  async (req, res) => {
    try {
      const { limit = 5 } = req.query;
      const limitNum = parseInt(limit, 10);

      if (isNaN(limitNum) || limitNum <= 0) {
        return res.status(400).json({
          success: false,
          message: 'limit은 양수여야 합니다.'
        });
      }

      log.info(`파노라마 데이터 조회 요청: limit=${limitNum}`);

      const panoramaData = await VideoPanoramaData.findAll({
        order: [['create_date', 'DESC']],
        limit: limitNum
      });

      log.info(`파노라마 데이터 조회 완료: ${panoramaData.length}개`);

      res.json({
        success: true,
        message: '파노라마 데이터 조회 성공',
        data: panoramaData
      });

    } catch (error) {
      log.error('파노라마 데이터 조회 오류:', error);
      res.status(500).json({
        success: false,
        message: '파노라마 데이터 조회 실패',
        error: error.message
      });
    }
  }
]);

/**
 * @swagger
 * /api/panorama/data/{id}:
 *   get:
 *     tags: [Panorama]
 *     security:
 *       - bearerAuth: []
 *     summary: 특정 파노라마 데이터 조회
 *     parameters:
 *       - in: path
 *         name: id
 *         description: 파노라마 데이터 ID
 *         required: true
 *         type: number
 *     responses:
 *       200:
 *         description: 파노라마 데이터 조회 성공
 *       404:
 *         description: 파노라마 데이터를 찾을 수 없음
 *       401:
 *         description: Unauthorized
 *       500:
 *         description: Internal server error
 */
router.get('/data/:id', [
  ValidationMiddleware.validJWTNeeded,
  PermissionMiddleware.minimumPermissionLevelRequired('panorama:access'),
  async (req, res) => {
    try {
      const { id } = req.params;
      const panoramaId = parseInt(id, 10);

      if (isNaN(panoramaId)) {
        return res.status(400).json({
          success: false,
          message: '유효하지 않은 ID입니다.'
        });
      }

      log.info(`파노라마 데이터 조회 요청: id=${panoramaId}`);

      const panoramaData = await VideoPanoramaData.findByPk(panoramaId);

      if (!panoramaData) {
        return res.status(404).json({
          success: false,
          message: '파노라마 데이터를 찾을 수 없습니다.'
        });
      }

      log.info(`파노라마 데이터 조회 완료: id=${panoramaId}`);

      res.json({
        success: true,
        message: '파노라마 데이터 조회 성공',
        data: panoramaData
      });

    } catch (error) {
      log.error('파노라마 데이터 조회 오류:', error);
      res.status(500).json({
        success: false,
        message: '파노라마 데이터 조회 실패',
        error: error.message
      });
    }
  }
]);

export const routesConfig = (app) => {
  log.info('Registering panorama routes...', 'Panorama');
  app.use('/api/panorama', router);
  log.info('Panorama routes registered', 'Panorama');
};

export default router;
