import fs from 'fs-extra';
import path from 'path';
import moment from 'moment-timezone';
import LoggerService from '../logger/logger.service.js';
import ConfigService from '../config/config.service.js';
import RecordingHistoryModel from '../../models/RecordingHistory.js';
import Camera from '../../models/Camera.js';
import sequelize from '../../models/index.js';
import { Op } from 'sequelize';

const logger = new LoggerService('RecordingService');
const RecordingHistory = RecordingHistoryModel(sequelize);

export class RecordingService {
  constructor() {
    this.activeRecordings = new Map(); // key: `${cameraName}_${scheduleId}`
    this.recordingsPath = ConfigService.recordingsPath;
  }

  async addRecordingHistory(scheduleId, cameraName, startTime, filename, fk_camera_id) {
    try {
      // 카메라 ID 조회
      const camera = await Camera.findOne({
        where: { name: cameraName }
      });

      if (!camera) {
        throw new Error(`Camera not found: ${cameraName}`);
      }

      const newRecord = {
        scheduleId,
        cameraName,
        fk_camera_id,
        filename,
        startTime: moment(startTime).tz('Asia/Seoul').format('YYYY-MM-DD HH:mm:ss'),
        status: 'recording',
        createdAt: moment().tz('Asia/Seoul').format('YYYY-MM-DD HH:mm:ss')
      };

      const createdRecord = await RecordingHistory.create(newRecord);
      logger.info('Recording history added:', createdRecord);
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

  async startRecording(cameraName, scheduleId, recordingType, fk_camera_id) {
    try {
      const key = `${cameraName}_${scheduleId}`;
      if (this.activeRecordings.has(key)) {
        logger.warn(`Recording already in progress for camera: ${cameraName}, schedule: ${scheduleId}`);
        return false;
      }

      // 한국 시간 기준으로 시간 정보 생성
      const nowMoment = moment().tz('Asia/Seoul');
      const timestamp = nowMoment.format('YYYY-MM-DD HH-mm-ss');
      const filename = `${cameraName}_${timestamp}.mp4`;
      const recordingPath = path.join(this.recordingsPath, cameraName, filename);

      // 녹화 시작 시 기록 추가 (한국 시간 사용)
      const recordingId = await this.addRecordingHistory(
        scheduleId,
        cameraName,
        timestamp,
        filename,
        fk_camera_id
      );

      // 녹화 시작 시간 (한국 시간)
      const startTime = nowMoment.toDate();
      const recordingInfo = {
        recordingId,
        scheduleId,
        fk_camera_id,
        startTime,
        recordingType,
        status: 'recording'
      };

      // 녹화 폴더 생성 (한국 시간 기준 날짜)
      const recordingDir = path.join(
        this.recordingsPath,
        cameraName,
        nowMoment.format('YYYY-MM-DD')
      );
      await fs.ensureDir(recordingDir);

      // 녹화 정보 파일 생성
      const infoFile = path.join(recordingDir, 'recording_info.json');
      await fs.writeJson(infoFile, {
        ...recordingInfo,
        recordingDir,
        timestamp: timestamp
      });

      this.activeRecordings.set(key, recordingInfo);
      logger.info(`Started recording for camera: ${cameraName}, schedule: ${scheduleId}`, recordingInfo);

      return true;
    } catch (error) {
      logger.error(`Failed to start recording for camera: ${cameraName}, schedule: ${scheduleId}`, error);
      return false;
    }
  }

  async stopRecording(cameraName, scheduleId) {
    try {
      const key = `${cameraName}_${scheduleId}`;
      if (!this.activeRecordings.has(key)) {
        logger.warn(`No active recording found for camera: ${cameraName}, schedule: ${scheduleId}`);
        return false;
      }

      const recordingInfo = this.activeRecordings.get(key);
      recordingInfo.status = 'stopped';

      // 종료 시간도 한국 시간으로 설정
      const endTimeMoment = moment().tz('Asia/Seoul');
      recordingInfo.endTime = endTimeMoment.toDate();

      // 녹화 정보 파일 업데이트
      const recordingDir = path.join(
        this.recordingsPath,
        cameraName,
        moment(recordingInfo.startTime).tz('Asia/Seoul').format('YYYY-MM-DD')
      );
      const infoFile = path.join(recordingDir, 'recording_info.json');

      if (await fs.pathExists(infoFile)) {
        await fs.writeJson(infoFile, {
          ...recordingInfo,
          recordingDir,
          endTimestamp: endTimeMoment.format('YYYY-MM-DDTHH-mm-ss')
        });
      }

      // 녹화 종료 시 기록 업데이트 (한국 시간 사용)
      await this.updateRecordingHistory(recordingInfo.recordingId, {
        endTime: endTimeMoment.format('YYYY-MM-DDTHH-mm-ss'),
        status: 'completed'
      });

      this.activeRecordings.delete(key);
      logger.info(`Stopped recording for camera: ${cameraName}, schedule: ${scheduleId}`, recordingInfo);

      return true;
    } catch (error) {
      logger.error(`Failed to stop recording for camera: ${cameraName}, schedule: ${scheduleId}`, error);
      return false;
    }
  }

  isRecording(cameraName, scheduleId) {
    const key = `${cameraName}_${scheduleId}`;
    return this.activeRecordings.has(key);
  }

  getActiveRecordings() {
    return Array.from(this.activeRecordings.entries()).map(([key, info]) => ({
      ...info
    }));
  }

  async getRecordingStatus(cameraName, scheduleId) {
    const key = `${cameraName}_${scheduleId}`;
    if (this.activeRecordings.has(key)) {
      return {
        isRecording: true,
        ...this.activeRecordings.get(key)
      };
    }

    return {
      isRecording: false,
      status: 'stopped'
    };
  }

  async getRecordingHistory(filters = {}) {
    try {
      const whereClause = {};

      // 필터 적용
      if (filters.cameraName) {
        whereClause.cameraName = filters.cameraName;
      }
      if (filters.scheduleId) {
        whereClause.scheduleId = filters.scheduleId;
      }
      if (filters.status) {
        whereClause.status = filters.status;
      }

      const recordingHistory = await RecordingHistory.findAll({
        where: whereClause,
        order: [['id', 'DESC']]
      });

      // 결과가 비어있는 경우 빈 배열 반환
      if (!recordingHistory || recordingHistory.length === 0) {
        return [];
      }

      // 시간 정보 포맷팅
      const formattedHistory = recordingHistory.map(record => ({
        ...record.toJSON(),
        startTime: record.startTime ? moment(record.startTime).tz('Asia/Seoul').format('YYYY-MM-DDTHH-mm-ss') : null,
        endTime: record.endTime ? moment(record.endTime).tz('Asia/Seoul').format('YYYY-MM-DDTHH-mm-ss') : null
      }));

      return formattedHistory;
    } catch (error) {
      logger.error('Error getting recording history:', error);
      return []; // 에러 발생 시 빈 배열 반환
    }
  }
}

export default new RecordingService(); 