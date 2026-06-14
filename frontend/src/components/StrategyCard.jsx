import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { formatDistanceToNow, parseISO } from "date-fns";
import { api } from "../api/client";

const NICHE_LABELS = {
  nature_ambient: "Nature Ambient",
  cozy_indoor: "Cozy Indoor",
  ocean_beach: "Ocean & Beach",
  forest_mountain: "Forest & Mountain",
  japanese_zen: "Japanese Zen",
  winter_snow: "Winter Snow",
  custom: "Custom",
};

function DecisionBadge({ decision }) {
  const changed = decision.old !== decision.new && decision.new !== null;
  const isSkip = decision.metric === "skipped";

  if (isSkip) {
    return (
      <div className="flex items-start gap-2 py-2 border-b border-gray-800 last:border-0">
        <span className="mt-0.5 text-gray-400">⏭</span>
        <div>
          <p className="text-sm text-gray-400">{decision.reason}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex items-start gap-2 py-2 border-b border-gray-800 last:border-0">
      <span className="mt-0.5">
        {changed ? (
          <span className="text-green-400">↑</span>
        ) : (
          <span className="text-gray-500">—</span>
        )}
      </span>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs font-mono bg-gray-800 text-gray-300 px-1.5 py-0.5 rounded">
            {decision.metric}
          </span>
          {changed && (
            <span className="text-xs text-gray-400">
              <span className="text-gray-500 line-through">{String(decision.old)}</span>
              {" → "}
              <span className="text-green-400 font-medium">{String(decision.new)}</span>
            </span>
          )}
          {!changed && decision.old != null && (
            <span className="text-xs text-gray-500">kept at {String(decision.old)}</span>
          )}
        </div>
        <p className="text-xs text-gray-500 mt-0.5">{decision.reason}</p>
      </div>
    </div>
  );
}

function SlideOver({ open, onClose, reports }) {
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex">
      <div
        className="fixed inset-0 bg-black/60"
        onClick={onClose}
        aria-hidden="true"
      />
      <div className="relative ml-auto w-full max-w-md bg-gray-900 border-l border-gray-800 h-full overflow-y-auto shadow-2xl">
        <div className="sticky top-0 bg-gray-900 border-b border-gray-800 px-4 py-3 flex items-center justify-between">
          <h2 className="font-semibold text-white">Optimization History</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white transition-colors text-xl leading-none"
          >
            ×
          </button>
        </div>

        <div className="p-4 space-y-6">
          {reports.length === 0 ? (
            <p className="text-gray-500 text-sm">
              No optimization reports yet. The optimizer runs daily at 05:00 UTC
              once you have 10+ uploaded videos.
            </p>
          ) : (
            reports.map((r) => (
              <div key={r.id} className="space-y-2">
                <div className="flex items-center justify-between">
                  <p className="text-xs text-gray-400">
                    {r.ran_at
                      ? formatDistanceToNow(parseISO(r.ran_at), {
                          addSuffix: true,
                        })
                      : "—"}
                  </p>
                  <span className="text-xs text-gray-500">
                    {r.videos_analyzed} videos analyzed
                  </span>
                </div>
                <div className="bg-gray-800/50 rounded-lg px-3 py-1">
                  {(r.decisions || []).length === 0 ? (
                    <p className="text-xs text-gray-500 py-2">No decisions made.</p>
                  ) : (
                    (r.decisions || []).map((d, i) => (
                      <DecisionBadge key={i} decision={d} />
                    ))
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}

export default function StrategyCard({ settings }) {
  const [showHistory, setShowHistory] = useState(false);

  const { data: optData } = useQuery({
    queryKey: ["optimization-data"],
    queryFn: () => api.getOptimizationStats().then((r) => r.data),
    staleTime: 5 * 60 * 1000,
  });

  const reports = optData?.reports || [];
  const lastReport = reports[0];
  const lastRanAt = lastReport?.ran_at;
  const isManualOverride = settings?.manual_override;

  const strategy = lastReport?.current_strategy || {
    shorts_per_day: settings?.shorts_per_day,
    long_interval_days: settings?.long_video_interval_days,
    upload_hour_shorts: settings?.upload_time_shorts,
    upload_hour_long: settings?.upload_time_long,
    niche_theme: settings?.niche_theme,
    long_duration_minutes: settings?.long_video_duration_minutes,
  };

  return (
    <>
      <div className="bg-gray-900 rounded-xl p-4 border border-gray-800">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-base font-semibold text-white">Strategy</h2>
          <div className="flex items-center gap-2">
            {isManualOverride ? (
              <span className="text-xs bg-yellow-900/60 text-yellow-300 border border-yellow-700/40 px-2 py-0.5 rounded-full">
                Manual override
              </span>
            ) : (
              <span className="text-xs bg-green-900/60 text-green-300 border border-green-700/40 px-2 py-0.5 rounded-full">
                🤖 Auto-optimized
              </span>
            )}
          </div>
        </div>

        <div className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm mb-3">
          <div>
            <p className="text-gray-500 text-xs">Niche</p>
            <p className="text-gray-200 font-medium">
              {NICHE_LABELS[strategy.niche_theme] || strategy.niche_theme || "—"}
            </p>
          </div>
          <div>
            <p className="text-gray-500 text-xs">Shorts / day</p>
            <p className="text-gray-200 font-medium">
              {strategy.shorts_per_day ?? "—"}
            </p>
          </div>
          <div>
            <p className="text-gray-500 text-xs">Long interval</p>
            <p className="text-gray-200 font-medium">
              {strategy.long_interval_days
                ? `Every ${strategy.long_interval_days}d`
                : "—"}
            </p>
          </div>
          <div>
            <p className="text-gray-500 text-xs">Upload times</p>
            <p className="text-gray-200 font-medium">
              {strategy.upload_hour_shorts || "—"}
              {strategy.upload_hour_long ? ` / ${strategy.upload_hour_long}` : ""}
              <span className="text-gray-500 text-xs ml-1">UTC</span>
            </p>
          </div>
          <div>
            <p className="text-gray-500 text-xs">Long duration</p>
            <p className="text-gray-200 font-medium">
              {strategy.long_duration_minutes
                ? `${strategy.long_duration_minutes} min`
                : "—"}
            </p>
          </div>
        </div>

        <div className="flex items-center justify-between pt-2 border-t border-gray-800">
          <p className="text-xs text-gray-500">
            {lastRanAt
              ? `Last optimized ${formatDistanceToNow(parseISO(lastRanAt), { addSuffix: true })}`
              : "Optimizing daily at 05:00 UTC"}
          </p>
          <button
            onClick={() => setShowHistory(true)}
            className="text-xs text-green-400 hover:text-green-300 transition-colors"
          >
            View history →
          </button>
        </div>
      </div>

      <SlideOver
        open={showHistory}
        onClose={() => setShowHistory(false)}
        reports={reports}
      />
    </>
  );
}
