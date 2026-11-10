import axios from "axios";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://localhost:8000",
  headers: {
    "Content-Type": "application/json",
  },
  timeout: 30000,
  withCredentials: true,
});

// Attach access token to normal requests.
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("access_token");

    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    } else {
      delete config.headers.Authorization;
    }

    return config;
  },
  (error) => Promise.reject(error)
);

// Prevent multiple simultaneous refresh requests.
let refreshPromise = null;

api.interceptors.response.use(
  (response) => response,

  async (error) => {
    const originalRequest = error.config;

    if (!originalRequest || error.response?.status !== 401) {
      return Promise.reject(error);
    }

    const requestUrl = originalRequest.url || "";

    // Never refresh for login, registration, or refresh requests.
    const excludedUrls = [
      "/auth/login",
      "/auth/register",
      "/auth/refresh",
    ];

    if (
      excludedUrls.some((url) => requestUrl.includes(url)) ||
      originalRequest._retry
    ) {
      return Promise.reject(error);
    }

    originalRequest._retry = true;

    try {
      if (!refreshPromise) {
        refreshPromise = api
          .post("/auth/refresh", {})
          .then((response) => {
            const newToken = response.data.access_token;

            if (!newToken) {
              throw new Error("No access token returned.");
            }

            localStorage.setItem("access_token", newToken);

            return newToken;
          })
          .finally(() => {
            refreshPromise = null;
          });
      }

      const newToken = await refreshPromise;

      originalRequest.headers = originalRequest.headers || {};
      originalRequest.headers.Authorization = `Bearer ${newToken}`;

      return api(originalRequest);

    } catch (refreshError) {
      localStorage.removeItem("access_token");

      // Reload so protected routes can redirect to login.
      window.location.href = "/login";

      return Promise.reject(refreshError);
    }
  }
);

export default api;