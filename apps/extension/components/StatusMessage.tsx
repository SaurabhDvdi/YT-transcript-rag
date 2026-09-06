import React from "react";

interface StatusMessageProps {
  type: "unsupported" | "error";
  title?: string;
  description?: string;
  onRetry?: () => void;
}

export const StatusMessage: React.FC<StatusMessageProps> = ({
  type,
  title,
  description,
  onRetry,
}) => {
  const isError = type === "error";

  const defaultTitle = isError
    ? "Unable to detect the current YouTube video."
    : "No supported YouTube video detected.";

  const defaultDescription = isError
    ? "Check that the current tab is an active YouTube video and try again."
    : "Open a YouTube video to get started.";

  return (
    <div
      role={isError ? "alert" : "region"}
      aria-label={isError ? "Error message" : "Status notification"}
      className={`flex flex-col items-center justify-center p-6 text-center rounded-xl border ${
        isError
          ? "bg-red-950/20 border-red-900/50 text-red-200"
          : "bg-zinc-900/50 border-zinc-800 text-zinc-300"
      }`}
    >
      <div
        className={`w-12 h-12 rounded-full flex items-center justify-center mb-4 ${
          isError ? "bg-red-900/40 text-red-400" : "bg-zinc-800 text-zinc-400"
        }`}
      >
        {isError ? (
          <svg
            className="w-6 h-6"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
            />
          </svg>
        ) : (
          <svg
            className="w-6 h-6"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"
            />
          </svg>
        )}
      </div>

      <h2 className="text-base font-semibold mb-2">{title || defaultTitle}</h2>

      <p className="text-xs text-zinc-400 max-w-xs leading-relaxed mb-4">
        {description || defaultDescription}
      </p>

      {isError && onRetry && (
        <button
          onClick={onRetry}
          type="button"
          className="inline-flex items-center px-4 py-2 text-xs font-semibold text-white bg-red-600 hover:bg-red-500 active:bg-red-700 rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-red-400 focus:ring-offset-2 focus:ring-offset-zinc-900"
        >
          <svg
            className="w-3.5 h-3.5 mr-1.5"
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
          Retry
        </button>
      )}
    </div>
  );
};
