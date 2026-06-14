import axios from "axios";

const axiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "/api",
  timeout: 30000,
});

axiosInstance.interceptors.request.use((config) => {
  const token = localStorage.getItem("tubeauto_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

axiosInstance.interceptors.response.use(
  (response) => response,
  (error) => {
    if (
      error.response?.status === 401 &&
      window.location.pathname !== "/login"
    ) {
      localStorage.removeItem("tubeauto_token");
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);

function testBody(key) {
  if (!key || key.startsWith("•")) return {};
  return { api_key: key };
}

export const api = {
  // App auth
  getAppStatus: () => axiosInstance.get("/auth/app-status"),
  appLogin: (password) => axiosInstance.post("/auth/app-login", { password }),
  appLogout: () => axiosInstance.post("/auth/app-logout"),

  // Google OAuth
  getAuthStatus: () => axiosInstance.get("/auth/status"),
  login: () => axiosInstance.get("/auth/login"),
  logout: () => axiosInstance.post("/auth/logout"),
  refreshToken: () => axiosInstance.post("/auth/refresh"),

  // Videos
  getVideos: (params) => axiosInstance.get("/videos", { params }),
  getVideo: (id) => axiosInstance.get(`/videos/${id}`),
  retryVideo: (id) => axiosInstance.post(`/videos/${id}/retry`),
  deleteVideo: (id) => axiosInstance.delete(`/videos/${id}`),
  triggerShort: () => axiosInstance.post("/videos/trigger/short"),
  triggerLong: () => axiosInstance.post("/videos/trigger/long"),

  // Jobs
  getJobs: (params) => axiosInstance.get("/jobs", { params }),
  getJobLogs: (id) => axiosInstance.get(`/jobs/${id}/logs`),

  // Settings
  getSettings: () => axiosInstance.get("/settings"),
  updateSettings: (data) => axiosInstance.put("/settings", data),
  testAnthropicKey: (key) => axiosInstance.post("/settings/test/anthropic", testBody(key)),
  testOpenAIKey: (key) => axiosInstance.post("/settings/test/openai", testBody(key)),
  testFalKey: (key) => axiosInstance.post("/settings/test/fal", testBody(key)),
  testApiframeKey: (key) => axiosInstance.post("/settings/test/apiframe", testBody(key)),

  // Stats
  getDashboardStats: () => axiosInstance.get("/stats/dashboard"),
  getViewsChart: () => axiosInstance.get("/stats/views-chart"),
  getCostBreakdown: () => axiosInstance.get("/stats/cost-breakdown"),
  getYouTubeStats: () => axiosInstance.get("/stats/youtube"),
  getOptimizationStats: () => axiosInstance.get("/stats/optimization"),
  updateDashboardStats: (data) => axiosInstance.post("/stats/dashboard", data),

  // YouTube
  getYouTubeQuota: () => axiosInstance.get("/youtube/quota"),
  syncYouTubeStats: () => axiosInstance.post("/youtube/sync-stats"),
};

export default axiosInstance;
