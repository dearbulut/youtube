import axios from "axios";

const axiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "http://localhost:8000",
  timeout: 30000,
});

axiosInstance.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      window.location.href = "/connect";
    }
    return Promise.reject(error);
  }
);

export const api = {
  // Auth
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
  getJobs: () => axiosInstance.get("/jobs"),
  getJobLogs: (id) => axiosInstance.get(`/jobs/${id}/logs`),

  // Settings
  getSettings: () => axiosInstance.get("/settings"),
  updateSettings: (data) => axiosInstance.put("/settings", data),
  testAnthropicKey: () => axiosInstance.post("/settings/test/anthropic"),
  testOpenAIKey: () => axiosInstance.post("/settings/test/openai"),
  testFalKey: () => axiosInstance.post("/settings/test/fal"),
  testApiframeKey: () => axiosInstance.post("/settings/test/apiframe"),

  // Stats
  getDashboardStats: () => axiosInstance.get("/stats/dashboard"),
  getViewsChart: () => axiosInstance.get("/stats/views-chart"),
  getCostBreakdown: () => axiosInstance.get("/stats/cost-breakdown"),
  getYouTubeStats: () => axiosInstance.get("/stats/youtube"),

  // YouTube
  getYouTubeQuota: () => axiosInstance.get("/youtube/quota"),
  syncYouTubeStats: () => axiosInstance.post("/youtube/sync-stats"),
};

export default axiosInstance;
