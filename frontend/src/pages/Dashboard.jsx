import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, useEffect } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ResponsiveContainer,
} from "recharts";
import { format, formatDistanceToNow, parseISO } from "date-fns";
import { api } from "../api/client";

// ── helpers ──────────────────────────────────────────────────────────────────

function StatCard({ icon, label, value, loading }) {
  return (
    <div className="bg-gray-900 rounded-xl p-4 flex flex-col gap-1">
      {loading ? (
        <>
          <div className="h-8 w-24 bg-gray-700 rounded animate-pulse" />
          <div className="h-4 w-16 bg-gray-800 rounded animate-pulse mt-1" />
        </>
      ) : (
        <>
          <span className="text-2xl font-bold text-white">
            {icon} {value ?? "—"}
          </span>
          <span className="text-sm text-gray-400">{label}</span>
        </>
      )}
    </div>
  );
}

function StatusBadge({ status }) {
  const map = {
    uploaded: "bg-green-700 text-green-200",
    pending: "bg-gray-700 text-gray-300",
    failed: "bg-red-700 text-red-200",
  };
  const cls =
    map[status] ||
    (status?.includes("generating") || status === "uploading"
      ? "bg-blue-700 text-blue-200 animate-pulse"
      : "bg-gray-700 text-gray-300");
  return (
    <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${cls}`}>
      {status}
    </span>
  );
}

function Countdown({ target }) {
  const [display, setDisplay] = useState("");

  useEffect(() => {
    if (!target) return;
    const update = () => {
      const diff = new Date(target) - Date.now();
      if (diff <= 0) {
        setDisplay("Now");
        return;
      }
      const h = Math.floor(diff / 3600000);
      const m = Math.floor((diff % 3600000) / 60000);
      const s = Math.floor((diff % 60000) / 1000);
      setDisplay(
        `${h > 0 ? `${h}h ` : ""}${m > 0 ? `${m}m ` : ""}${s}s`
      );
    };
    update();
    const id = setInterval(update, 1000);
    return () => clearInterval(id);
  }, [target]);

  return <span className="font-mono text-green-400">{display || "—"}</span>;
}

// ── main component ────────────────────────────────────────────────────────────

export default function Dashboard() {
  const queryClient = useQueryClient();
  const [togglingAuto, setTogglingAuto] = useState(false);

  const dashboardStats = useQuery({
    queryKey: ["dashboard-stats"],
    queryFn: () => api.getDashboardStats().then((r) => r.data),
    refetchInterval: 30000,
  });

  const viewsChart = useQuery({
    queryKey: ["views-chart"],
    queryFn: () => api.getViewsChart().then((r) => r.data),
  });

  const stats = dashboardStats.data;
  const chartData = viewsChart.data || [];

  async function handleToggleAutomation() {
    if (!stats) return;
    setTogglingAuto(true);
    try {
      await api.updateSettings({
        automation_enabled: !stats.automation_enabled,
      });
      queryClient.invalidateQueries(["dashboard-stats"]);
    } catch {
      // ignore
    } finally {
      setTogglingAuto(false);
    }
  }

  return (
    <div className="space-y-6">
      {/* ── Page header ─────────────────────────────────────────────────── */}
      <div>
        <h1 className="text-2xl font-bold text-white">Dashboard</h1>
        <p className="text-gray-400 mt-1 text-sm">
          Overview of your TubeAuto automation pipeline
        </p>
      </div>

      {/* ── Channel info ─────────────────────────────────────────────────── */}
      {stats?.channel_name && (
        <div className="bg-gray-900 rounded-xl p-4 flex items-center gap-4">
          {stats.channel_thumbnail ? (
            <img
              src={stats.channel_thumbnail}
              alt="channel"
              className="w-14 h-14 rounded-full object-cover"
            />
          ) : (
            <div className="w-14 h-14 rounded-full bg-gray-700 flex items-center justify-center text-2xl">
              📺
            </div>
          )}
          <div>
            <p className="font-semibold text-white text-lg">
              {stats.channel_name}
            </p>
            {stats.subscriber_count != null && (
              <p className="text-sm text-gray-400">
                {Number(stats.subscriber_count).toLocaleString()} subscribers
              </p>
            )}
          </div>
        </div>
      )}

      {/* ── Automation status banner ─────────────────────────────────────── */}
      {dashboardStats.isLoading ? (
        <div className="h-14 bg-gray-800 rounded-xl animate-pulse" />
      ) : (
        <div
          className={`rounded-xl p-4 flex items-center justify-between ${
            stats?.automation_enabled
              ? "bg-green-900/40 border border-green-700/50"
              : "bg-red-900/40 border border-red-700/50"
          }`}
        >
          <span className="text-base font-medium text-white">
            {stats?.automation_enabled
              ? "🟢 Automation Active"
              : "🔴 Paused"}
          </span>
          <button
            onClick={handleToggleAutomation}
            disabled={togglingAuto}
            className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-colors disabled:opacity-50 ${
              stats?.automation_enabled
                ? "bg-red-700 hover:bg-red-600 text-white"
                : "bg-green-700 hover:bg-green-600 text-white"
            }`}
          >
            {togglingAuto
              ? "Saving…"
              : stats?.automation_enabled
              ? "Pause"
              : "Enable"}
          </button>
        </div>
      )}

      {/* ── Pipeline running card ─────────────────────────────────────────── */}
      {stats?.pipeline_running && (
        <div className="bg-gray-900 rounded-xl p-4 flex items-center gap-3 border border-green-700/40">
          <span className="relative flex h-3 w-3">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-500 opacity-75" />
            <span className="relative inline-flex rounded-full h-3 w-3 bg-green-500" />
          </span>
          <span className="text-white font-medium">⚙️ Pipeline Running</span>
          <span className="text-gray-400 text-sm">
            A job is currently in progress
          </span>
        </div>
      )}

      {/* ── 4 stat cards ─────────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          icon="📈"
          label="Today's Views"
          value={stats?.today_views?.toLocaleString()}
          loading={dashboardStats.isLoading}
        />
        <StatCard
          icon="🎬"
          label="Total Videos"
          value={stats?.total_videos?.toLocaleString()}
          loading={dashboardStats.isLoading}
        />
        <StatCard
          icon="$"
          label="This Month's Spend"
          value={
            stats?.monthly_spend != null
              ? `$${Number(stats.monthly_spend).toFixed(2)}`
              : null
          }
          loading={dashboardStats.isLoading}
        />
        <StatCard
          icon="👥"
          label="Subscribers"
          value={stats?.subscriber_count?.toLocaleString()}
          loading={dashboardStats.isLoading}
        />
      </div>

      {/* ── Two column: recent uploads + next scheduled ───────────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Recent uploads */}
        <div className="lg:col-span-2 bg-gray-900 rounded-xl p-4">
          <h2 className="text-base font-semibold text-white mb-3">
            Recent Uploads
          </h2>
          {dashboardStats.isLoading ? (
            <div className="space-y-2">
              {[...Array(4)].map((_, i) => (
                <div
                  key={i}
                  className="h-10 bg-gray-800 rounded animate-pulse"
                />
              ))}
            </div>
          ) : dashboardStats.isError ? (
            <p className="text-red-400 text-sm">Failed to load uploads.</p>
          ) : (stats?.recent_uploads || []).length === 0 ? (
            <p className="text-gray-500 text-sm">No uploads yet.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-gray-500 border-b border-gray-800">
                    <th className="text-left pb-2 font-medium w-20">Thumb</th>
                    <th className="text-left pb-2 font-medium">Title</th>
                    <th className="text-left pb-2 font-medium">Status</th>
                    <th className="text-right pb-2 font-medium">Views</th>
                    <th className="text-right pb-2 font-medium">Uploaded</th>
                  </tr>
                </thead>
                <tbody>
                  {(stats.recent_uploads || []).map((v) => (
                    <tr
                      key={v.id}
                      className="border-b border-gray-800/50 last:border-0"
                    >
                      <td className="py-2">
                        <div className="bg-gray-700 w-16 h-9 rounded" />
                      </td>
                      <td className="py-2 pr-3">
                        <span
                          className="text-gray-200 line-clamp-2 leading-tight"
                          title={v.title}
                        >
                          {v.title}
                        </span>
                      </td>
                      <td className="py-2">
                        <StatusBadge status={v.status} />
                      </td>
                      <td className="py-2 text-right text-gray-300">
                        {v.views?.toLocaleString() ?? "—"}
                      </td>
                      <td className="py-2 text-right text-gray-400 whitespace-nowrap">
                        {v.uploaded_at
                          ? format(
                              parseISO(v.uploaded_at),
                              "MMM d, HH:mm"
                            )
                          : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Next scheduled */}
        <div className="bg-gray-900 rounded-xl p-4">
          <h2 className="text-base font-semibold text-white mb-3">
            Next Scheduled
          </h2>
          {dashboardStats.isLoading ? (
            <div className="space-y-4">
              <div className="h-12 bg-gray-800 rounded animate-pulse" />
              <div className="h-12 bg-gray-800 rounded animate-pulse" />
            </div>
          ) : (
            <div className="space-y-4">
              <div className="space-y-1">
                <p className="text-xs text-gray-500 uppercase tracking-wide">
                  Next Short
                </p>
                {stats?.next_short_at ? (
                  <>
                    <p className="text-sm text-gray-300">
                      {format(
                        parseISO(stats.next_short_at),
                        "MMM d, HH:mm"
                      )}
                    </p>
                    <p className="text-xs text-gray-500">
                      in{" "}
                      <Countdown target={stats.next_short_at} />
                    </p>
                  </>
                ) : (
                  <p className="text-sm text-gray-500">Not scheduled</p>
                )}
              </div>
              <div className="space-y-1">
                <p className="text-xs text-gray-500 uppercase tracking-wide">
                  Next Long Video
                </p>
                {stats?.next_long_at ? (
                  <>
                    <p className="text-sm text-gray-300">
                      {format(
                        parseISO(stats.next_long_at),
                        "MMM d, HH:mm"
                      )}
                    </p>
                    <p className="text-xs text-gray-500">
                      in{" "}
                      <Countdown target={stats.next_long_at} />
                    </p>
                  </>
                ) : (
                  <p className="text-sm text-gray-500">Not scheduled</p>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* ── Views chart ───────────────────────────────────────────────────── */}
      <div className="bg-gray-900 rounded-xl p-4">
        <h2 className="text-base font-semibold text-white mb-4">
          Views – Last 30 Days
        </h2>
        {viewsChart.isLoading ? (
          <div className="h-64 bg-gray-800 rounded animate-pulse" />
        ) : viewsChart.isError ? (
          <p className="text-red-400 text-sm">Failed to load chart.</p>
        ) : (
          <ResponsiveContainer width="100%" height={256}>
            <LineChart
              data={chartData}
              margin={{ top: 4, right: 8, left: 0, bottom: 0 }}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis
                dataKey="date"
                tick={{ fill: "#9ca3af", fontSize: 11 }}
                tickFormatter={(v) => {
                  try {
                    return format(parseISO(v), "MMM d");
                  } catch {
                    return v;
                  }
                }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                tick={{ fill: "#9ca3af", fontSize: 11 }}
                axisLine={false}
                tickLine={false}
                width={40}
              />
              <Tooltip
                contentStyle={{
                  background: "#111827",
                  border: "1px solid #374151",
                  borderRadius: 8,
                  color: "#f9fafb",
                }}
                labelFormatter={(v) => {
                  try {
                    return format(parseISO(v), "MMM d, yyyy");
                  } catch {
                    return v;
                  }
                }}
              />
              <Line
                type="monotone"
                dataKey="views"
                stroke="#22c55e"
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 4 }}
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
