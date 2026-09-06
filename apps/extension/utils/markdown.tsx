import React from "react";
import type { Citation } from "@youtube-ai/shared-types";
import { formatTimestamp } from "../components/CitationChip";

/**
 * Format plain answer text for clipboard copying:
 * - Replaces [E1], [E2] markers with readable timestamp references if citations are present.
 * - Appends a clean Sources list if verified citations exist.
 */
export function formatAnswerForCopy(content: string, citations?: Citation[]): string {
  let cleaned = content;

  if (citations && citations.length > 0) {
    // Replace [E1] with [01:15]
    citations.forEach((cit, idx) => {
      const marker = `\\[E${idx + 1}\\]`;
      const timeStr = `[${formatTimestamp(cit.start)}–${formatTimestamp(cit.end)}]`;
      cleaned = cleaned.replace(new RegExp(marker, "g"), timeStr);
    });

    // Also remove any remaining unmapped [E#] markers
    cleaned = cleaned.replace(/\[E\d+\]/g, "");

    const sourceList = citations
      .map((cit, idx) => {
        const citText = (cit as { text?: string }).text;
        return `Source ${idx + 1}: ${formatTimestamp(cit.start)}–${formatTimestamp(cit.end)}${citText ? ` ("${citText.trim()}")` : ""}`;
      })
      .join("\n");

    return `${cleaned.trim()}\n\n---\n${sourceList}`;
  }

  // If no citations, clean any phantom [E#] tags
  return cleaned.replace(/\[E\d+\]/g, "").trim();
}

/**
 * Parse inline formatting: bold (**), italic (*), and inline code (`).
 * Generates safe React elements without dangerouslySetInnerHTML.
 */
export function renderInlineMarkdown(
  text: string,
  keyPrefix = "inline",
): React.ReactNode[] {
  const parts: React.ReactNode[] = [];
  // Tokenize by code, bold, italic
  const regex = /(`[^`]+`|\*\*[^*]+\*\*|\*[^*]+\*)/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push(text.substring(lastIndex, match.index));
    }

    const token = match[0];
    const itemKey = `${keyPrefix}_${match.index}`;

    if (token.startsWith("`") && token.endsWith("`")) {
      parts.push(
        <code
          key={itemKey}
          className="px-1.5 py-0.5 rounded bg-zinc-100 dark:bg-zinc-800 text-amber-700 dark:text-amber-300 font-mono text-[11px] border border-zinc-200 dark:border-zinc-700/60"
        >
          {token.slice(1, -1)}
        </code>,
      );
    } else if (token.startsWith("**") && token.endsWith("**")) {
      parts.push(
        <strong key={itemKey} className="font-semibold text-zinc-900 dark:text-zinc-100">
          {token.slice(2, -2)}
        </strong>,
      );
    } else if (token.startsWith("*") && token.endsWith("*")) {
      parts.push(
        <em key={itemKey} className="italic text-zinc-800 dark:text-zinc-200">
          {token.slice(1, -1)}
        </em>,
      );
    }

    lastIndex = regex.lastIndex;
  }

  if (lastIndex < text.length) {
    parts.push(text.substring(lastIndex));
  }

  return parts;
}

/**
 * Safe block-level Markdown renderer without third-party HTML parsers.
 * Supports paragraphs, bullet lists, numbered lists, and fenced code blocks.
 */
export function renderSafeMarkdown(content: string): React.ReactNode {
  const lines = content.split("\n");
  const nodes: React.ReactNode[] = [];
  let currentList: { type: "ul" | "ol"; items: string[] } | null = null;
  let inCodeBlock = false;
  let codeBlockLines: string[] = [];

  const flushList = (key: number) => {
    if (!currentList) return;
    if (currentList.type === "ul") {
      nodes.push(
        <ul
          key={`ul_${key}`}
          className="space-y-1 my-2 pl-4 list-disc marker:text-amber-500"
        >
          {currentList.items.map((item, i) => (
            <li key={i} className="text-xs leading-relaxed">
              {renderInlineMarkdown(item, `li_${key}_${i}`)}
            </li>
          ))}
        </ul>,
      );
    } else {
      nodes.push(
        <ol
          key={`ol_${key}`}
          className="space-y-1 my-2 pl-4 list-decimal marker:text-amber-500"
        >
          {currentList.items.map((item, i) => (
            <li key={i} className="text-xs leading-relaxed">
              {renderInlineMarkdown(item, `li_${key}_${i}`)}
            </li>
          ))}
        </ol>,
      );
    }
    currentList = null;
  };

  lines.forEach((line, idx) => {
    const trimmed = line.trim();

    // Code block toggle
    if (trimmed.startsWith("```")) {
      if (inCodeBlock) {
        // End code block
        nodes.push(
          <pre
            key={`code_${idx}`}
            className="my-2 p-2.5 rounded-lg bg-zinc-950 text-zinc-200 font-mono text-[11px] overflow-x-auto border border-zinc-800"
          >
            <code>{codeBlockLines.join("\n")}</code>
          </pre>,
        );
        codeBlockLines = [];
        inCodeBlock = false;
      } else {
        flushList(idx);
        inCodeBlock = true;
      }
      return;
    }

    if (inCodeBlock) {
      codeBlockLines.push(line);
      return;
    }

    // Bullet list items (- or * or •)
    const bulletMatch = trimmed.match(/^[-*•]\s+(.+)/);
    if (bulletMatch && bulletMatch[1]) {
      if (!currentList || currentList.type !== "ul") {
        flushList(idx);
        currentList = { type: "ul", items: [] };
      }
      currentList.items.push(bulletMatch[1]);
      return;
    }

    // Numbered list items (1. item)
    const numberedMatch = trimmed.match(/^\d+\.\s+(.+)/);
    if (numberedMatch && numberedMatch[1]) {
      if (!currentList || currentList.type !== "ol") {
        flushList(idx);
        currentList = { type: "ol", items: [] };
      }
      currentList.items.push(numberedMatch[1]);
      return;
    }

    // Regular line
    flushList(idx);
    if (trimmed.length > 0) {
      nodes.push(
        <p key={`p_${idx}`} className="text-xs leading-relaxed my-1.5">
          {renderInlineMarkdown(trimmed, `p_${idx}`)}
        </p>,
      );
    }
  });

  flushList(lines.length);

  // If code block unclosed at end of stream
  if (inCodeBlock && codeBlockLines.length > 0) {
    nodes.push(
      <pre
        key="code_unclosed"
        className="my-2 p-2.5 rounded-lg bg-zinc-950 text-zinc-200 font-mono text-[11px] overflow-x-auto border border-zinc-800"
      >
        <code>{codeBlockLines.join("\n")}</code>
      </pre>,
    );
  }

  return <div className="space-y-1">{nodes}</div>;
}
