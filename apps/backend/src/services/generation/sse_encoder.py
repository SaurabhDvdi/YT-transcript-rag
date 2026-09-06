"""Server-Sent Events (SSE) wire protocol encoder."""

from src.schemas.generation import StreamEvent


def encode_sse(event: StreamEvent) -> str:
    """Encodes a typed StreamEvent into standard Server-Sent Events (SSE) wire format."""
    return f"event: {event.type}\ndata: {event.model_dump_json(by_alias=True)}\n\n"
