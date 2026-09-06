# UI & Design System Specification (Phase 11)

## 1. Design Philosophy

The YouTube AI Assistant interface is engineered specifically for sidepanel ergonomics (360px–480px width) to harmonize naturally with YouTube's web application while delivering a modern, accessible, and responsive user experience.

---

## 2. Design Tokens & CSS Variables

The extension employs semantic tokens mapped to CSS variables, supporting seamless theme switches without hardcoded color values.

### 2.1 CSS Variables Reference

| Token                   | CSS Variable          | Light Theme            | Dark Theme             |
| :---------------------- | :-------------------- | :--------------------- | :--------------------- |
| **Base Background**     | `--bg-base`           | `#f8fafc` (Slate 50)   | `#09090b` (Zinc 950)   |
| **Surface Background**  | `--bg-surface`        | `#ffffff` (White)      | `#18181b` (Zinc 900)   |
| **Elevated Background** | `--bg-elevated`       | `#f1f5f9` (Slate 100)  | `#27272a` (Zinc 800)   |
| **Theme Border**        | `--border-theme`      | `#e2e8f0` (Slate 200)  | `#27272a` (Zinc 800)   |
| **Primary Text**        | `--text-primary`      | `#0f172a` (Slate 900)  | `#f4f4f5` (Zinc 100)   |
| **Secondary Text**      | `--text-secondary`    | `#475569` (Slate 600)  | `#a1a1aa` (Zinc 400)   |
| **Muted Text**          | `--text-muted`        | `#94a3b8` (Slate 400)  | `#71717a` (Zinc 500)   |
| **Brand Color**         | `--color-brand`       | `#4f46e5` (Indigo 600) | `#6366f1` (Indigo 500) |
| **Brand Hover**         | `--color-brand-hover` | `#4338ca` (Indigo 700) | `#4f46e5` (Indigo 600) |

---

## 3. Typography & Sizing

- **Font Family**: Inter, `-apple-system`, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif.
- **Monospace Family**: `ui-monospace`, SFMono-Regular, Menlo, Monaco, Consolas, monospace.
- **Scale**:
  - `10px` (`text-[10px]`): Metadata, timestamps, status tags.
  - `11px` (`text-[11px]`): Tooltips, secondary actions, badge labels.
  - `12px` (`text-xs`): Chat body text, buttons, list titles, input text.
  - `14px` (`text-sm`): Card headings, header title.

---

## 4. Component Architecture

### 4.1 `CitationChip`

- **Purpose**: Render clickable transcript citation boundaries.
- **Visuals**: Amber accent badge (`bg-amber-500/15 text-amber-600 dark:text-amber-400 border border-amber-500/30`).
- **Interaction**:
  - `onClick`: Sends `{ type: "SEEK_VIDEO", timestamp }` message to the YouTube tab.
  - `onMouseEnter` / `onFocus`: Reveals floating tooltip with verified transcript excerpt.
  - Temporary feedback badge (`Seeked!`) confirms player jump.

### 4.2 `QuickActions`

- **Purpose**: Provide fast one-click prompts.
- **Actions**:
  1. _Summarize_: "Summarize the main topics and takeaways of this video in a concise overview."
  2. _Key Points_: "List the key points and important takeaways from this video in bullet points."
  3. _Explain Simply_: "Explain the core concepts of this video in simple, beginner-friendly terms."
- **Ergonomics**: Horizontal wrapping layout, amber icon accents, disabled during active generation.

### 4.3 `ChatMessageItem`

- **Purpose**: Render individual user and assistant messages.
- **Assistant Message**:
  - Safe Markdown parser (`renderSafeMarkdown`): bold, italic, lists, and fenced code blocks without external HTML injectors.
  - Streaming cursor animation (`animate-pulse`) when actively generating.
  - Interactive citation badges mapped to verified evidence.
  - Action footer: One-click formatted clipboard copy, retry button on error.

### 4.4 `ConversationDrawer`

- **Purpose**: Slide-over management for conversation threads.
- **Features**:
  - Search input with live client-side title filtering.
  - Rename conversation in-place with Enter to save and Esc to cancel.
  - Delete conversation triggering an accessible confirmation modal (`role="alertdialog"`).
  - Clear current chat button.

### 4.5 `SettingsModal`

- **Purpose**: Manage user preferences and application metadata.
- **Features**:
  - Theme selection: Light, Dark, or System Default.
  - Grounding & verification system information.
  - Keyboard accessible: Esc key dismiss, autofocus on close control.

### 4.6 `VideoInfo`

- **Purpose**: Display the currently detected YouTube video context.
- **Features**:
  - 16:9 thumbnail preview with fallback icon.
  - Two-line clamped title with full title tooltip.
  - Status badges: "Transcript ✓", "AI Ready ✓".
  - Copy clean video link button.

---

## 5. Accessibility (a11y) Guidelines

1. **Contrast Ratios**: All foreground/background color combinations exceed WCAG 2.1 AA (4.5:1 for normal text, 3:1 for large text and UI controls).
2. **Keyboard Navigation**:
   - All interactive controls (`button`, `a`, `input`) are keyboard focusable with visible focus rings (`focus:ring-2 focus:ring-brand/40`).
   - Modal and drawer overlays trap Escape keys (`handleKeyDown: "Escape"`).
3. **ARIA Semantics**:
   - Dialogs use `role="dialog"` or `role="alertdialog"` with `aria-labelledby` and `aria-describedby`.
   - Floating citation evidence uses `role="tooltip"`.
   - Streaming responses and status indicators use `aria-live="polite"`.
