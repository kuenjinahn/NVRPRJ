
// API 타겟 URL 반환 (vue.config.js와 server.js에서 사용)
const getApiTarget = () => {
  const env = process.env.NODE_ENV || 'development';
  const url = env === 'production'
    ? 'http://192.168.0.24:9091'
    : 'http://localhost:9091';

  // 디버깅용 로그
  console.log(`[API Config] Environment: ${env}, URL: ${url}`);

  return url;
};

// API 기본 URL 반환 (getApiTarget 사용)
const getApiBaseUrl = () => {
  const env = process.env.NODE_ENV || 'development';

  // 모든 환경에서 프록시 사용 (UI 서버를 통해 백엔드로 전달)
  if (env === 'development') {
    return '/api'; // 프록시를 통해 localhost:9091로 전달
  } else {
    return '/api'; // 프록시를 통해 20.41.121.184:9091로 전달
  }
};

// 소켓 기본 URL 반환 (getApiTarget 사용)
const getSocketBaseUrl = () => {
  return getApiTarget();
};

// CommonJS export
module.exports = {
  getApiBaseUrl,
  getSocketBaseUrl,
  getApiTarget
};
