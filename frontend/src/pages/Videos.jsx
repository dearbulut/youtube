import { useState, useEffect, useRef } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { format, parseISO } from "date-fns";
import { api } from "../api/client";

// ── helpers ──────────────────────────────────────────────────────────────────

function statusStyle(status) {
  if (!status) return "bg-gray-700 text-gray-300";
  if (status === "uploaded") return "bg-green-700/80 text-green-200";
  if (status === "pending") return "bg-gray-700 text-gray-300";
  if (status === "failed") return "bg-red-700/80 text-red-200";
  if (
    status.includes("generating") ||
    status === "uploading" ||
    status === "processing"
  )
    return "bg-blue-700/80 text-blue-200 animate-pulse";
  return "bg-gray-700 text-gray-300";
}

function StatusBadge({ status }) {
  return (
    <span
      className={`text-xs px-2 py-0.5 rounded-full font-medium ${statusStyle(
        status
      )}`}
    >
      {status ?? "unknown"}
    </span>
  );
}

function Toast({ message, type = "info", onClose }) {
  useEffect(() => {
    const id = setTimeout(onClose, 4000);
    return () => clearTimeout(id);
  }, [onClose]);

  const bg =
    type === "success"
      ? "bg-green-800 border-green-600"
      : type === "error"
      ? "bg-red-900 border-red-600"
      : "bg-gray-800 border-gray-600";

  return (
    <div
      className={`fixed bottom-6 right-6 z-50 flex items-center gap-3 px-4 py-3 rounded-xl border shadow-xl text-sm text-white ${bg}`}
    >
      <span>{message}</span>
      <button onClick={onClose} className="text-gray-400 hover:text-white ml-2">
        ✕
      </button>
    </div>
  );
}

const STEP_ICONS = {
  done: "✅",
  failed: "❌",
  running: "⏳",
  pending: "⬜",
};

function stepIcon(status) {
  if (status === "done" || status === "completed" || status === "success")
    return STEP_ICONS.done;
  if (status === "failed" || status === "error") return STEP_ICONS.failed;
  if (status === "running" || status === "in_progress") return STEP_ICONS.running;
  return STEP_ICONS.pending;
}

// ── VideoCard ─────────────────────────────────────────────────────────────────

function VideoCard({ video, onClick }) {
  const thumbnailUrl = video.thumbnail_path
    ? `/storage/thumbnails/${video.thumbnail_path.split("/").pop()}`
    : null;

  return (
    <div
      className="bg-gray-900 rounded-xl overflow-hidden cursor-pointer hover:ring-1 hover:ring-gray-600 transition-all group"
      onClick={() => onClick(video)}
    >
      {/* Thumbnail */}
      <div className="relative aspect-video bg-gray-800">
        {thumbnailUrl ? (
          <img
            src={thumbnailUrl}
            alt={video.title}
            className="w-full h-full object-cover"
            onError={(e) => {
              e.target.style.display = "none";
              e.target.nextSibling.style.display = "flex";
            }}
          />
        ) : null}
        <div
          className={`absolute inset-0 flex items-center justify-center text-4xl text-gray-600 ${
            thumbnailUrl ? "hidden" : "flex"
          }`}
        >
          {video.type === "short" ? "📱" : "🎬"}
        </div>
        {/* Duration badge */}
        {video.duration && (
          <span className="absolute bottom-1 right-1 bg-black/80 text-white text-xs px-1.5 py-0.5 rounded">
            {video.duration}
          </span>
        )}
      </div>

      {/* Info */}
      <div className="p-3 space-y-2">
        <p className="text-sm text-gray-100 font-medium line-clamp-2 leading-snug">
          {video.title || "Untitled"}
        </p>
        <div className="flex items-center justify-between">
          <StatusBadge status={video.status} />
          <span className="text-xs text-gray-500">
            {video.type === "short" ? "Short" : "Long"}
          </span>
        </div>
        <div className="flex items-center justify-between text-xs text-gray-500">
          <span>
            {video.views != null ? `${video.views.toLocaleString()} views` : "—"}
          </span>
          {video.cost != null && <span>${Number(video.cost).toFixed(3)}</span>}
        </div>
        {video.uploaded_at && (
          <p className="text-xs text-gray-600">
            {format(parseISO(video.uploaded_at), "MMM d, yyyy HH:mm")}
          </p>
        )}

        {/* Action buttons */}
        <div
          className="flex gap-2 pt-1"
          onClick={(e) => e.stopPropagation()}
        >
          {video.youtube_url && (
            <a
              href={video.youtube_url}
              target="_blank"
              rel="noreferrer"
              className="flex-1 text-center text-xs bg-gray-800 hover:bg-gray-700 text-gray-200 py-1 rounded-lg transition-colors"
            >
              ▶ YouTube
            </a>
          )}
          {video.status === "failed" && (
            <RetryButton videoId={video.id} />
          )}
          <DeleteButton videoId={video.id} />
        </div>
      </div>
    </div>
  );
}

