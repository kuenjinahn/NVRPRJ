import fs from 'fs';
import path from 'path';
import EventSettingModel from '../../models/EventSetting.js';
import sequelize from '../../models/index.js';
import LoggerService from '../logger/logger.service.js';

const EventSetting = EventSettingModel(sequelize);
const logger = new LoggerService('RecordingCleanup');

class RecordingCleanupService {
  constructor() {
    this.cleanupInterval = null;
    this.recordingsPath = path.join(process.cwd(), 'outputs', 'nvr', 'recordings');
    this.defaultDeleteDays = 30; // 기본값: 30일
  }

  /**
   * EventSetting 테이블에서 object_json을 파싱하여 recodingFileDeleteDays 값을 가져옴
   */
  async getDeleteDaysFromSettings() {
    try {
      const eventSetting = await EventSetting.findOne({
        where: { id: 1 }, // 기본 설정 레코드
        attributes: ['object_json']
      });

      if (eventSetting && eventSetting.object_json) {
        const objectConfig = JSON.parse(eventSetting.object_json);
        const recordingConfig = objectConfig.recording || {};
        return recordingConfig.recodingFileDeleteDays || this.defaultDeleteDays;
      }

      return this.defaultDeleteDays;
    } catch (error) {
      logger.error('Error getting delete days from settings:', error);
      return this.defaultDeleteDays;
    }
  }

  /**
   * 파일의 생성 시간을 확인
   */
  getFileCreationTime(filePath) {
    try {
      const stats = fs.statSync(filePath);
      return stats.birthtime || stats.mtime;
    } catch (error) {
      logger.error(`Error getting file creation time for ${filePath}:`, error);
      return null;
    }
  }

  /**
   * 파일이 삭제 대상인지 확인
   */
  isFileExpired(filePath, deleteDays) {
    const creationTime = this.getFileCreationTime(filePath);
    if (!creationTime) return false;

    const cutoffDate = new Date();
    cutoffDate.setDate(cutoffDate.getDate() - deleteDays);
    return creationTime < cutoffDate;
  }

  /**
   * 파일과 관련 JSON 파일을 삭제
   */
  deleteFileAndMetadata(filePath) {
    try {
      // 메인 파일 삭제
      if (fs.existsSync(filePath)) {
        fs.unlinkSync(filePath);
        logger.info(`Deleted file: ${filePath}`);
      }

      // 관련 JSON 파일 삭제
      const jsonPath = filePath.replace(/\.(mp4|avi|mov)$/, '.json');
      if (fs.existsSync(jsonPath)) {
        fs.unlinkSync(jsonPath);
        logger.info(`Deleted metadata file: ${jsonPath}`);
      }

      return true;
    } catch (error) {
      logger.error(`Error deleting file ${filePath}:`, error);
      return false;
    }
  }

  /**
   * 디렉토리 내의 모든 파일을 재귀적으로 검사하고 삭제
   */
  async cleanupDirectory(dirPath, deleteDays) {
    try {
      if (!fs.existsSync(dirPath)) {
        return;
      }

      const items = fs.readdirSync(dirPath);
      let deletedCount = 0;

      for (const item of items) {
        const itemPath = path.join(dirPath, item);
        const stats = fs.statSync(itemPath);

        if (stats.isDirectory()) {
          // 디렉토리인 경우 재귀적으로 처리
          const subDeletedCount = await this.cleanupDirectory(itemPath, deleteDays);
          deletedCount += subDeletedCount;

          // 디렉토리가 비어있으면 삭제
          const remainingItems = fs.readdirSync(itemPath);
          if (remainingItems.length === 0) {
            fs.rmdirSync(itemPath);
            logger.info(`Deleted empty directory: ${itemPath}`);
          }
        } else if (stats.isFile()) {
          // 파일인 경우 삭제 대상인지 확인
          const isVideoFile = /\.(mp4|avi|mov)$/i.test(item);
          if (isVideoFile && this.isFileExpired(itemPath, deleteDays)) {
            if (this.deleteFileAndMetadata(itemPath)) {
              deletedCount++;
            }
          }
        }
      }

      return deletedCount;
    } catch (error) {
      logger.error(`Error cleaning up directory ${dirPath}:`, error);
      return 0;
    }
  }

  /**
   * 메인 정리 프로세스
   */
  async performCleanup() {
    try {
      logger.info('Starting recording file cleanup process...');

      // 설정에서 삭제 일수 가져오기
      const deleteDays = await this.getDeleteDaysFromSettings();
      logger.info(`Using delete days: ${deleteDays}`);

      // 녹화 디렉토리 정리
      const deletedCount = await this.cleanupDirectory(this.recordingsPath, deleteDays);

      logger.info(`Cleanup completed. Deleted ${deletedCount} files.`);

      return {
        success: true,
        deletedCount,
        deleteDays,
        timestamp: new Date().toISOString()
      };
    } catch (error) {
      logger.error('Error in cleanup process:', error);
      return {
        success: false,
        error: error.message,
        timestamp: new Date().toISOString()
      };
    }
  }

  /**
   * 정기적인 정리 작업 시작
   */
  startCleanup(intervalHours = 24) {
    if (this.cleanupInterval) {
      this.stopCleanup();
    }

    // 즉시 한 번 실행
    this.performCleanup();

    // 정기적으로 실행
    this.cleanupInterval = setInterval(async () => {
      await this.performCleanup();
    }, intervalHours * 60 * 60 * 1000);

    logger.info(`Recording cleanup service started with ${intervalHours} hour interval`);
  }

  /**
   * 정리 작업 중지
   */
  stopCleanup() {
    if (this.cleanupInterval) {
      clearInterval(this.cleanupInterval);
      this.cleanupInterval = null;
      logger.info('Recording cleanup service stopped');
    }
  }

  /**
   * 수동으로 정리 작업 실행
   */
  async manualCleanup() {
    logger.info('Manual cleanup requested');
    return await this.performCleanup();
  }

  /**
   * 현재 설정 정보 반환
   */
  async getCleanupInfo() {
    const deleteDays = await this.getDeleteDaysFromSettings();
    return {
      deleteDays,
      recordingsPath: this.recordingsPath,
      isRunning: !!this.cleanupInterval,
      lastCheck: new Date().toISOString()
    };
  }
}

export default new RecordingCleanupService(); 