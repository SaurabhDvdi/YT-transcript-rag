import React, { useState, useEffect, useRef, useCallback } from "react";
import type { ConversationMessage } from "@youtube-ai/shared-types";
import { apiClient, ApiClientError } from "../services/api";
import { getVideoConversationId, setVideoConversationId } from "../services/storage";
import { ConversationDrawer } from "./ConversationDrawer";
import { ChatMessageItem, type ChatMessageData } from "./ChatMessageItem";
import { QuickActions } from "./QuickActions";
import { formatAnswerForCopy } from "../utils/markdown";

interface QuestionAnsweringProps {
  videoId: string;
  isReady: boolean;
}

export const QuestionAnswering: React.FC<QuestionAnsweringProps> = ({
  videoId,
  isReady,
}) => {
  const [messages, setMessages] = useState<ChatMessageData[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [activeTitle, setActiveTitle] = useState<string>("New Chat");
  const [isLoadingHistory, setIsLoadingHistory] = useState(false);
  const [question, setQuestion] = useState("");
  const [isAsking, setIsAsking] = useState(false);
  const [globalError, setGlobalError] = useState<string | null>(null);
  const [isDrawerOpen, setIsDrawerOpen] = useState(false);

  const abortControllerRef = useRef<AbortController | null>(null);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const scrollContainerRef = useRef<HTMLDivElement | null>(null);
  const isUserScrolledUpRef = useRef(false);

  const scrollToBottomIfNeeded = useCallback(() => {
    if (!isUserScrolledUpRef.current) {
      messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, []);

  const handleScroll = useCallback(() => {
    if (!scrollContainerRef.current) return;
    const { scrollTop, scrollHeight, clientHeight } = scrollContainerRef.current;
    isUserScrolledUpRef.current = scrollHeight - scrollTop - clientHeight > 60;
  }, []);

  // Video switching: abort in-flight requests, load active conversation for the new video
  useEffect(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }

    setMessages([]);
    setQuestion("");
    setIsAsking(false);
    setGlobalError(null);
    setIsDrawerOpen(false);
    setIsLoadingHistory(true);
    setActiveTitle("New Chat");

    let isMounted = true;

    async function loadActiveConversation() {
      try {
        const storedConvId = await getVideoConversationId(videoId);
        if (!isMounted) return;

        if (storedConvId) {
          try {
            const detail = await apiClient.getConversation(storedConvId);
            if (isMounted) {
              setConversationId(detail.conversation.id);
              setActiveTitle(detail.conversation.title || "Conversation");
              setMessages(
                detail.messages.map((m: ConversationMessage) => ({
                  ...m,
                  status: "complete",
                })),
              );
            }
          } catch {
            // Stale or deleted conversation, clear stored ID
            if (isMounted) {
              setConversationId(null);
              setActiveTitle("New Chat");
              await setVideoConversationId(videoId, null);
            }
          }
        } else {
          setConversationId(null);
          setActiveTitle("New Chat");
        }
      } catch (err) {
        console.warn("Error loading conversation history:", err);
      } finally {
        if (isMounted) {
          setIsLoadingHistory(false);
        }
      }
    }

    loadActiveConversation();

    return () => {
      isMounted = false;
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [videoId]);

  useEffect(() => {
    scrollToBottomIfNeeded();
  }, [messages, scrollToBottomIfNeeded]);

  const handleCancel = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsAsking(false);
    setMessages((prev) =>
      prev.map((m) =>
        m.status === "sending"
          ? {
              ...m,
              status: "error",
              errorText: "Generation stopped by user.",
              content: m.content || "Generation stopped by user.",
            }
          : m,
      ),
    );
  }, []);

  const handleStartNewChat = useCallback(async () => {
    if (isAsking) {
      handleCancel();
    }
    setMessages([]);
    setConversationId(null);
    setActiveTitle("New Chat");
    await setVideoConversationId(videoId, null);
  }, [handleCancel, isAsking, videoId]);

  const handleSelectConversation = useCallback(
    async (selectedConvId: string) => {
      if (isAsking) {
        handleCancel();
      }
      setIsLoadingHistory(true);
      try {
        const detail = await apiClient.getConversation(selectedConvId);
        setConversationId(detail.conversation.id);
        setActiveTitle(detail.conversation.title || "Conversation");
        setMessages(
          detail.messages.map((m: ConversationMessage) => ({
            ...m,
            status: "complete",
          })),
        );
        await setVideoConversationId(videoId, detail.conversation.id);
      } catch {
        setGlobalError("Failed to switch conversation thread");
      } finally {
        setIsLoadingHistory(false);
      }
    },
    [handleCancel, isAsking, videoId],
  );

  const handleClearCurrentConversation = useCallback(async () => {
    if (isAsking) {
      handleCancel();
    }
    if (conversationId) {
      try {
        await apiClient.deleteConversation(conversationId, videoId);
      } catch {
        // Ignore deletion errors on local clear
      }
    }
    setMessages([]);
    setConversationId(null);
    setActiveTitle("New Chat");
    await setVideoConversationId(videoId, null);
  }, [conversationId, handleCancel, isAsking, videoId]);

  const executeQuestion = useCallback(
    async (queryText: string) => {
      const trimmed = queryText.trim();
      if (!trimmed || !isReady || isAsking) {
        return;
      }

      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }

      const controller = new AbortController();
      abortControllerRef.current = controller;

      setIsAsking(true);
      setGlobalError(null);
      setQuestion("");
      isUserScrolledUpRef.current = false;

      const clientRequestId = crypto.randomUUID();
      let activeConvId = conversationId;

      try {
        // Ensure conversation exists
        if (!activeConvId) {
          const newConvRes = await apiClient.createConversation(
            videoId,
            controller.signal,
          );
          activeConvId = newConvRes.conversation.id;
          setConversationId(activeConvId);
          setActiveTitle(newConvRes.conversation.title || "New Chat");
          await setVideoConversationId(videoId, activeConvId);
        }

        // Add optimistic user message
        const userMsg: ChatMessageData = {
          id: clientRequestId,
          role: "user",
          content: trimmed,
          status: "complete",
          createdAt: new Date().toISOString(),
        };

        // Add pending assistant message
        const pendingAssistantMsg: ChatMessageData = {
          id: `pending_${clientRequestId}`,
          role: "assistant",
          content: "",
          citations: [],
          status: "sending",
          createdAt: new Date().toISOString(),
        };

        setMessages((prev) => [...prev, userMsg, pendingAssistantMsg]);

        // Stream answer question
        await apiClient.streamQuestion(
          videoId,
          trimmed,
          {
            conversationId: activeConvId,
            clientRequestId,
          },
          {
            onToken(event) {
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === `pending_${clientRequestId}`
                    ? { ...m, content: m.content + event.text }
                    : m,
                ),
              );
            },
            onCitation(event) {
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === `pending_${clientRequestId}`
                    ? {
                        ...m,
                        citations: [...(m.citations ?? []), event.citation],
                      }
                    : m,
                ),
              );
            },
            onDone(event) {
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === `pending_${clientRequestId}`
                    ? {
                        ...m,
                        id: event.message.id,
                        content: event.message.content,
                        citations: event.message.citations,
                        grounded: event.message.grounded,
                        status: "complete",
                      }
                    : m,
                ),
              );
              // Update title from server if Turn 1 auto-titled
              if (activeConvId) {
                apiClient
                  .getConversation(activeConvId)
                  .then((res) => {
                    if (res.conversation.title) {
                      setActiveTitle(res.conversation.title);
                    }
                  })
                  .catch(() => {});
              }
            },
            onError(event) {
              setMessages((prev) =>
                prev.map((m) =>
                  m.id === `pending_${clientRequestId}`
                    ? {
                        ...m,
                        status: "error",
                        errorText: event.message,
                        content: m.content || "Failed to generate answer.",
                      }
                    : m,
                ),
              );
            },
          },
          controller.signal,
        );
      } catch (err: unknown) {
        if (controller.signal.aborted) {
          return;
        }

        const errMsg =
          err instanceof ApiClientError
            ? err.userMessage
            : err instanceof Error
              ? err.message
              : "Unable to generate answer.";

        setMessages((prev) =>
          prev.map((m) =>
            m.id === `pending_${clientRequestId}`
              ? {
                  ...m,
                  status: "error",
                  errorText: errMsg,
                  content: m.content || "Failed to generate answer.",
                }
              : m,
          ),
        );
      } finally {
        if (abortControllerRef.current === controller) {
          abortControllerRef.current = null;
        }
        setIsAsking(false);
      }
    },
    [isReady, isAsking, conversationId, videoId],
  );

  const handleSubmit = useCallback(
    async (e?: React.FormEvent) => {
      if (e) e.preventDefault();
      await executeQuestion(question);
    },
    [executeQuestion, question],
  );

  const handleRetry = useCallback(
    (failedMessageId: string) => {
      const idx = messages.findIndex((m) => m.id === failedMessageId);
      const prevMsg = idx > 0 ? messages[idx - 1] : undefined;
      if (prevMsg && prevMsg.role === "user") {
        const userPrompt = prevMsg.content;
        executeQuestion(userPrompt);
      }
    },
    [messages, executeQuestion],
  );

  const handleExportConversation = useCallback(() => {
    if (messages.length === 0) return;

    const lines: string[] = [
      `# YouTube AI Assistant — Conversation Export`,
      `**Conversation:** ${activeTitle}`,
      `**Video:** https://www.youtube.com/watch?v=${videoId}`,
      `**Date:** ${new Date().toLocaleString()}`,
      `\n---\n`,
    ];

    messages.forEach((m) => {
      const speaker = m.role === "user" ? "### User" : "### Assistant";
      lines.push(`${speaker}\n${formatAnswerForCopy(m.content, m.citations)}\n`);
    });

    const blob = new Blob([lines.join("\n")], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `youtube-ai-${videoId}-${Date.now()}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }, [messages, activeTitle, videoId]);

  return (
    <div className="relative rounded-2xl bg-white dark:bg-zinc-900/80 border border-zinc-200 dark:border-zinc-800 p-3.5 space-y-3 shadow-xs flex flex-col transition-colors">
      {/* Conversation Drawer Modal */}
      <ConversationDrawer
        videoId={videoId}
        isOpen={isDrawerOpen}
        activeConversationId={conversationId}
        onClose={() => setIsDrawerOpen(false)}
        onSelectConversation={handleSelectConversation}
        onNewChat={handleStartNewChat}
        onClearConversation={handleClearCurrentConversation}
      />

      {/* Header */}
      <div className="flex items-center justify-between pb-2 border-b border-zinc-100 dark:border-zinc-800">
        <div className="flex items-center space-x-2 truncate">
          <button
            type="button"
            onClick={() => setIsDrawerOpen((prev) => !prev)}
            className="p-1 -ml-1 text-zinc-500 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-100 hover:bg-zinc-100 dark:hover:bg-zinc-800 rounded-md transition-colors flex items-center space-x-1 cursor-pointer"
            title="Open conversation drawer"
            aria-label="Open conversation drawer"
          >
            <svg
              className="w-4 h-4 text-amber-500"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M4 6h16M4 12h16M4 18h7"
              />
            </svg>
          </button>
          <h3
            className="text-xs font-semibold text-zinc-800 dark:text-zinc-200 truncate"
            title={activeTitle}
          >
            {activeTitle}
          </h3>
          {messages.length > 0 && (
            <span className="text-[10px] text-zinc-400 font-mono bg-zinc-100 dark:bg-zinc-800 px-1.5 py-0.5 rounded-md shrink-0">
              {messages.filter((m) => m.role === "user").length} turns
            </span>
          )}
        </div>

        <div className="flex items-center space-x-1.5 shrink-0">
          {messages.length > 0 && (
            <button
              type="button"
              onClick={handleExportConversation}
              className="p-1 text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200 hover:bg-zinc-100 dark:hover:bg-zinc-800 rounded transition-colors"
              title="Export conversation as Markdown"
            >
              <svg
                className="w-3.5 h-3.5"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
                />
              </svg>
            </button>
          )}

          <button
            type="button"
            onClick={handleStartNewChat}
            disabled={isAsking}
            className="text-[11px] font-medium text-amber-600 dark:text-amber-400 hover:underline disabled:opacity-40 cursor-pointer"
            title="Start a new conversation thread"
          >
            + New Chat
          </button>
        </div>
      </div>

      {/* Quick Actions Bar */}
      {isReady && (
        <div className="pt-0.5 pb-1">
          <QuickActions
            onSelectAction={executeQuestion}
            disabled={!isReady || isAsking}
          />
        </div>
      )}

      {/* Messages Scroll Area */}
      <div
        ref={scrollContainerRef}
        onScroll={handleScroll}
        className="space-y-3.5 max-h-80 min-h-[140px] overflow-y-auto pr-1 text-xs scrollbar-thin scrollbar-thumb-zinc-300 dark:scrollbar-thumb-zinc-700"
        role="log"
        aria-live="polite"
      >
        {isLoadingHistory && (
          <div className="py-8 text-center text-zinc-400 text-xs font-mono">
            <div className="w-4 h-4 border-2 border-amber-500 border-t-transparent rounded-full animate-spin mx-auto mb-2" />
            Loading conversation history...
          </div>
        )}

        {!isLoadingHistory && messages.length === 0 && (
          <div className="py-8 text-center space-y-2">
            <div className="w-8 h-8 rounded-full bg-amber-500/15 text-amber-500 mx-auto flex items-center justify-center">
              <svg
                className="w-4 h-4"
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
                />
              </svg>
            </div>
            <p className="text-zinc-700 dark:text-zinc-300 font-medium text-xs">
              Ask anything about this video
            </p>
            <p className="text-[11px] text-zinc-400 max-w-xs mx-auto leading-relaxed">
              Use a Quick Action above or ask questions to verify facts with jumpable
              timestamps.
            </p>
          </div>
        )}

        {messages.map((msg) => (
          <ChatMessageItem
            key={msg.id}
            message={msg}
            videoId={videoId}
            onRetry={handleRetry}
          />
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Global Error Banner */}
      {globalError && (
        <div className="rounded-lg bg-red-50 dark:bg-red-950/40 border border-red-200 dark:border-red-900/40 p-2 text-xs text-red-600 dark:text-red-300 flex items-center justify-between">
          <span>{globalError}</span>
          <button
            type="button"
            onClick={() => setGlobalError(null)}
            className="text-red-400 hover:text-red-600 text-xs"
          >
            ✕
          </button>
        </div>
      )}

      {/* Input Form */}
      <form
        onSubmit={handleSubmit}
        className="space-y-2 pt-1 border-t border-zinc-100 dark:border-zinc-800"
      >
        <div className="relative">
          <input
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) {
                e.preventDefault();
                handleSubmit();
              }
            }}
            disabled={!isReady || isAsking}
            placeholder={
              isReady
                ? messages.length > 0
                  ? "Ask a follow-up (Ctrl+Enter to send)..."
                  : "Ask a question about the video (Ctrl+Enter to send)..."
                : "Waiting for video knowledge index..."
            }
            className="w-full text-xs bg-zinc-50 dark:bg-zinc-950/80 border border-zinc-200 dark:border-zinc-700/80 rounded-xl px-3 py-2 text-zinc-900 dark:text-zinc-100 placeholder-zinc-400 focus:outline-none focus:border-amber-500 focus:ring-1 focus:ring-amber-500 disabled:opacity-40 disabled:cursor-not-allowed shadow-inner transition-colors"
          />
        </div>

        <div className="flex items-center justify-between">
          <span className="text-[10px] text-zinc-400 font-medium">
            Grounded in transcript evidence
          </span>

          <div className="flex items-center space-x-2">
            {isAsking && (
              <button
                type="button"
                onClick={handleCancel}
                className="px-2.5 py-1 text-xs font-semibold text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-950/50 border border-red-200 dark:border-red-800/60 rounded-lg transition-colors flex items-center space-x-1 cursor-pointer"
                title="Stop generating response"
              >
                <span className="inline-block w-2 h-2 bg-red-500 rounded-xs" />
                <span>Stop</span>
              </button>
            )}

            <button
              type="submit"
              disabled={!isReady || isAsking || !question.trim()}
              className="inline-flex items-center px-3.5 py-1.5 text-xs font-semibold text-zinc-950 bg-amber-400 hover:bg-amber-300 active:bg-amber-500 disabled:opacity-40 disabled:cursor-not-allowed rounded-lg transition-colors focus:outline-none focus:ring-2 focus:ring-amber-400 cursor-pointer shadow-xs"
            >
              {isAsking ? "Streaming..." : "Send"}
            </button>
          </div>
        </div>
      </form>
    </div>
  );
};
