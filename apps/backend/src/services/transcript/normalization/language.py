"""Language selection and display name resolution."""

import re

from src.services.transcript.normalization.constants import DEFAULT_PREFERRED_LANGUAGES
from src.services.transcript.types import RawCaptionTrack

LANGUAGE_DISPLAY_NAMES: dict[str, str] = {
    "en": "English",
    "en-US": "English (United States)",
    "en-GB": "English (United Kingdom)",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "hi": "Hindi",
    "ja": "Japanese",
    "ko": "Korean",
    "zh": "Chinese",
    "zh-Hans": "Chinese (Simplified)",
    "zh-Hant": "Chinese (Traditional)",
    "pt": "Portuguese",
    "pt-BR": "Portuguese (Brazil)",
    "ru": "Russian",
    "it": "Italian",
    "ar": "Arabic",
    "nl": "Dutch",
    "tr": "Turkish",
}


def get_language_display_name(language_code: str) -> str:
    """Gets human-readable display name for a language code."""
    if not language_code:
        return "Unknown"

    direct = LANGUAGE_DISPLAY_NAMES.get(language_code)
    if direct:
        return direct

    base = re.split(r"[-_]", language_code)[0].lower()
    base_match = LANGUAGE_DISPLAY_NAMES.get(base)
    if base_match:
        return base_match

    return language_code.upper()


def _normalize_lang(code: str) -> str:
    return code.lower().strip()


def _language_matches(track_lang: str, target_lang: str) -> bool:
    norm_track = _normalize_lang(track_lang)
    norm_target = _normalize_lang(target_lang)
    if norm_track == norm_target:
        return True
    base_track = norm_track.split("-")[0].split("_")[0]
    base_target = norm_target.split("-")[0].split("_")[0]
    return base_track == base_target


def select_best_caption_track(
    tracks: list[RawCaptionTrack],
    preferred_languages: list[str] | None = None,
) -> RawCaptionTrack | None:
    """Selects the best caption track based on priority:

    1. Manual captions in requested languages
    2. Auto-generated captions in requested languages
    3. Manual English captions
    4. Auto-generated English captions
    5. Any available manual caption track
    6. Any available auto-generated caption track
    """
    if not tracks:
        return None

    prefs = preferred_languages or DEFAULT_PREFERRED_LANGUAGES

    # 1. Manual captions in requested languages
    for pref in prefs:
        for t in tracks:
            if not t.is_auto_generated and _language_matches(t.language_code, pref):
                return t

    # 2. Auto-generated captions in requested languages
    for pref in prefs:
        for t in tracks:
            if t.is_auto_generated and _language_matches(t.language_code, pref):
                return t

    # 3. Manual English
    for t in tracks:
        if not t.is_auto_generated and _language_matches(t.language_code, "en"):
            return t

    # 4. Auto-generated English
    for t in tracks:
        if t.is_auto_generated and _language_matches(t.language_code, "en"):
            return t

    # 5. Any manual caption
    for t in tracks:
        if not t.is_auto_generated:
            return t

    # 6. Any auto caption
    return tracks[0] if tracks else None
