import React from "react";

interface LoadingStateProps {
  message?: string;
}

export const LoadingState: React.FC<LoadingStateProps> = ({
  message = "Detecting video...",
}) => {
  return (
    <div
      role="status"
      aria-live="polite"
      className="flex flex-col items-center justify-center p-8 text-center space-y-4 rounded-xl bg-zinc-900/60 border border-zinc-800"
    >
      <div className="relative w-10 h-10">
        {/* Outer subtle ring */}
        <div className="absolute inset-0 rounded-full border-2 border-zinc-700 opacity-30" />
        {/* Animated spinner */}
        <div className="absolute inset-0 rounded-full border-2 border-red-500 border-t-transparent animate-spin" />
      </div>
      <p className="text-sm font-medium text-zinc-300 animate-pulse">{message}</p>
    </div>
  );
};
