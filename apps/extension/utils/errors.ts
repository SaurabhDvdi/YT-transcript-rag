/**
 * Base custom error for extension operations.
 */
export class ExtensionError extends Error {
  public readonly code: string;
  public readonly userMessage: string;

  constructor(message: string, code: string = "EXTENSION_ERROR", userMessage?: string) {
    super(message);
    this.name = "ExtensionError";
    this.code = code;
    this.userMessage = userMessage ?? "An unexpected extension error occurred.";
    Object.setPrototypeOf(this, new.target.prototype);
  }
}

/**
 * Error thrown when YouTube video detection fails or encounters invalid input.
 */
export class VideoDetectionError extends ExtensionError {
  constructor(
    message: string,
    userMessage: string = "Unable to detect the current YouTube video.",
  ) {
    super(message, "VIDEO_DETECTION_ERROR", userMessage);
    this.name = "VideoDetectionError";
  }
}

/**
 * Error thrown during cross-context extension messaging.
 */
export class MessagingError extends ExtensionError {
  constructor(
    message: string,
    userMessage: string = "Communication between extension components failed.",
  ) {
    super(message, "MESSAGING_ERROR", userMessage);
    this.name = "MessagingError";
  }
}

/**
 * Format any thrown error into a safe, user-facing error message.
 * Ensures stack traces and raw internal error objects are never leaked to users.
 */
export function getFriendlyErrorMessage(
  error: unknown,
  fallback: string = "An unexpected error occurred.",
): string {
  if (error instanceof ExtensionError) {
    return error.userMessage;
  }
  if (error instanceof Error && error.message) {
    // If it's a standard error without sensitive details, sanitize length
    return error.message.length < 120 ? error.message : fallback;
  }
  return fallback;
}
