import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";

function addDays(date, days) {
  const d = new Date(date);
  d.setDate(d.getDate() + days);
  return d;
}

function formatDate(date) {
  return date.toLocaleDateString("en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
  });
}

function formatDateShort(date) {
  return date.toLocaleDateString("en-US", { weekday: "short", day: "numeric" });
}

function formatTime(date) {
  return date.toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

function buildSchedule(settings, days = 7) {
  if (!settings) return [];
  const shortsPerDay = settings.shorts_per_day ?? 2;
  const longInterval = settings.long_video_interval_days ?? 3;
  const shortsTime = settings.shorts_upload_time ?? "10:00";
  const longTime = settings.long_upload_time ?? "18:00";

  const events = [];
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const [sh, sm] = shortsTime.split(":").map(Number);
  const [lh, lm] = longTime.split(":").map(Number);

  for (let i = 0; i < days; i++) {
    const day = addDays(today, i);

    for (let s = 0; s < shortsPerDay; s++) {
      const hour = (sh + s * 4) % 24;
      const dt = new Date(day);
      dt.setHours(hour, sm, 0, 0);
      events.push({ date: dt, type: "short", label: "Short Video" });
    }

    if (i % longInterval === 0) {
      const dt = new Date(day);
      dt.setHours(lh, lm, 0, 0);
      events.push({ date: dt, type: "long", label: "Long Video" });
    }
  }

  return events.sort((a, b) => a.date - b.date);
}

function getWeekDays() {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const day = today.getDay();
  const monday = addDays(today, day === 0 ? -6 : 1 - day);
  return Array.from({ length: 7 }, (_, i) => addDays(monday, i));
}

export default function Schedule() {
  const queryClient = useQueryClient();

  const { data: settings, isLoading } = useQuery(
    ["settings"],
    () => api.getSettings().then((r) => r.data)
  );

  const [form, setForm] = useState(null);

  if (settings && form === null) {
    setForm({
      shorts_per_day: settings.shorts_per_day ?? 2,
      long_video_interval_days: settings.long_video_interval_days ?? 3,
      shorts_upload_time: settings.shorts_upload_time ?? "10:00",
      long_upload_time: settings.long_upload_time ?? "18:00",
      long_video_duration: settings.long_video_duration ?? 60,
    });
  }

  const updateSettings = useMutation(
    (data) => api.updateSettings(data).then((r) => r.data),
    { onSuccess: () => queryClient.invalidateQueries(["settings"]) }
  );

  const fv = form ?? {
    shorts_per_day: 2,
    long_video_interval_days: 3,
    shorts_upload_time: "10:00",
    long_upload_time: "18:00",
    long_video_duration: 60,
  };

  const schedule = buildSchedule(fv);
  const weekDays = getWeekDays();

  const eventsByDay = {};
  schedule.forEach((ev) => {
    const key = ev.date.toDateString();
    if (!eventsByDay[key]) eventsByDay[key] = [];
    eventsByDay[key].push(ev);
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-2 border-green-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold text-white">Schedule</h1>
        <p className="text-gray-400 mt-1">Configure your automated upload schedule.</p>
      </div>

      {/* Settings card */}
      <div className="bg-gray-900 rounded-xl border border-gray-800 p-6 space-y-6">
        <h2 className="text-lg font-semibold text-white">Schedule Settings</h2>

        {/* Shorts per day */}
        <div>
          <div className="flex justify-between mb-2">
            <label className="text-sm font-medium text-gray-300">Shorts per day</label>
            <span className="text-sm font-semibold text-green-400">{fv.shorts_per_day}</span>
          </div>
          <input
            type="range"
            min={1}
            max={4}
            value={fv.shorts_per_day}
            onChange={(e) =>
              setForm((f) => ({ ...f, shorts_per_day: Number(e.target.value) }))
            }
            className="w-full accent-green-500"
          />
          <div className="flex justify-between text-xs text-gray-500 mt-1">
            <span>1</span>
            <span>2</span>
            <span>3</span>
            <span>4</span>
          </div>
        </div>

        {/* Long video interval */}
        <div>
          <div className="flex justify-between mb-2">
            <label className="text-sm font-medium text-gray-300">Long video interval</label>
            <span className="text-sm font-semibold text-green-400">
              Every {fv.long_video_interval_days} day{fv.long_video_interval_days > 1 ? "s" : ""}
            </span>
          </div>
          <input
            type="range"
            min={1}
            max={7}
            value={fv.long_video_interval_days}
            onChange={(e) =>
              setForm((f) => ({ ...f, long_video_interval_days: Number(e.target.value) }))
            }
            className="w-full accent-green-500"
          />
          <div className="flex justify-between text-xs text-gray-500 mt-1">
            {[1, 2, 3, 4, 5, 6, 7].map((n) => (
              <span key={n}>{n}</span>
            ))}
          </div>
        </div>

        {/* Upload times */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Shorts upload time (UTC)
            </label>
            <input
              type="time"
              value={fv.shorts_upload_time}
              onChange={(e) =>
                setForm((f) => ({ ...f, shorts_upload_time: e.target.value }))
              }
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-green-500"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Long video upload time (UTC)
            </label>
            <input
              type="time"
              value={fv.long_upload_time}
              onChange={(e) =>
                setForm((f) => ({ ...f, long_upload_time: e.target.value }))
              }
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-green-500"
            />
          </div>
        </div>

        {/* Long video duration */}
        <div>
          <label className="block text-sm font-medium text-gray-300 mb-2">
            Long video duration
          </label>
          <select
            value={fv.long_video_duration}
            onChange={(e) =>
              setForm((f) => ({ ...f, long_video_duration: Number(e.target.value) }))
            }
            className="w-full sm:w-48 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-green-500"
          >
            <option value={30}>30 minutes</option>
            <option value={60}>60 minutes</option>
            <option value={120}>120 minutes</option>
            <option value={180}>180 minutes</option>
          </select>
        </div>

        {/* Save */}
        <div className="flex items-center gap-3 pt-2">
          <button
            onClick={() => updateSettings.mutate(fv)}
            disabled={updateSettings.isLoading}
            className="px-4 py-2 bg-green-600 hover:bg-green-500 disabled:opacity-50 text-white text-sm font-medium rounded-lg transition-colors"
          >
            {updateSettings.isLoading ? "Saving..." : "Save Settings"}
          </button>
          {updateSettings.isSuccess && (
            <span className="text-green-400 text-sm">Settings saved.</span>
          )}
          {updateSettings.isError && (
            <span className="text-red-400 text-sm">Failed to save.</span>
          )}
        </div>
      </div>

      {/* Next 7 days preview */}
      <div className="bg-gray-900 rounded-xl border border-gray-800 p-6">
        <h2 className="text-lg font-semibold text-white mb-4">Next 7 Days</h2>
        <div className="space-y-0">
          {schedule.map((ev, idx) => (
            <div
              key={idx}
              className="flex items-center gap-4 py-2.5 border-b border-gray-800 last:border-0"
            >
              <div className="w-32 text-sm text-gray-400 shrink-0">{formatDate(ev.date)}</div>
              <div className="w-14 text-sm text-gray-400 shrink-0">{formatTime(ev.date)}</div>
              <div className="flex items-center gap-2">
                <span
                  className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                    ev.type === "short"
                      ? "bg-blue-900/60 text-blue-300"
                      : "bg-purple-900/60 text-purple-300"
                  }`}
                >
                  {ev.type === "short" ? "SHORT" : "LONG"}
                </span>
                <span className="text-sm text-white">{ev.label}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Weekly calendar grid */}
      <div className="bg-gray-900 rounded-xl border border-gray-800 p-6">
        <h2 className="text-lg font-semibold text-white mb-4">Weekly Calendar</h2>
        <div className="grid grid-cols-7 gap-1">
          {["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].map((d) => (
            <div
              key={d}
              className="text-center text-xs font-semibold text-gray-500 py-2 uppercase tracking-wide"
            >
              {d}
            </div>
          ))}
          {weekDays.map((day) => {
            const key = day.toDateString();
            const dayEvents = eventsByDay[key] ?? [];
            const isToday = key === new Date().toDateString();
            return (
              <div
                key={key}
                className={`min-h-[80px] rounded-lg p-1.5 border ${
                  isToday
                    ? "border-green-600 bg-green-950/20"
                    : "border-gray-800 bg-gray-800/30"
                }`}
              >
                <div
                  className={`text-xs font-medium mb-1 ${
                    isToday ? "text-green-400" : "text-gray-400"
                  }`}
                >
                  {formatDateShort(day)}
                </div>
                <div className="space-y-0.5">
                  {dayEvents.map((ev, i) => (
                    <div
                      key={i}
                      className={`text-xs rounded px-1 py-0.5 truncate ${
                        ev.type === "short"
                          ? "bg-blue-900/50 text-blue-300"
                          : "bg-purple-900/50 text-purple-300"
                      }`}
                    >
                      {formatTime(ev.date)} {ev.type === "short" ? "Short" : "Long"}
                    </div>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