function RetryButton({ videoId }) {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: () => api.retryVideo(videoId),
    onSuccess: () => queryClient.invalidateQueries(["videos"]),
  });
  return (
    <button
      onClick={() => mutation.mutate()}
      disabled={mutation.isPending}
      className="flex-1 text-xs bg-blue-800 hover:bg-blue-700 text-white py-1 rounded-lg transition-colors disabled:opacity-50"
    >
      {mutation.isPending ? "…" : "🔄 Retry"}
    </button>
  );
}

function DeleteButton({ videoId }) {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: () => api.deleteVideo(videoId),
    onMutate: async () => {
      await queryClient.cancelQueries(["videos"]);
      const prev = queryClient.getQueriesData(["videos"]);
      queryClient.setQueriesData(["videos"], (old) => {
        if (!old) return old;
        return {
          ...old,
          data: {
            ...old.data,
            videos: (old.data?.videos || []).filter((v) => v.id !== videoId),
          },
        };
      });
      return { prev };
    },
    onError: (_e, _v, ctx) => {
      if (ctx?.prev) {
        ctx.prev.forEach(([key, data]) =>
          queryClient.setQueryData(key, data)
        );
      }
    },
    onSettled: () => queryClient.invalidateQueries(["videos"]),
  });
  return (
    <button
      onClick={() => {
        if (window.confirm("Delete this video?")) mutation.mutate();
      }}
      disabled={mutation.isPending}
      className="text-xs bg-gray-800 hover:bg-red-900 text-gray-400 hover:text-red-300 py-1 px-2 rounded-lg transition-colors disabled:opacity-50"
    >
      🗑
    </button>
  );
}

// ── SlideOver ─────────────────────────────────────────────────────────────────

