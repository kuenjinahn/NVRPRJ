import axios from 'axios';
import { getApiBaseUrl } from '@/config/api.config.js';

const api = axios.create({
  baseURL: getApiBaseUrl(),
});

// 디버깅용 로그
console.log(`[API Index] Base URL: ${getApiBaseUrl()}`);
console.log(`[API Index] Current environment: ${process.env.NODE_ENV}`);
console.log(`[API Index] Location origin: ${location.origin}`);

api.interceptors.request.use(
  (config) => {
    const user = JSON.parse(localStorage.getItem('user'));

    if (user && user.access_token) {
      config.headers['Authorization'] = `Bearer ${user.access_token}`;
    }

    // Add logging for API requests
    console.log(`API Request: ${config.method.toUpperCase()} ${config.url}`, config);

    return Promise.resolve(config);
  },

  (error) => {
    console.error('API Request Error:', error);
    return Promise.reject(error);
  }
);

api.interceptors.response.use(
  (response) => {
    // Add logging for API responses
    console.log(`API Response: ${response.config.method.toUpperCase()} ${response.config.url}`, response);
    return Promise.resolve(response);
  },

  (error) => {
    console.error('API Response Error:', error);
    return Promise.reject(error);
  }
);

export default api;
