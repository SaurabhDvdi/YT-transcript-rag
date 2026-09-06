"""Caption text normalization and sanitization."""

import html
import re

NOISE_TAGS_REGEX = re.compile(
    r"\[(?:music|applause|laughter|cheering|giggles|sigh|gasp|screaming|inaudible)\]"
    r"|\((?:music|applause|laughter|cheering|giggles|sigh|gasp|screaming|inaudible)\)",
    re.IGNORECASE,
)
MUSIC_NOTES_REGEX = re.compile(r"[♪♫]")
WHITESPACE_REGEX = re.compile(r"\s+")


def decode_html_entities(text: str) -> str:
    """Decodes HTML entities without external DOM dependencies."""
    if not text or "&" not in text:
        return text
    return html.unescape(text)


def remove_noise_tags(text: str) -> str:
    """Strips non-speech audio cues commonly found in YouTube auto-captions."""
    text = MUSIC_NOTES_REGEX.sub("", text)
    return NOISE_TAGS_REGEX.sub("", text)


def clean_caption_text(text: str) -> str:
    """Normalizes raw caption text: unescapes HTML, strips noise tags, collapses whitespace."""
    if not text:
        return ""
    decoded = decode_html_entities(text)
    without_noise = remove_noise_tags(decoded)
    return WHITESPACE_REGEX.sub(" ", without_noise).strip()


normalize_text = clean_caption_text
