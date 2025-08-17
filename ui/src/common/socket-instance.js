import { io } from 'socket.io-client';
import { getSocketBaseUrl } from '@/config/api.config.js';

export default io(
  process.env.NODE_ENV === 'development'
    ? `${location.protocol}//${location.hostname}:${process.env.VUE_APP_SERVER_PORT}`
    : getSocketBaseUrl(),
  {
    autoConnect: false,
    //forceNew: true,
    reconnection: true,
    reconnectionDelay: 500,
    maxReconnectionAttempts: Infinity,
  }
);
