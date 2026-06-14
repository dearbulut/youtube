import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import axiosInstance from "../api/client";

export default function Login() {
  const navigate = useNavigate();
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [isFirstRun, setIsFirstRun] = useState(false);
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    axiosInstance
      .get("/auth/app-status")
      .then((r) => setIsFirstRun(!r.data.password_configured))
      .catch(() => setIsFirstRun(false))
      .finally(() => setChecking(false));
  }, []);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!password) return;
    setLoading(true);
    setError("");
    try {
      const { data } = await axiosInstance.post("/auth/app-login", { password });
      localStorage.setItem("tubeauto_token", data.token);
      navigate("/", { replace: true });
    } catch (err) {
      const msg = err.response?.data?.detail;
      setError(msg === "Incorrect password" ? "Incorrect password" : "Login failed");
    } finally {
      setLoading(false);
    }
  }

  if (checking) {
    return (
      <div className="min-h-screen bg-[#0f0f0f] flex items-center justify-center">
        <div className="w-8 h-8 border-2 border-green-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#0f0f0f] flex items-center justify-center px-4">
      <div className="w-full max-w-[400px] bg-gray-900 rounded-xl p-8 border border-gray-800 shadow-2xl">
        <div className="text-center mb-8">
          <div className="text-5xl mb-3">🎬</div>
          <h1 className="text-2xl font-bold text-white">TubeAuto</h1>
          <p className="text-gray-400 text-sm mt-1">YouTube Automation</p>
        </div>

        <h2 className="text-lg font-semibold text-white mb-6 text-center">
          {isFirstRun ? "Set your password" : "Sign in"}
        </h2>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder={isFirstRun ? "Choose a password" : "Password"}
              autoFocus
              className="w-full bg-gray-800 text-white placeholder-gray-500 rounded-lg px-4 py-3 border border-gray-700 focus:border-green-500 focus:outline-none focus:ring-1 focus:ring-green-500 transition-colors"
            />
            {error && (
              <p className="text-red-400 text-sm mt-2">{error}</p>
            )}
          </div>

          <button
            type="submit"
            disabled={loading || !password}
            className="w-full bg-green-600 hover:bg-green-500 disabled:opacity-50 disabled:cursor-not-allowed text-white font-semibold py-3 rounded-lg transition-colors"
          >
            {loading ? "Signing in…" : isFirstRun ? "Set password & sign in" : "Sign in"}
          </button>
        </form>

        {isFirstRun && (
          <p className="text-gray-500 text-xs text-center mt-4">
            This password protects your TubeAuto dashboard.
          </p>
        )}
      </div>
    </div>
  );
}
