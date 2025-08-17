import { spawn } from 'child_process';
import path from 'path';
import fs from 'fs-extra';
import moment from 'moment-timezone';
import Database from '../../api/database.js';
import LoggerService from '../logger/logger.service.js';
import ConfigService from '../config/config.service.js';
import { nanoid } from 'nanoid';
import ScheduleModel from '../../models/schedule.js';
import RecordingHistoryModel from '../../models/RecordingHistory.js';
import sequelize from '../../models/index.js';
import { Op } from 'sequelize';
const Schedule = ScheduleModel(sequelize);
const RecordingHistory = RecordingHistoryModel(sequelize);

const logger = new LoggerService('RecordingProcess');

class RecordingProcess {
  constructor() {
    this.activeRecordings = new Map(); // key: `${cameraName}_${scheduleId}`
    this.checkInterval = null;
    this.recordingsPath = ConfigService.recordingsPath;
    this.lastRetryTimes = new Map();
  }

  isTimeInRange(currentTime, startTime, endTime) {
    const [currentHour, currentMinute] = currentTime.split(':');
    const [startHour, startMinute] = startTime.split(':');
    const [endHour, endMinute] = endTime.split(':');

    const current = parseInt(currentHour) * 60 + parseInt(currentMinute);
    const start = parseInt(startHour) * 60 + parseInt(startMinute);
    const end = parseInt(endHour) * 60 + parseInt(endMinute);

    return current >= start && current < end;
  }

  async getCurrentlyActiveSchedules() {
    try {
      const schedules = await Schedule.findAll({
        where: {
          isActive: true
        }
      });

      const now = new Date();
      const currentDay = now.getDay();
      const currentTime = now.toLocaleTimeString('en-US', {
        hour12: false,
        hour: '2-digit',
        minute: '2-digit'
      });

      // 오늘 날짜의 녹화 히스토리 확인 (LIKE → 범위 조건)
      const today = moment().tz('Asia/Seoul').startOf('day');
      const tomorrow = moment(today).add(1, 'days');
      const recordingHistory = await RecordingHistory.findAll({
        where: {
          startTime: {
            [Op.gte]: today.toDate(),
            [Op.lt]: tomorrow.toDate()
          },
          status: {
            [Op.in]: ['completed', 'stopped']
          }
        }
      });

      return schedules.filter(schedule => {
        // 기본 스케줄 조건 확인
        const isScheduleActive = schedule.isActive &&
          schedule.days_of_week.includes(currentDay) &&
          this.isTimeInRange(currentTime, schedule.start_time, schedule.end_time);

        if (!isScheduleActive) return false;

        // 이미 완료된 녹화가 있는지 확인 (진행중인 녹화는 제외)
        const hasCompletedRecording = recordingHistory.some(record =>
          record.scheduleId === schedule.id &&
          record.cameraName === schedule.cameraName &&
          (record.status === 'completed' || record.status === 'stopped')
        );

        // 활성화된 스케줄이지만 이미 완료된 녹화가 있으면 제외
        return !hasCompletedRecording;
      });
    } catch (error) {
      logger.error('Error getting active schedules:', error);
      return [];
    }
  }

  async addRecordingHistory(scheduleId, cameraName, timeInfo, filename, fk_camera_id) {
    try {
      // 동일한 파일명으로 진행 중인 녹화가 있는지 확인
      const existingRecordings = await RecordingHistory.findAll({
        where: {
          [Op.or]: [
            { filename: filename },
            {
              scheduleId: scheduleId,
              cameraName: cameraName,
              fk_camera_id: fk_camera_id,
              status: 'recording'
            }
          ]
        }
      });

      // 기존 녹화들의 상태를 'stopped'로 업데이트
      for (const existing of existingRecordings) {
        logger.info(`Marking existing recording as stopped: ${existing.id}`);
        await existing.update({
          status: 'stopped',
          endTime: timeInfo.formattedForDB,
          updatedAt: timeInfo.formattedForDB
        });
      }

      const newRecord = {
        scheduleId,
        cameraName,
        filename,
        startTime: timeInfo.formattedForDB,
        endTime: null,
        status: 'recording',
        createdAt: timeInfo.formattedForDB,
        fk_camera_id: fk_camera_id
      };
      logger.info('newRecord', newRecord);
      // 새 녹화 추가
      const createdRecord = await RecordingHistory.create(newRecord);

      logger.info('Recording history updated:', {
        newRecordId: createdRecord.id,
        stoppedRecords: existingRecordings.map(r => r.id),
        filename,
        cameraName
      });

      return createdRecord.id;
    } catch (error) {
      logger.error('Error in addRecordingHistory:', error);
      throw error;
    }
  }

