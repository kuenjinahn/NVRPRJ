import api from './index';

const resource = '/statistic';

export const getRealtimeTemp = async (params) => await api.get(`${resource}/realtime-temp`, { params });

export const getDailyRoiAvgTemp = async (params) => await api.get(`${resource}/daily-roi-avg-temp`, { params });

export const getDailyRoiMinChange = async (params) => await api.get(`${resource}/daily-roi-min-change`, { params });

export const getRoiDataList = async (params) => await api.get(`${resource}/roi-data-list`, { params });

export const getRoiTimeSeriesData = async (params) => await api.get(`${resource}/roi-time-series`, { params });
