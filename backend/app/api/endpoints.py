import uuid
import psutil
import re
import urllib.parse
import ipaddress
import socket
from pathlib import Path
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, UploadFile, File, Header, HTTPException, Depends, status
from fastapi.responses import FileResponse
from pydantic import BaseModel

from backend.app.core.config import settings, BASE_DIR
from backend.app.core.database import (
    record_media_file,
    log_activity,
    check_user_daily_quota,
    get_user_daily_video_count
)
from backend.app.core.security import get_current_user, get_current_user_optional
from backend.app.core.ass_styler import ASSGenerator
from backend.app.services.ffmpeg_service import FFmpegService
from backend.app.services.llm_service import LLMService
from backend.app.services.youtube_service import YouTubeService

router = APIRouter()

SAFE_FILENAME_REGEX = re.compile(r"^[a-zA-Z0-9_\-\.]+$")
ALLOWED_SERVE_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm", ".srt", ".ass", ".mp3"}
ALLOWED_YOUTUBE_DOMAINS = {"youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be"}

def validate_safe_media_path(filename: str, allowed_dirs: List[Path]) -> Path:
    """
    Strictly validates filename against path traversal attacks (.. / \\ null bytes)
    and ensures it stays strictly within permitted media directories.
    """
    if not filename or not SAFE_FILENAME_REGEX.match(filename) or ".." in filename:
        raise HTTPException(status_code=400, detail="Invalid filename format.")

    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_SERVE_EXTENSIONS:
        raise HTTPException(status_code=403, detail="File extension not permitted.")

    for directory in allowed_dirs:
        try:
            resolved_dir = directory.resolve()
            candidate = (directory / filename).resolve()
            if candidate.is_relative_to(resolved_dir) and candidate.is_file():
                return candidate
        except Exception:
            continue

    raise HTTPException(status_code=404, detail="File not found.")

def validate_youtube_url(url_str: str):
    """Protects against SSRF and private network scanning during YouTube import."""
    try:
        parsed = urllib.parse.urlparse(url_str.strip())
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid URL format.")

    if parsed.scheme not in ("http", "https"):
        raise HTTPException(status_code=400, detail="Only HTTP/HTTPS URLs are allowed.")

    hostname = (parsed.hostname or "").lower()
    if not hostname or hostname not in ALLOWED_YOUTUBE_DOMAINS:
        raise HTTPException(
            status_code=400,
            detail="Only valid YouTube and YouTube Shorts URLs are accepted."
        )

    # Validate resolved IP to block SSRF to internal/private VPS networks
    try:
        addr_info = socket.getaddrinfo(hostname, None)
        for entry in addr_info:
            ip_str = entry[4][0]
            ip = ipaddress.ip_address(ip_str)
            if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_unspecified:
                raise HTTPException(status_code=400, detail="Access to internal network addresses is strictly prohibited.")
    except socket.gaierror:
        raise HTTPException(status_code=400, detail="Could not resolve YouTube host address.")

class YouTubeImportRequest(BaseModel):
    url: str

class TranscribeRequest(BaseModel):
    video_id: str

class TranslateRequest(BaseModel):
    segments: List[Dict[str, Any]]
    target_language: str = "Burmese"

class RenderRequest(BaseModel):
    video_id: str
    segments: List[Dict[str, Any]]
    aspect_ratio: str = "9:16"
    font_name: str = "Myanmar Text"
    font_size: int = 70
    primary_color: str = "#FFFFFF"
    highlight_color: str = "#FFDD00"
    outline_color: str = "#000000"
    bg_color: str = "#000000"
    style_preset: str = "karaoke"
    position: str = "bottom"