  async updateRecordingHistory(recordingId, updates) {
    try {
      const currentRecord = await RecordingHistory.findByPk(recordingId);

      if (!currentRecord) {
        logger.warn(`Recording history not found for ID: ${recordingId}`);
        return;
      }

      // 이미 종료된 녹화는 업데이트하지 않음
      if (['completed', 'stopped', 'error'].includes(currentRecord.status) && updates.status === 'recording') {
        logger.warn(`Skipping update for already finished recording: ${recordingId}`);
        return;
      }

      const updatedRecord = {
        ...updates,
        updatedAt: moment().tz('Asia/Seoul').format('YYYY-MM-DD HH:mm:ss')
      };

      await currentRecord.update(updatedRecord);

      logger.info('Recording history updated:', {
        id: recordingId,
        previousStatus: currentRecord.status,
        newStatus: updates.status,
        updates
      });
    } catch (error) {
      logger.error('Error in updateRecordingHistory:', error);
    }
  }

  async startRecording(cameraName, scheduleId, source, fk_camera_id, recoding_bitrate = '1024k') {
    // HLS 레코딩 설정 확인
    const hlsConfig = ConfigService.recordings?.hls;
    logger.info(`=== Recording Config Debug ===`);
    logger.info(`ConfigService.recordings:`, ConfigService.recordings);
    logger.info(`HLS Config Check - enabled: ${hlsConfig?.enabled}, segmentDuration: ${hlsConfig?.segmentDuration}, maxSegments: ${hlsConfig?.maxSegments}`);
    logger.info(`Full HLS config:`, JSON.stringify(hlsConfig, null, 2));
    logger.info(`=============================`);

    if (hlsConfig?.enabled) {
      logger.info(`Starting HLS recording for camera: ${cameraName}`);
      return this.startHLSRecording(cameraName, scheduleId, source, fk_camera_id, recoding_bitrate);
    }

    logger.info(`Starting MP4 recording for camera: ${cameraName}`);
    // 기존 MP4 레코딩 로직
    const recordingKey = `${cameraName}_${scheduleId}`;
    let recordingId = null;

    try {
      // 이미 녹화 중인지 확인
      const existingRecording = this.activeRecordings.get(recordingKey);
      if (existingRecording) {
        if (existingRecording.process && !existingRecording.process.killed) {
          logger.debug(`Recording already in progress for schedule: ${recordingKey}, skipping...`);
          return;
        }
      }

      // 시간 정보 생성 (한국 시간 기준)
      const nowMoment = moment().tz('Asia/Seoul');
      const timeInfo = {
        timestamp: nowMoment.unix(),
        formattedForFile: nowMoment.format('YYYY-MM-DDTHH-mm-ss'),
        formattedForDisplay: nowMoment.format('YYYY-MM-DDTHH:mm:ss'),
        dateString: nowMoment.format('YYYY-MM-DD'),
        formattedForDB: nowMoment.format('YYYY-MM-DD HH:mm:ss')
      };

      // 녹화 디렉토리 생성
      const recordingDir = path.join(
        this.recordingsPath,
        cameraName,
        timeInfo.dateString
      );
      await fs.ensureDir(recordingDir);

      // 파일명 생성
      const filename = `${cameraName}_${timeInfo.formattedForFile}.mp4`;
      const outputPath = path.join(recordingDir, filename);

      // HLS 세그먼트 파일명 패턴 (1시간 단위)
      const segmentPattern = `${cameraName}_${timeInfo.formattedForFile}_%02d.ts`;
      const playlistName = `${cameraName}_${timeInfo.formattedForFile}.m3u8`;
      const segmentPath = path.join(recordingDir, segmentPattern);
      const playlistPath = path.join(recordingDir, playlistName);

      // 기존 파일 확인 및 제거
      if (await fs.pathExists(outputPath)) {
        try {
          await fs.unlink(outputPath);
          logger.info(`Removed existing recording file: ${outputPath}`);
        } catch (err) {
          logger.error(`Failed to remove existing recording file: ${err.message}`);
        }
      }

      // recordingHistory에 추가 - 한 번만 수행
      try {
        recordingId = await this.addRecordingHistory(scheduleId, cameraName, timeInfo, filename, fk_camera_id);
      } catch (error) {
        logger.error('Failed to add recording history:', error);
        return;
      }

      // source URL에서 -i 옵션 제거
      let rtspUrl = source;
      if (rtspUrl.includes('-i')) {
        rtspUrl = rtspUrl.replace(/-i\s+/, '').trim();
      }

      // FFMPEG 프로세스 시작
      const ffmpeg = spawn('ffmpeg', [
        '-y',
        '-rtsp_transport', 'tcp',
        '-i', rtspUrl,
        '-c:v', 'libx264',
        '-preset', 'ultrafast',
        '-tune', 'zerolatency',
        '-profile:v', 'baseline',
        '-level', '3.0',
        '-pix_fmt', 'yuv420p',
        '-r', '30',
        '-g', '15',
        '-keyint_min', '15',
        '-force_key_frames', 'expr:gte(t,n_forced*1)',
        '-b:v', recoding_bitrate,
        '-maxrate', recoding_bitrate,
        '-bufsize', recoding_bitrate,
        '-c:a', 'aac',
        '-b:a', '128k',
        '-ar', '44100',
        '-strict', '-2',
        '-f', 'mp4',
        '-movflags', '+faststart+frag_keyframe+empty_moov+default_base_moof',
        '-reset_timestamps', '1',
        '-loglevel', 'error',
        '-reconnect', '1',
        '-reconnect_at_eof', '1',
        '-reconnect_streamed', '1',
        '-reconnect_delay_max', '5',
        outputPath
      ], {
        windowsHide: true,
        windowsVerbatimArguments: true,
        env: { ...process.env, FFREPORT: `file=${recordingDir}/ffmpeg-${recordingKey}.log:level=32` }
      });

      // console.log('=====> ffmpeg', ffmpeg);
      let hasError = false;
      let errorMessage = '';

      // FFMPEG 에러 로그 처리
      ffmpeg.stderr.on('data', (data) => {
        const message = data.toString();

        // 타임스탬프 관련 경고 메시지 필터링
        if (message.includes('Non-monotonic DTS') ||
          message.includes('changing to') ||
          message.includes('This may result in incorrect timestamps')) {
          return; // 이 메시지들은 무시
        }

        logger.debug(`FFMPEG [${recordingKey}]: ${message}`);

        // 주요 에러 체크
        if (message.includes('Connection refused') ||
          message.includes('Connection timed out') ||
          message.includes('Invalid data found') ||
          message.includes('Error opening input') ||
          message.includes('Broken pipe') ||
          message.includes('End of file')) {
          hasError = true;
          errorMessage = message;
          logger.error(`FFMPEG Error for schedule ${recordingKey}:`, message);
        }
      });

      // 프로세스 종료 처리
      ffmpeg.on('close', async (code) => {
        logger.info(`Recording stopped for schedule: ${recordingKey}, exit code: ${code}`);

        // 파일 크기 확인
        try {
          const stats = await fs.stat(outputPath);
          if (stats.size === 0) {
            logger.error(`Empty recording file detected for schedule: ${recordingKey}`);
            await fs.unlink(outputPath);
            // 녹화 히스토리 업데이트 - 에러 상태로
            if (recordingId) {
              await this.updateRecordingHistory(recordingId, {
                endTime: moment().tz('Asia/Seoul').format('YYYY-MM-DDTHH:mm:ss'),
                status: 'error',
                errorMessage: 'Empty recording file'
              });
            }
          } else {
            // 정상 종료 시 녹화 히스토리 업데이트
            if (recordingId) {
              await this.updateRecordingHistory(recordingId, {
                endTime: moment().tz('Asia/Seoul').format('YYYY-MM-DDTHH:mm:ss'),
                status: hasError ? 'error' : 'completed',
                errorMessage: hasError ? errorMessage : undefined
              });
            }
          }
        } catch (err) {
          logger.error(`Error checking recording file: ${err.message}`);
          if (recordingId) {
            await this.updateRecordingHistory(recordingId, {
              endTime: moment().tz('Asia/Seoul').format('YYYY-MM-DDTHH:mm:ss'),
              status: 'error',
              errorMessage: err.message
            });
          }
        }

        this.activeRecordings.delete(recordingKey);

        // 비정상 종료 시 재시도
        if (code !== 0 && !hasError) {
          const lastRetryTime = this.lastRetryTimes.get(recordingKey) || 0;
          const now = Date.now();
          if (now - lastRetryTime > 60000) {
            logger.warn(`Abnormal exit for schedule ${recordingKey}, attempting to restart...`);
            this.lastRetryTimes.set(recordingKey, now);
            // 재시도 시에는 새로운 recordingHistory 생성
            // setTimeout(() => {
            //   this.startRecording(cameraName, scheduleId, source, fk_camera_id);
            // }, 5000);
          } else {
            logger.warn(`Skipping retry for ${recordingKey} due to frequent failures`);
          }
        }
      });

      // 프로세스 에러 처리
      ffmpeg.on('error', async (err) => {
        logger.error(`FFMPEG process error for schedule ${recordingKey}:`, err);
        hasError = true;
        if (recordingId) {
          await this.updateRecordingHistory(recordingId, {
            status: 'error',
            errorMessage: err.message
          });
        }
      });

      // 녹화 정보 저장
      const recordingInfo = {
        recordingId,
        cameraName,
        scheduleId,
        process: ffmpeg,
        timeInfo,
        outputPath,
        hasError: false,
        pid: ffmpeg.pid,
        startTime: Date.now()
      };

      this.activeRecordings.set(recordingKey, recordingInfo);
      // logger.info(`====> this.activeRecordings: ${Array.from(this.activeRecordings.entries())}`);
      // 녹화 메타데이터 저장
      const metadataPath = path.join(recordingDir, `${filename}.json`);
      await fs.writeJson(metadataPath, {
        recordingId,
        scheduleId,
        cameraName,
        startTime: timeInfo.formattedForFile,
        filename,
        outputPath,
        rtspUrl,
        status: 'recording'
      });

    } catch (error) {
      logger.error(`Failed to start recording for schedule: ${recordingKey}`, error);
      // 시작 실패 시 히스토리 업데이트
      if (recordingId) {
        await this.updateRecordingHistory(recordingId, {
          endTime: moment().tz('Asia/Seoul').format('YYYY-MM-DDTHH:mm:ss'),
          status: 'error',
          errorMessage: error.message
        });
      }
      this.activeRecordings.delete(recordingKey);
    }
  }