function SlideOver({ video, onClose }) {
  const [selectedJobId, setSelectedJobId] = useState(null);

  const jobsQuery = useQuery({
    queryKey: ["video-jobs", video?.id],
    queryFn: () =>
      api
        .getJobs({ video_id: video.id })
        .then((r) => r.data),
    enabled: !!video,
  });

  const jobs = jobsQuery.data?.jobs || jobsQuery.data || [];

  const activeJob =
    jobs.find((j) => j.id === selectedJobId) || jobs[0] || null;

  const logsQuery = useQuery({
    queryKey: ["job-logs", activeJob?.id],
    queryFn: () => api.getJobLogs(activeJob.id).then((r) => r.data),
    enabled: !!activeJob?.id,
    refetchInterval: activeJob?.status === "running" ? 3000 : false,
  });

  const logsRef = useRef(null);
  useEffect(() => {
    if (logsRef.current) {
      logsRef.current.scrollTop = logsRef.current.scrollHeight;
    }
  }, [logsQuery.data]);

  if (!video) return null;

  const thumbnailUrl = video.thumbnail_path
    ? `/storage/thumbnails/${video.thumbnail_path.split("/").pop()}`
    : null;

  return (
    <>
      {/* Overlay */}
      <div
        className="fixed inset-0 bg-black/60 z-40"
        onClick={onClose}
      />
      {/* Panel */}
      <div className="fixed right-0 top-0 h-full w-full max-w-xl bg-gray-950 border-l border-gray-800 z-50 flex flex-col overflow-hidden shadow-2xl">
        {/* Header */}
        <div className="flex items-start justify-between p-4 border-b border-gray-800 shrink-0">
          <div className="flex gap-3 items-start">
            {thumbnailUrl ? (
              <img
                src={thumbnailUrl}
                alt=""
                className="w-20 h-11 rounded object-cover bg-gray-800"
              />
            ) : (
              <div className="w-20 h-11 rounded bg-gray-800 flex items-center justify-center text-2xl">
                {video.type === "short" ? "📱" : "🎬"}
              </div>
            )}
            <div className="min-w-0">
              <p className="text-white font-medium text-sm leading-snug line-clamp-3">
                {video.title || "Untitled"}
              </p>
              <div className="flex items-center gap-2 mt-1">
                <StatusBadge status={video.status} />
                <span className="text-xs text-gray-500">{video.type}</span>
              </div>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white ml-2 text-xl leading-none shrink-0"
          >
            ✕
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-4 space-y-5">
          {/* Details */}
          <div className="grid grid-cols-2 gap-3 text-sm">
            {[
              ["Duration", video.duration],
              ["Views", video.views?.toLocaleString()],
              ["Cost", video.cost != null ? `$${Number(video.cost).toFixed(4)}` : null],
              [
                "Uploaded",
                video.uploaded_at
                  ? format(parseISO(video.uploaded_at), "MMM d, yyyy HH:mm")
                  : null,
              ],
              ["Type", video.type],
              ["ID", video.id],
            ].map(([k, v]) =>
              v ? (
                <div key={k}>
                  <p className="text-xs text-gray-500">{k}</p>
                  <p className="text-gray-200">{v}</p>
                </div>
              ) : null
            )}
          </div>

          {video.youtube_url && (
            <a
              href={video.youtube_url}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-2 text-sm text-green-400 hover:text-green-300"
            >
              ▶ Watch on YouTube ↗
            </a>
          )}

          {/* Jobs */}
          {jobsQuery.isLoading ? (
            <div className="space-y-2">
              {[...Array(3)].map((_, i) => (
                <div key={i} className="h-8 bg-gray-800 rounded animate-pulse" />
              ))}
            </div>
          ) : jobs.length === 0 ? (
            <p className="text-gray-500 text-sm">No jobs found for this video.</p>
          ) : (
            <>
              {/* Job selector */}
              {jobs.length > 1 && (
                <div className="flex gap-2 overflow-x-auto pb-1">
                  {jobs.map((j) => (
                    <button
                      key={j.id}
                      onClick={() => setSelectedJobId(j.id)}
                      className={`text-xs px-3 py-1 rounded-full whitespace-nowrap border transition-colors ${
                        (activeJob?.id === j.id)
                          ? "bg-gray-700 border-gray-500 text-white"
                          : "border-gray-700 text-gray-400 hover:text-gray-200"
                      }`}
                    >
                      {j.type || `Job ${j.id}`}
                    </button>
                  ))}
                </div>
              )}

              {/* Job steps timeline */}
              {activeJob && (
                <div>
                  <p className="text-xs text-gray-500 uppercase tracking-wide mb-2">
                    Pipeline Steps
                  </p>
                  <div className="space-y-1">
                    {(activeJob.steps || []).map((step, i) => (
                      <div
                        key={i}
                        className="flex items-center gap-3 text-sm py-1.5 border-b border-gray-800/50 last:border-0"
                      >
                        <span className="text-base w-5 shrink-0">
                          {stepIcon(step.status)}
                        </span>
                        <span className="flex-1 text-gray-200">
                          {step.name || step.step}
                        </span>
                        {step.duration != null && (
                          <span className="text-xs text-gray-500 shrink-0">
                            {typeof step.duration === "number"
                              ? `${step.duration.toFixed(1)}s`
                              : step.duration}
                          </span>
                        )}
                      </div>
                    ))}
                    {(!activeJob.steps || activeJob.steps.length === 0) && (
                      <p className="text-gray-600 text-xs">No step data.</p>
                    )}
                  </div>
                </div>
              )}

              {/* Logs */}
              {activeJob && (
                <div>
                  <p className="text-xs text-gray-500 uppercase tracking-wide mb-2">
                    Logs
                  </p>
                  <div
                    ref={logsRef}
                    className="bg-gray-900 rounded-lg p-3 h-48 overflow-y-auto font-mono text-xs text-green-400 whitespace-pre-wrap leading-relaxed"
                  >
                    {logsQuery.isLoading ? (
                      <span className="text-gray-600">Loading logs…</span>
                    ) : logsQuery.isError ? (
                      <span className="text-red-400">Failed to load logs.</span>
                    ) : (
                      logsQuery.data?.logs ||
                      logsQuery.data ||
                      "No logs available."
                    )}
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function Videos() {
  const queryClient = useQueryClient();
  const [filters, setFilters] = useState({ type: "all", status: "all", page: 1 });
  const [selectedVideo, setSelectedVideo] = useState(null);
  const [toast, setToast] = useState(null);

  const showToast = (message, type = "info") =>
    setToast({ message, type, key: Date.now() });

  const videosQuery = useQuery({
    queryKey: ["videos", filters],
    queryFn: () =>
      api
        .getVideos({
          type: filters.type !== "all" ? filters.type : undefined,
          status: filters.status !== "all" ? filters.status : undefined,
          page: filters.page,
        })
        .then((r) => r.data),
    keepPreviousData: true,
  });

  const triggerShort = useMutation({
    mutationFn: () => api.triggerShort(),
    onSuccess: () => {
      showToast("⚡ Short video generation triggered!", "success");
      queryClient.invalidateQueries(["videos"]);
    },
    onError: () => showToast("Failed to trigger short generation.", "error"),
  });

  const triggerLong = useMutation({
    mutationFn: () => api.triggerLong(),
    onSuccess: () => {
      showToast("⚡ Long video generation triggered!", "success");
      queryClient.invalidateQueries(["videos"]);
    },
    onError: () => showToast("Failed to trigger long generation.", "error"),
  });

  function handleTriggerShort() {
    if (window.confirm("Generate a new Short video now?")) {
      triggerShort.mutate();
    }
  }

  function handleTriggerLong() {
    if (window.confirm("Generate a new Long video now?")) {
      triggerLong.mutate();
    }
  }

  const videos =
    videosQuery.data?.videos ||
    videosQuery.data?.items ||
    (Array.isArray(videosQuery.data) ? videosQuery.data : []);

  const totalPages = videosQuery.data?.total_pages || videosQuery.data?.pages || 1;

  function setFilter(key, value) {
    setFilters((prev) => ({ ...prev, [key]: value, page: 1 }));
  }

  return (
    <div className="space-y-6">
      {/* ── Header ──────────────────────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-white">Videos</h1>
          <p className="text-gray-400 text-sm mt-0.5">
            Manage your generated videos
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={handleTriggerShort}
            disabled={triggerShort.isPending}
            className="flex items-center gap-1.5 px-4 py-2 bg-purple-700 hover:bg-purple-600 text-white text-sm font-medium rounded-lg transition-colors disabled:opacity-50"
          >
            ⚡ Generate Short
          </button>
          <button
            onClick={handleTriggerLong}
            disabled={triggerLong.isPending}
            className="flex items-center gap-1.5 px-4 py-2 bg-blue-700 hover:bg-blue-600 text-white text-sm font-medium rounded-lg transition-colors disabled:opacity-50"
          >
            ⚡ Generate Long
          </button>
        </div>
      </div>

      {/* ── Filter bar ──────────────────────────────────────────────────── */}
      <div className="flex gap-3 flex-wrap">
        <div className="flex items-center gap-2">
          <label className="text-xs text-gray-500">Type</label>
          <select
            value={filters.type}
            onChange={(e) => setFilter("type", e.target.value)}
            className="bg-gray-800 border border-gray-700 text-gray-200 text-sm rounded-lg px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-gray-500"
          >
            <option value="all">All</option>
            <option value="short">Short</option>
            <option value="long">Long</option>
          </select>
        </div>
        <div className="flex items-center gap-2">
          <label className="text-xs text-gray-500">Status</label>
          <select
            value={filters.status}
            onChange={(e) => setFilter("status", e.target.value)}
            className="bg-gray-800 border border-gray-700 text-gray-200 text-sm rounded-lg px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-gray-500"
          >
            <option value="all">All</option>
            <option value="uploaded">Uploaded</option>
            <option value="pending">Pending</option>
            <option value="generating">Generating</option>
            <option value="failed">Failed</option>
          </select>
        </div>
      </div>

      {/* ── Grid ────────────────────────────────────────────────────────── */}
      {videosQuery.isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="bg-gray-900 rounded-xl overflow-hidden">
              <div className="aspect-video bg-gray-800 animate-pulse" />
              <div className="p-3 space-y-2">
                <div className="h-4 bg-gray-800 rounded animate-pulse" />
                <div className="h-4 bg-gray-800 rounded w-3/4 animate-pulse" />
              </div>
            </div>
          ))}
        </div>
      ) : videosQuery.isError ? (
        <div className="text-center py-20">
          <p className="text-red-400">Failed to load videos.</p>
          <button
            onClick={() => videosQuery.refetch()}
            className="mt-3 text-sm text-gray-400 underline"
          >
            Try again
          </button>
        </div>
      ) : videos.length === 0 ? (
        <div className="text-center py-24">
          <p className="text-4xl mb-3">🎬</p>
          <p className="text-gray-400">No videos found.</p>
          <p className="text-gray-600 text-sm mt-1">
            Trigger generation above to create your first video.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {videos.map((video) => (
            <VideoCard
              key={video.id}
              video={video}
              onClick={setSelectedVideo}
            />
          ))}
        </div>
      )}

      {/* ── Pagination ──────────────────────────────────────────────────── */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2 pt-2">
          <button
            onClick={() =>
              setFilters((p) => ({ ...p, page: Math.max(1, p.page - 1) }))
            }
            disabled={filters.page <= 1}
            className="px-3 py-1.5 text-sm bg-gray-800 hover:bg-gray-700 text-gray-200 rounded-lg disabled:opacity-40 transition-colors"
          >
            ← Prev
          </button>
          <span className="text-sm text-gray-400">
            Page {filters.page} of {totalPages}
          </span>
          <button
            onClick={() =>
              setFilters((p) => ({
                ...p,
                page: Math.min(totalPages, p.page + 1),
              }))
            }
            disabled={filters.page >= totalPages}
            className="px-3 py-1.5 text-sm bg-gray-800 hover:bg-gray-700 text-gray-200 rounded-lg disabled:opacity-40 transition-colors"
          >
            Next →
          </button>
        </div>
      )}

      {/* ── SlideOver ────────────────────────────────────────────────────── */}
      {selectedVideo && (
        <SlideOver
          video={selectedVideo}
          onClose={() => setSelectedVideo(null)}
        />
      )}

      {/* ── Toast ────────────────────────────────────────────────────────── */}
      {toast && (
        <Toast
          key={toast.key}
          message={toast.message}
          type={toast.type}
          onClose={() => setToast(null)}
        />
      )}
    </div>
  );
}
