'use-strict';

import AlertHistory from '../../../models/AlertHistory.js';
import AlertSetting from '../../../models/AlertSetting.js';

export const list = async (options = {}) => {
  return await AlertHistory.findAndCountAll({
    order: [['alert_accur_time', 'DESC']],
    ...options
  });
};

export const findById = async (id) => {
  return await AlertHistory.findOne({ where: { id } });
};

export const createAlert = async (alertData) => {
  const alert = {
    fk_camera_id: alertData.fk_camera_id,
    alert_accur_time: alertData.alert_accur_time || new Date(),
    alert_type: alertData.alert_type,
    alert_level: alertData.alert_level,
    alert_status: alertData.alert_status || 'NEW',
    fk_detect_zone_id: alertData.fk_detect_zone_id || 0,
    fk_process_user_id: alertData.fk_process_user_id || 0,
    alert_process_time: alertData.alert_process_time,
    alert_description: alertData.alert_description,
    create_date: new Date(),
    update_date: new Date()
  };

  return await AlertHistory.create(alert);
};

export const updateAlert = async (id, alertData) => {
  const alert = await AlertHistory.findOne({ where: { id } });
  if (!alert) return null;

  alertData.update_date = new Date();
  return await alert.update(alertData);
};

export const removeById = async (id) => {
  return await AlertHistory.destroy({ where: { id } });
};

export const getAlertsByCamera = async (cameraId) => {
  return await AlertHistory.findAll({
    where: { fk_camera_id: cameraId },
    order: [['alert_accur_time', 'DESC']]
  });
};

export const getAlertsByStatus = async (status) => {
  return await AlertHistory.findAll({
    where: { alert_status: status },
    order: [['alert_accur_time', 'DESC']]
  });
};

export const getAlertSettings = async (userId) => {
  const setting = await AlertSetting.findOne({
    where: { fk_user_id: userId },
    order: [['id', 'DESC']]
  });

  return setting;
};

export const createAlertSettings = async (settingsData, userId) => {
  // JSON 설정을 문자열로 변환
  const alertSettingsJson = typeof settingsData === 'string'
    ? settingsData
    : JSON.stringify(settingsData);

  const setting = {
    alert_setting_json: alertSettingsJson,
    fk_user_id: userId,
    create_date: new Date(),
    update_date: new Date()
  };

  return await AlertSetting.create(setting);
};

export const updateAlertSettings = async (settingsData, userId) => {
  // 해당 사용자의 설정 찾기
  const existingSetting = await AlertSetting.findOne({
    where: { fk_user_id: userId }
  });

  // JSON 설정을 문자열로 변환
  const alertSettingsJson = typeof settingsData === 'string'
    ? settingsData
    : JSON.stringify(settingsData);

  // 설정이 존재하면 업데이트, 없으면 새로 생성
  if (existingSetting) {
    return await existingSetting.update({
      alert_setting_json: alertSettingsJson,
      update_date: new Date()
    });
  } else {
    return await createAlertSettings(settingsData, userId);
  }
};

export const getDefaultAlertSettings = () => {
  return {
    alert: {
      enabled: true,
      notificationType: '팝업',
      delay: 5,
      priority: '높음',
      repeatInterval: 15,
      useSound: true,
      leakThreshold: 5
    },
    alarmLevels: [
      {
        id: 1,
        name: '1단계 (주의)',
        threshold: 60,
        description: '최저온도의 차가 이하일경우 주의 단계 알림을 발송합니다.',
        color: 'light-blue'
      },
      {
        id: 2,
        name: '2단계 (경고)',
        threshold: 70,
        description: '최저온도의 차가 이하일경우 주의 단계 알림을 발송합니다.',
        color: 'blue'
      },
      {
        id: 3,
        name: '3단계 (위험)',
        threshold: 80,
        description: '최저온도의 차가 이하일경우 주의 단계 알림을 발송합니다.',
        color: 'amber darken-2'
      },
      {
        id: 4,
        name: '4단계 (심각)',
        threshold: 90,
        description: '최저온도의 차가 이하일경우 주의 단계 알림을 발송합니다.',
        color: 'orange darken-3'
      },
      {
        id: 5,
        name: '5단계 (비상)',
        threshold: 100,
        description: '최저온도의 차가 이하일경우 주의 단계 알림을 발송합니다.',
        color: 'red darken-3'
      }
    ],
    notification: {
      emailEnabled: false,
      emailAddress: '',
      emailAlarmLevel: 3,
      smsEnabled: false,
      phoneNumber: '',
      smsAlarmLevel: 4
    }
  };
}; 