  async startHLSRecording(cameraName, scheduleId, source, fk_camera_id, recoding_bitrate = '1024k') {
    const recordingKey = `${cameraName}_${scheduleId}`;
    let recordingId = null;

    try {
      // 이미 녹화 중인지 확인
      const existingRecording = this.activeRecordings.get(recordingKey);
      if (existingRecording) {
        if (existingRecording.process && !existingRecording.process.killed) {
          logger.debug(`HLS Recording already in progress for schedule: ${recordingKey}, skipping...`);
          return;
        }
      }

      // 시간 정보 생성 (한국 시간 기준)
      const nowMoment = moment().tz('Asia/Seoul');
      const timeInfo = {
        timestamp: nowMoment.unix(),
        formattedForFile: nowMoment.format('YYYY-MM-DDTHH-mm-ss'),
        formattedForDisplay: nowMoment.format('YYYY-MM-DDTHH:mm:ss'),
        dateString: nowMoment.format('YYYY-MM-DD'),
        formattedForDB: nowMoment.format('YYYY-MM-DD HH:mm:ss')
      };

      // HLS 녹화 디렉토리 생성
      const recordingDir = path.join(
        this.recordingsPath,
        cameraName,
        timeInfo.dateString,
        'hls'
      );
      await fs.ensureDir(recordingDir);

      // HLS 세그먼트 파일명 패턴 (1시간 단위)
      const segmentPattern = `${cameraName}_${timeInfo.formattedForFile}_%02d.ts`;
      const playlistName = `${cameraName}_${timeInfo.formattedForFile}.m3u8`;
      const segmentPath = path.join(recordingDir, segmentPattern);
      const playlistPath = path.join(recordingDir, playlistName);

      // recordingHistory에 추가
      try {
        recordingId = await this.addRecordingHistory(scheduleId, cameraName, timeInfo, playlistName, fk_camera_id);
      } catch (error) {
        logger.error('Failed to add HLS recording history:', error);
        return;
      }

      // source URL에서 -i 옵션 제거
      let rtspUrl = source;
      if (rtspUrl.includes('-i')) {
        rtspUrl = rtspUrl.replace(/-i\s+/, '').trim();
      }

      // HLS FFMPEG 프로세스 시작 (설정값 기반)
      const hlsConfig = ConfigService.recordings?.hls;
      const ffmpeg = spawn('ffmpeg', [
        '-y',
        '-rtsp_transport', 'tcp',
        '-i', rtspUrl,
        '-c:v', 'libx264',
        '-preset', 'ultrafast',
        '-tune', 'zerolatency',
        '-profile:v', 'baseline',
        '-level', '3.0',
        '-pix_fmt', 'yuv420p',
        '-r', '30',
        '-g', '30',
        '-keyint_min', '30',
        '-force_key_frames', 'expr:gte(t,n_forced*1)',
        '-b:v', recoding_bitrate,
        '-maxrate', recoding_bitrate,
        '-bufsize', recoding_bitrate,
        '-c:a', 'aac',
        '-b:a', '128k',
        '-ar', '44100',
        '-strict', '-2',
        // HLS 세그먼트 설정 (설정값 기반)
        '-f', 'hls',
        '-hls_time', (hlsConfig?.segmentDuration || 30).toString(),
        '-hls_list_size', '0',  // 모든 세그먼트 유지 (0 = 무제한)
        '-hls_segment_filename', segmentPath,
        '-hls_flags', 'append_list',  // delete_segments 제거하여 세그먼트 보존
        '-hls_allow_cache', '0',
        '-loglevel', 'error',
        '-reconnect', '1',
        '-reconnect_at_eof', '1',
        '-reconnect_streamed', '1',
        '-reconnect_delay_max', '5',
        playlistPath
      ], {
        windowsHide: true,
        windowsVerbatimArguments: true,
        env: { ...process.env, FFREPORT: `file=${recordingDir}/ffmpeg-${recordingKey}.log:level=32` }
      });

      let hasError = false;
      let errorMessage = '';

      // FFMPEG 에러 로그 처리
      ffmpeg.stderr.on('data', (data) => {
        const message = data.toString();

        // 타임스탬프 관련 경고 메시지 필터링
        if (message.includes('Non-monotonic DTS') ||
          message.includes('changing to') ||
          message.includes('This may result in incorrect timestamps')) {
          return; // 이 메시지들은 무시
        }

        logger.debug(`FFMPEG HLS [${recordingKey}]: ${message}`);

        // 주요 에러 체크
        if (message.includes('Connection refused') ||
          message.includes('Connection timed out') ||
          message.includes('Invalid data found') ||
          message.includes('Error opening input') ||
          message.includes('Broken pipe') ||
          message.includes('End of file')) {
          hasError = true;
          errorMessage = message;
          logger.error(`FFMPEG HLS Error for schedule ${recordingKey}:`, message);
        }
      });

      // 프로세스 종료 처리
      ffmpeg.on('close', async (code) => {
        logger.info(`HLS Recording stopped for schedule: ${recordingKey}, exit code: ${code}`);

        // 플레이리스트 파일 존재 확인
        try {
          const stats = await fs.stat(playlistPath);
          if (stats.size === 0) {
            logger.error(`Empty HLS playlist detected for schedule: ${recordingKey}`);
            await fs.unlink(playlistPath);
            // 녹화 히스토리 업데이트 - 에러 상태로
            if (recordingId) {
              await this.updateRecordingHistory(recordingId, {
                endTime: moment().tz('Asia/Seoul').format('YYYY-MM-DDTHH:mm:ss'),
                status: 'error',
                errorMessage: 'Empty HLS playlist'
              });
            }
          } else {
            // 정상 종료 시 녹화 히스토리 업데이트
            if (recordingId) {
              await this.updateRecordingHistory(recordingId, {
                endTime: moment().tz('Asia/Seoul').format('YYYY-MM-DDTHH:mm:ss'),
                status: hasError ? 'error' : 'completed',
                errorMessage: hasError ? errorMessage : undefined
              });
            }

            // HLS 녹화 완료 후 세그먼트 정리 수행
            const recordingInfo = this.activeRecordings.get(recordingKey);
            if (!hasError && recordingInfo?.hlsConfig?.autoCleanup) {
              try {
                const maxSegments = recordingInfo.hlsConfig?.maxSegments || 2880;
                await this.cleanupHLSSegments(cameraName, recordingInfo.timeInfo.dateString, maxSegments);
                logger.info(`HLS cleanup completed for ${recordingKey}, max segments: ${maxSegments}`);
              } catch (cleanupError) {
                logger.error(`HLS cleanup failed for ${recordingKey}:`, cleanupError);
              }
            }
          }
        } catch (err) {
          logger.error(`Error checking HLS playlist: ${err.message}`);
          if (recordingId) {
            await this.updateRecordingHistory(recordingId, {
              endTime: moment().tz('Asia/Seoul').format('YYYY-MM-DDTHH:mm:ss'),
              status: 'error',
              errorMessage: err.message
            });
          }
        }

        this.activeRecordings.delete(recordingKey);

        // 비정상 종료 시 재시도
        if (code !== 0 && !hasError) {
          const lastRetryTime = this.lastRetryTimes.get(recordingKey) || 0;
          const now = Date.now();
          if (now - lastRetryTime > 60000) {
            logger.warn(`Abnormal exit for HLS schedule ${recordingKey}, attempting to restart...`);
            this.lastRetryTimes.set(recordingKey, now);
          } else {
            logger.warn(`Skipping retry for ${recordingKey} due to frequent failures`);
          }
        }
      });

      // 프로세스 에러 처리
      ffmpeg.on('error', async (err) => {
        logger.error(`FFMPEG HLS process error for schedule ${recordingKey}:`, err);
        hasError = true;
        if (recordingId) {
          await this.updateRecordingHistory(recordingId, {
            status: 'error',
            errorMessage: err.message
          });
        }
      });

      // 녹화 정보 저장
      const recordingInfo = {
        recordingId,
        cameraName,
        scheduleId,
        process: ffmpeg,
        timeInfo,
        outputPath: playlistPath,
        segmentDir: recordingDir,
        hasError: false,
        pid: ffmpeg.pid,
        startTime: Date.now(),
        isHLS: true,
        hlsConfig
      };

      this.activeRecordings.set(recordingKey, recordingInfo);

      // 녹화 메타데이터 저장
      const metadataPath = path.join(recordingDir, `${playlistName}.json`);
      await fs.writeJson(metadataPath, {
        recordingId,
        scheduleId,
        cameraName,
        startTime: timeInfo.formattedForFile,
        filename: playlistName,
        outputPath: playlistPath,
        segmentDir: recordingDir,
        rtspUrl,
        status: 'recording',
        isHLS: true,
        segmentDuration: (hlsConfig?.segmentDuration || 30),   // 30초
        maxSegments: (hlsConfig?.maxSegments || 2880)
      });

    } catch (error) {
      logger.error(`Failed to start HLS recording for schedule: ${recordingKey}`, error);
      // 시작 실패 시 히스토리 업데이트
      if (recordingId) {
        await this.updateRecordingHistory(recordingId, {
          status: 'error',
          errorMessage: error.message
        });
      }
    }
  }