def persist_gemini_key_if_new(key: Optional[str]):
    if not key or len(key.strip()) < 15:
        return
    key = key.strip()
    env_file = BASE_DIR / ".env"
    try:
        content = env_file.read_text(encoding="utf-8") if env_file.exists() else ""
        if f"GEMINI_API_KEY={key}" not in content:
            lines = content.splitlines()
            new_lines = []
            replaced = False
            for l in lines:
                if l.startswith("GEMINI_API_KEY="):
                    new_lines.append(f"GEMINI_API_KEY={key}")
                    replaced = True
                else:
                    new_lines.append(l)
            if not replaced:
                new_lines.append(f"GEMINI_API_KEY={key}")
            env_file.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
        settings.GEMINI_API_KEY = key
    except Exception as e:
        print(f"[Persist Key Error] {e}")

@router.get("/health")
def health_check():
    """Returns server status and RAM footprint in MB (for 1GB VPS monitoring)."""
    mem_info = psutil.Process().memory_info()
    ram_mb = round(mem_info.rss / (1024 * 1024), 2)
    sys_mem = psutil.virtual_memory()
    return {
        "status": "online",
        "app_ram_mb": ram_mb,
        "total_system_ram_mb": round(sys_mem.total / (1024 * 1024), 2),
        "available_system_ram_mb": round(sys_mem.available / (1024 * 1024), 2),
        "is_1gb_vps_safe": ram_mb < 200
    }

@router.get("/demo")
def load_demo():
    """Returns metadata for the pre-generated sample 9:16 reel."""
    return {
        "video_id": "demo_reel",
        "filename": "demo_reel.mp4",
        "video_url": "/api/video/demo_reel.mp4",
        "duration": 4.29,
        "width": 1080,
        "height": 1920,
        "aspect_ratio": "9:16"
    }

@router.post("/upload")
async def upload_video(
    file: UploadFile = File(...),
    authorization: Optional[str] = Header(None)
):
    """
    Uploads a video using chunked streaming with OOM memory protection.
    Caps max file size directly during stream and validates video format before storage.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename required.")

    ext = Path(file.filename).suffix.lower()
    if ext not in [".mp4", ".mov", ".mkv", ".webm"]:
        raise HTTPException(status_code=400, detail="Unsupported format. Permitted: MP4, MOV, MKV, WebM.")

    # Sanitize client filename
    sanitized_filename = re.sub(r"[^a-zA-Z0-9_\-\. ]", "_", Path(file.filename).name)[:100]

    video_id = str(uuid.uuid4())[:8]
    video_path = settings.UPLOAD_DIR / f"{video_id}{ext}"
    audio_path = settings.UPLOAD_DIR / f"{video_id}.mp3"

    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    total_bytes = 0
    first_chunk = True

    try:
        with open(video_path, "wb") as f:
            while True:
                chunk = await file.read(1024 * 1024)  # 1MB chunks
                if not chunk:
                    break
                total_bytes += len(chunk)
                if total_bytes > max_bytes:
                    raise HTTPException(
                        status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        detail=f"Uploaded file exceeds maximum limit of {settings.MAX_UPLOAD_SIZE_MB}MB."
                    )
                if first_chunk:
                    # Validate magic bytes
                    is_valid_magic = (
                        b"ftyp" in chunk[:32] or 
                        chunk[:4] == b"\x1a\x45\xdf\xa3" or 
                        b"moov" in chunk[:64] or
                        b"mdat" in chunk[:64]
                    )
                    if not is_valid_magic:
                        raise HTTPException(status_code=400, detail="Invalid video header or corrupted file.")
                    first_chunk = False
                f.write(chunk)

        if total_bytes == 0:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")

        # Probe metadata
        meta = FFmpegService.probe_video(video_path)

        # Extract audio (fast 64k mono MP3)
        FFmpegService.extract_audio(video_path, audio_path)

    except HTTPException:
        if video_path.exists():
            video_path.unlink()
        if audio_path.exists():
            audio_path.unlink()
        raise
    except Exception as e:
        if video_path.exists():
            video_path.unlink()
        if audio_path.exists():
            audio_path.unlink()
        raise HTTPException(status_code=500, detail=f"Failed to process video: {e}")

    # Register in DB with 3-day retention
    user = await get_current_user_optional(authorization)
    user_id = user["id"] if user else None
    record_media_file(
        video_id=video_id,
        filename=sanitized_filename,
        file_path=str(video_path),
        file_size_bytes=total_bytes,
        user_id=user_id,
        source_type="upload",
        hours_to_expire=settings.AUTO_CLEANUP_HOURS
    )

    return {
        "video_id": video_id,
        "filename": sanitized_filename,
        "video_url": f"/api/video/{video_id}{ext}",
        "duration": meta["duration"],
        "width": meta["width"],
        "height": meta["height"],
        "aspect_ratio": meta["aspect_ratio"]
    }

@router.post("/import-youtube")
async def import_youtube_video(
    req: YouTubeImportRequest,
    authorization: Optional[str] = Header(None)
):
    """Imports YouTube/Shorts video with anti-SSRF verification and 3-day retention."""
    url = req.url.strip()
    validate_youtube_url(url)

    user = await get_current_user_optional(authorization)
    user_id = user["id"] if user else None

    try:
        meta = await YouTubeService.import_video(url, user_id=user_id)
        return meta
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to import YouTube video: {e}")

@router.get("/user/quota")
async def get_user_quota(user: Dict[str, Any] = Depends(get_current_user)):
    """Returns today's processed video count and remaining daily quota."""
    is_admin = user.get("role") == "admin"
    if is_admin:
        return {"used": 0, "limit": 9999, "remaining": 9999, "is_admin": True}
    used = get_user_daily_video_count(user["id"])
    return {
        "used": used,
        "limit": 3,
        "remaining": max(0, 3 - used),
        "is_admin": False
    }

