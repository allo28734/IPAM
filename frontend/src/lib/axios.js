import axios from 'axios';

// Configure the base axios instance to point to the FastAPI backend.
// In Docker production, Nginx proxies /api/ to the backend internally,
// so the default relative path '/api/v1' works without any configuration.
// For local development, set VITE_API_BASE_URL in frontend/.env.development.
const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
});

// ── Request Interceptor ───────────────────────────────────────
// Attach JWT token from localStorage to every outgoing request.
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// ── Response Interceptor ──────────────────────────────────────
// Redirect to /login on 401 Unauthorized responses.
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      localStorage.removeItem('access_token');
      // Only redirect if not already on the login page
      if (window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

export default api;