  async stopRecording(cameraName, scheduleId) {
    try {
      const recordingKey = `${cameraName}_${scheduleId}`;
      const recordingInfo = this.activeRecordings.get(recordingKey);
      if (!recordingInfo) {
        return;
      }

      // FFMPEG 프로세스 종료
      if (recordingInfo.process && !recordingInfo.process.killed) {
        try {
          recordingInfo.process.kill('SIGTERM');
          // 5초 후에도 종료되지 않으면 강제 종료
          setTimeout(() => {
            try {
              if (!recordingInfo.process.killed) {
                recordingInfo.process.kill('SIGKILL');
              }
            } catch (e) {
              logger.debug(`Process already terminated: ${e.message}`);
            }
          }, 5000);
        } catch (e) {
          logger.error(`Error killing process: ${e.message}`);
        }
      }

      // recordingHistory 업데이트
      if (recordingInfo.recordingId) {
        const endTime = moment().tz('Asia/Seoul').format('YYYY-MM-DDTHH:mm:ss');
        await this.updateRecordingHistory(recordingInfo.recordingId, {
          endTime,
          status: recordingInfo.hasError ? 'error' : 'stopped'
        });
      }

      // 메타데이터 업데이트
      const metadataPath = `${recordingInfo.outputPath}.json`;
      if (await fs.pathExists(metadataPath)) {
        const metadata = await fs.readJson(metadataPath);
        metadata.endTime = moment().tz('Asia/Seoul').format('YYYY-MM-DDTHH:mm:ss');
        metadata.status = recordingInfo.hasError ? 'error' : 'stopped';
        await fs.writeJson(metadataPath, metadata);
      }

      this.activeRecordings.delete(recordingKey);
      logger.info(`Stopped recording for schedule: ${recordingKey}`);

    } catch (error) {
      logger.error(`Failed to stop recording for schedule: ${cameraName}_${scheduleId}`, error);
      this.activeRecordings.delete(`${cameraName}_${scheduleId}`);
    }
  }

