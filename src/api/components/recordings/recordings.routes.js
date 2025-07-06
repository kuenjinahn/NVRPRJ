'use-strict';

import * as RecordingsController from './recordings.controller.js';
import * as RecordingsModel from './recordings.model.js';

import * as PaginationMiddleware from '../../middlewares/pagination.middleware.js';
import * as PermissionMiddleware from '../../middlewares/auth.permission.middleware.js';
import * as ValidationMiddleware from '../../middlewares/auth.validation.middleware.js';
import * as RecordingsValidationMiddleware from '../../middlewares/recordings.validation.middleware.js';

import Database from '../../database.js';
import LoggerService from '../../../services/logger/logger.service.js';
import { spawn } from 'child_process';
import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';
import { dirname, resolve } from 'path';
import moment from 'moment-timezone';
import { createHash } from 'crypto';
import ConfigService from '../../../services/config/config.service.js';
import { execAsync } from '../../utils/execAsync.js';
import { v4 as uuidv4 } from 'uuid';

const logger = new LoggerService();

// Get current file's directory path
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// 썸네일 저장 디렉토리 설정
const THUMBNAIL_DIR = resolve(process.env.CUI_STORAGE_PATH || 'storage', 'thumbnails');
const RECORDINGS_DIR = resolve(process.env.CUI_STORAGE_PATH || 'storage', 'recordings');

// 썸네일 디렉토리가 없으면 생성
if (!fs.existsSync(THUMBNAIL_DIR)) {
  fs.mkdirSync(THUMBNAIL_DIR, { recursive: true });
  logger.info('Created thumbnail directory:', THUMBNAIL_DIR);
}

async function findLatestVideoFile(directoryPath) {
  try {
    const files = await fs.promises.readdir(directoryPath);
    const videoFiles = files
      .filter(file => file.endsWith('.mp4') || file.endsWith('.avi'))
      .map(file => ({
        name: file,
        path: path.join(directoryPath, file),
        stat: fs.statSync(path.join(directoryPath, file))
      }))
      .sort((a, b) => b.stat.mtime.getTime() - a.stat.mtime.getTime());

    return videoFiles.length > 0 ? videoFiles[0] : null;
  } catch (error) {
    logger.error(`Error finding latest video file: ${error.message}`);
    return null;
  }
}

async function generateThumbnail(videoPath, thumbnailPath) {
  try {
    // 비디오 파일 존재 확인
    if (!fs.existsSync(videoPath)) {
      logger.error(`Video file not found at path: ${videoPath}`);
      return false;
    }

    // 썸네일 디렉토리 생성
    const thumbnailDir = path.dirname(thumbnailPath);
    if (!fs.existsSync(thumbnailDir)) {
      fs.mkdirSync(thumbnailDir, { recursive: true });
      logger.debug(`Created thumbnail directory: ${thumbnailDir}`);
    }

    // 비디오 중간 지점에서 프레임 추출 (더 의미있는 썸네일을 위해)
    const ffmpegCmd = `ffmpeg -i "${videoPath}" -vf "select=eq(n\\,100),scale=640:360:force_original_aspect_ratio=decrease,pad=640:360:(ow-iw)/2:(oh-ih)/2,setsar=1" -frames:v 1 -q:v 2 "${thumbnailPath}" -y`;
    logger.debug(`Executing FFmpeg command: ${ffmpegCmd}`);

    await execAsync(ffmpegCmd);

    // 썸네일 생성 시간 메타데이터 저장
    const thumbnailMeta = {
      videoMtime: fs.statSync(videoPath).mtime.getTime(),
      generatedAt: Date.now()
    };
    await fs.promises.writeFile(
      `${thumbnailPath}.meta`,
      JSON.stringify(thumbnailMeta),
      'utf8'
    );

    logger.info(`Successfully generated thumbnail at: ${thumbnailPath}`);
    return true;
  } catch (error) {
    logger.error(`Failed to generate thumbnail: ${error.message}`);
    return false;
  }
}

async function shouldRegenerateThumbnail(videoPath, thumbnailPath) {
  try {
    if (!fs.existsSync(thumbnailPath)) return true;

    const metaPath = `${thumbnailPath}.meta`;
    if (!fs.existsSync(metaPath)) return true;

    const meta = JSON.parse(await fs.promises.readFile(metaPath, 'utf8'));
    const videoMtime = fs.statSync(videoPath).mtime.getTime();

    return videoMtime > meta.videoMtime;
  } catch (error) {
    logger.error(`Error checking thumbnail regeneration: ${error.message}`);
    return true;
  }
}

