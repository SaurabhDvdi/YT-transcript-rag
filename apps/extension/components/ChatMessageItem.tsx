import React, { useState } from "react";
import type { Citation } from "@youtube-ai/shared-types";
import { CitationChip } from "./CitationChip";
import { renderSafeMarkdown, formatAnswerForCopy } from "../utils/markdown";

export interface ChatMessageData {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  grounded?: boolean;
  status?: "sending" | "complete" | "error";
  errorText?: string;
  createdAt?: string;
}

interface ChatMessageItemProps {
  message: ChatMessageData;
  videoId: string;
  onRetry?: (messageId: string) => void;
}

export const ChatMessageItem: React.FC<ChatMessageItemProps> = ({
  message,
  videoId,
  onRetry,
}) => {
  const [copied, setCopied] = useState(false);
  const isUser = message.role === "user";

  const handleCopy = async () => {
    try {
      const copyText = formatAnswerForCopy(message.content, message.citations);
      await navigator.clipboard.writeText(copyText);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Ignore clipboard write failures
    }
  };

  return (
    <div
      className={`flex flex-col group ${isUser ? "items-end" : "items-start"} w-full animate-in fade-in slide-in-from-bottom-1 duration-150`}
    >
      {/* Sender & Timestamp Header */}
      <div className="flex items-center space-x-1.5 mb-1 px-1 text-[10px] text-zinc-500 dark:text-zinc-400 font-medium">
        <span>{isUser ? "You" : "Assistant"}</span>
        {message.createdAt && (
          <span className="font-mono text-[9px] text-zinc-400 dark:text-zinc-500">
            &bull;{" "}
            {new Date(message.createdAt).toLocaleTimeString([], {
              hour: "2-digit",
              minute: "2-digit",
            })}
          </span>
        )}
      </div>

      {/* Bubble Container */}
      <div
        className={`max-w-[92%] rounded-2xl px-3.5 py-2.5 text-xs transition-colors shadow-xs ${
          isUser
            ? "bg-zinc-800 dark:bg-zinc-800 text-white rounded-tr-xs"
            : "bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-850 text-zinc-800 dark:text-zinc-200 rounded-tl-xs shadow-xs"
        }`}
      >
        {/* Sending / Pre-token Thinking Spinner */}
        {message.status === "sending" && !message.content && (
          <div className="flex items-center space-x-2 py-1">
            <div className="w-3 h-3 border-2 border-amber-500 border-t-transparent rounded-full animate-spin" />
            <span className="text-zinc-500 dark:text-zinc-400 font-mono text-[11px]">
              Searching transcript &amp; thinking...
            </span>
          </div>
        )}

        {/* Streaming State */}
        {message.status === "sending" && message.content && (
          <div className="space-y-1.5">
            <div className="prose prose-xs max-w-none text-zinc-800 dark:text-zinc-200">
              {renderSafeMarkdown(message.content)}
              <span className="inline-block w-1.5 h-3 bg-amber-500 dark:bg-amber-400 ml-0.5 animate-pulse align-middle" />
            </div>
            <div className="flex items-center space-x-1.5 text-zinc-400 dark:text-zinc-500 text-[10px] font-mono pt-1">
              <span className="w-1.5 h-1.5 bg-amber-500 rounded-full animate-ping" />
              <span>Streaming answer...</span>
            </div>
          </div>
        )}

        {/* Error State */}
        {message.status === "error" && (
          <div className="space-y-2 text-red-600 dark:text-red-300">
            <div className="flex items-center space-x-1.5 font-semibold text-[11px]">
              <svg
                className="w-3.5 h-3.5 shrink-0"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                />
              </svg>
              <span>{message.errorText ?? "Generation stopped unexpectedly."}</span>
            </div>
            {message.content && (
              <div className="text-zinc-600 dark:text-zinc-400 text-[11px] opacity-80 border-t border-red-200 dark:border-red-900/40 pt-1.5">
                {renderSafeMarkdown(message.content)}
              </div>
            )}
            {onRetry && (
              <button
                type="button"
                onClick={() => onRetry(message.id)}
                className="inline-flex items-center space-x-1 px-2.5 py-1 text-[11px] font-medium rounded-md bg-red-100 dark:bg-red-950/60 hover:bg-red-200 dark:hover:bg-red-900/60 text-red-700 dark:text-red-300 transition-colors border border-red-200 dark:border-red-800/60 cursor-pointer"
              >
                <svg
                  className="w-3 h-3"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                  />
                </svg>
                <span>Retry</span>
              </button>
            )}
          </div>
        )}

        {/* Complete State */}
        {message.status === "complete" && (
          <div className="space-y-2">
            {/* Grounding Warning Banner if ungrounded */}
            {!isUser && message.grounded === false && (
              <div className="inline-flex items-center space-x-1 px-2 py-0.5 rounded text-[10px] font-medium bg-amber-50 dark:bg-amber-950/40 text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-800/50">
                <span>⚠️ Note: Answer may not be fully grounded in video</span>
              </div>
            )}

            {/* Markdown Content */}
            <div className="prose prose-xs max-w-none text-zinc-900 dark:text-zinc-100">
              {renderSafeMarkdown(message.content)}
            </div>

            {/* Citations Footer */}
            {!isUser && message.citations && message.citations.length > 0 && (
              <div className="pt-2 border-t border-zinc-100 dark:border-zinc-800/80 space-y-1.5">
                <span className="text-[10px] text-zinc-500 dark:text-zinc-400 font-medium block">
                  Sources &amp; Timestamps:
                </span>
                <div className="flex flex-wrap gap-1.5">
                  {message.citations.map((cit, idx) => (
                    <CitationChip
                      key={`${cit.chunkId}_${idx}`}
                      citation={cit}
                      videoId={videoId}
                    />
                  ))}
                </div>
              </div>
            )}

            {/* Copy / Actions Toolbar */}
            {!isUser && (
              <div className="flex items-center justify-end pt-1 opacity-80 hover:opacity-100 transition-opacity">
                <button
                  type="button"
                  onClick={handleCopy}
                  title="Copy answer with citations"
                  className="inline-flex items-center space-x-1 px-1.5 py-0.5 rounded text-[10px] text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200 transition-colors"
                >
                  {copied ? (
                    <>
                      <svg
                        className="w-3 h-3 text-emerald-500"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M5 13l4 4L19 7"
                        />
                      </svg>
                      <span className="text-emerald-500 font-medium">Copied!</span>
                    </>
                  ) : (
                    <>
                      <svg
                        className="w-3 h-3"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"
                        />
                      </svg>
                      <span>Copy</span>
                    </>
                  )}
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
