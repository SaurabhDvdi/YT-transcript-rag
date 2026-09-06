"""Parsers for YouTube JSON3 and TimedText XML caption responses."""

import json
import re

from src.services.transcript.normalization.normalize import decode_html_entities
from src.services.transcript.types import RawCaptionEvent

XML_TEXT_TAG_REGEX = re.compile(r"<text\s+([^>]*?)>([\s\S]*?)<\/text>", re.IGNORECASE)
XML_P_TAG_REGEX = re.compile(r"<p\s+([^>]*?)>([\s\S]*?)<\/p>", re.IGNORECASE)
HTML_TAG_STRIP_REGEX = re.compile(r"<[^>]+>")


def parse_json3_captions(json_text: str) -> list[RawCaptionEvent]:
    """Parses YouTube's JSON3 caption response format."""
    events: list[RawCaptionEvent] = []
    try:
        data = json.loads(json_text)
        raw_events = data.get("events")
        if not isinstance(raw_events, list):
            return []

        for evt in raw_events:
            t_start = evt.get("tStartMs")
            if t_start is None or not isinstance(t_start, (int, float)):
                continue

            text_parts: list[str] = []
            segs = evt.get("segs")
            if isinstance(segs, list):
                for seg in segs:
                    if isinstance(seg, dict) and "utf8" in seg:
                        text_parts.append(str(seg["utf8"]))

            text = "".join(text_parts).strip()
            if text and text != "\n":
                duration = evt.get("dDurationMs", 0)
                events.append(
                    RawCaptionEvent(
                        t_start_ms=int(t_start),
                        d_duration_ms=int(duration) if isinstance(duration, (int, float)) else 0,
                        text=text,
                    )
                )
    except Exception:
        return []

    return events


def parse_xml_captions(xml_text: str) -> list[RawCaptionEvent]:
    """Parses YouTube's XML / TimedText caption response format using robust regex."""
    events: list[RawCaptionEvent] = []

    # Pattern 1: <text start="1.23" dur="4.56">...</text>
    for match in XML_TEXT_TAG_REGEX.finditer(xml_text):
        attrs, raw_content = match.group(1), match.group(2)
        start_m = re.search(r'start="([\d.]+)"', attrs, re.IGNORECASE)
        dur_m = re.search(r'dur="([\d.]+)"', attrs, re.IGNORECASE)

        if start_m:
            try:
                start_sec = float(start_m.group(1))
                dur_sec = float(dur_m.group(1)) if dur_m else 0.0
                clean_text = decode_html_entities(HTML_TAG_STRIP_REGEX.sub("", raw_content)).strip()
                if clean_text:
                    events.append(
                        RawCaptionEvent(
                            t_start_ms=round(start_sec * 1000),
                            d_duration_ms=round(dur_sec * 1000),
                            text=clean_text,
                        )
                    )
            except ValueError:
                continue

    if events:
        return events

    # Pattern 2: <p t="1230" d="4560">...</p>
    for match in XML_P_TAG_REGEX.finditer(xml_text):
        attrs, raw_content = match.group(1), match.group(2)
        t_m = re.search(r't="(\d+)"', attrs, re.IGNORECASE)
        d_m = re.search(r'd="(\d+)"', attrs, re.IGNORECASE)

        if t_m:
            try:
                t_ms = int(t_m.group(1))
                d_ms = int(d_m.group(1)) if d_m else 0
                clean_text = decode_html_entities(HTML_TAG_STRIP_REGEX.sub("", raw_content)).strip()
                if clean_text:
                    events.append(
                        RawCaptionEvent(
                            t_start_ms=t_ms,
                            d_duration_ms=d_ms,
                            text=clean_text,
                        )
                    )
            except ValueError:
                continue

    return events
