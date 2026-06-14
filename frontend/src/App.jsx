import { Routes, Route, Navigate, NavLink, useNavigate } from "react-router-dom";
import Dashboard from "./pages/Dashboard.jsx";
import Videos from "./pages/Videos.jsx";
import Schedule from "./pages/Schedule.jsx";
import Settings from "./pages/Settings.jsx";
import Connect from "./pages/Connect.jsx";
import Login from "./pages/Login.jsx";
import { api } from "./api/client";

const navItems = [
  { to: "/", label: "Dashboard", icon: "📊", end: true },
  { to: "/videos", label: "Videos", icon: "🎬" },
  { to: "/schedule", label: "Schedule", icon: "📅" },
  { to: "/settings", label: "Settings", icon: "⚙️" },
];

function ProtectedRoute({ children }) {
  const token = localStorage.getItem("tubeauto_token");
  if (!token) return <Navigate to="/login" replace />;
  return children;
}

function Layout() {
  const navigate = useNavigate();

  async function handleSignOut() {
    try {
      await api.appLogout();
    } catch {
      // ignore
    }
    localStorage.removeItem("tubeauto_token");
    navigate("/login", { replace: true });
  }

  return (
    <div className="flex min-h-screen">
      <aside className="fixed top-0 left-0 h-full w-56 bg-gray-900 border-r border-gray-800 flex flex-col">
        <div className="px-4 py-6 border-b border-gray-800">
          <div className="text-green-400 text-lg font-bold">🎥 TubeAuto</div>
          <div className="text-gray-500 text-xs mt-1">YouTube Automation</div>
        </div>
        <nav className="flex-1 px-2 py-4 space-y-1">
          {navItems.map(({ to, label, icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-green-900/50 text-green-400"
                    : "text-gray-400 hover:text-gray-200"
                }`
              }
            >
              <span>{icon}</span>
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="px-4 py-4 border-t border-gray-800">
          <button
            onClick={handleSignOut}
            className="w-full text-left text-sm text-gray-500 hover:text-gray-300 transition-colors flex items-center gap-2 px-1"
          >
            <span>↩</span>
            <span>Sign out</span>
          </button>
        </div>
      </aside>

      <main className="ml-56 flex-1 p-6">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/videos" element={<Videos />} />
          <Route path="/schedule" element={<Schedule />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="/connect" element={<Connect />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/*"
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      />
    </Routes>
  );
}
