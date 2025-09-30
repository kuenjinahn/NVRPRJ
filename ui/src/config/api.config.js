
// config.ini에서 IP 설정을 읽어오는 함수 (브라우저 환경에서는 기본값 사용)
const getApiTarget = () => {
  // 브라우저 환경에서는 config.ini를 직접 읽을 수 없으므로 기본값 사용
  // 실제 IP는 server.js와 vue.config.js에서 config.ini를 읽어서 프록시로 처리

  // 모든 환경에서 현재 호스트의 포트를 사용 (프록시를 통해 처리)
  const url = `${location.protocol}//${location.hostname}:${location.port}`;

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

// ES6 export
export {
  getApiBaseUrl,
  getSocketBaseUrl,
  getApiTarget
};
