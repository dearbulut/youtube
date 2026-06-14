import { Routes, Route, Navigate, NavLink } from "react-router-dom";
import Dashboard from "./pages/Dashboard.jsx";
import Videos from "./pages/Videos.jsx";
import Schedule from "./pages/Schedule.jsx";
import Settings from "./pages/Settings.jsx";
import Connect from "./pages/Connect.jsx";

const navItems = [
  { to: "/", label: "Dashboard", icon: "📊", end: true },
  { to: "/videos", label: "Videos", icon: "🎬" },
  { to: "/schedule", label: "Schedule", icon: "📅" },
  { to: "/settings", label: "Settings", icon: "⚙️" },
];

export default function App() {
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
