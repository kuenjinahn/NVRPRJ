import api from './index';

const resource = '/alerts';

export const addAlert = async (alertData) => await api.post(resource, alertData);

export const changeAlert = async (alertId, alertData) => await api.patch(`${resource}/${alertId}`, alertData);

export const getAlert = async (alertId) => await api.get(`${resource}/${alertId}`);

export const getAlerts = async (parameters) => await api.get(`${resource}${parameters ? parameters : ''}`);

export const removeAlert = async (alertId) => await api.delete(`${resource}/${alertId}`);

export const getAlertsByCamera = async (cameraId) => await api.get(`${resource}/camera/${cameraId}`);

export const getAlertsByStatus = async (status) => await api.get(`${resource}/status/${status}`);

export const updateAlertStatus = async (alertId, status, processUserId) => {
  return await api.patch(`${resource}/${alertId}`, {
    alert_status: status,
    fk_process_user_id: processUserId,
    alert_process_time: new Date().toISOString()
  });
};

export const completeAlert = async (alertId, processUserId, description) => {
  return await api.patch(`${resource}/${alertId}`, {
    alert_status: 'COMPLETED',
    fk_process_user_id: processUserId,
    alert_process_time: new Date().toISOString(),
    alert_description: description
  });
};

export const getAlertSettings = async () => {
  try {
    const response = await api.get(`${resource}/settings`);
    return response.data;
  } catch (error) {
    console.error('Error fetching alert settings:', error);
    throw error;
  }
};

export const getAlertSettingsForUser = async (userId) => {
  try {
    const response = await api.get(`${resource}/settings/${userId}`);
    return response.data;
  } catch (error) {
    console.error(`Error fetching alert settings for user ${userId}:`, error);
    throw error;
  }
};

export const saveAlertSettings = async (settings) => {
  try {
    const response = await api.post(`${resource}/settings`, { settings });
    return response.data;
  } catch (error) {
    console.error('Error saving alert settings:', error);
    throw error;
  }
};

export const saveAlertSettingsForUser = async (userId, settings) => {
  try {
    const response = await api.post(`${resource}/settings/${userId}`, { settings });
    return response.data;
  } catch (error) {
    console.error(`Error saving alert settings for user ${userId}:`, error);
    throw error;
  }
};

export const getDefaultAlertSettings = async () => {
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
        description: '최저온도의 차가 이하일경우 경고 단계 알림을 발송합니다.',
        color: 'blue'
      },
      {
        id: 3,
        name: '3단계 (위험)',
        threshold: 80,
        description: '최저온도의 차가 이하일경우 위험 단계 알림을 발송합니다.',
        color: 'amber darken-2'
      },
      {
        id: 4,
        name: '4단계 (심각)',
        threshold: 90,
        description: '온도가 90℃ 이상일 경우 심각 단계 알림을 발송합니다.',
        color: 'orange darken-3'
      },
      {
        id: 5,
        name: '5단계 (비상)',
        threshold: 100,
        description: '최저온도의 차가 이하일경우 비상 단계 알림을 발송합니다.',
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

export const getWeeklyAlertStats = async () => await api.get('/alerts/weekly-stats');

export const getRecentAlertCounts = async () => await api.get('/alerts/recent_alert');

export const updatePopupClose = async (alertId) => {
  return await api.patch(`${resource}/${alertId}`, {
    popup_close: 1
  });
}; 
