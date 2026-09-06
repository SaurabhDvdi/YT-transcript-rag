import React from "react";
import type { VideoBackendState } from "../hooks/useVideoBackend";

interface BackendStatusProps {
  state: VideoBackendState;
  onRetry: () => void;
}

/**
 * Formats a duration in seconds into H:MM:SS or MM:SS.
 */
function formatDuration(seconds: number): string {
  if (!seconds || isNaN(seconds) || seconds < 0) return "0:00";

  const totalSecs = Math.round(seconds);
  const hrs = Math.floor(totalSecs / 3600);
  const mins = Math.floor((totalSecs % 3600) / 60);
  const secs = totalSecs % 60;

  if (hrs > 0) {
    return `${hrs}:${mins.toString().padStart(2, "0")}:${secs.toString().padStart(2, "0")}`;
  }
  return `${mins}:${secs.toString().padStart(2, "0")}`;
}

export const BackendStatus: React.FC<BackendStatusProps> = ({ state, onRetry }) => {
  if (state.status === "idle") {
    return null;
  }

  if (state.status === "registering") {
    return (
      <div className="rounded-xl bg-zinc-900/60 border border-zinc-800 p-3.5 flex items-center space-x-3 shadow-sm">
        <div className="w-4 h-4 rounded-full border-2 border-amber-500 border-t-transparent animate-spin flex-shrink-0" />
        <p className="text-xs text-zinc-300 animate-pulse">
          Connecting to backend service...
        </p>
      </div>
    );
  }

  if (state.status === "error") {
    const isQuota = state.code === "QUOTA_EXCEEDED";
    return (
      <div
        role="alert"
        className={`rounded-xl ${isQuota ? "bg-amber-950/30 border-amber-600/50" : "bg-amber-950/25 border-amber-800/40"} p-3.5 space-y-2.5 shadow-sm`}
      >
        <div className="flex items-start justify-between">
          <div className="flex items-center space-x-2">
            <span
              className={`w-2 h-2 rounded-full ${isQuota ? "bg-amber-400" : "bg-amber-500"}`}
            />
            <h3
              className={`text-xs font-semibold ${isQuota ? "text-amber-300" : "text-amber-200"}`}
            >
              {isQuota ? "Daily Usage Limit Reached" : "Backend Service Unavailable"}
            </h3>
          </div>
          <span className="text-[10px] font-mono text-amber-400/80 uppercase">
            {state.code ?? "OFFLINE"}
          </span>
        </div>

        <p className="text-xs text-zinc-300 leading-relaxed">
          {isQuota
            ? state.message ||
              "Daily usage limit reached for transcripts and questions. Quota resets at 00:00 UTC."
            : state.message ||
              "The video was detected, but the backend service could not be reached."}
        </p>

        <div className="flex items-center justify-between pt-1">
          <button
            type="button"
            onClick={onRetry}
            className="inline-flex items-center px-3 py-1.5 text-xs font-semibold text-zinc-900 bg-amber-400 hover:bg-amber-300 active:bg-amber-500 rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-amber-400 focus:ring-offset-2 focus:ring-offset-zinc-900"
          >
            <svg
              className="w-3 h-3 mr-1.5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              aria-hidden="true"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
              />
            </svg>
            Retry Connection
          </button>

          {state.requestId && (
            <span className="text-[10px] font-mono text-zinc-500 truncate max-w-[120px]">
              ID: {state.requestId.slice(0, 8)}
            </span>
          )}
        </div>
      </div>
    );
  }

  const { processingStatus, transcript, retrievalStatus } = state;

  return (
    <div className="rounded-xl bg-zinc-900/70 border border-zinc-800/80 p-3.5 space-y-3 shadow-sm">
      {/* Top row: Backend Service Connected indicator */}
      <div className="flex items-center justify-between">
        <span className="text-[11px] font-medium text-zinc-400">Backend Service</span>
        <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium bg-emerald-950/60 text-emerald-400 border border-emerald-800/60">
          <span className="w-1.5 h-1.5 mr-1.5 rounded-full bg-emerald-500" />
          Connected
        </span>
      </div>

      {/* Transcript section */}
      <div className="pt-2 border-t border-zinc-800/60 space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-[11px] font-medium text-zinc-400">Transcript</span>

          {processingStatus === "ready" && (
            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium bg-emerald-950/70 text-emerald-300 border border-emerald-700/60">
              <svg
                className="w-3 h-3 mr-1 text-emerald-400"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2.5}
                  d="M5 13l4 4L19 7"
                />
              </svg>
              Ready
            </span>
          )}

          {(processingStatus === "processing" || processingStatus === "accepted") && (
            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium bg-sky-950/60 text-sky-300 border border-sky-800/60">
              <span className="w-1.5 h-1.5 mr-1.5 rounded-full bg-sky-400 animate-ping" />
              Processing...
            </span>
          )}

          {processingStatus === "unavailable" && (
            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium bg-zinc-800 text-zinc-400 border border-zinc-700">
              Unavailable
            </span>
          )}

          {processingStatus === "error" && (
            <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[11px] font-medium bg-red-950/60 text-red-400 border border-red-800/60">
              Failed
            </span>
          )}
        </div>

        {/* State details: Ready */}
        {processingStatus === "ready" && transcript && (
          <div className="grid grid-cols-3 gap-2 pt-1">
            <div className="bg-zinc-950/50 rounded-lg p-2 border border-zinc-800/50">
              <span className="text-[10px] text-zinc-500 block">Language</span>
              <span className="text-xs font-semibold text-zinc-200 truncate block">
                {transcript.language}
              </span>
            </div>
            <div className="bg-zinc-950/50 rounded-lg p-2 border border-zinc-800/50">
              <span className="text-[10px] text-zinc-500 block">Segments</span>
              <span className="text-xs font-semibold text-zinc-200 block">
                {transcript.segmentCount}
              </span>
            </div>
            <div className="bg-zinc-950/50 rounded-lg p-2 border border-zinc-800/50">
              <span className="text-[10px] text-zinc-500 block">Duration</span>
              <span className="text-xs font-semibold text-zinc-200 block">
                {formatDuration(transcript.duration)}
              </span>
            </div>
          </div>
        )}

        {/* AI Knowledge Retrieval Indexing Status */}
        {processingStatus === "ready" && retrievalStatus === "indexing" && (
          <div className="flex items-center space-x-2 pt-2 border-t border-zinc-800/40 text-xs text-amber-400/90">
            <div className="w-3 h-3 rounded-full border-2 border-amber-400 border-t-transparent animate-spin flex-shrink-0" />
            <span>Preparing video for AI questions...</span>
          </div>
        )}

        {processingStatus === "ready" && retrievalStatus === "ready" && (
          <div className="flex items-center justify-between pt-2 border-t border-zinc-800/40 text-[11px] text-zinc-400">
            <span>AI Knowledge Index</span>
            <span className="inline-flex items-center text-emerald-400 font-medium">
              <svg
                className="w-3 h-3 mr-1 text-emerald-400"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2.5}
                  d="M5 13l4 4L19 7"
                />
              </svg>
              Ready
            </span>
          </div>
        )}

        {/* State details: Processing */}
        {(processingStatus === "processing" || processingStatus === "accepted") && (
          <p className="text-xs text-zinc-400 leading-relaxed pt-0.5 animate-pulse">
            Acquiring and normalizing video captions...
          </p>
        )}

        {/* State details: Unavailable */}
        {processingStatus === "unavailable" && (
          <div className="rounded-lg bg-zinc-950/40 p-2.5 border border-zinc-800/60">
            <p className="text-xs text-zinc-400 leading-relaxed">
              This video does not currently have an accessible transcript.
            </p>
          </div>
        )}

        {/* State details: Failed */}
        {processingStatus === "error" && (
          <div className="rounded-lg bg-red-950/20 p-2.5 border border-red-900/30">
            <p className="text-xs text-red-300 leading-relaxed">
              Transcript acquisition encountered an unexpected failure.
            </p>
          </div>
        )}
      </div>

      {state.requestId && (
        <div className="flex items-center justify-between text-[10px] text-zinc-500 font-mono pt-1 border-t border-zinc-800/40">
          <span>Request ID</span>
          <span title={state.requestId}>{state.requestId.slice(0, 8)}...</span>
        </div>
      )}
    </div>
  );
};
