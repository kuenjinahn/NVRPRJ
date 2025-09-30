import { io } from 'socket.io-client';
import { getSocketBaseUrl } from '@/config/api.config.js';

const socket = io(
  process.env.NODE_ENV === 'development'
    ? `${location.protocol}//${location.hostname}:${process.env.VUE_APP_SERVER_PORT}`
    : getSocketBaseUrl(),
  {
    autoConnect: true, // 자동 연결 활성화
    reconnection: true,
    reconnectionDelay: 2000, // 재연결 지연 시간 증가 (2초)
    maxReconnectionAttempts: 10, // 재연결 시도 횟수 제한
    timeout: 20000, // 연결 타임아웃 20초
    transports: ['polling', 'websocket'], // 폴링 우선, WebSocket 폴백
    upgrade: true, // 자동 업그레이드
    // 연결 안정성을 위한 추가 설정
    pingTimeout: 60000, // 핑 타임아웃 60초
    pingInterval: 25000, // 핑 간격 25초
    closeOnBeforeunload: false, // 페이지 이탈 시 연결 유지
  }
);

// 연결 상태 모니터링 및 자동 복구
socket.on('connect', () => {
  console.log('[Socket] Connected successfully:', socket.id);
  console.log('[Socket] Transport:', socket.io.engine.transport.name);
});

socket.on('disconnect', (reason) => {
  console.log('[Socket] Disconnected:', reason);

  // 연결 끊김 시 자동 재연결 시도
  if (reason === 'io server disconnect') {
    console.log('[Socket] Server disconnected, attempting to reconnect...');
    socket.connect();
  }
});

socket.on('connect_error', (error) => {
  console.error('[Socket] Connection error:', error.message);

  // 연결 오류 시 폴링 방식으로 전환
  if (error.message === 'timeout' || error.message === 'server error') {
    console.log('[Socket] Switching to polling transport...');
    socket.io.opts.transports = ['polling'];
  }
});

socket.on('reconnect', (attemptNumber) => {
  console.log('[Socket] Reconnected after', attemptNumber, 'attempts');
});

// 페이지 가시성 변경 감지 (탭 전환 시 스트림 유지)
document.addEventListener('visibilitychange', () => {
  if (document.visibilityState === 'visible' && !socket.connected) {
    console.log('[Socket] Page became visible, reconnecting...');
    socket.connect();
  }
});

// 네트워크 상태 변경 감지
window.addEventListener('online', () => {
  console.log('[Socket] Network online, reconnecting...');
  if (!socket.connected) {
    socket.connect();
  }
});

export default socket;
