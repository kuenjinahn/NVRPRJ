import api from './index';
import moment from 'moment-timezone';

const resource = '/recordings';

export const getRecordingHistory = async (params = {}) => {
  // 날짜 파라미터가 있는 경우 KST로 변환
  if (params.startDate || params.endDate) {
    const newParams = { ...params };

    if (params.startDate) {
      // UTC 시간을 KST로 변환하고 해당일의 시작으로 설정
      newParams.startDate = moment.utc(params.startDate)
        .tz('Asia/Seoul')
        .startOf('day')
        .format('YYYY-MM-DDTHH:mm:ss.SSS[Z]');
    }

    if (params.endDate) {
      // UTC 시간을 KST로 변환하고 해당일의 끝으로 설정
      newParams.endDate = moment.utc(params.endDate)
        .tz('Asia/Seoul')
        .endOf('day')
        .format('YYYY-MM-DDTHH:mm:ss.SSS[Z]');
    }

    const response = await api.get(`${resource}/history`, { params: newParams });
    return response.data;
  }

  const response = await api.get(`${resource}/history`, { params });
  return response.data;
};

export const getVideoThumbnail = async (recordingId) => {
  try {
    console.log(`Requesting thumbnail for recording ID: ${recordingId}`);
    const response = await api.get(`${resource}/thumbnail/${recordingId}`, {
      responseType: 'blob'
    });
    console.log(`Thumbnail response status: ${response.status}`);

    if (response.status === 200) {
      const blob = new Blob([response.data], { type: 'image/png' });
      const thumbnailUrl = URL.createObjectURL(blob);
      console.log(`Generated thumbnail URL: ${thumbnailUrl}`);
      return thumbnailUrl;
    } else {
      console.error(`Failed to fetch thumbnail. Status: ${response.status}`);
      return null;
    }
  } catch (error) {
    console.error('Error fetching thumbnail:', error.message);
    return null;
  }
};

export const getRecordingStatus = async (cameraName) => {
  const response = await api.get(`${resource}/status/${cameraName}`);
  return response.data;
};

export const getActiveRecordings = async () => {
  const response = await api.get(`${resource}/active`);
  return response.data;
};

// 특정 날짜의 모든 MP4 segment 파일 목록 조회
export const getRecordingSegments = async (date, file_path = null) => {
  const params = { date };

  // file_path가 제공된 경우 추가
  if (file_path) {
    params.file_path = file_path;
  }

  const response = await api.get(`${resource}/segments`, { params });
  return response.data;
};

export default {
  getRecordingHistory,
  getVideoThumbnail,
  getRecordingStatus,
  getActiveRecordings,
  getRecordingSegments
}; 
