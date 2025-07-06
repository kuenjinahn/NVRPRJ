import { io } from 'socket.io-client';

export default io(
  process.env.NODE_ENV === 'development'
    ? `${location.protocol}//${location.hostname}:${process.env.VUE_APP_SERVER_PORT}`
    : 'http://20.41.121.184:9091',
  {
    autoConnect: false,
    //forceNew: true,
    reconnection: true,
    reconnectionDelay: 500,
    maxReconnectionAttempts: Infinity,
  }
);
