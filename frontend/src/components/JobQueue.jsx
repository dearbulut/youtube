import React from "react";

function formatTime(dateStr) {
  if (!dateStr) return "";
  const d = new Date(dateStr);
  return d.toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}

function StatusIcon({ status }) {
  const running = [
    "generating_video",
    "generating_audio",
    "generating_thumbnail",
    "uploading",
    "assembling",
    "writing_seo",
    "writing_idea",
    "running",
    "in_progress",
  ];

  if (status === "uploaded" || status === "done" || status === "success") {
    return <span title="Done">✅</span>;
  }
  if (status === "failed" || status === "error") {
    return <span title="Failed">❌</span>;
  }
  if (running.includes(status)) {
    return (
      <span className="inline-flex items-center gap-1">
        <span className="w-2 h-2 rounded-full bg-blue-400 animate-pulse inline-block" />
        ⏳
      </span>
    );
  }
  return <span title={status}>⏳</span>;
}

function isRunning(status) {
  const runningStatuses = [
    "generating_video",
    "generating_audio",
    "generating_thumbnail",
    "uploading",
    "assembling",
    "writing_seo",
    "writing_idea",
    "running",
    "in_progress",
  ];
  return runningStatuses.includes(status);
}

function isFailed(status) {
  return status === "failed" || status === "error";
}

export default function JobQueue({ jobs = [] }) {
  const recent = jobs.slice(0, 10);

  return (
    <div className="bg-gray-900 border border-gray-700 rounded-xl p-4">
      <h2 className="text-gray-100 font-semibold text-base mb-3">Job Queue</h2>

      {recent.length === 0 ? (
        <p className="text-gray-500 text-sm text-center py-4">No recent jobs</p>
      ) : (
        <ul className="flex flex-col gap-1">
          {recent.map((job, i) => {
            const running = isRunning(job.status || job.step);
            const failed = isFailed(job.status || job.step);
            const stepLabel = (job.step || job.status || "unknown")
              .replace(/_/g, " ")
              .replace(/\b\w/g, (c) => c.toUpperCase());

            return (
              <li
                key={job.id || i}
                className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors ${
                  running
                    ? "bg-blue-950 border border-blue-800"
                    : failed
                    ? "bg-red-950 border border-red-800"
                    : "bg-gray-800 border border-transparent"
                }`}
              >
                {/* Status icon */}
                <span className="text-base flex-shrink-0">
                  <StatusIcon status={job.status || job.step} />
                </span>

                {/* Step name */}
                <span
                  className={`flex-1 font-medium truncate ${
                    failed
                      ? "text-red-400"
                      : running
                      ? "text-blue-300"
                      : "text-gray-200"
                  }`}
                >
                  {stepLabel}
                </span>

                {/* Video ID */}
                {job.video_id && (
                  <span className="text-xs text-gray-500 flex-shrink-0">
                    #{job.video_id}
                  </span>
                )}

                {/* Started time */}
                {(job.started_at || job.created_at) && (
                  <span className="text-xs text-gray-600 flex-shrink-0">
                    {formatTime(job.started_at || job.created_at)}
                  </span>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
