import type { Citation } from "./generation";

/**
 * Valid roles for conversation participants.
 */
export type MessageRole = "user" | "assistant";

/**
 * Origin of the conversation title.
 */
export type TitleSource = "auto" | "user";

/**
 * A conversation thread associated with a specific YouTube video.
 */
export interface Conversation {
  id: string;
  videoId: string;
  title: string;
  titleSource: TitleSource;
  createdAt: string;
  updatedAt: string;
  userId?: string | null;
}

/**
 * Lightweight conversation metadata for drawer and listing views.
 */
export interface ConversationSummary {
  id: string;
  videoId: string;
  title: string;
  titleSource: TitleSource;
  createdAt: string;
  updatedAt: string;
  userId?: string | null;
}

/**
 * A message within a conversation.
 */
export interface ConversationMessage {
  id: string;
  conversationId: string;
  role: MessageRole;
  content: string;
  citations?: Citation[];
  grounded?: boolean;
  clientRequestId?: string;
  createdAt: string;
}

/**
 * Response returned when a conversation is created.
 */
export interface CreateConversationResponse {
  success: true;
  conversation: Conversation;
  requestId: string;
}

/**
 * Response returned when listing conversations for a video.
 */
export interface ConversationListResponse {
  success: true;
  videoId: string;
  conversations: Conversation[];
  requestId: string;
}

/**
 * Response returned when fetching a single conversation with its recent messages.
 */
export interface ConversationDetailResponse {
  success: true;
  conversation: Conversation;
  messages: ConversationMessage[];
  requestId: string;
}

/**
 * Paginated response for messages within a conversation.
 */
export interface ConversationMessagesResponse {
  success: true;
  conversationId: string;
  messages: ConversationMessage[];
  nextCursor?: string;
  requestId: string;
}

/**
 * Request payload for updating conversation metadata (e.g. title).
 */
export interface ConversationUpdateRequest {
  title: string;
}

/**
 * Response returned after successfully updating a conversation.
 */
export interface ConversationUpdateResponse {
  success: true;
  conversation: Conversation;
  requestId: string;
}

/**
 * Response returned after successfully deleting a conversation.
 */
export interface ConversationDeleteResponse {
  success: true;
  conversationId: string;
  requestId: string;
}

// ============================================================================
// Typed Streaming Protocol (SSE)
// ============================================================================

export interface StreamStartEvent {
  type: "start";
  requestId: string;
  conversationId: string;
  messageId: string;
}

export interface StreamTokenEvent {
  type: "token";
  text: string;
}

export interface StreamCitationEvent {
  type: "citation";
  citation: Citation;
}

export interface StreamDoneEvent {
  type: "done";
  message: ConversationMessage;
}

export interface StreamErrorEvent {
  type: "error";
  code: string;
  message: string;
}

export type StreamEvent =
  | StreamStartEvent
  | StreamTokenEvent
  | StreamCitationEvent
  | StreamDoneEvent
  | StreamErrorEvent;