  async checkAndUpdateRecordings() {
    try {
      const activeSchedules = await this.getCurrentlyActiveSchedules();
      // console.log('====> activeSchedules', activeSchedules);
      // 현재 활성화된 스케줄의 카메라와 스케줄ID를 맵으로 관리
      const activeScheduleMap = new Map();
      activeSchedules.forEach(schedule => {
        const scheduleKey = `${schedule.cameraName}_${schedule.id}`;
        activeScheduleMap.set(scheduleKey, schedule);
      });

      // console.log('this.activeRecordings:', Object.fromEntries(this.activeRecordings));
      // 현재 녹화 중인 프로세스 확인 및 중지
      for (const [recordingKey, recordingInfo] of this.activeRecordings) {
        // 해당 스케줄이 더 이상 활성화되지 않은 경우 녹화 중지
        if (!activeScheduleMap.has(recordingKey)) {
          logger.info(`Stopping recording for inactive schedule: ${recordingKey}`);
          await this.stopRecording(recordingInfo.cameraName, recordingInfo.scheduleId);
        }
      }

      // 새로운 녹화 시작
      for (const schedule of activeSchedules) {
        const scheduleKey = `${schedule.cameraName}_${schedule.id}`;

        // 이미 녹화 중인 경우 스킵
        if (this.activeRecordings.has(scheduleKey)) {
          continue;
        }

        // 오늘 이미 완료된 녹화가 있는지 다시 한번 확인 (LIKE → 범위 조건)
        const today = moment().tz('Asia/Seoul').startOf('day');
        const tomorrow = moment(today).add(1, 'days');
        const recordingHistory = await RecordingHistory.findAll({
          where: {
            scheduleId: schedule.id,
            cameraName: schedule.cameraName,
            startTime: {
              [Op.gte]: today.toDate(),
              [Op.lt]: tomorrow.toDate()
            },
            status: {
              [Op.in]: ['completed', 'stopped']
            }
          }
        });

        if (recordingHistory.length > 0) {
          logger.info(`Skipping recording for schedule ${scheduleKey} as it was already completed today`);
          continue;
        }

        logger.info(`Starting new recording for schedule: ${scheduleKey}`);
        // console.log('=====> schedule', schedule);
        await this.startRecording(schedule.cameraName, schedule.id, schedule.source, schedule.fk_camera_id, schedule.recoding_bitrate);
      }

    } catch (error) {
      logger.error('Error in checkAndUpdateRecordings:', error);
    }
  }

