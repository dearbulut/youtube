import React from "react";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

function formatDuration(seconds) {
  if (!seconds && seconds !== 0) return "--:--";
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}

function formatDate(dateStr) {
  if (!dateStr) return "";
  const d = new Date(dateStr);
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

const STATUS_BADGE = {
  uploaded: "bg-green-600 text-green-100",
  pending: "bg-gray-600 text-gray-200",
  failed: "bg-red-600 text-red-100",
};

const ACTIVE_STATUSES = [
  "generating_video",
  "generating_audio",
  "generating_thumbnail",
  "uploading",
  "assembling",
  "writing_seo",
];

function StatusBadge({ status }) {
  let cls = "text-xs font-semibold px-2 py-0.5 rounded-full ";
  if (STATUS_BADGE[status]) {
    cls += STATUS_BADGE[status];
  } else if (ACTIVE_STATUSES.includes(status)) {
    cls += "bg-blue-600 text-blue-100 animate-pulse";
  } else {
    cls += "bg-gray-600 text-gray-200";
  }

  const label = status
    ? status.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())
    : "Unknown";

  return <span className={cls}>{label}</span>;
}

export default function VideoCard({ video, onClick, onRetry, onDelete }) {
  const {
    id,
    type,
    status,
    title,
    youtube_id,
    thumbnail_path,
    duration_seconds,
    cost_usd,
    views,
    uploaded_at,
    created_at,
  } = video || {};

  const thumbnailFilename = thumbnail_path ? thumbnail_path.split("/").pop() : null;
  const thumbnailSrc = thumbnailFilename
    ? `${API_BASE}/thumbnails/${thumbnailFilename}`
    : null;

  const displayDate = uploaded_at || created_at;

  function handleClick(e) {
    if (typeof onClick === "function") onClick(video);
  }

  function handleRetry(e) {
    e.stopPropagation();
    if (typeof onRetry === "function") onRetry(video);
  }

  function handleDelete(e) {
    e.stopPropagation();
    if (typeof onDelete === "function") onDelete(video);
  }

  return (
    <div
      className="bg-gray-900 border border-gray-700 rounded-xl overflow-hidden cursor-pointer hover:border-gray-500 transition-colors flex flex-col"
      onClick={handleClick}
    >
      {/* Thumbnail */}
      <div className="relative aspect-video bg-gray-800">
        {thumbnailSrc ? (
          <img
            src={thumbnailSrc}
            alt={title || "Video thumbnail"}
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-4xl text-gray-600">
            🎬
          </div>
        )}
        {/* Status badge */}
        <div className="absolute top-2 right-2">
          <StatusBadge status={status} />
        </div>
      </div>

      {/* Content */}
      <div className="p-3 flex flex-col gap-2 flex-1">
        {/* Title */}
        <p className="font-medium text-gray-100 text-sm leading-snug line-clamp-2">
          {title || "Untitled Video"}
        </p>

        {/* Duration + Type */}
        <div className="flex items-center gap-2 text-xs text-gray-400">
          <span>{formatDuration(duration_seconds)}</span>
          <span
            className={`px-1.5 py-0.5 rounded text-xs font-medium ${
              type === "short"
                ? "bg-purple-900 text-purple-200"
                : "bg-indigo-900 text-indigo-200"
            }`}
          >
            {type === "short" ? "Short" : "Long"}
          </span>
        </div>

        {/* Views + Cost */}
        <div className="flex items-center gap-3 text-xs text-gray-400">
          <span>👁 {views != null ? views.toLocaleString() : "—"}</span>
          <span>💰 ${cost_usd != null ? Number(cost_usd).toFixed(2) : "0.00"}</span>
        </div>

        {/* Date */}
        <div className="text-xs text-gray-500">{formatDate(displayDate)}</div>

        {/* Actions */}
        <div className="flex items-center gap-2 mt-auto pt-1">
          {youtube_id && (
            <a
              href={`https://www.youtube.com/watch?v=${youtube_id}`}
              target="_blank"
              rel="noopener noreferrer"
              onClick={(e) => e.stopPropagation()}
              className="text-xs px-2 py-1 rounded bg-red-700 hover:bg-red-600 text-white transition-colors"
            >
              YouTube
            </a>
          )}
          {status === "failed" && (
            <button
              onClick={handleRetry}
              className="text-xs px-2 py-1 rounded bg-yellow-700 hover:bg-yellow-600 text-white transition-colors"
            >
              Retry
            </button>
          )}
          <button
            onClick={handleDelete}
            className="text-xs px-2 py-1 rounded bg-gray-700 hover:bg-red-800 text-gray-200 transition-colors ml-auto"
          >
            Delete
          </button>
        </div>
      </div>
    </div>
  );
}
