import api from './index';

const resource = '/panorama';

// 파노라마 데이터 조회 (최근 5개)
export const getPanoramaData = async (limit = 5) => {
  try {
    const response = await api.get(`${resource}/data`, {
      params: { limit }
    });
    return response.data;
  } catch (error) {
    console.error('Error fetching panorama data:', error);
    throw error;
  }
};

// 파노라마 데이터 상세 조회
export const getPanoramaDataById = async (id) => {
  try {
    const response = await api.get(`${resource}/data/${id}`);
    return response.data;
  } catch (error) {
    console.error('Error fetching panorama data by ID:', error);
    throw error;
  }
};


