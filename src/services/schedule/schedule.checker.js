import ScheduleModel from '../../models/schedule.js';
import sequelize from '../../models/index.js';
const Schedule = ScheduleModel(sequelize);

import LoggerService from '../logger/logger.service.js';
// import RecordingService from '../recording/recording.service.js'; // Python으로 이동됨

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

      // recording.process.js와 동일한 키 형식 사용: cameraName_scheduleId
      const currentScheduleKeys = new Set(recordingSchedules.map(s => `${s.cameraName}_${s.id}`));

      // 이전에 녹화 중이었지만 현재는 녹화 중이 아닌 스케줄들 확인
      logger.info(`🔍 checkSchedules - lastCheck:`, Array.from(this.lastCheck.entries()));
      logger.info(`🔍 checkSchedules - currentScheduleKeys:`, Array.from(currentScheduleKeys));

      // 레코딩 중지 로직은 Python으로 이동됨
      // for (const [scheduleKey, wasRecording] of this.lastCheck.entries()) {
      //   if (wasRecording && !currentScheduleKeys.has(scheduleKey)) {
      //     // 녹화 중지 - scheduleKey에서 cameraName과 scheduleId 추출
      //     const [cameraName, scheduleId] = scheduleKey.split('_');
      //     if (cameraName && scheduleId) {
      //       await RecordingService.stopRecording(cameraName, parseInt(scheduleId));
      //       logger.info(`🛑 Stopped recording for schedule: ${scheduleKey} (schedule ended)`);
      //     } else {
      //       logger.warn(`⚠️ Invalid schedule key format: ${scheduleKey}`);
      //     }
      //   }
      // }

      // 현재 녹화해야 할 스케줄들 처리 - Python으로 이동됨
      logger.info(`🎬 recordingSchedules:`, recordingSchedules);
      // for (const schedule of recordingSchedules) {
      //   const { cameraName, id, recording_type, fk_camera_id, source, recoding_bitrate } = schedule;
      //   const scheduleKey = `${cameraName}_${id}`;

      //   // 이미 녹화 중인 경우 스킵
      //   if (this.lastCheck.has(scheduleKey)) {
      //     logger.debug(`⏭️ Recording already active for schedule: ${scheduleKey}`);
      //     continue;
      //   }

      //   // 녹화 시작
      //   await RecordingService.startRecording(cameraName, id, source, fk_camera_id, recoding_bitrate);
      //   logger.info(`🎬 Started recording for schedule: ${scheduleKey} (camera_id: ${fk_camera_id})`);
      // }

      // 현재 상태 저장 - scheduleKey 형식으로 저장
      this.lastCheck.clear();
      currentScheduleKeys.forEach(scheduleKey => {
        this.lastCheck.set(scheduleKey, true);
      });

      if (recordingSchedules.length > 0) {
        logger.info('✅ Currently active recording schedules:', {
          count: recordingSchedules.length,
          schedules: recordingSchedules.map(s => ({
            id: s.id,
            cameraName: s.cameraName,
            fk_camera_id: s.fk_camera_id,
            start_time: s.start_time,
            end_time: s.end_time,
            recording_type: s.recording_type,
            scheduleKey: `${s.cameraName}_${s.id}`,
            source: s.source
          }))
        });
      }

      // 녹화 상태 요약
      logger.info(`📊 Recording status summary:`, {
        totalSchedules: recordingSchedules.length,
        activeRecordings: Array.from(this.lastCheck.keys()),
        lastCheckSize: this.lastCheck.size
      });

      return recordingSchedules;
    } catch (error) {
      logger.error('Error in schedule check:', error);
      return [];
    }
  }

  startChecking(intervalSeconds = 30) {
    if (this.checkInterval) {
      this.stopChecking();
    }

    this.checkInterval = setInterval(async () => {
      await this.checkSchedules();
    }, intervalSeconds * 1000);

    logger.info(`🔄 Schedule checker started with ${intervalSeconds} second interval`);
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