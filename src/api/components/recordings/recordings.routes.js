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
const RECORDINGS_DIR = resolve(process.env.CUI_STORAGE_PATH || 'outputs/nvr', 'recordings');

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
  // 카메라 이름을 실제 폴더명으로 매핑
  let actualCameraName = cameraName;

  // 데이터베이스의 카메라명을 실제 폴더명으로 변환
  if (cameraName === '댐영상1' || cameraName === 'camera1') {
    actualCameraName = 'camera1';
  } else if (cameraName === '댐영상2' || cameraName === 'camera2') {
    actualCameraName = 'camera2';
  }

  const recordingPath = resolve(RECORDINGS_DIR, actualCameraName, date);
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

    // CORS 헤더 설정 (HLS 스트리밍 최적화)
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
      'If-Modified-Since',
      'Cache-Control'
    ].join(', '));
    res.header('Access-Control-Expose-Headers', [
      'Content-Range',
      'Accept-Ranges',
      'Content-Length',
      'Content-Type',
      'ETag',
      'Last-Modified',
      'Cache-Control'
    ].join(', '));

    if (req.method === 'OPTIONS') {
      return res.status(200).end();
    }

    next();
  });

  // 비디오 스트리밍 라우트를 가장 먼저 등록
  logger.info('Registering video streaming routes');

  // HLS 세그먼트 파일 스트리밍 라우트 (HLS 재생을 위해 필요)
  app.get('/api/recordings/hls/:cameraName/:date/:filename', async (req, res) => {
    const requestId = req.headers['x-request-id'] || 'unknown';
    const { cameraName, date, filename } = req.params;

    try {
      // 파라미터 검증
      if (!cameraName || !date || !filename) {
        logger.warn(`[${requestId}] Invalid parameters: cameraName=${cameraName}, date=${date}, filename=${filename}`);
        return res.status(400).json({ error: 'Invalid parameters' });
      }

      // 파일명 검증 (보안)
      if (filename.includes('..') || filename.includes('/') || filename.includes('\\')) {
        logger.warn(`[${requestId}] Invalid filename: ${filename}`);
        return res.status(400).json({ error: 'Invalid filename' });
      }

      // URL 중복 패턴 검사 및 수정
      if (filename.includes('//api/recordings/hls//')) {
        logger.warn(`[${requestId}] Filename contains duplicate path, fixing: ${filename}`);
        filename = filename.replace(/\/\/api\/recordings\/hls\/\/api\/recordings\/hls\//g, '/api/recordings/hls/');
        logger.info(`[${requestId}] Fixed filename: ${filename}`);
      }

      // HLS 파일 경로 생성
      const hlsPath = path.join(RECORDINGS_DIR, cameraName, date, 'hls');
      logger.debug(`[${requestId}] HLS path: ${hlsPath}`);

      // 파일 존재 확인
      const filePath = path.join(hlsPath, filename);
      logger.debug(`[${requestId}] Full file path: ${filePath}`);

      if (!await fs.promises.access(filePath).then(() => true).catch(() => false)) {
        logger.warn(`[${requestId}] HLS file not found: ${filePath}`);
        return res.status(404).json({ error: 'HLS file not found' });
      }

      // 파일 정보 확인
      const stat = await fs.promises.stat(filePath);
      const fileSize = stat.size;

      // 적절한 Content-Type 설정
      let contentType = 'application/octet-stream';
      if (filename.endsWith('.ts')) {
        contentType = 'video/mp2t';
      } else if (filename.endsWith('.m3u8')) {
        contentType = 'application/vnd.apple.mpegurl';
      }

      // CORS 및 캐시 헤더 설정
      res.setHeader('Content-Type', contentType);
      res.setHeader('Content-Length', fileSize);
      res.setHeader('Cache-Control', 'no-cache');
      res.setHeader('Access-Control-Allow-Origin', '*');
      res.setHeader('Access-Control-Allow-Methods', 'GET, OPTIONS');
      res.setHeader('Access-Control-Allow-Headers', 'Range, If-None-Match, If-Modified-Since');

      // Range 요청 지원 (비디오 세그먼트 스트리밍 최적화)
      const range = req.headers.range;
      if (range) {
        const parts = range.replace(/bytes=/, '').split('-');
        const start = parseInt(parts[0], 10);
        const end = parts[1] ? parseInt(parts[1], 10) : fileSize - 1;
        const chunksize = (end - start) + 1;

        res.status(206);
        res.setHeader('Content-Range', `bytes ${start}-${end}/${fileSize}`);
        res.setHeader('Accept-Ranges', 'bytes');
        res.setHeader('Content-Length', chunksize);

        const stream = fs.createReadStream(filePath, { start, end });
        stream.pipe(res);
      } else {
        // 전체 파일 스트리밍
        const fileStream = fs.createReadStream(filePath);
        fileStream.pipe(res);
      }

      logger.debug(`[${requestId}] HLS file streaming: ${filename} (${fileSize} bytes)`);
    } catch (error) {
      logger.error(`[${requestId}] HLS file streaming error: ${error.message}`);
      res.status(500).json({ error: 'HLS file streaming failed' });
    }
  });

  // MP4 파일 직접 스트리밍 라우트
  app.get('/api/recordings/stream/:id', async (req, res) => {
    const requestId = req.headers['x-request-id'] || 'unknown';
    const startTime = Date.now();
    const id = req.params.id;

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
        // 한국 시간으로 변환하여 날짜 추출
        const kstDate = moment(recording.startTime).tz('Asia/Seoul');
        datePart = kstDate.format('YYYY-MM-DD');
      } else if (typeof recording.startTime === 'string' && recording.startTime.includes('T')) {
        // ISO 문자열을 한국 시간으로 변환
        const kstDate = moment(recording.startTime).tz('Asia/Seoul');
        datePart = kstDate.format('YYYY-MM-DD');
      } else if (typeof recording.startTime === 'string' && recording.startTime.length >= 10) {
        // 혹시 '2025-05-21 09:41:21' 같은 형식일 때
        datePart = recording.startTime.substring(0, 10);
      }

      // MP4 파일 경로 직접 확인
      let videoFile = null;

      // file_path가 제공된 경우 해당 경로 사용
      if (req.query.file_path) {
        const filePath = req.query.file_path;
        // 상대 경로인 경우 outputs/nvr 기준으로 절대 경로 구성
        if (filePath.startsWith('./outputs/nvr/')) {
          videoFile = path.resolve(process.cwd(), filePath.substring(2));
        } else if (filePath.startsWith('outputs/nvr/')) {
          videoFile = path.resolve(process.cwd(), filePath);
        } else {
          videoFile = filePath;
        }

        logger.info(`[${requestId}] Using file_path from query: ${videoFile}`);
      } else {
        // 기존 로직 (DB의 filename 사용)
        const videoPath = getVideoPath(recording.cameraName, datePart);

        // DB에 저장된 파일 경로가 절대 경로인지 확인
        if (recording.filename && path.isAbsolute(recording.filename)) {
          videoFile = recording.filename;
        } else if (recording.filename) {
          // 상대 경로인 경우 전체 경로 구성
          videoFile = path.join(videoPath, recording.filename);
        }

        // MP4 파일 존재 확인
        if (!videoFile || !fs.existsSync(videoFile)) {
          // 파일명으로 검색 시도
          videoFile = await findVideoFileByFilename(videoPath, recording.filename);
        }

        // 여전히 파일을 찾지 못한 경우, 다른 가능한 경로 시도
        if (!videoFile || !fs.existsSync(videoFile)) {
          // 파일명에서 경로 부분을 제거하고 파일명만 사용
          const pathParts = recording.filename.split('/');
          const shortFilename = pathParts[pathParts.length - 1];

          if (shortFilename !== recording.filename) {
            const alternativePath = path.join(videoPath, shortFilename);
            if (fs.existsSync(alternativePath)) {
              videoFile = alternativePath;
              logger.info(`[${requestId}] Found file using alternative path: ${videoFile}`);
            }
          }
        }
      }

      if (!videoFile || !fs.existsSync(videoFile)) {
        logger.warn(`[${requestId}] MP4 file not found: ${videoFile}`);
        return res.status(404).json({ error: 'Video file not found' });
      }

      // 파일 정보 확인
      const stat = fs.statSync(videoFile);
      const fileSize = stat.size;
      const range = req.headers.range;

      // Range 요청 처리 (비디오 스트리밍을 위해)
      if (range) {
        const parts = range.replace(/bytes=/, "").split("-");
        const start = parseInt(parts[0], 10);
        const end = parts[1] ? parseInt(parts[1], 10) : fileSize - 1;
        const chunksize = (end - start) + 1;
        const file = fs.createReadStream(videoFile, { start, end });

        const head = {
          'Content-Range': `bytes ${start}-${end}/${fileSize}`,
          'Accept-Ranges': 'bytes',
          'Content-Length': chunksize,
          'Content-Type': 'video/mp4',
          'Cache-Control': 'public, max-age=3600',
          'Access-Control-Allow-Origin': '*',
          'Access-Control-Allow-Headers': 'Range'
        };

        res.writeHead(206, head);
        file.pipe(res);
      } else {
        // 전체 파일 스트리밍
        const head = {
          'Content-Length': fileSize,
          'Content-Type': 'video/mp4',
          'Cache-Control': 'public, max-age=3600',
          'Access-Control-Allow-Origin': '*'
        };

        res.writeHead(200, head);
        fs.createReadStream(videoFile).pipe(res);
      }

      const duration = Date.now() - startTime;
      logger.info(`[${requestId}] MP4 streaming completed in ${duration}ms`);

    } catch (error) {
      logger.error(`[${requestId}] MP4 file streaming error: ${error.message}`);
      res.status(500).json({ error: 'MP4 file streaming failed' });
    }
  });

  // 기존 HLS 스트리밍 라우트 (호환성 유지)
  app.get('/api/recordings/hls/:id', async (req, res) => {
    const requestId = req.headers['x-request-id'] || 'unknown';
    const startTime = Date.now();
    const id = req.params.id;

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
        // 한국 시간으로 변환하여 날짜 추출
        const kstDate = moment(recording.startTime).tz('Asia/Seoul');
        datePart = kstDate.format('YYYY-MM-DD');
      } else if (typeof recording.startTime === 'string' && recording.startTime.includes('T')) {
        // ISO 문자열을 한국 시간으로 변환
        const kstDate = moment(recording.startTime).tz('Asia/Seoul');
        datePart = kstDate.format('YYYY-MM-DD');
      } else if (typeof recording.startTime === 'string' && recording.startTime.length >= 10) {
        // 혹시 '2025-05-21 09:41:21' 같은 형식일 때
        datePart = recording.startTime.substring(0, 10);
      }

      // 녹화 파일 경로 생성
      const videoPath = getVideoPath(recording.cameraName, datePart);

      // 먼저 HLS 파일 (.m3u8) 확인
      let videoFile = await findVideoFileByFilename(videoPath, recording.filename);

      // .m3u8 파일이 없으면 .m3u8.json 파일에서 실제 파일명 확인
      if (!videoFile && recording.filename && recording.filename.endsWith('.m3u8')) {
        const jsonPath = path.join(videoPath, `${recording.filename}.json`);
        try {
          if (await fs.promises.access(jsonPath).then(() => true).catch(() => false)) {
            const metadata = await fs.promises.readJson(jsonPath);

            // metadata에서 실제 .m3u8 파일 경로 확인
            if (metadata.playlistPath) {
              const actualPlaylistPath = metadata.playlistPath;
              if (await fs.promises.access(actualPlaylistPath).then(() => true).catch(() => false)) {
                videoFile = actualPlaylistPath;
                logger.info(`[${requestId}] Found HLS playlist from metadata: ${videoFile}`);
              }
            } else if (metadata.filename) {
              // metadata에 filename이 있으면 해당 파일 확인
              const actualFilePath = path.join(videoPath, 'hls', metadata.filename);
              if (await fs.promises.access(actualFilePath).then(() => true).catch(() => false)) {
                videoFile = actualFilePath;
                logger.info(`[${requestId}] Found HLS playlist from metadata filename: ${videoFile}`);
              }
            }

            // 여전히 파일을 찾지 못했으면 hls 디렉토리에서 .m3u8 파일 검색
            if (!videoFile) {
              const hlsPath = path.join(videoPath, 'hls');
              if (await fs.promises.access(hlsPath).then(() => true).catch(() => false)) {
                const hlsFiles = await fs.promises.readdir(hlsPath);
                const m3u8Files = hlsFiles.filter(file => file.endsWith('.m3u8'));
                if (m3u8Files.length > 0) {
                  // 가장 최근 파일 선택 (파일명에 시간이 포함되어 있다고 가정)
                  const latestFile = m3u8Files.sort().pop();
                  videoFile = path.join(hlsPath, latestFile);
                  logger.info(`[${requestId}] Found HLS playlist from hls directory: ${videoFile}`);
                }
              }
            }
          }
        } catch (jsonError) {
          logger.debug(`[${requestId}] Could not read metadata file: ${jsonError.message}`);
        }
      }

      if (!videoFile) {
        logger.warn(`[${requestId}] Video file not found: ${recording.filename}`);
        return res.status(404).json({ error: 'Video file not found' });
      }

      // HLS 파일인지 확인
      const isHLS = videoFile.endsWith('.m3u8');

      if (isHLS) {
        // HLS 스트리밍 처리
        try {
          const stat = await fs.promises.stat(videoFile);
          const fileSize = stat.size;

          // HLS 플레이리스트 내용을 읽어서 세그먼트 파일 경로를 수정
          let playlistContent = await fs.promises.readFile(videoFile, 'utf8');

          // 디버깅을 위한 로그 - 전체 내용 로깅
          logger.debug(`[${requestId}] Original playlist content (full):`, playlistContent);
          logger.debug(`[${requestId}] Original playlist content (first 1000 chars):`, playlistContent.substring(0, 1000));

          // 원본 플레이리스트에서 .ts 파일 경로 확인
          const originalTsFiles = playlistContent.match(/^[^#\n]*\.ts$/gm) || [];
          logger.debug(`[${requestId}] Original TS files found:`, originalTsFiles);

          // 원본 플레이리스트에서 .m3u8 파일 경로 확인
          const originalM3u8Files = playlistContent.match(/^[^#\n]*\.m3u8$/gm) || [];
          logger.debug(`[${requestId}] Original M3U8 files found:`, originalM3u8Files);

          // 원본 플레이리스트에서 중복 경로 패턴 검사
          const originalDuplicatePatterns = [
            /\/\/api\/recordings\/hls\/\/api\/recordings\/hls\//g,
            /\/api\/recordings\/hls\/\/api\/recordings\/hls\//g,
            /\/\/api\/recordings\/hls\/api\/recordings\/hls\//g,
            /\/api\/recordings\/hls\/\/api\/recordings\/hls\//g
          ];

          for (const pattern of originalDuplicatePatterns) {
            const matches = playlistContent.match(pattern);
            if (matches && matches.length > 0) {
              logger.error(`[${requestId}] Found ${matches.length} duplicate patterns in ORIGINAL playlist: ${pattern.source}`);
              logger.error(`[${requestId}] Duplicate matches:`, matches);
            }
          }

          // 원본 플레이리스트에서 모든 경로 패턴 검사
          const allPaths = playlistContent.match(/[^\s#\n]+/g) || [];
          const suspiciousPaths = allPaths.filter(path =>
            path.includes('api/recordings/hls') &&
            (path.includes('//') || path.includes('\\\\'))
          );

          if (suspiciousPaths.length > 0) {
            logger.error(`[${requestId}] Found suspicious paths in original playlist:`, suspiciousPaths);
          }

          // HLS 플레이리스트를 줄 단위로 파싱하여 수정
          const lines = playlistContent.split('\n');
          const modifiedLines = [];

          logger.debug(`[${requestId}] Processing ${lines.length} lines in playlist`);

          for (let i = 0; i < lines.length; i++) {
            const originalLine = lines[i];
            const trimmedLine = originalLine.trim();

            // 주석이나 빈 줄은 그대로 유지
            if (trimmedLine.startsWith('#') || trimmedLine === '') {
              modifiedLines.push(originalLine);
              continue;
            }

            // .ts 파일인 경우 경로 수정
            if (trimmedLine.endsWith('.ts')) {
              const filename = trimmedLine;
              const baseUrl = `/api/recordings/hls/${recording.cameraName}/${datePart}`;
              const fullUrl = `${baseUrl}/${filename}`;
              logger.debug(`[${requestId}] Line ${i + 1}: Replacing .ts path: ${filename} -> ${fullUrl}`);
              modifiedLines.push(fullUrl);
            }
            // .m3u8 파일인 경우 경로 수정
            else if (trimmedLine.endsWith('.m3u8')) {
              const filename = trimmedLine;
              const baseUrl = `/api/recordings/hls/${recording.cameraName}/${datePart}`;
              const fullUrl = `${baseUrl}/${filename}`;
              logger.debug(`[${requestId}] Line ${i + 1}: Replacing .m3u8 path: ${filename} -> ${fullUrl}`);
              modifiedLines.push(fullUrl);
            }
            // 다른 내용은 그대로 유지
            else {
              modifiedLines.push(originalLine);
            }
          }

          // 추가 안전장치: 모든 중복 패턴을 찾아서 수정
          let finalPlaylistContent = modifiedLines.join('\n');

          logger.debug(`[${requestId}] Before duplicate pattern fix:`, finalPlaylistContent.substring(0, 1000));

          // 모든 가능한 중복 패턴을 체계적으로 제거
          const duplicatePatterns = [
            /\/\/api\/recordings\/hls\/\/api\/recordings\/hls\//g,
            /\/api\/recordings\/hls\/\/api\/recordings\/hls\//g,
            /\/\/api\/recordings\/hls\/api\/recordings\/hls\//g,
            /\/api\/recordings\/hls\/\/api\/recordings\/hls\//g,
            /\/\/api\/recordings\/hls\/\/api\/recordings\/hls\//g,
            /\/api\/recordings\/hls\/\/api\/recordings\/hls\//g
          ];

          let totalFixes = 0;
          for (const pattern of duplicatePatterns) {
            const matches = finalPlaylistContent.match(pattern);
            if (matches && matches.length > 0) {
              logger.warn(`[${requestId}] Found ${matches.length} matches for pattern: ${pattern.source}`);
              logger.warn(`[${requestId}] Matches:`, matches);

              const beforeFix = finalPlaylistContent;
              finalPlaylistContent = finalPlaylistContent.replace(pattern, '/api/recordings/hls/');
              const afterFix = finalPlaylistContent;

              if (beforeFix !== afterFix) {
                totalFixes += matches.length;
                logger.info(`[${requestId}] Applied fix for pattern: ${pattern.source}`);
                logger.debug(`[${requestId}] Before fix:`, beforeFix.substring(0, 500));
                logger.debug(`[${requestId}] After fix:`, afterFix.substring(0, 500));
              }
            }
          }

          if (totalFixes > 0) {
            logger.info(`[${requestId}] Total fixes applied: ${totalFixes}`);
            logger.debug(`[${requestId}] After all fixes:`, finalPlaylistContent.substring(0, 1000));
          }

          // 최종 검증: 중복 패턴이 완전히 제거되었는지 확인
          if (finalPlaylistContent.includes('//api/recordings/hls//')) {
            logger.error(`[${requestId}] Final validation failed: still contains duplicate patterns`);
            logger.error(`[${requestId}] Remaining content:`, finalPlaylistContent);
            return res.status(500).json({ error: 'Failed to fix playlist paths' });
          }

          // 최종 플레이리스트 내용을 사용
          playlistContent = finalPlaylistContent;

          // 수정된 플레이리스트에서 .ts 파일 경로 확인
          const modifiedTsFiles = modifiedLines.filter(line => line.endsWith('.ts') && !line.startsWith('#'));
          logger.debug(`[${requestId}] Modified TS files:`, modifiedTsFiles);

          // 플레이리스트 검증: 모든 .ts 파일이 올바른 경로를 가지고 있는지 확인
          const tsFiles = modifiedLines.filter(line => line.endsWith('.ts') && !line.startsWith('#'));
          const invalidPaths = tsFiles.filter(path => !path.startsWith('/api/recordings/hls/'));

          if (invalidPaths.length > 0) {
            logger.warn(`[${requestId}] Found invalid paths in playlist:`, invalidPaths);
          }

          // 플레이리스트에 최소한 하나의 .ts 파일이 있는지 확인
          if (tsFiles.length === 0) {
            logger.warn(`[${requestId}] No .ts files found in playlist`);
          } else {
            logger.info(`[${requestId}] Found ${tsFiles.length} .ts files in playlist`);
            logger.debug(`[${requestId}] TS files:`, tsFiles);
          }

          // 각 .ts 파일의 경로를 개별적으로 검증
          for (let i = 0; i < tsFiles.length; i++) {
            const tsPath = tsFiles[i];
            logger.debug(`[${requestId}] TS file ${i + 1}: ${tsPath}`);

            // 경로 형식 검증
            if (!tsPath.startsWith('/api/recordings/hls/')) {
              logger.error(`[${requestId}] Invalid TS path format: ${tsPath}`);
            }

            // 중복 경로 검증
            if (tsPath.includes('//api/recordings/hls//')) {
              logger.error(`[${requestId}] Duplicate path detected in TS file: ${tsPath}`);
            }
          }

          // 최종 검증: 중복 경로가 있는지 확인
          const duplicatePaths = tsFiles.filter(path => path.includes('//api/recordings/hls//'));
          if (duplicatePaths.length > 0) {
            logger.error(`[${requestId}] Found duplicate paths in playlist:`, duplicatePaths);
            // 중복 경로 수정 시도
            playlistContent = playlistContent.replace(/\/\/api\/recordings\/hls\/\/api\/recordings\/hls\//g, '/api/recordings/hls/');
            logger.info(`[${requestId}] Attempted to fix duplicate paths`);
          }

          // 최종 검증: 응답 전에 중복 경로가 있는지 한 번 더 확인
          const finalCheck = playlistContent.includes('//api/recordings/hls//');
          if (finalCheck) {
            logger.error(`[${requestId}] Final check: Still has duplicate paths, attempting emergency fix`);
            playlistContent = playlistContent.replace(/\/\/api\/recordings\/hls\/\/api\/recordings\/hls\//g, '/api/recordings/hls/');
            logger.info(`[${requestId}] Emergency fix applied`);
          }

          // 추가 검증: 모든 중복 패턴을 찾아서 수정
          const allDuplicatePatterns = playlistContent.match(/\/\/api\/recordings\/hls\/\/api\/recordings\/hls\//g);
          if (allDuplicatePatterns && allDuplicatePatterns.length > 0) {
            logger.error(`[${requestId}] Found ${allDuplicatePatterns.length} duplicate patterns, applying comprehensive fix`);
            playlistContent = playlistContent.replace(/\/\/api\/recordings\/hls\/\/api\/recordings\/hls\//g, '/api/recordings/hls/');
            logger.info(`[${requestId}] Comprehensive fix applied`);
          }

          // 추가 안전장치: 모든 가능한 중복 패턴을 찾아서 수정
          const allPossibleDuplicates = [
            /\/\/api\/recordings\/hls\/\/api\/recordings\/hls\//g,
            /\/api\/recordings\/hls\/\/api\/recordings\/hls\//g,
            /\/\/api\/recordings\/hls\/api\/recordings\/hls\//g,
            /\/api\/recordings\/hls\/\/api\/recordings\/hls\//g
          ];

          for (const pattern of allPossibleDuplicates) {
            if (playlistContent.match(pattern)) {
              logger.warn(`[${requestId}] Found additional duplicate pattern:`, pattern.source);
              playlistContent = playlistContent.replace(pattern, '/api/recordings/hls/');
            }
          }

          // 수정된 HLS 플레이리스트 스트리밍
          res.setHeader('Content-Type', 'application/vnd.apple.mpegurl');
          res.setHeader('Content-Length', Buffer.byteLength(finalPlaylistContent, 'utf8'));
          res.setHeader('Cache-Control', 'no-cache');
          res.setHeader('Access-Control-Allow-Origin', '*');

          // 최종 플레이리스트 내용 로깅 (디버깅용)
          logger.debug(`[${requestId}] Final playlist content (first 1000 chars):`, finalPlaylistContent.substring(0, 1000));

          // .ts 파일 경로 최종 확인
          const finalTsFiles = finalPlaylistContent.match(/^[^#\n]*\.ts$/gm) || [];
          logger.info(`[${requestId}] Final TS files count: ${finalTsFiles.length}`);
          if (finalTsFiles.length > 0) {
            logger.debug(`[${requestId}] Final TS files:`, finalTsFiles.slice(0, 5)); // 처음 5개만 로깅
          }

          res.send(playlistContent);

          logger.info(`[${requestId}] HLS streaming started with corrected paths: ${videoFile} (${fileSize} bytes)`);
        } catch (hlsError) {
          logger.error(`[${requestId}] HLS streaming error: ${hlsError.message}`);
          return res.status(500).json({ error: 'HLS streaming failed' });
        }
        return;
      }

      // MP4 비디오 스트리밍 처리 (기존 로직)
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

  // HLS 스트리밍 라우트 (최적화)
  app.get('/api/recordings/hls/:id', async (req, res) => {
    const requestId = req.headers['x-request-id'] || 'unknown';
    const id = req.params.id;

    logger.info(`[${requestId}] HLS playlist request for recording ID: ${id}`);

    try {
      // recordingHistory에서 녹화 정보 찾기
      const recording = await RecordingsModel.getRecordingHistoryById(id);

      if (!recording) {
        logger.warn(`[${requestId}] Recording not found in history: ${id}`);
        return res.status(404).json({ error: 'Recording not found' });
      }

      // HLS 파일 경로 생성
      let datePart = '';
      if (recording.startTime instanceof Date) {
        // 한국 시간으로 변환하여 날짜 추출
        const kstDate = moment(recording.startTime).tz('Asia/Seoul');
        datePart = kstDate.format('YYYY-MM-DD');
      } else if (typeof recording.startTime === 'string' && recording.startTime.includes('T')) {
        // ISO 문자열을 한국 시간으로 변환
        const kstDate = moment(recording.startTime).tz('Asia/Seoul');
        datePart = kstDate.format('YYYY-MM-DD');
      } else if (typeof recording.startTime === 'string' && recording.startTime.length >= 10) {
        datePart = recording.startTime.substring(0, 10);
      }

      // HLS 플레이리스트 파일 경로 생성
      const hlsPath = path.join(RECORDINGS_DIR, recording.cameraName, datePart, 'hls');
      let playlistFile = path.join(hlsPath, recording.filename);

      logger.info(`[${requestId}] Searching for HLS files in: ${hlsPath}`);
      logger.info(`[${requestId}] Expected playlist file: ${playlistFile}`);

      // HLS 디렉토리 존재 확인
      if (!fs.existsSync(hlsPath)) {
        logger.error(`[${requestId}] HLS directory not found: ${hlsPath}`);
        return res.status(404).json({ error: 'HLS directory not found' });
      }

      // 파일이 존재하지 않으면 HLS 디렉토리에서 .m3u8 파일을 찾아서 사용
      if (!fs.existsSync(playlistFile)) {
        // logger.warn(`[${requestId}] HLS playlist not found: ${playlistFile}, searching for .m3u8 files...`);

        try {
          // HLS 디렉토리가 존재하는지 확인
          // if (!fs.existsSync(hlsPath)) {
          //   logger.error(`[${requestId}] HLS directory not found: ${hlsPath}`);
          //   return res.status(404).json({ error: 'HLS directory not found' });
          // }

          const hlsFiles = fs.readdirSync(hlsPath);
          const m3u8Files = hlsFiles.filter(file => file.endsWith('.m3u8'));
          const tsFiles = hlsFiles.filter(file => file.endsWith('.ts'));

          logger.info(`[${requestId}] HLS directory contents:`, {
            totalFiles: hlsFiles.length,
            m3u8Files: m3u8Files,
            tsFiles: tsFiles.length,
            allFiles: hlsFiles
          });

          if (m3u8Files.length > 0) {
            // 녹화 시작 시간과 가장 가까운 파일을 찾기
            let bestMatch = null;
            let bestTimeDiff = Infinity;

            const recordingStartTime = new Date(recording.startTime);

            for (const m3u8File of m3u8Files) {
              // 파일명에서 시간 추출 (예: 댐영상2_2025-07-09T14-33-11.m3u8)
              const timeMatch = m3u8File.match(/(\d{4}-\d{2}-\d{2}T\d{2}-\d{2}-\d{2})/);
              if (timeMatch) {
                const fileTimeStr = timeMatch[1].replace(/-/g, ':').replace('T', ' ');
                const fileTime = new Date(fileTimeStr);
                const timeDiff = Math.abs(fileTime.getTime() - recordingStartTime.getTime());

                if (timeDiff < bestTimeDiff) {
                  bestTimeDiff = timeDiff;
                  bestMatch = m3u8File;
                }
              }
            }

            if (bestMatch) {
              playlistFile = path.join(hlsPath, bestMatch);
              logger.info(`[${requestId}] Using best matching HLS playlist: ${bestMatch} (time diff: ${bestTimeDiff}ms)`);
            } else {
              // 시간 매칭이 안되면 가장 최근 파일 사용
              m3u8Files.sort().reverse();
              const actualFilename = m3u8Files[0];
              playlistFile = path.join(hlsPath, actualFilename);
              logger.info(`[${requestId}] Using most recent HLS playlist: ${actualFilename}`);
            }
          } else {
            logger.error(`[${requestId}] No .m3u8 files found in HLS directory: ${hlsPath}`);
            return res.status(404).json({ error: 'No HLS playlist files found' });
          }
        } catch (error) {
          logger.error(`[${requestId}] Error searching for HLS files: ${error.message}`);
          return res.status(404).json({ error: 'HLS directory not accessible' });
        }
      }

      // 플레이리스트 파일 존재 확인
      if (!fs.existsSync(playlistFile)) {
        logger.error(`[${requestId}] Final playlist file not found: ${playlistFile}`);
        return res.status(404).json({
          error: 'HLS playlist file not found',
          message: `Playlist file not found: ${playlistFile}`,
          requestId: requestId,
          recordingId: id
        });
      }

      // M3U8 파일을 읽어서 세그먼트 경로를 API 엔드포인트로 변경
      const playlistContent = fs.readFileSync(playlistFile, 'utf8');

      // M3U8 파일 형식 검증
      if (!playlistContent.trim().startsWith('#EXTM3U')) {
        logger.error(`[${requestId}] Invalid M3U8 file format: ${playlistFile}`);
        logger.error(`[${requestId}] File content preview: ${playlistContent.substring(0, 200)}`);
        return res.status(400).json({ error: 'Invalid M3U8 file format' });
      }

      // 세그먼트 파일 경로를 API 엔드포인트로 변경
      const modifiedPlaylist = playlistContent.replace(
        /([^\/\n]+\.ts)/g,
        `/api/recordings/hls/${recording.cameraName}/${datePart}/$1`
      );

      logger.info(`[${requestId}] M3U8 playlist processed successfully, segments found: ${(modifiedPlaylist.match(/\.ts/g) || []).length}`);

      const modifiedContent = Buffer.from(modifiedPlaylist, 'utf8');
      const fileSize = modifiedContent.length;
      const range = req.headers.range;

      if (range) {
        const parts = range.replace(/bytes=/, '').split('-');
        const start = parseInt(parts[0], 10);
        const end = parts[1] ? parseInt(parts[1], 10) : fileSize - 1;
        const chunksize = end - start + 1;
        const head = {
          'Content-Range': `bytes ${start}-${end}/${fileSize}`,
          'Accept-Ranges': 'bytes',
          'Content-Length': chunksize,
          'Content-Type': 'application/vnd.apple.mpegurl',
        };

        res.writeHead(206, head);
        res.end(modifiedContent.slice(start, end + 1));
      } else {
        const head = {
          'Content-Length': fileSize,
          'Content-Type': 'application/vnd.apple.mpegurl',
          'Cache-Control': 'no-cache, no-store, must-revalidate',
          'Pragma': 'no-cache',
          'Expires': '0',
        };
        res.writeHead(200, head);
        res.end(modifiedContent);
      }
    } catch (error) {
      logger.error(`[${requestId}] Error streaming HLS: ${error.message}`, {
        error: error.stack,
        recordingId: id,
        requestUrl: req.url,
        userAgent: req.headers['user-agent']
      });
      res.status(500).json({
        error: 'Error streaming HLS',
        message: error.message,
        requestId: requestId
      });
    }
  });

  // HLS 세그먼트 파일 스트리밍 라우트 (카메라명/날짜 기반 - 실제 파일 구조와 일치)
  app.get('/api/recordings/hls/:cameraName/:date/:segment', async (req, res) => {
    const requestId = req.headers['x-request-id'] || 'unknown';
    const { cameraName, date, segment } = req.params;

    logger.info(`[${requestId}] HLS segment request for camera: ${cameraName}, date: ${date}, segment: ${segment}`);

    try {
      // 파일명 검증 (보안)
      if (segment.includes('..') || segment.includes('/') || segment.includes('\\')) {
        logger.warn(`[${requestId}] Invalid segment filename: ${segment}`);
        return res.status(400).json({ error: 'Invalid segment filename' });
      }

      // HLS 세그먼트 파일 경로 생성
      const hlsPath = path.join(RECORDINGS_DIR, cameraName, date, 'hls');
      const segmentFile = path.join(hlsPath, segment);

      // 세그먼트 파일 존재 확인
      if (!fs.existsSync(segmentFile)) {
        logger.warn(`[${requestId}] HLS segment not found: ${segmentFile}`);
        return res.status(404).json({ error: 'HLS segment file not found' });
      }

      // TS 파일 스트리밍
      const stat = fs.statSync(segmentFile);
      const fileSize = stat.size;
      const range = req.headers.range;

      if (range) {
        const parts = range.replace(/bytes=/, '').split('-');
        const start = parseInt(parts[0], 10);
        const end = parts[1] ? parseInt(parts[1], 10) : fileSize - 1;
        const chunksize = end - start + 1;
        const file = fs.createReadStream(segmentFile, { start, end });
        const head = {
          'Content-Range': `bytes ${start}-${end}/${fileSize}`,
          'Accept-Ranges': 'bytes',
          'Content-Length': chunksize,
          'Content-Type': 'video/mp2t',
        };

        res.writeHead(206, head);
        file.pipe(res);
      } else {
        const head = {
          'Content-Length': fileSize,
          'Content-Type': 'video/mp2t',
          'Cache-Control': 'public, max-age=3600', // 1시간 캐시 (HLS 세그먼트용)
          'Accept-Ranges': 'bytes',
        };
        res.writeHead(200, head);
        fs.createReadStream(segmentFile).pipe(res);
      }

      logger.debug(`[${requestId}] HLS segment streaming: ${segment} (${fileSize} bytes)`);
    } catch (error) {
      logger.error(`[${requestId}] Error streaming HLS segment: ${error.message}`, {
        error: error.stack,
        cameraName,
        date,
        segment,
        requestUrl: req.url,
        userAgent: req.headers['user-agent']
      });
      res.status(500).json({
        error: 'Error streaming HLS segment',
        message: error.message,
        requestId: requestId
      });
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

  // 녹화 기록 조회 라우트 (MP4 segment 파일 기반)
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

      // MP4 파일 경로로 변환하여 반환
      const processedRecordings = recordings.map(record => {
        const data = record.dataValues || record;
        return {
          ...data,
          id: data.id || '',
          cameraName: data.cameraName || data.camera_name || 'Unknown Camera',
          filename: data.filename || data.file_path || 'Unknown File',
          startTime: data.startTime || data.start_time || new Date().toISOString(),
          endTime: data.endTime || data.end_time || null,
          status: data.status || 'completed',
          // MP4 파일 경로 정보 추가
          filePath: data.filename || data.file_path,
          fileType: 'mp4'
        };
      });

      res.status(200).send(processedRecordings);
    } catch (error) {
      logger.error(`Error fetching recording history: ${error.message}`);
      res.status(500).send({
        statusCode: 500,
        message: error.message,
      });
    }
  });

  // 특정 날짜의 모든 MP4 segment 파일 목록 조회 API
  app.get('/api/recordings/segments', async (req, res) => {
    try {
      const { date, file_path } = req.query;

      if (!date) {
        return res.status(400).json({ error: 'Date parameter is required' });
      }

      // 날짜 범위 설정 (선택된 날짜의 시작부터 끝까지)
      const startDate = new Date(date);
      startDate.setHours(0, 0, 0, 0);
      const endDate = new Date(date);
      endDate.setHours(23, 59, 59, 999);

      // 전체 카메라의 녹화 기록 조회 (카메라 ID 제한 없음)
      const recordings = await RecordingsModel.getRecordingHistoryByDateRange(startDate, endDate);

      // MP4 segment 파일 정보로 변환
      const segmentFiles = recordings.map(record => {
        const data = record.dataValues || record;

        // DB에서 실제 파일명을 가져오기 (file_path 파라미터는 검색용으로만 사용)
        // 모델에서 filename은 실제로 file_path DB 컬럼에 매핑됨
        const fullFilePath = data.filename || 'Unknown File';

        // 전체 경로에서 파일명만 추출 (예: ./outputs/nvr/recordings/camera1/2025-09-02/segment_000.mp4 -> segment_000.mp4)
        const actualFilename = fullFilePath.split('/').pop() || fullFilePath;
        const actualFilePath = fullFilePath;

        // 디버깅을 위한 로그
        console.log('Processing record:', {
          id: data.id,
          cameraName: data.cameraName || data.camera_name,
          fullFilePath: fullFilePath,
          actualFilename: actualFilename
        });

        return {
          id: data.id,
          cameraId: data.fk_camera_id,
          cameraName: data.cameraName || data.camera_name || 'Unknown Camera',
          filename: actualFilename, // DB의 실제 파일명 사용
          startTime: data.startTime || data.start_time,
          endTime: data.endTime || data.end_time,
          duration: data.duration || 0,
          fileSize: data.fileSize || data.file_size || 0,
          status: data.status || 'completed',
          filePath: actualFilePath, // 실제 파일 경로
          // 상대 경로로 반환하여 클라이언트의 프록시를 통해 접근하도록 함
          streamUrl: `/api/recordings/stream/${data.id}`,
          fileType: 'mp4'
        };
      });

      // 시작 시간순으로 정렬
      segmentFiles.sort((a, b) => new Date(a.startTime) - new Date(b.startTime));

      res.status(200).json({
        date: date,
        totalSegments: segmentFiles.length,
        segments: segmentFiles
      });

    } catch (error) {
      logger.error(`Error fetching MP4 segments: ${error.message}`);
      res.status(500).json({
        error: 'Failed to fetch MP4 segments',
        message: error.message
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
  // 레코딩 상태 조회 API는 Python으로 이동됨 - 제거
  // app.get('/api/recordings/status/:cameraName', ...)

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
  // 레코딩 상태 조회 API는 Python으로 이동됨 - 제거
  // app.get('/api/recordings/active', ...)

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
  // 레코딩 시작 API는 Python으로 이동됨 - 제거
  // app.post('/api/recordings', ...)

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

    if (videoFile) {
      return path.join(videoPath, videoFile);
    }

    // 파일을 찾지 못한 경우, 파일명만 추출하여 다시 검색
    const pathParts = filename.split('/');
    const shortFilename = pathParts[pathParts.length - 1];

    if (shortFilename !== filename) {
      const shortVideoFile = files.find(file => file === shortFilename);
      if (shortVideoFile) {
        return path.join(videoPath, shortVideoFile);
      }
    }

    return null;
  } catch (error) {
    logger.error(`Error finding video file for filename ${filename}:`, error);
    return null;
  }
}

// Helper function to generate thumbnail to buffer
async function generateThumbnailToBuffer(videoPath) {
  return new Promise((resolve, reject) => {
    const ffmpeg = spawn('ffmpeg', [
      '-loglevel', 'error',  // error만 출력하여 진행 상황 로그 억제
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
      '-loglevel', 'error',  // error만 출력하여 진행 상황 로그 억제
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

