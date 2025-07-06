import axios from 'axios';

const api = axios.create({
  baseURL:
    process.env.NODE_ENV === 'development' || process.env.NODE_ENV === 'test'
      ? `${location.protocol}//${location.hostname}:9091/api`
      : `${location.origin}/api`,
});

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
