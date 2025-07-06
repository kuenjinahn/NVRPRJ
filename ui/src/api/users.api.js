import api from './index';

const resource = '/users';

export const addUser = async (userData) => await api.post(resource, userData);

export const changeUser = async (userId, userData) => {
  const startTime = new Date().toISOString();
  console.log('=== changeUser API 호출 시작 ===');
  console.log('시간:', startTime);
  console.log('요청 URL:', `${resource}/${userId}`);
  console.log('요청 데이터:', JSON.stringify(userData, null, 2));

  try {
    const response = await api.patch(`${resource}/${userId}`, userData);
    const endTime = new Date().toISOString();
    console.log('=== changeUser API 호출 성공 ===');
    console.log('응답 시간:', endTime);
    console.log('소요 시간:', new Date(endTime) - new Date(startTime), 'ms');
    console.log('응답 상태:', response.status);
    console.log('응답 데이터:', JSON.stringify(response.data, null, 2));
    return response;
  } catch (error) {
    const endTime = new Date().toISOString();
    console.error('=== changeUser API 호출 실패 ===');
    console.error('실패 시간:', endTime);
    console.error('소요 시간:', new Date(endTime) - new Date(startTime), 'ms');
    console.error('에러 메시지:', error.message);
    console.error('에러 상세:', error.response ? {
      status: error.response.status,
      data: error.response.data
    } : '응답 없음');
    throw error;
  }
};

export const getUser = async (userId) => await api.get(`${resource}/${userId}`);

export const getUsers = async (parameters) => await api.get(`${resource}${parameters ? parameters : ''}`);

export const removeUser = async (userId) => await api.delete(`${resource}/${userId}`);

export const getUserAccessHistory = async (userId, parameters) => await api.get(`${resource}/access-history${parameters ? parameters : ''}`);
