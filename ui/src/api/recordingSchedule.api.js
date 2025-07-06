import api from './index';

const resource = '/schedules';

export const getSchedules = async () => {
  return await api.get(resource);
};

export const createSchedule = async (scheduleData) => {
  return await api.post(resource, scheduleData);
};

export const updateSchedule = async (scheduleId, scheduleData) => {
  return await api.put(`${resource}/${scheduleId}`, scheduleData);
};

export const deleteSchedule = async (scheduleId) => {
  return await api.delete(`${resource}/${scheduleId}`);
};

export const toggleSchedule = async (scheduleId, isActive) => {
  return await api.patch(`${resource}/${scheduleId}/toggle`, { isActive });
};

