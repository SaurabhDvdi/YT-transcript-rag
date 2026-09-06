import React, { useState, useEffect, useCallback, useRef } from "react";
import type { Conversation } from "@youtube-ai/shared-types";
import { apiClient } from "../services/api";

interface ConversationDrawerProps {
  videoId: string;
  isOpen: boolean;
  activeConversationId: string | null;
  onClose: () => void;
  onSelectConversation: (conversationId: string) => void;
  onNewChat: () => void;
  onClearConversation: () => void;
}

export const ConversationDrawer: React.FC<ConversationDrawerProps> = ({
  videoId,
  isOpen,
  activeConversationId,
  onClose,
  onSelectConversation,
  onNewChat,
  onClearConversation,
}) => {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitleText, setEditTitleText] = useState("");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  // Delete Confirmation State
  const [deletingConv, setDeletingConv] = useState<Conversation | null>(null);

  const drawerRef = useRef<HTMLDivElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);
  const cancelDeleteRef = useRef<HTMLButtonElement>(null);

  const fetchConversations = useCallback(async () => {
    if (!videoId) return;
    setIsLoading(true);
    setErrorMessage(null);
    try {
      const res = await apiClient.listConversations(videoId, 50);
      setConversations(res.conversations);
    } catch {
      setErrorMessage("Failed to load conversations");
    } finally {
      setIsLoading(false);
    }
  }, [videoId]);

  useEffect(() => {
    if (isOpen) {
      fetchConversations();
      setSearchQuery("");
      setEditingId(null);
      setDeletingConv(null);
      setTimeout(() => searchInputRef.current?.focus(), 50);
    }
  }, [isOpen, fetchConversations]);

  // Esc key handling
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!isOpen) return;
      if (e.key === "Escape") {
        if (deletingConv) {
          setDeletingConv(null);
        } else {
          onClose();
        }
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, deletingConv, onClose]);

  const confirmDelete = async () => {
    if (!deletingConv) return;
    const targetId = deletingConv.id;
    try {
      await apiClient.deleteConversation(targetId, videoId);
      setConversations((prev) => prev.filter((c) => c.id !== targetId));
      if (activeConversationId === targetId) {
        onNewChat();
      }
      setDeletingConv(null);
    } catch {
      setErrorMessage("Failed to delete conversation");
    }
  };

  const handleStartEdit = (e: React.MouseEvent, conv: Conversation) => {
    e.stopPropagation();
    setEditingId(conv.id);
    setEditTitleText(conv.title);
  };

  const handleSaveEdit = async (
    e: React.FormEvent | React.MouseEvent,
    conversationId: string,
  ) => {
    e.stopPropagation();
    if (e.type === "submit") (e as React.FormEvent).preventDefault();
    const cleanTitle = editTitleText.trim();
    if (!cleanTitle) {
      setEditingId(null);
      return;
    }

    try {
      const res = await apiClient.updateConversationTitle(
        conversationId,
        cleanTitle,
        videoId,
      );
      setConversations((prev) =>
        prev.map((c) =>
          c.id === conversationId ? { ...c, title: res.conversation.title } : c,
        ),
      );
      setEditingId(null);
    } catch {
      setErrorMessage("Failed to rename conversation");
    }
  };

  if (!isOpen) return null;

  const filteredConversations = conversations.filter((c) =>
    (c.title || "New Conversation")
      .toLowerCase()
      .includes(searchQuery.toLowerCase().trim()),
  );

  return (
    <div
      ref={drawerRef}
      className="absolute inset-0 bg-white/95 dark:bg-zinc-950/95 backdrop-blur-sm z-30 flex flex-col rounded-xl overflow-hidden border border-zinc-200 dark:border-zinc-800 shadow-2xl animate-in fade-in duration-150"
      role="dialog"
      aria-label="Conversation History Drawer"
    >
      {/* Header */}
      <div className="flex items-center justify-between px-3.5 py-2.5 border-b border-zinc-200 dark:border-zinc-800/80 bg-zinc-50 dark:bg-zinc-900/60">
        <div className="flex items-center space-x-2">
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
              d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"
            />
          </svg>
          <span className="text-xs font-semibold text-zinc-900 dark:text-zinc-100">
            Conversations
          </span>
        </div>

        <div className="flex items-center space-x-1.5">
          <button
            type="button"
            onClick={onNewChat}
            className="text-[11px] px-2.5 py-1 rounded-md bg-amber-500 hover:bg-amber-400 active:bg-amber-600 text-zinc-950 font-semibold transition-colors flex items-center space-x-1 shadow-xs"
            title="Start a new chat"
          >
            <span>+ New</span>
          </button>
          <button
            type="button"
            onClick={onClose}
            className="text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-200 p-1 rounded hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors"
            title="Close drawer (Esc)"
            aria-label="Close drawer"
          >
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
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>
      </div>

      {/* Search Input */}
      <div className="px-3 pt-2.5 pb-1">
        <div className="relative">
          <svg
            className="w-3.5 h-3.5 text-zinc-400 absolute left-2.5 top-2.5 pointer-events-none"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
            />
          </svg>
          <input
            ref={searchInputRef}
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search conversations..."
            className="w-full text-xs pl-8 pr-7 py-1.5 rounded-lg bg-zinc-100 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 text-zinc-900 dark:text-zinc-100 placeholder-zinc-400 focus:outline-none focus:ring-1 focus:ring-amber-500"
          />
          {searchQuery && (
            <button
              type="button"
              onClick={() => setSearchQuery("")}
              className="absolute right-2 top-2 text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200 text-xs"
              title="Clear search"
            >
              ✕
            </button>
          )}
        </div>
      </div>

      {/* Error message if any */}
      {errorMessage && (
        <div className="px-3 py-1.5 bg-red-100 dark:bg-red-950/60 border-b border-red-200 dark:border-red-800/50 text-[11px] text-red-700 dark:text-red-300">
          {errorMessage}
        </div>
      )}

      {/* Conversation List */}
      <div className="flex-1 overflow-y-auto px-2 py-2 space-y-1 scrollbar-thin scrollbar-thumb-zinc-300 dark:scrollbar-thumb-zinc-700">
        {isLoading ? (
          <div className="flex items-center justify-center py-8 text-zinc-500 text-xs">
            <div className="w-3.5 h-3.5 border-2 border-amber-500 border-t-transparent rounded-full animate-spin mr-2" />
            <span>Loading conversations...</span>
          </div>
        ) : filteredConversations.length === 0 ? (
          <div className="text-center py-8 px-4 space-y-1">
            {searchQuery ? (
              <>
                <p className="text-zinc-500 dark:text-zinc-400 text-xs">
                  No conversations match &ldquo;{searchQuery}&rdquo;
                </p>
                <button
                  type="button"
                  onClick={() => setSearchQuery("")}
                  className="text-amber-600 dark:text-amber-400 text-[11px] hover:underline pt-1"
                >
                  Clear search
                </button>
              </>
            ) : (
              <>
                <p className="text-zinc-700 dark:text-zinc-300 font-medium text-xs">
                  No conversations yet
                </p>
                <p className="text-[11px] text-zinc-500">
                  Ask your first question about this video to start a conversation.
                </p>
              </>
            )}
          </div>
        ) : (
          filteredConversations.map((conv) => {
            const isActive = conv.id === activeConversationId;
            const isEditing = conv.id === editingId;

            return (
              <div
                key={conv.id}
                onClick={() => {
                  if (!isEditing) {
                    onSelectConversation(conv.id);
                    onClose();
                  }
                }}
                className={`group flex items-center justify-between px-2.5 py-2 rounded-lg text-xs cursor-pointer transition-colors border ${
                  isActive
                    ? "bg-amber-50 dark:bg-amber-950/30 border-amber-300 dark:border-amber-700/60 text-amber-950 dark:text-amber-200"
                    : "bg-zinc-50 dark:bg-zinc-900/40 hover:bg-zinc-100 dark:hover:bg-zinc-800/60 border-zinc-200 dark:border-zinc-800/50 text-zinc-800 dark:text-zinc-300"
                }`}
              >
                {isEditing ? (
                  <form
                    onSubmit={(e) => handleSaveEdit(e, conv.id)}
                    className="flex items-center space-x-1 flex-1 mr-1"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <input
                      type="text"
                      value={editTitleText}
                      onChange={(e) => setEditTitleText(e.target.value)}
                      maxLength={100}
                      className="bg-white dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 text-xs px-2 py-0.5 rounded border border-amber-500 focus:outline-none flex-1"
                      autoFocus
                    />
                    <button
                      type="submit"
                      className="text-emerald-600 dark:text-emerald-400 hover:opacity-80 px-1 py-0.5 text-xs font-bold"
                      title="Save title"
                    >
                      ✓
                    </button>
                    <button
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        setEditingId(null);
                      }}
                      className="text-zinc-500 hover:text-zinc-700 dark:hover:text-zinc-300 px-1 py-0.5 text-xs"
                      title="Cancel"
                    >
                      ✕
                    </button>
                  </form>
                ) : (
                  <>
                    <div className="flex-1 truncate pr-2">
                      <div className="font-medium truncate">
                        {conv.title || "New Conversation"}
                      </div>
                      <div className="text-[10px] text-zinc-400 dark:text-zinc-500">
                        {new Date(conv.updatedAt).toLocaleDateString(undefined, {
                          month: "short",
                          day: "numeric",
                          hour: "2-digit",
                          minute: "2-digit",
                        })}
                      </div>
                    </div>

                    <div className="flex items-center space-x-1 opacity-0 group-hover:opacity-100 transition-opacity">
                      <button
                        type="button"
                        onClick={(e) => handleStartEdit(e, conv)}
                        className="p-1 text-zinc-400 hover:text-zinc-700 dark:hover:text-zinc-200 hover:bg-zinc-200 dark:hover:bg-zinc-700 rounded"
                        title="Rename conversation"
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
                            d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z"
                          />
                        </svg>
                      </button>
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          setDeletingConv(conv);
                        }}
                        className="p-1 text-zinc-400 hover:text-red-500 hover:bg-zinc-200 dark:hover:bg-zinc-700 rounded"
                        title="Delete conversation"
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
                            d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                          />
                        </svg>
                      </button>
                    </div>
                  </>
                )}
              </div>
            );
          })
        )}
      </div>

      {/* Delete Confirmation Modal Overlay */}
      {deletingConv && (
        <div
          className="absolute inset-0 bg-black/60 z-50 flex items-center justify-center p-4 backdrop-blur-xs animate-in fade-in duration-100"
          role="alertdialog"
          aria-labelledby="delete-dialog-title"
          aria-describedby="delete-dialog-desc"
        >
          <div className="bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-700 rounded-xl p-4 space-y-3 max-w-xs w-full shadow-2xl">
            <h4
              id="delete-dialog-title"
              className="text-xs font-bold text-zinc-900 dark:text-zinc-100"
            >
              Delete &ldquo;{deletingConv.title || "Conversation"}&rdquo;?
            </h4>
            <p
              id="delete-dialog-desc"
              className="text-[11px] text-zinc-600 dark:text-zinc-400 leading-relaxed"
            >
              This permanently removes this conversation and all its messages. This action
              cannot be undone.
            </p>
            <div className="flex items-center justify-end space-x-2 pt-1">
              <button
                ref={cancelDeleteRef}
                type="button"
                onClick={() => setDeletingConv(null)}
                className="px-2.5 py-1 text-xs font-medium rounded-md bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-300 hover:bg-zinc-200 dark:hover:bg-zinc-700 transition-colors cursor-pointer"
                autoFocus
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={confirmDelete}
                className="px-2.5 py-1 text-xs font-semibold rounded-md bg-red-600 hover:bg-red-500 text-white transition-colors cursor-pointer"
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Footer */}
      <div className="px-3.5 py-2 border-t border-zinc-200 dark:border-zinc-800/80 bg-zinc-50 dark:bg-zinc-900/60 flex items-center justify-between">
        <button
          type="button"
          onClick={() => {
            onClearConversation();
            onClose();
          }}
          className="text-[11px] text-zinc-500 hover:text-red-500 transition-colors flex items-center space-x-1"
        >
          <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
            />
          </svg>
          <span>Clear current chat</span>
        </button>
        <span className="text-[10px] text-zinc-400 font-mono">
          {conversations.length} thread{conversations.length === 1 ? "" : "s"}
        </span>
      </div>
    </div>
  );
};
