import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.app.services.llm_service import LLMService

async def main():
    p = Path(__file__).resolve().parent.parent / "uploads" / "demo_reel.mp3"
    print(f"Testing Groq Whisper STT on {p.name}...")
    segs = await LLMService.transcribe_audio_groq(p)
    print("Transcription result:")
    for s in segs:
        print(f"[{s['start']}s - {s['end']}s]: {s['text']}")
        print(f"Words: {[w['text'] for w in s.get('words', [])]}")

    print("\nTesting Gemini Burmese translation...")
    translated = await LLMService.translate_segments_gemini(segs, target_language="Burmese")
    for t in translated:
        print(f"Burmese [{t['start']}s - {t['end']}s]:")
        print(f"Text: {t['text']}")
        print(f"Chunks: {[w['text'] for w in t.get('words', [])]}")

if __name__ == "__main__":
    asyncio.run(main())