// 비디오 파일 경로 생성 함수 개선
const getVideoPath = (cameraName, date) => {
  const recordingPath = resolve(RECORDINGS_DIR, cameraName, date);
  logger.debug('Generated video path:', recordingPath);
  return recordingPath;
};

/**
 * @swagger
 * tags:
 *  name: Recordings
 */

export const routesConfig = (app) => {
  // Express 앱 설정 조정
  app.set('max-http-header-size', 32768); // 32KB

  // 초기 미들웨어 설정
  app.use((req, res, next) => {
    // 모든 요청에 대한 기본 로깅
    // logger.info('Incoming request:', {
    //   method: req.method,
    //   url: req.url,
    //   path: req.path,
    //   params: req.params,
    //   query: req.query,
    //   timestamp: new Date().toISOString()
    // });

    // CORS 헤더 설정
    res.header('Access-Control-Allow-Origin', '*');
    res.header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
    res.header('Access-Control-Allow-Headers', [
      'Origin',
      'X-Requested-With',
      'Content-Type',
      'Accept',
      'Authorization',
      'Range',
      'If-None-Match',
      'If-Modified-Since'
    ].join(', '));
    res.header('Access-Control-Expose-Headers', [
      'Content-Range',
      'Accept-Ranges',
      'Content-Length',
      'Content-Type',
      'ETag',
      'Last-Modified'
    ].join(', '));

    if (req.method === 'OPTIONS') {
      return res.status(200).end();
    }

    next();
  });

  // 비디오 스트리밍 라우트를 가장 먼저 등록
  logger.info('Registering video streaming routes');

  // 스트리밍 ID 기반 라우트
  app.get('/api/recordings/stream/:id', async (req, res) => {
    const requestId = req.headers['x-request-id'] || 'unaknown';
    const startTime = Date.now();
    const id = req.params.id;
    // console.log("====> stream :", id);
    try {
      // recordingHistory에서 녹화 정보 찾기
      const recording = await RecordingsModel.getRecordingHistoryById(id);

      if (!recording) {
        logger.warn(`[${requestId}] Recording not found in history: ${id}`);
        return res.status(404).json({ error: 'Recording not found' });
      }

      // 녹화 파일 경로 생성
      let datePart = '';
      if (recording.startTime instanceof Date) {
        datePart = recording.startTime.toISOString().split('T')[0];
      } else if (typeof recording.startTime === 'string' && recording.startTime.includes('T')) {
        datePart = recording.startTime.split('T')[0];
      } else if (typeof recording.startTime === 'string' && recording.startTime.length >= 10) {
        // 혹시 '2025-05-21 09:41:21' 같은 형식일 때
        datePart = recording.startTime.substring(0, 10);
      }

      // 녹화 파일 경로 생성
      const videoPath = getVideoPath(recording.cameraName, datePart);
      const videoFile = await findVideoFileByFilename(videoPath, recording.filename);

      if (!videoFile) {
        logger.warn(`[${requestId}] Video file not found: ${recording.filename}`);
        return res.status(404).json({ error: 'Video file not found' });
      }

      // 비디오 스트리밍 처리
      const stat = fs.statSync(videoFile);
      const fileSize = stat.size;
      const range = req.headers.range;

      if (range) {
        const parts = range.replace(/bytes=/, '').split('-');
        const start = parseInt(parts[0], 10);
        const end = parts[1] ? parseInt(parts[1], 10) : fileSize - 1;
        const chunksize = end - start + 1;
        const file = fs.createReadStream(videoFile, { start, end });
        const head = {
          'Content-Range': `bytes ${start}-${end}/${fileSize}`,
          'Accept-Ranges': 'bytes',
          'Content-Length': chunksize,
          'Content-Type': 'video/mp4',
        };

        res.writeHead(206, head);
        file.pipe(res);
      } else {
        const head = {
          'Content-Length': fileSize,
          'Content-Type': 'video/mp4',
        };
        res.writeHead(200, head);
        fs.createReadStream(videoFile).pipe(res);
      }
    } catch (error) {
      logger.error(`[${requestId}] Error streaming video: ${error.message}`);
      res.status(500).json({ error: 'Error streaming video' });
    }
  });

  logger.info('Initializing recordings routes', {
    timestamp: new Date().toISOString(),
    environment: process.env.NODE_ENV,
    appRoutes: Object.keys(app._router.stack)
      .filter(key => app._router.stack[key].route)
      .map(key => app._router.stack[key].route.path)
  });

  // 헤더 크기 제한 설정
  app.use((req, res, next) => {
    // 헤더 크기 제한 증가
    req.maxHeadersCount = 1000;
    // 청크 크기 설정
    req.maxRequestSize = 50 * 1024 * 1024; // 50MB
    next();
  });

  /**
   * @swagger
   * /api/recordings:
   *   get:
   *     tags: [Recordings]
   *     security:
   *       - bearerAuth: []
   *     summary: Get all recordings
   *     parameters:
   *       - in: query
   *         name: cameras
   *         description: Cameras
   *         example: "Camera One,Camera Two"
   *         type: string
   *       - in: query
   *         name: labels
   *         description: Labels
   *         example: "Human,Person,Face"
   *         type: string
   *       - in: query
   *         name: type
   *         description: Type
   *         example: "Snapshot,Video"
   *         type: string
   *       - in: query
   *         name: start
   *         type: number
   *         description: Start index
   *       - in: query
   *         name: page
   *         type: number
   *         description: Page
   *       - in: query
   *         name: pageSize
   *         type: number
   *         description: Page size
   *       - in: query
   *         name: from
   *         description: Start Date
   *         example: "2020-01-01"
   *         format: date
   *         pattern: "YYYY-MM-DD"
   *         minLength: 0
   *         maxLength: 10
   *       - in: query
   *         name: to
   *         description: End Date
   *         example: "2020-02-01"
   *         format: date
   *         pattern: "YYYY-MM-DD"
   *         minLength: 0
   *         maxLength: 10
   *     responses:
   *       200:
   *         description: Successfull
   *       401:
   *         description: Unauthorized
   *       500:
   *         description: Internal server error
   */
  app.get('/api/recordings', [
    ValidationMiddleware.validJWTNeeded,
    PermissionMiddleware.minimumPermissionLevelRequired('recordings:access'),
    RecordingsController.list,
    PaginationMiddleware.pages,
  ]);

  // 녹화 기록 조회 라우트
  app.get('/api/recordings/history', async (req, res) => {
    try {
      let recordings;
      // console.log("====> history req.query :", req.query);
      if (req.query.startDate && req.query.endDate) {
        // 기간별 녹화 기록 조회
        const startDate = new Date(req.query.startDate);
        const endDate = new Date(req.query.endDate);
        // console.log("====> history :", req.query.cameraIds);
        if (req.query.cameraIds) {
          // 여러 카메라 ID 처리
          const cameraIds = Array.isArray(req.query.cameraIds)
            ? req.query.cameraIds
            : req.query.cameraIds.split(',');
          // console.log("====> history cameraIds :", cameraIds);
          recordings = await Promise.all(
            cameraIds.map(cameraId =>
              RecordingsModel.getRecordingHistoryByDateRange(startDate, endDate, cameraId)
            )
          );
          // 결과 병합 및 중복 제거
          recordings = recordings.flat().filter((record, index, self) =>
            index === self.findIndex(r => r.id === record.id)
          );
        } else {
          // 단일 카메라 ID 또는 전체 카메라
          recordings = await RecordingsModel.getRecordingHistoryByDateRange(
            startDate,
            endDate,
            req.query.cameraId
          );
        }
      } else if (req.query.cameraId) {
        // 특정 카메라의 녹화 기록 조회
        recordings = await RecordingsModel.getRecordingHistoryByCameraId(req.query.cameraId);
      } else {
        // 전체 녹화 기록 조회
        recordings = await RecordingsModel.getAllRecordingHistory();
      }

      res.status(200).send(recordings);
    } catch (error) {
      logger.error(`Error fetching recording history: ${error.message}`);
      res.status(500).send({
        statusCode: 500,
        message: error.message,
      });
    }
  });

  /**
   * @swagger
   * /api/recordings/status/{cameraName}:
   *   get:
   *     tags: [Recordings]
   *     security:
   *       - bearerAuth: []
   *     summary: Get recording status for specific camera
   *     parameters:
   *       - in: path
   *         name: cameraName
   *         schema:
   *           type: string
   *         required: true
   *         description: Name of the camera
   *     responses:
   *       200:
   *         description: Successfull
   *       401:
   *         description: Unauthorized
   *       500:
   *         description: Internal server error
   */
  app.get('/api/recordings/status/:cameraName', [
    ValidationMiddleware.validJWTNeeded,
    PermissionMiddleware.minimumPermissionLevelRequired('recordings:access'),
    async (req, res) => {
      try {
        const { cameraName } = req.params;
        const recordingHistory = await RecordingsModel.getRecordingHistoryByCameraId(cameraName);
        const activeRecordings = recordingHistory.filter(record => record.status === 'recording');

        res.json({
          isRecording: activeRecordings.length > 0,
          currentRecording: activeRecordings[0] || null
        });
      } catch (error) {
        logger.error('Error fetching recording status:', error);
        res.status(500).json({ error: 'Failed to fetch recording status' });
      }
    }
  ]);

  /**
   * @swagger
   * /api/recordings/active:
   *   get:
   *     tags: [Recordings]
   *     security:
   *       - bearerAuth: []
   *     summary: Get active recordings
   *     responses:
   *       200:
   *         description: Successfull
   *       401:
   *         description: Unauthorized
   *       500:
   *         description: Internal server error
   */
  app.get('/api/recordings/active', [
    ValidationMiddleware.validJWTNeeded,
    PermissionMiddleware.minimumPermissionLevelRequired('recordings:access'),
    async (req, res) => {
      try {
        const activeRecordings = await RecordingsModel.getRecordingHistoryByStatus('recording');
        res.json(activeRecordings);
      } catch (error) {
        logger.error('Error fetching active recordings:', error);
        res.status(500).json({ error: 'Failed to fetch active recordings' });
      }
    }
  ]);

  /**
   * @swagger
   * /api/recordings/thumbnail/{id}:
   *   get:
   *     tags: [Recordings]
   *     security:
   *       - bearerAuth: []
   *     summary: Get recording thumbnail by recording ID
   *     parameters:
   *       - in: path
   *         name: id
   *         schema:
   *           type: string
   *         required: true
   *         description: ID of the recording
   *     responses:
   *       200:
   *         description: Thumbnail image
   *       404:
   *         description: Recording or video file not found
   *       500:
   *         description: Internal server error
   */
  app.get('/api/recordings/thumbnail/:id', [
    ValidationMiddleware.validJWTNeeded,
    PermissionMiddleware.minimumPermissionLevelRequired('recordings:access'),
    async (req, res) => {
      const requestId = req.headers['x-request-id'] || 'unknown';
      try {
        const { id } = req.params;
        logger.info(`[${requestId}] Fetching thumbnail for recording ID: ${id}`);

        // Get recording info from database
        const recording = await RecordingsModel.getRecordingHistoryById(id);

        if (!recording) {
          logger.warn(`[${requestId}] Recording not found with ID: ${id}`);
          return res.status(404).json({
            error: 'Recording not found',
            id
          });
        }

        // 날짜 파싱 및 검증
        let recordingDate;
        try {
          logger.debug(`[${requestId}] Raw startTime: ${recording.startTime}`);
          if (typeof recording.startTime === 'string' && recording.startTime.length >= 10) {
            recordingDate = recording.startTime.substring(0, 10);
            logger.debug(`[${requestId}] Extracted date: ${recordingDate}`);
          } else {
            throw new Error(`Invalid startTime format: ${recording.startTime}`);
          }
        } catch (error) {
          logger.error(`[${requestId}] Error parsing date:`, error);
          return res.status(400).json({
            error: 'Invalid date format',
            details: error.message,
            startTime: recording.startTime
          });
        }

        const videoPath = getVideoPath(recording.cameraName, recordingDate);

        // Check if video directory exists
        if (!fs.existsSync(videoPath)) {
          logger.warn(`[${requestId}] Video directory not found: ${videoPath}`);
          return res.status(404).json({
            error: 'Video directory not found',
            path: videoPath
          });
        }

        // Find the specific video file
        const videoFile = await findVideoFileByFilename(videoPath, recording.filename);
        if (!videoFile) {
          logger.warn(`[${requestId}] Video file not found: ${recording.filename}`);
          return res.status(404).json({
            error: 'Video file not found',
            filename: recording.filename
          });
        }

        try {
          // Generate thumbnail directly to buffer
          const thumbnailBuffer = await generateThumbnailToBuffer(videoFile);
          logger.info(`[${requestId}] Thumbnail generated successfully`);

          // Send the thumbnail with proper content type
          res.set('Content-Type', 'image/png');
          res.send(thumbnailBuffer);
        } catch (error) {
          logger.error(`[${requestId}] Failed to generate thumbnail:`, error);
          return res.status(500).json({
            error: 'Failed to generate thumbnail',
            details: error.message
          });
        }
      } catch (error) {
        logger.error(`[${requestId}] Error in thumbnail endpoint:`, error);
        res.status(500).json({
          error: 'Internal server error',
          details: error.message
        });
      }
    }
  ]);

  /**
   * @swagger
   * /api/recordings/video/{cameraName}/{date}/{filename}:
   *   get:
   *     tags: [Recordings]
   *     security:
   *       - bearerAuth: []
   *     summary: Stream video recording
   *     parameters:
   *       - in: path
   *         name: cameraName
   *         schema:
   *           type: string
   *         required: true
   *         description: Name of the camera
   *       - in: path
   *         name: date
   *         schema:
   *           type: string
   *         required: true
   *         description: Recording date (YYYY-MM-DD format)
   *       - in: path
   *         name: filename
   *         schema:
   *           type: string
   *         required: true
   *         description: Name of the video file
   *     responses:
   *       200:
   *         description: Video stream
   *       404:
   *         description: Video file not found
   *       500:
   *         description: Internal server error
   */
  app.get('/api/recordings/video/:cameraName/:date/:filename', [
    ValidationMiddleware.validJWTNeeded,
    PermissionMiddleware.minimumPermissionLevelRequired('recordings:access'),
    async (req, res) => {
      try {
        const { cameraName, date, filename } = req.params;

        // 비디오 파일 경로 생성
        const videoBasePath = path.join(RECORDINGS_DIR, cameraName, date);
        const videoPath = path.join(videoBasePath, filename);

        logger.debug('Processing video stream request', {
          cameraName,
          date,
          filename,
          videoBasePath,
          videoPath,
          exists: fs.existsSync(videoPath)
        });

        // 파일 정보 확인
        const stat = fs.statSync(videoPath);
        const fileSize = stat.size;
        const range = req.headers.range;

        // 청크 크기 제한 설정
        const maxChunkSize = 10 * 1024 * 1024; // 10MB

        if (range) {
          const parts = range.replace(/bytes=/, '').split('-');
          let start = parseInt(parts[0], 10);
          let end = parts[1] ? parseInt(parts[1], 10) : fileSize - 1;

          // 청크 크기 제한 적용
          if (end - start >= maxChunkSize) {
            end = start + maxChunkSize - 1;
          }

          const chunksize = (end - start) + 1;
          const file = fs.createReadStream(videoPath, { start, end });
          const head = {
            'Content-Range': `bytes ${start}-${end}/${fileSize}`,
            'Accept-Ranges': 'bytes',
            'Content-Length': chunksize,
            'Content-Type': 'video/mp4'
          };

          logger.debug('Streaming video range', {
            start,
            end,
            chunksize,
            headers: head
          });

          res.writeHead(206, head);
          file.pipe(res);

          file.on('error', (error) => {
            logger.error('Stream error:', error);
            if (!res.headersSent) {
              res.status(500).json({
                error: 'Failed to stream video',
                details: error.message
              });
            }
          });
        } else {
          // 전체 파일 스트리밍 시에도 청크 단위로 전송
          const head = {
            'Content-Length': fileSize,
            'Content-Type': 'video/mp4',
            'Accept-Ranges': 'bytes',
            'Transfer-Encoding': 'chunked'
          };

          res.writeHead(200, head);
          const stream = fs.createReadStream(videoPath, {
            highWaterMark: maxChunkSize
          });
          stream.pipe(res);

          stream.on('error', (error) => {
            logger.error('Stream error:', error);
            if (!res.headersSent) {
              res.status(500).json({
                error: 'Failed to stream video',
                details: error.message
              });
            }
          });
        }
      } catch (error) {
        logger.error('Error streaming video:', {
          error: error.message,
          stack: error.stack,
          params: req.params
        });

        if (!res.headersSent) {
          res.status(500).json({
            error: 'Failed to stream video',
            details: error.message
          });
        }
      }
    }
  ]);

  /**
   * @swagger
   * /api/recordings/{id}:
   *   get:
   *     tags: [Recordings]
   *     security:
   *       - bearerAuth: []
   *     summary: Get specific recording by ID
   *     parameters:
   *       - in: path
   *         name: id
   *         schema:
   *           type: string
   *         required: true
   *         description: ID of the recording
   *     responses:
   *       200:
   *         description: Successfull
   *       401:
   *         description: Unauthorized
   *       404:
   *         description: Not found
   *       500:
   *         description: Internal server error
   */
  app.get('/api/recordings/:id', [
    ValidationMiddleware.validJWTNeeded,
    PermissionMiddleware.minimumPermissionLevelRequired('recordings:access'),
    RecordingsController.getById,
  ]);

  /**
   * @swagger
   * /api/recordings:
   *   post:
   *     tags: [Recordings]
   *     security:
   *       - bearerAuth: []
   *     summary: Creates new recording
   *     requestBody:
   *       required: true
   *       content:
   *         application/json:
   *          schema:
   *            type: object
   *            properties:
   *              camera:
   *                type: string
   *              trigger:
   *                type: string
   *              type:
   *                type: string
   *     responses:
   *       201:
   *         description: Successfull
   *       401:
   *         description: Unauthorized
   *       500:
   *         description: Internal server error
   */
  app.post('/api/recordings', [
    ValidationMiddleware.validJWTNeeded,
    PermissionMiddleware.minimumPermissionLevelRequired('notifications:edit'),
    RecordingsValidationMiddleware.hasValidFields,
    async (req, res) => {
      const requestId = uuidv4();
      const startTime = Date.now();

      try {
        const { camera, trigger, type } = req.body;
        logger.info(`[${requestId}] Starting new recording`, { camera, trigger, type });

        // 녹화 정보 생성
        const recording = {
          id: uuidv4(),
          cameraName: camera,
          startTime: new Date().toISOString(),
          status: 'recording',
          trigger: trigger,
          type: type
        };

        // 녹화 디렉토리 생성
        const recordingDate = recording.startTime.substring(0, 10);
        const videoPath = getVideoPath(camera, recordingDate);
        if (!fs.existsSync(videoPath)) {
          fs.mkdirSync(videoPath, { recursive: true });
          logger.debug(`[${requestId}] Created recording directory: ${videoPath}`);
        }

        // 카메라 스트림 URL 생성
        const streamUrl = `rtsp://${camera}/stream`;

        // 녹화 파일명 생성
        const filename = `${recording.id}.mp4`;
        const videoFilePath = path.join(videoPath, filename);

        // 섬네일 파일명 생성
        const thumbnailFilename = `${recording.id}.png`;
        const thumbnailPath = path.join(videoPath, thumbnailFilename);

        // 첫 프레임 캡처 및 섬네일 생성
        try {
          await generateThumbnailFromStream(streamUrl, thumbnailPath);
          logger.info(`[${requestId}] Generated initial thumbnail: ${thumbnailPath}`);
        } catch (error) {
          logger.error(`[${requestId}] Failed to generate initial thumbnail:`, error);
          // 섬네일 생성 실패는 녹화 시작을 막지 않음
        }

        // 녹화 시작
        const ffmpeg = spawn('ffmpeg', [
          '-i', streamUrl,
          '-c:v', 'copy',
          '-c:a', 'aac',
          '-f', 'mp4',
          videoFilePath
        ]);

        // 녹화 정보 저장
        recording.filename = filename;
        await RecordingsModel.addRecordingHistory(recording);

        const duration = Date.now() - startTime;
        logger.info(`[${requestId}] Recording started successfully in ${duration}ms`, {
          recordingId: recording.id,
          videoPath: videoFilePath,
          thumbnailPath: thumbnailPath
        });

        res.status(201).json(recording);
      } catch (error) {
        const duration = Date.now() - startTime;
        logger.error(`[${requestId}] Error starting recording:`, {
          error: error.message,
          stack: error.stack,
          duration: `${duration}ms`
        });

        res.status(500).json({
          error: 'Failed to start recording',
          message: error.message
        });
      }
    }
  ]);

  /**
   * @swagger
   * /api/recordings:
   *   delete:
   *     tags: [Recordings]
   *     security:
   *       - bearerAuth: []
   *     summary: Remove all recordings
   *     responses:
   *       204:
   *         description: Successfull
   *       401:
   *         description: Unauthorized
   *       500:
   *         description: Internal server error
   */
  app.delete('/api/recordings', [
    ValidationMiddleware.validJWTNeeded,
    PermissionMiddleware.minimumPermissionLevelRequired('recordings:edit'),
    RecordingsController.removeAll,
  ]);

  /**
   * @swagger
   * /api/recordings/{id}:
   *   delete:
   *     tags: [Recordings]
   *     security:
   *       - bearerAuth: []
   *     summary: Delete recording by id
   *     parameters:
   *       - in: path
   *         name: id
   *         schema:
   *           type: string
   *         required: true
   *         description: ID of the recordings
   *     responses:
   *       200:
   *         description: Successfull
   *       400:
   *         description: Bad request
   *       404:
   *         description: Not found
   *       500:
   *         description: Internal server error
   */
  app.delete('/api/recordings/:id', [
    ValidationMiddleware.validJWTNeeded,
    PermissionMiddleware.minimumPermissionLevelRequired('recordings:edit'),
    async (req, res) => {
      const requestId = req.headers['x-request-id'] || 'unknown';
      const startTime = Date.now();
      const id = req.params.id;

      try {
        logger.info(`[${requestId}] Deleting recording from database: ${id}`);

        // 녹화 삭제 실행 (DB에서만 삭제)
        await RecordingsModel.removeById(id);

        const duration = Date.now() - startTime;
        logger.info(`[${requestId}] Successfully deleted recording from database in ${duration}ms`);

        res.status(200).json({
          message: 'Recording deleted from database successfully',
          id: id
        });
      } catch (error) {
        const duration = Date.now() - startTime;
        logger.error(`[${requestId}] Error deleting recording from database:`, {
          error: error.message,
          stack: error.stack,
          duration: `${duration}ms`
        });

        // Not Found 에러 처리
        if (error.message.includes('Recording not found')) {
          return res.status(404).json({
            error: 'Recording not found',
            message: error.message
          });
        }

        res.status(500).json({
          error: 'Failed to delete recording from database',
          message: error.message
        });
      }
    }
  ]);

  // 라우트 등록 완료 후 전체 라우트 목록 출력
  const routes = app._router.stack
    .filter(r => r.route)
    .map(r => ({
      path: r.route.path,
      method: Object.keys(r.route.methods)[0].toUpperCase()
    }));

  logger.info('Registered routes:', {
    count: routes.length,
    routes: routes,
    timestamp: new Date().toISOString()
  });
};
// Helper function to find video file by filename
async function findVideoFileByFilename(videoPath, filename) {
  try {
    const files = await fs.promises.readdir(videoPath);
    const videoFile = files.find(file => file === filename);

    return videoFile ? path.join(videoPath, videoFile) : null;
  } catch (error) {
    logger.error(`Error finding video file for filename ${filename}:`, error);
    return null;
  }
}

