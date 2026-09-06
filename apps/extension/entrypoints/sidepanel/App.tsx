import React, { useState } from "react";
import { useCurrentVideo } from "../../hooks/useCurrentVideo";
import { useVideoBackend } from "../../hooks/useVideoBackend";
import { useAuth } from "../../hooks/useAuth";
import { useTheme } from "../../hooks/useTheme";
import { VideoInfo } from "../../components/VideoInfo";
import { BackendStatus } from "../../components/BackendStatus";
import { QuestionAnswering } from "../../components/QuestionAnswering";
import { LoadingState } from "../../components/LoadingState";
import { StatusMessage } from "../../components/StatusMessage";
import { AuthPanel } from "../../components/AuthPanel";
import { UserMenu } from "../../components/UserMenu";
import { SettingsModal } from "../../components/SettingsModal";

export const App: React.FC = () => {
  const { state: videoState, retry: retryVideoDetection } = useCurrentVideo();
  const currentVideo = videoState.status === "detected" ? videoState.video : null;
  const { backendState, retry: retryBackend } = useVideoBackend(currentVideo);
  const auth = useAuth();
  const { resolvedTheme } = useTheme();

  const [showSettings, setShowSettings] = useState(false);
  // showAuthPanel: true = show login/register; false = dismissed (anonymous mode)
  const [showAuthPanel, setShowAuthPanel] = useState(
    !auth.isAuthenticated && !auth.isLoading,
  );

  // When auth state loads — if already authenticated, keep panel hidden
  const shouldShowAuthPanel = showAuthPanel && !auth.isAuthenticated && !auth.isLoading;

  const isTranscriptReady =
    backendState.status === "connected" &&
    (backendState.processingStatus === "ready" || !!backendState.transcript);
  const isAiReady =
    backendState.status === "connected" && backendState.retrievalStatus === "ready";

  return (
    <div
      className={`flex flex-col min-h-screen bg-base text-primary p-3.5 sm:p-4 select-none font-sans transition-colors duration-200 ${
        resolvedTheme === "dark" ? "dark" : ""
      }`}
    >
      {/* Extension Header */}
      <header className="flex items-center justify-between pb-3 mb-3 border-b border-theme">
        <div className="flex items-center space-x-2.5">
          {/* YouTube Assistant Logo Mark */}
          <div className="w-7 h-7 rounded-lg bg-red-600 flex items-center justify-center shadow-sm shadow-red-950/30 shrink-0">
            <svg
              className="w-4 h-4 text-white fill-current"
              viewBox="0 0 24 24"
              aria-hidden="true"
            >
              <path d="M10 15l5.19-3L10 9v6m11.56-7.83c.13.47.22 1.1.28 1.9.07.8.1 1.49.1 2.09L22 12c0 2.19-.16 3.8-.44 4.83-.25.9-.83 1.48-1.73 1.73-.47.13-1.33.22-2.65.28-1.3.07-2.49.1-3.59.1L12 19c-4.19 0-6.8-.16-7.83-.44-.9-.25-1.48-.83-1.73-1.73-.13-.47-.22-1.1-.28-1.9-.07-.8-.1-1.49-.1-2.09L2 12c0-2.19.16-3.8.44-4.83.25-.9.83-1.48 1.73-1.73.47-.13 1.33-.22 2.65-.28 1.3-.07 2.49-.1 3.59-.1L12 5c4.19 0 6.8.16 7.83.44.9.25 1.48.83 1.73 1.73z" />
            </svg>
          </div>
          <div>
            <h1 className="text-xs font-bold tracking-tight text-primary leading-tight">
              YouTube AI Assistant
            </h1>
            <p className="text-[10px] text-muted font-medium">
              Grounded Video Intelligence
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          {/* Authenticated: show user menu */}
          {auth.isAuthenticated && <UserMenu auth={auth} />}

          {/* Anonymous: show "Sign In" badge */}
          {!auth.isLoading && !auth.isAuthenticated && !shouldShowAuthPanel && (
            <button
              id="header-signin-btn"
              type="button"
              onClick={() => setShowAuthPanel(true)}
              className="text-[10px] font-medium px-2 py-1 rounded-md bg-brand/10 border border-brand/25 text-brand hover:bg-brand/20 transition-colors"
            >
              Sign in
            </button>
          )}

          {/* Settings button */}
          <button
            id="settings-trigger-btn"
            type="button"
            aria-label="Settings"
            onClick={() => setShowSettings(true)}
            className="p-1.5 rounded-lg text-muted hover:text-primary hover:bg-elevated transition-colors"
            title="Settings & Appearance"
          >
            <svg
              className="w-4 h-4"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
              />
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
              />
            </svg>
          </button>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col space-y-3.5">
        {/* Auth Panel (dismissible) */}
        {shouldShowAuthPanel && (
          <AuthPanel auth={auth} onDismiss={() => setShowAuthPanel(false)} />
        )}

        {videoState.status === "loading" && <LoadingState />}

        {videoState.status === "detected" && (
          <div className="space-y-3.5">
            <VideoInfo
              video={videoState.video}
              transcriptReady={isTranscriptReady}
              aiReady={isAiReady}
            />
            <BackendStatus state={backendState} onRetry={retryBackend} />
            <QuestionAnswering videoId={videoState.video.videoId} isReady={isAiReady} />
          </div>
        )}

        {videoState.status === "unsupported" && <StatusMessage type="unsupported" />}

        {videoState.status === "error" && (
          <StatusMessage
            type="error"
            description={videoState.message}
            onRetry={retryVideoDetection}
          />
        )}
      </main>

      {/* Settings Modal */}
      <SettingsModal isOpen={showSettings} onClose={() => setShowSettings(false)} />

      {/* Modern Compact Footer */}
      <footer className="mt-4 pt-2.5 border-t border-theme text-center">
        <p className="text-[10px] text-muted">
          Cross-browser YouTube Assistant &bull; Cloudflare Workers & Gemini
        </p>
      </footer>
    </div>
  );
};