@router.post("/transcribe")
async def transcribe_audio(
    req: TranscribeRequest,
    x_gemini_api_key: Optional[str] = Header(None),
    x_groq_api_key: Optional[str] = Header(None),
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Transcribes audio using cloud Whisper/Gemini with word-level timestamps (0MB server RAM).
    Strictly enforces 3-video/day rate limit for regular users. Uses global host Gemini key.
    """
    # 1. Enforce Daily Quota (3 videos/day for regular users, unlimited for admin)
    allowed, used_today, remaining = check_user_daily_quota(user, video_id=req.video_id)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=f"Daily quota reached ({used_today}/3 videos used today). Please come back tomorrow or contact admin."
        )

    audio_path = settings.UPLOAD_DIR / f"{req.video_id}.mp3"
    if not audio_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found for this video ID.")

    # Global host API key prioritized, falling back to user custom key if provided
    effective_gemini = settings.GEMINI_API_KEY or user.get("gemini_key") or x_gemini_api_key
    effective_groq = settings.GROQ_API_KEY or user.get("groq_key") or x_groq_api_key

    if x_gemini_api_key and user.get("role") == "admin":
        persist_gemini_key_if_new(x_gemini_api_key)

    if not effective_gemini and not effective_groq:
        raise HTTPException(
            status_code=503,
            detail="Server Gemini API key is not configured. Please contact the administrator."
        )

    try:
        segments = await LLMService.transcribe_audio(
            audio_path,
            gemini_key=effective_gemini,
            groq_key=effective_groq
        )
        # Log successful transcription for quota tracking
        log_activity(user["id"], "transcribe", details=req.video_id)
        return {"status": "success", "segments": segments}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/translate")
async def translate_subtitles(
    req: TranslateRequest,
    x_gemini_api_key: Optional[str] = Header(None),
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Translates subtitle segments into natural, conversational phrasing (Burmese/Thai/etc.).
    Requires authenticated user and uses global host Gemini key.
    """
    effective_gemini = settings.GEMINI_API_KEY or user.get("gemini_key") or x_gemini_api_key

    if not effective_gemini:
        raise HTTPException(
            status_code=503,
            detail="Server Gemini API key is not configured. Please contact the administrator."
        )

    try:
        translated = await LLMService.translate_segments_gemini(
            req.segments,
            target_language=req.target_language,
            api_key=effective_gemini
        )
        log_activity(user["id"], "translate", details=f"Target: {req.target_language}")
        return {"status": "success", "segments": translated}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/render")
async def render_video(
    req: RenderRequest,
    authorization: Optional[str] = Header(None)
):
    """Generates styled ASS subtitles, creates SRT, and burns into MP4."""
    matches = list(settings.UPLOAD_DIR.glob(f"{req.video_id}.*"))
    video_matches = [m for m in matches if m.suffix.lower() in [".mp4", ".mov", ".mkv", ".webm"]]
    if not video_matches:
        raise HTTPException(status_code=404, detail="Source video not found.")

    src_video = video_matches[0]
    ass_path = settings.OUTPUT_DIR / f"{req.video_id}.ass"
    srt_path = settings.OUTPUT_DIR / f"{req.video_id}.srt"
    out_video = settings.OUTPUT_DIR / f"{req.video_id}_burned.mp4"

    # Generate ASS with chosen style & aspect ratio
    ASSGenerator.generate(
        segments=req.segments,
        output_path=ass_path,
        aspect_ratio=req.aspect_ratio,
        font_name=req.font_name,
        font_size=req.font_size,
        primary_color_hex=req.primary_color,
        highlight_color_hex=req.highlight_color,
        outline_color_hex=req.outline_color,
        bg_color_hex=req.bg_color,
        style_preset=req.style_preset,
        position=req.position
    )

    # Generate SRT
    FFmpegService.generate_srt(req.segments, srt_path)

    # Check if text contains Myanmar Unicode characters
    import re
    from backend.app.services.harfbuzz_service import HarfBuzzRenderer

    is_myanmar = any(
        re.search(r"[\u1000-\u109F\uAA60-\uAA7F]", s.get("text", ""))
        for s in req.segments
    )

    try:
        if is_myanmar:
            meta = FFmpegService.probe_video(src_video)
            HarfBuzzRenderer.burn_video(
                video_path=src_video,
                segments=req.segments,
                output_video_path=out_video,
                video_width=meta["width"],
                video_height=meta["height"],
                duration=meta["duration"],
                font_name=req.font_name,
                font_size=req.font_size,
                primary_color_hex=req.primary_color,
                highlight_color_hex=req.highlight_color,
                style_preset=req.style_preset,
                position=req.position
            )
        else:
            FFmpegService.burn_subtitles(
                video_path=src_video,
                ass_path=ass_path,
                output_video_path=out_video,
                fonts_dir=settings.FONTS_DIR
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Burning failed: {e}")

    # Register burned output in DB with 3-day retention
    if out_video.exists():
        user = await get_current_user_optional(authorization)
        user_id = user["id"] if user else None
        record_media_file(
            video_id=f"{req.video_id}_burned",
            filename=f"{req.video_id}_burned.mp4",
            file_path=str(out_video),
            file_size_bytes=out_video.stat().st_size,
            user_id=user_id,
            source_type="render",
            hours_to_expire=settings.AUTO_CLEANUP_HOURS
        )

    return {
        "status": "ready",
        "video_url": f"/api/video/{req.video_id}_burned.mp4",
        "download_url": f"/api/download/{req.video_id}_burned.mp4",
        "srt_url": f"/api/download/{req.video_id}.srt",
        "ass_url": f"/api/download/{req.video_id}.ass"
    }

@router.get("/download/{filename}")
async def download_file(filename: str):
    """Downloads burned video, SRT, or ASS with strict path traversal validation."""
    file_path = validate_safe_media_path(filename, [settings.OUTPUT_DIR])
    return FileResponse(file_path, filename=filename, media_type="application/octet-stream")

@router.get("/video/{filename}")
async def stream_video(filename: str):
    """Streams video for frontend player with strict path traversal validation."""
    file_path = validate_safe_media_path(filename, [settings.UPLOAD_DIR, settings.OUTPUT_DIR])
    ext = file_path.suffix.lower()
    media_type = "video/mp4" if ext == ".mp4" else ("video/webm" if ext == ".webm" else "application/octet-stream")
    return FileResponse(file_path, media_type=media_type)