// Helper function to generate thumbnail to buffer
async function generateThumbnailToBuffer(videoPath) {
  return new Promise((resolve, reject) => {
    const ffmpeg = spawn('ffmpeg', [
      '-i', videoPath,
      '-vf', 'select=eq(n\\,1),scale=320:180:force_original_aspect_ratio=decrease,pad=320:180:(ow-iw)/2:(oh-ih)/2,setsar=1',
      '-frames:v', '1',
      '-f', 'image2',
      '-'
    ]);

    const chunks = [];
    ffmpeg.stdout.on('data', chunk => chunks.push(chunk));
    ffmpeg.stderr.on('data', data => logger.debug('FFmpeg output:', data.toString()));

    ffmpeg.on('close', (code) => {
      if (code !== 0) {
        reject(new Error(`FFmpeg process exited with code ${code}`));
        return;
      }
      resolve(Buffer.concat(chunks));
    });

    ffmpeg.on('error', reject);
  });
}

// Helper function to generate thumbnail from video stream
async function generateThumbnailFromStream(streamUrl, outputPath) {
  return new Promise((resolve, reject) => {
    const ffmpeg = spawn('ffmpeg', [
      '-i', streamUrl,
      '-vf', 'select=eq(n\\,1),scale=320:180:force_original_aspect_ratio=decrease,pad=320:180:(ow-iw)/2:(oh-ih)/2,setsar=1',
      '-frames:v', '1',
      '-f', 'image2',
      outputPath
    ]);

    ffmpeg.stderr.on('data', data => logger.debug('FFmpeg output:', data.toString()));

    ffmpeg.on('close', (code) => {
      if (code !== 0) {
        reject(new Error(`FFmpeg process exited with code ${code}`));
        return;
      }
      resolve();
    });

    ffmpeg.on('error', reject);
  });
}

