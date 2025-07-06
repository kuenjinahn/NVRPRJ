import api from './index';

const resource = '/eventHistory';

export const getEventHistory = async (filters = {}) => {
  const { startDate, endDate, label } = filters;
  const params = {};

  if (startDate) params.startDate = startDate;
  if (endDate) params.endDate = endDate;
  if (label) params.label = label;

  const response = await api.get(resource, { params });
  return response.data;
};

export default {
  getEventHistory
}; 