  async cleanupHLSSegments(cameraName, recordingDate, maxSegments) {
    try {
      // 설정값에서 maxSegments 가져오기
      const hlsConfig = ConfigService.recordings?.hls;
      const defaultMaxSegments = hlsConfig?.maxSegments || 2880;
      const segmentsToKeep = maxSegments || defaultMaxSegments;

      const hlsDir = path.join(
        this.recordingsPath,
        cameraName,
        recordingDate,
        'hls'
      );

      if (!await fs.pathExists(hlsDir)) {
        return;
      }

      const files = await fs.readdir(hlsDir);
      const tsFiles = files.filter(file => file.endsWith('.ts')).sort();

      // 최대 세그먼트 수를 초과하는 오래된 파일 삭제
      if (tsFiles.length > segmentsToKeep) {
        const filesToDelete = tsFiles.slice(0, tsFiles.length - segmentsToKeep);

        for (const file of filesToDelete) {
          const filePath = path.join(hlsDir, file);
          await fs.unlink(filePath);
          logger.debug(`Deleted old HLS segment: ${file}`);
        }

        // 플레이리스트 파일 업데이트
        const playlistFiles = files.filter(file => file.endsWith('.m3u8'));
        for (const playlistFile of playlistFiles) {
          await this.updateHLSPlaylist(path.join(hlsDir, playlistFile), segmentsToKeep);
        }
      }
    } catch (error) {
      logger.error(`Error cleaning up HLS segments: ${error.message}`);
    }
  }

