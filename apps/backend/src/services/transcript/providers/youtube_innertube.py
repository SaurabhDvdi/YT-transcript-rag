"""Primary transcript provider using YouTube's Innertube Player API."""

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


class YouTubeInnertubeProvider:
    """Primary transcript provider using YouTube's Innertube API."""

    @property
    def name(self) -> str:
        return "youtube-innertube"

    async def get_transcript(
        self, video_id: str, options: TranscriptOptions | None = None
    ) -> TranscriptResult:
        player_url = "https://www.youtube.com/youtubei/v1/player"
        body = {
            "context": {
                "client": {
                    "clientName": "ANDROID",
                    "clientVersion": "19.09.37",
                    "hl": "en",
                    "gl": "US",
                },
            },
            "videoId": video_id,
        }
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "com.google.android.youtube/19.09.37 (Linux; U; Android 14; US) gzip",
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(player_url, json=body, headers=headers)
                if resp.status_code != 200:
                    raise AppError(
                        "PROVIDER_TEMPORARY_FAILURE",
                        502,
                        f"Innertube API returned HTTP {resp.status_code}",
                    )
                data = resp.json()
        except AppError:
            raise
        except Exception as err:
            raise AppError(
                "PROVIDER_TEMPORARY_FAILURE",
                502,
                f"Innertube network failure: {err}",
            ) from err

        captions = data.get("captions", {})
        tracklist = captions.get("playerCaptionsTracklistRenderer", {})
        raw_tracks = tracklist.get("captionTracks", [])

        if not raw_tracks or not isinstance(raw_tracks, list):
            raise AppError(
                "CAPTIONS_UNAVAILABLE",
                404,
                "No caption tracks available in Innertube response.",
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
