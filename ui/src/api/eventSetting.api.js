// EventSetting API utility

import api from './index';

const resource = '/eventSetting';

export const getEventSetting = async () => {
  const response = await api.get(resource);
  return response.data;
};

export const updateEventSetting = async (id, data) => {
  const response = await api.put(`${resource}/${id}`, data);
  return response.data;
};

export const createEventSetting = async (data) => {
  const response = await api.post(resource, data);
  return response.data;
};

export default {
  getEventSetting,
  updateEventSetting,
  createEventSetting
}; 
