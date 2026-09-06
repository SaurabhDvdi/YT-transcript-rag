"""Secondary fallback transcript provider parsing watch page player responses."""

import json
import re

import httpx

from src.core.errors import AppError
from src.schemas.transcript import Transcript
from src.services.transcript.normalization.language import (
    get_language_display_name,
    select_best_caption_track,
)
from src.services.transcript.normalization.segment_merger import merge_raw_caption_events
from src.services.transcript.normalization.validation import validate_transcript
from src.services.transcript.providers.caption_parser import (
    parse_json3_captions,
    parse_xml_captions,
)
from src.services.transcript.types import (
    RawCaptionTrack,
    TranscriptOptions,
    TranscriptResult,
    TranscriptSource,
)

YT_INITIAL_PLAYER_RESPONSE_REGEX = re.compile(
    r"ytInitialPlayerResponse\s*=\s*(\{.+?\});\s*(?:var|<\/script)", re.DOTALL
)
YT_INITIAL_PLAYER_FALLBACK_REGEX = re.compile(
    r"ytInitialPlayerResponse\s*=\s*(\{.+?\});", re.DOTALL
)


class YouTubeWatchProvider:
    """Secondary fallback transcript provider parsing watch page HTML."""

    @property
    def name(self) -> str:
        return "youtube-watch"

    async def get_transcript(
        self, video_id: str, options: TranscriptOptions | None = None
    ) -> TranscriptResult:
        watch_url = f"https://www.youtube.com/watch?v={video_id}"
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        }

        try:
            async with httpx.AsyncClient(headers=headers, timeout=15.0) as client:
                resp = await client.get(watch_url)
                if resp.status_code != 200:
                    raise AppError(
                        "PROVIDER_TEMPORARY_FAILURE",
                        502,
                        f"Watch page returned HTTP {resp.status_code}",
                    )
                html = resp.text
        except AppError:
            raise
        except Exception as err:
            raise AppError(
                "PROVIDER_TEMPORARY_FAILURE",
                502,
                f"Watch page network failure: {err}",
            ) from err

        match = YT_INITIAL_PLAYER_RESPONSE_REGEX.search(
            html
        ) or YT_INITIAL_PLAYER_FALLBACK_REGEX.search(html)
        if not match:
            raise AppError(
                "CAPTIONS_UNAVAILABLE",
                404,
                "Player response could not be extracted from watch page.",
            )

        try:
            player_data = json.loads(match.group(1))
        except Exception as err:
            raise AppError(
                "PROVIDER_INVALID_RESPONSE",
                502,
                "Failed to parse ytInitialPlayerResponse from watch page.",
            ) from err

        captions = player_data.get("captions", {})
        tracklist = captions.get("playerCaptionsTracklistRenderer", {})
        raw_tracks = tracklist.get("captionTracks", [])

        if not raw_tracks or not isinstance(raw_tracks, list):
            raise AppError(
                "CAPTIONS_UNAVAILABLE",
                404,
                "No caption tracks available on watch page.",
            )

        parsed_tracks: list[RawCaptionTrack] = []
        for t in raw_tracks:
            base_url = t.get("baseUrl")
            if not base_url:
                continue
            name_obj = t.get("name", {})
            name_str = ""
            if isinstance(name_obj, dict):
                runs = name_obj.get("runs")
                if isinstance(runs, list) and runs and "text" in runs[0]:
                    name_str = runs[0]["text"]
                elif "simpleText" in name_obj:
                    name_str = name_obj["simpleText"]

            kind = t.get("kind")
            vss_id = t.get("vssId", "")
            is_auto = kind == "asr" or vss_id.startswith("a.")

            parsed_tracks.append(
                RawCaptionTrack(
                    base_url=base_url,
                    name=name_str,
                    vss_id=vss_id,
                    language_code=t.get("languageCode", "en"),
                    is_auto_generated=is_auto,
                    kind=kind,
                )
            )

        prefs = options.preferred_languages if options else None
        selected = select_best_caption_track(parsed_tracks, prefs)
        if not selected:
            raise AppError("LANGUAGE_UNAVAILABLE", 404, "No suitable language caption track found.")

        caption_text = ""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                c_resp = await client.get(f"{selected.base_url}&fmt=json3")
                if c_resp.status_code == 200:
                    caption_text = c_resp.text
        except Exception:
            pass

        if not caption_text:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    fb_resp = await client.get(selected.base_url)
                    if fb_resp.status_code == 200:
                        caption_text = fb_resp.text
            except Exception as err:
                raise AppError(
                    "PROVIDER_TEMPORARY_FAILURE",
                    502,
                    f"Failed to fetch caption data: {err}",
                ) from err

        events = parse_json3_captions(caption_text)
        if not events:
            events = parse_xml_captions(caption_text)

        if not events:
            raise AppError(
                "TRANSCRIPT_NOT_FOUND", 404, "Caption track returned zero text segments."
            )

        segments = merge_raw_caption_events(events)
        if not segments:
            raise AppError(
                "TRANSCRIPT_NOT_FOUND", 404, "Normalized transcript produced zero valid segments."
            )

        total_dur = segments[-1].end if segments else 0.0
        result = TranscriptResult(
            video_id=video_id,
            language=get_language_display_name(selected.language_code),
            language_code=selected.language_code,
            is_auto_generated=selected.is_auto_generated,
            segments=segments,
            total_duration=total_dur,
            source=TranscriptSource(
                provider=self.name,
                language_code=selected.language_code,
                is_auto_generated=selected.is_auto_generated,
            ),
        )

        validate_transcript(
            Transcript(
                video_id=result.video_id,
                language=result.language,
                language_code=result.language_code,
                is_auto_generated=result.is_auto_generated,
                segments=result.segments,
                total_duration=result.total_duration,
            )
        )

        return result
