import ScheduleModel from '../../models/schedule.js';
import sequelize from '../../models/index.js';
const Schedule = ScheduleModel(sequelize);

import LoggerService from '../logger/logger.service.js';
import RecordingService from '../recording/recording.service.js';

const logger = new LoggerService('ScheduleChecker');

class ScheduleChecker {
  constructor() {
    this.checkInterval = null;
    this.lastCheck = new Map(); // 마지막 체크 상태 저장
    this.lastCheckMissCount = new Map();
  }

  isTimeInRange(currentTime, startTime, endTime) {
    const [currentHour, currentMinute] = currentTime.split(':');
    const [startHour, startMinute] = startTime.split(':');
    const [endHour, endMinute] = endTime.split(':');

    const current = parseInt(currentHour) * 60 + parseInt(currentMinute);
    const start = parseInt(startHour) * 60 + parseInt(startMinute);
    const end = parseInt(endHour) * 60 + parseInt(endMinute) + 1;

    return current >= start && current <= end;
  }

  async getCurrentlyRecordingSchedules() {
    try {
      const schedules = await Schedule.findAll({
        where: { isActive: 1 },
        attributes: ['id', 'cameraName', 'fk_camera_id', 'start_time', 'end_time', 'recording_type', 'days_of_week', 'source']
      });

      const now = new Date();
      const currentDay = now.getDay();
      const currentTime = now.toLocaleTimeString('en-US', {
        hour12: false,
        hour: '2-digit',
        minute: '2-digit'
      });

      const recordingSchedules = schedules.filter(schedule => {
        const days = schedule.days_of_week || [];
        return (
          schedule.isActive &&
          days.includes(currentDay) &&
          this.isTimeInRange(currentTime, schedule.start_time, schedule.end_time)
        );
      });

      return recordingSchedules;
    } catch (error) {
      logger.error('Error checking recording schedules:', error);
      return [];
    }
  }

  async checkSchedules() {
    try {
      const recordingSchedules = await this.getCurrentlyRecordingSchedules();
      const currentCameras = new Set(recordingSchedules.map(s => s.cameraName));

      // 이전에 녹화 중이었지만 현재는 녹화 중이 아닌 카메라들 확인
      console.log('checkSchedules lastCheck', this.lastCheck);
      console.log('checkSchedules currentCameras', currentCameras);
      for (const [cameraName, wasRecording] of this.lastCheck.entries()) {
        if (wasRecording && !currentCameras.has(cameraName)) {
          // 녹화 중지
          await RecordingService.stopRecording(cameraName);
          logger.info(`Stopped recording for camera: ${cameraName} (schedule ended)`);
        }
      }

      // 현재 녹화해야 할 스케줄들 처리
      logger.info(`recordingSchedules:`, recordingSchedules);
      for (const schedule of recordingSchedules) {
        const { cameraName, id, recording_type, fk_camera_id, bitrate } = schedule;

        // 이미 녹화 중인지 확인
        if (!RecordingService.isRecording(cameraName)) {
          // 녹화 시작
          await RecordingService.startRecording(cameraName, id, recording_type, fk_camera_id);
          logger.info(`Started recording for camera: ${cameraName} (schedule ${id}, camera_id: ${fk_camera_id})`);
        }
      }

      // 현재 상태 저장
      this.lastCheck.clear();
      currentCameras.forEach(cameraName => {
        this.lastCheck.set(cameraName, true);
      });

      if (recordingSchedules.length > 0) {
        logger.info('Currently recording schedules:', {
          count: recordingSchedules.length,
          schedules: recordingSchedules.map(s => ({
            id: s.id,
            cameraName: s.cameraName,
            fk_camera_id: s.fk_camera_id,
            start_time: s.start_time,
            end_time: s.end_time,
            recording_type: s.recording_type,
            isRecording: RecordingService.isRecording(s.cameraName),
            source: s.source
          }))
        });
      }

      // // 녹화 중지 조건을 더 엄격하게
      // for (const [recordingKey, recordingInfo] of this.activeRecordings) {
      //   if (!currentCameras.has(recordingKey)) {
      //     const missCount = this.lastCheckMissCount.get(recordingKey) || 0;
      //     if (missCount >= 2) {
      //       logger.info(`Stopping recording for inactive schedule: ${recordingKey}`);
      //       await this.stopRecording(recordingInfo.cameraName, recordingInfo.scheduleId);
      //       this.lastCheckMissCount.delete(recordingKey);
      //     } else {
      //       this.lastCheckMissCount.set(recordingKey, missCount + 1);
      //     }
      //   } else {
      //     this.lastCheckMissCount.delete(recordingKey);
      //   }
      // }

      return recordingSchedules;
    } catch (error) {
      logger.error('Error in schedule check:', error);
      return [];
    }
  }

  startChecking(intervalMinutes = 1) {
    if (this.checkInterval) {
      this.stopChecking();
    }

    this.checkInterval = setInterval(async () => {
      await this.checkSchedules();
    }, intervalMinutes * 30 * 1000);

    logger.info('Schedule checker started');
  }

  stopChecking() {
    if (this.checkInterval) {
      clearInterval(this.checkInterval);
      this.checkInterval = null;
      logger.info('Schedule checker stopped');
    }
  }
}

export default new ScheduleChecker(); 