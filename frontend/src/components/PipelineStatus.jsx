import React from "react";

const STEPS = [
  { label: "Idea", icon: "💡" },
  { label: "Video", icon: "🎬" },
  { label: "Audio", icon: "🎵" },
  { label: "Thumbnail", icon: "🖼️" },
  { label: "SEO", icon: "✍️" },
  { label: "Upload", icon: "📤" },
];

const STEP_STATUS_MAP = {
  pending: -1,
  writing_idea: 0,
  generating_video: 1,
  generating_audio: 2,
  generating_thumbnail: 3,
  writing_seo: 4,
  uploading: 5,
  uploaded: 6,
  failed: null,
};

function getActiveStep(job) {
  if (!job) return -1;
  const mapped = STEP_STATUS_MAP[job.step || job.status];
  return mapped !== undefined ? mapped : -1;
}

function StepCircle({ index, activeStep, failed }) {
  let base = "w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold border-2 transition-all ";
  if (failed && index === activeStep) {
    return (
      <div className={base + "border-red-500 bg-red-900 text-red-200"}>
        {index + 1}
      </div>
    );
  }
  if (index < activeStep) {
    return (
      <div className={base + "border-green-500 bg-green-900 text-green-200"}>
        ✓
      </div>
    );
  }
  if (index === activeStep) {
    return (
      <div className={base + "border-blue-500 bg-blue-900 text-blue-200 animate-pulse"}>
        {index + 1}
      </div>
    );
  }
  return (
    <div className={base + "border-gray-600 bg-gray-800 text-gray-500"}>
      {index + 1}
    </div>
  );
}

export default function PipelineStatus({ jobs = [], running = false }) {
  const lastJob = jobs && jobs.length > 0 ? jobs[0] : null;
  const activeStep = running && lastJob ? getActiveStep(lastJob) : running ? 0 : -1;
  const isFailed = lastJob && (lastJob.status === "failed" || lastJob.step === "failed");

  const lastCompleted = jobs
    ? jobs.find((j) => j.status === "uploaded" || j.step === "uploaded")
    : null;

  return (
    <div className="bg-gray-900 border border-gray-700 rounded-xl p-4">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-gray-100 font-semibold text-base">Pipeline Status</h2>
        {running ? (
          <span className="flex items-center gap-1.5 text-green-400 text-sm font-medium">
            <span className="w-2 h-2 rounded-full bg-green-400 animate-pulse inline-block" />
            Running
          </span>
        ) : (
          <span className="text-gray-500 text-sm">Idle</span>
        )}
      </div>

      {/* Stepper */}
      <div className="flex items-center gap-1 overflow-x-auto pb-1">
        {STEPS.map((step, i) => (
          <React.Fragment key={step.label}>
            <div className="flex flex-col items-center gap-1 min-w-[48px]">
              <StepCircle index={i} activeStep={activeStep} failed={isFailed} />
              <span className="text-[10px] text-gray-400 text-center leading-tight">
                <span className="block">{step.icon}</span>
                <span className="block">{step.label}</span>
              </span>
            </div>
            {i < STEPS.length - 1 && (
              <div
                className={`flex-1 h-0.5 mb-4 ${
                  i < activeStep ? "bg-green-600" : "bg-gray-700"
                }`}
              />
            )}
          </React.Fragment>
        ))}
      </div>

      {/* Info */}
      <div className="mt-3 text-xs text-gray-500">
        {running && lastJob ? (
          <p>
            Processing:{" "}
            <span className="text-blue-400 font-medium">
              {(lastJob.step || lastJob.status || "").replace(/_/g, " ")}
            </span>
            {lastJob.video_id && (
              <span className="ml-1 text-gray-600">· video #{lastJob.video_id}</span>
            )}
          </p>
        ) : lastCompleted ? (
          <p>
            Last completed:{" "}
            <span className="text-green-400">
              video #{lastCompleted.video_id}
            </span>
          </p>
        ) : (
          <p>No pipeline running</p>
        )}
      </div>
    </div>
  );
}
