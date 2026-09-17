import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.app.core.config import settings
from backend.app.core.ass_styler import ASSGenerator
from backend.app.services.ffmpeg_service import FFmpegService
from backend.app.services.llm_service import LLMService

async def run_full_pipeline():
    print("=== Step 1: Transcribing Demo Reel Audio ===")
    audio_path = settings.UPLOAD_DIR / "demo_reel.mp3"
    assert audio_path.exists(), f"Audio {audio_path} not found"
    
    segments = await LLMService.transcribe_audio(audio_path)
    print(f"Transcribed {len(segments)} segments:")
    for s in segments:
        print(f"  [{s['start']}s - {s['end']}s]: {s['text']}")
        print(f"  Words: {[w['text'] for w in s.get('words', [])]}")

    print("\n=== Step 2: Translating to Spoken Burmese (Reel Style) ===")
    translated_segments = await LLMService.translate_segments_gemini(
        segments,
        target_language="Burmese"
    )
    for s in translated_segments:
        print(f"  Segment {s['id']}: length {len(s['text'])} chars, chunks {len(s.get('words', []))}")

    print("\n=== Step 3: Generating Styled ASS Subtitles ===")
    ass_path = settings.OUTPUT_DIR / "demo_reel.ass"
    ASSGenerator.generate(
        segments=translated_segments,
        output_path=ass_path,
        aspect_ratio="9:16",
        font_name="Myanmar Text",
        font_size=72,
        primary_color_hex="#FFFFFF",
        highlight_color_hex="#FFDD00",
        style_preset="karaoke",
        position="bottom"
    )
    print(f"ASS generated at {ass_path}")

    print("\n=== Step 4: Burning Subtitles into 9:16 MP4 ===")
    video_path = settings.UPLOAD_DIR / "demo_reel.mp4"
    burned_mp4 = settings.OUTPUT_DIR / "demo_reel_burned.mp4"
    
    FFmpegService.burn_subtitles(
        video_path=video_path,
        ass_path=ass_path,
        output_video_path=burned_mp4,
        fonts_dir=settings.FONTS_DIR
    )
    print(f"SUCCESS: Burned video created at {burned_mp4} (size: {burned_mp4.stat().st_size} bytes)")

if __name__ == "__main__":
    asyncio.run(run_full_pipeline())
