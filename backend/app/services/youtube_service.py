import os
import uuid
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional
import yt_dlp

from backend.app.core.config import settings
from backend.app.core.database import record_media_file
from backend.app.services.ffmpeg_service import FFmpegService

class YouTubeService:
    @staticmethod
    def _download_sync(url: str, video_id: str) -> Dict[str, Any]:
        output_template = str(settings.UPLOAD_DIR / f"{video_id}.%(ext)s")
        ydl_opts = {
            "format": "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best",
            "outtmpl": output_template,
            "merge_output_format": "mp4",
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "extractor_args": {
                "youtube": {
                    "player_client": ["android", "ios"]
                }
            },
            # Limit download rate or size to avoid exhausting VPS memory/disk
            "max_filesize": settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024,
        }

        # Optional cookie support if cookies.txt is provided in data folder
        cookie_file = settings.DATA_DIR / "cookies.txt"
        if cookie_file.exists():
            ydl_opts["cookiefile"] = str(cookie_file)


        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # First extract info to check duration
            info = ydl.extract_info(url, download=False)
            if not info:
                raise ValueError("Could not retrieve information for this YouTube video.")

            duration = info.get("duration", 0)
            if duration and duration > settings.MAX_YOUTUBE_DURATION_SEC:
                raise ValueError(
                    f"Video duration is {int(duration)}s. Maximum supported length is {settings.MAX_YOUTUBE_DURATION_SEC}s (5 minutes) for Shorts and Reels."
                )

            # Perform the download
            ydl.download([url])

            title = info.get("title", "youtube_short")
            return {
                "title": title,
                "duration": duration
            }

    @classmethod
    async def import_video(cls, url: str, user_id: Optional[int] = None) -> Dict[str, Any]:
        """Downloads YouTube/Shorts video asynchronously in threadpool to prevent blocking the event loop."""
        video_id = str(uuid.uuid4())[:8]
        video_path = settings.UPLOAD_DIR / f"{video_id}.mp4"
        audio_path = settings.UPLOAD_DIR / f"{video_id}.mp3"

        # Execute yt-dlp in thread pool
        info = await asyncio.to_thread(cls._download_sync, url, video_id)

        # Check that mp4 file was generated
        if not video_path.exists():
            # In case yt-dlp output a different extension like .mkv
            matches = list(settings.UPLOAD_DIR.glob(f"{video_id}.*"))
            video_matches = [m for m in matches if m.suffix.lower() in [".mp4", ".mkv", ".webm"]]
            if not video_matches:
                raise RuntimeError("Failed to locate downloaded YouTube video file.")
            actual_video = video_matches[0]
            if actual_video.suffix.lower() != ".mp4":
                # Convert to mp4
                actual_video.rename(video_path)

        # Extract audio (fast 64k mono MP3 for STT)
        FFmpegService.extract_audio(video_path, audio_path)

        # Probe video dimensions and aspect ratio
        meta = FFmpegService.probe_video(video_path)
        file_size = video_path.stat().st_size

        # Record in DB with 3-day (72h) retention
        sanitized_title = "".join(c for c in info.get("title", "yt_video") if c.isalnum() or c in " _-")[:40]
        filename = f"{sanitized_title}.mp4"

        record_media_file(
            video_id=video_id,
            filename=filename,
            file_path=str(video_path),
            file_size_bytes=file_size,
            user_id=user_id,
            source_type="youtube",
            hours_to_expire=settings.AUTO_CLEANUP_HOURS
        )

        return {
            "video_id": video_id,
            "filename": filename,
            "video_url": f"/api/video/{video_id}.mp4",
            "duration": meta["duration"],
            "width": meta["width"],
            "height": meta["height"],
            "aspect_ratio": meta["aspect_ratio"]
        }