  async performHLSCleanup() {
    try {
      const hlsConfig = ConfigService.recordings?.hls;
      if (!hlsConfig?.autoCleanup) return;

      const cameras = await this.getActiveCameras();

      for (const camera of cameras) {
        const recordingDate = moment().tz('Asia/Seoul').format('YYYY-MM-DD');
        await this.cleanupHLSSegments(
          camera.name,
          recordingDate,
          hlsConfig?.maxSegments
        );
      }

      logger.debug('HLS cleanup completed');
    } catch (error) {
      logger.error('Error during HLS cleanup:', error);
    }
  }

  start() {
    if (this.checkInterval) {
      this.stop();
    }

    // 체크 주기를 30초로 증가
    this.checkInterval = setInterval(() => {
      this.checkAndUpdateRecordings();
    }, 30000);

    logger.info('Recording process started, checking schedules every 30 seconds');
  }

  stop() {
    if (this.checkInterval) {
      clearInterval(this.checkInterval);
      this.checkInterval = null;

      // 모든 녹화 중지
      for (const [recordingKey, recordingInfo] of this.activeRecordings) {
        this.stopRecording(recordingInfo.cameraName, recordingInfo.scheduleId);
      }

      logger.info('Recording process stopped');
    }
  }
}

export default new RecordingProcess(); 