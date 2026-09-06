import React from "react";

interface QuickActionItem {
  id: string;
  label: string;
  prompt: string;
  icon: React.ReactNode;
  description: string;
}

const QUICK_ACTIONS: QuickActionItem[] = [
  {
    id: "summarize",
    label: "Summarize",
    prompt:
      "Summarize the main topics and takeaways of this video in a concise overview.",
    description: "Get a high-level summary of the entire video",
    icon: (
      <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
        />
      </svg>
    ),
  },
  {
    id: "key-points",
    label: "Key Points",
    prompt:
      "List the key points and important takeaways from this video in bullet points.",
    description: "Extract the core bullet points and arguments",
    icon: (
      <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M4 6h16M4 10h16M4 14h16M4 18h16"
        />
      </svg>
    ),
  },
  {
    id: "explain-simply",
    label: "Explain Simply",
    prompt: "Explain the core concepts of this video in simple, beginner-friendly terms.",
    description: "Clear explanation avoiding excessive technical jargon",
    icon: (
      <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
        />
      </svg>
    ),
  },
];

interface QuickActionsProps {
  onSelectAction: (prompt: string) => void;
  disabled?: boolean;
}

export const QuickActions: React.FC<QuickActionsProps> = ({
  onSelectAction,
  disabled = false,
}) => {
  return (
    <div className="flex items-center gap-1.5 flex-wrap">
      {QUICK_ACTIONS.map((action) => (
        <button
          key={action.id}
          type="button"
          disabled={disabled}
          onClick={() => onSelectAction(action.prompt)}
          title={action.description}
          className="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-lg text-xs font-medium transition-colors cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed bg-zinc-100 dark:bg-zinc-800/80 hover:bg-zinc-200 dark:hover:bg-zinc-700/80 active:bg-zinc-300 dark:active:bg-zinc-600 text-zinc-800 dark:text-zinc-200 border border-zinc-200 dark:border-zinc-700/60 shadow-xs focus:outline-none focus:ring-2 focus:ring-amber-500/40"
        >
          <span className="text-amber-600 dark:text-amber-400">{action.icon}</span>
          <span>{action.label}</span>
        </button>
      ))}
    </div>
  );
};
