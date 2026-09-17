import json
import subprocess
import logging
from pathlib import Path
from typing import Dict, Any, List
from backend.app.core.config import settings

logger = logging.getLogger(__name__)

def escape_ffmpeg_path(path: Path) -> str:
    """Escape file path for FFmpeg filter syntax (especially on Windows)."""
    p_str = str(path.resolve()).replace("\\", "/")
    # Escape colon for Windows drive letter e.g. D\:
    return p_str.replace(":", "\\:")

class FFmpegService:
    @staticmethod
    def probe_video(video_path: Path) -> Dict[str, Any]:
        """Probes video metadata using ffprobe."""
        cmd = [
            "ffprobe",
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height,r_frame_rate,duration",
            "-show_entries", "format=duration",
            "-of", "json",
            str(video_path)
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            raise RuntimeError(f"FFprobe error: {res.stderr}")
            
        data = json.loads(res.stdout)
        stream = data.get("streams", [{}])[0]
        fmt = data.get("format", {})
        
        width = int(stream.get("width", 1080))
        height = int(stream.get("height", 1920))
        
        # Duration fallback
        duration_str = stream.get("duration") or fmt.get("duration") or "0"
        duration = float(duration_str)
        
        # Aspect Ratio Classification
        ratio = width / height if height > 0 else 9/16
        if ratio < 0.7:
            aspect_ratio = "9:16"
        elif 0.85 <= ratio <= 1.15:
            aspect_ratio = "1:1"
        else:
            aspect_ratio = "16:9"
            
        return {
            "width": width,
            "height": height,
            "duration": duration,
            "aspect_ratio": aspect_ratio
        }

    @staticmethod
    def extract_audio(video_path: Path, output_audio_path: Path) -> Path:
        """Extracts 16kHz mono audio as MP3 (lightweight, under 500KB for API upload)."""
        output_audio_path.parent.mkdir(parents=True, exist_ok=True)
        cmd = [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-vn",
            "-acodec", "libmp3lame",
            "-ar", "16000",
            "-ac", "1",
            "-b:a", "64k",
            "-threads", str(settings.FFMPEG_THREADS),
            str(output_audio_path)
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            raise RuntimeError(f"FFmpeg audio extraction failed: {res.stderr}")
        return output_audio_path

    @staticmethod
    def burn_subtitles(
        video_path: Path,
        ass_path: Path,
        output_video_path: Path,
        fonts_dir: Path
    ) -> Path:
        """
        Burns styled ASS subtitles into video using libass.
        Constrained to 1-2 threads to keep peak RAM under 200MB on 1GB VPS.
        """
        output_video_path.parent.mkdir(parents=True, exist_ok=True)
        
        ass_esc = escape_ffmpeg_path(ass_path)
        fonts_esc = escape_ffmpeg_path(fonts_dir)
        vf_filter = f"subtitles='{ass_esc}':fontsdir='{fonts_esc}'"
        
        cmd = [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-vf", vf_filter,
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "22",
            "-c:a", "copy",
            "-threads", str(settings.FFMPEG_THREADS),
            str(output_video_path)
        ]
        logger.info(f"Running burn command: {' '.join(cmd)}")
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            raise RuntimeError(f"FFmpeg subtitle burning failed: {res.stderr}")
        return output_video_path

    @staticmethod
    def generate_srt(segments: List[Dict[str, Any]], output_path: Path) -> Path:
        """Generates standard .srt subtitle file."""
        def format_srt_time(sec: float) -> str:
            h = int(sec // 3600)
            m = int((sec % 3600) // 60)
            s = int(sec % 60)
            ms = int(round((sec - int(sec)) * 1000))
            if ms >= 1000:
                ms = 999
            return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

        srt_lines = []
        for idx, seg in enumerate(segments, 1):
            start = format_srt_time(float(seg.get("start", 0.0)))
            end = format_srt_time(float(seg.get("end", 0.0)))
            text = seg.get("text", "").strip()
            srt_lines.append(f"{idx}\n{start} --> {end}\n{text}\n")

        output_path.write_text("\n".join(srt_lines), encoding="utf-8")
        return output_path
