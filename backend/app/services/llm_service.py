import json
import logging
import base64
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
import httpx

from backend.app.core.config import settings
from backend.app.core.burmese_shaping import (
    normalize_myanmar_unicode,
    segment_myanmar_syllables,
    chunk_text_for_reels
)

logger = logging.getLogger(__name__)

CANDIDATE_GEMINI_MODELS = [
    "gemini-2.5-flash",
    "gemini-flash-latest",
    "gemini-2.5-flash-lite",
    "gemini-flash-lite-latest",
    "gemini-3.5-flash"
]

def robust_json_loads(text: str) -> Any:
    """Robustly parses JSON from LLM output, handling markdown fences and common syntax issues."""
    cleaned = re.sub(r"^```json\s*", "", text.strip(), flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    try:
        return json.loads(cleaned)
    except Exception:
        pass

    # Extract JSON array or object
    match = re.search(r"(\[[\s\S]*\]|\{[\s\S]*\})", cleaned)
    if match:
        candidate = match.group(1)
        # Fix trailing commas
        candidate = re.sub(r",\s*([\]}])", r"\1", candidate)
        # Fix missing commas between objects: } { -> }, {
        candidate = re.sub(r"\}\s*\{", "}, {", candidate)
        try:
            return json.loads(candidate)
        except Exception:
            pass

    # Regex extraction fallback for segments
    segments = []
    item_pattern = re.compile(
        r'\{\s*"id"\s*:\s*(\d+)\s*,\s*"start"\s*:\s*([\d\.]+)\s*,\s*"end"\s*:\s*([\d\.]+)\s*,\s*"text"\s*:\s*"([^"]+)"',
        re.DOTALL
    )
    for m in item_pattern.finditer(cleaned):
        segments.append({
            "id": int(m.group(1)),
            "start": float(m.group(2)),
            "end": float(m.group(3)),
            "text": m.group(4),
            "words": []
        })
    if segments:
        return segments

    raise json.JSONDecodeError("Could not parse LLM JSON output", text, 0)

BURMESE_REEL_SYSTEM_PROMPT = """You are an elite short-form video subtitle translator specializing in TikTok, Instagram Reels, and YouTube Shorts.

Translate the provided dialogue segments into natural, conversational, spoken Burmese (စကားပြောစတိုင် / Colloquial).

CRITICAL RULES:
1. NEVER use stiff textbook/literary Burmese endings (NEVER use 'သည်။', 'ပါသည်', 'သွားရောက်ခဲ့သည်', 'ဖြစ်ပေါ်လာသည်').
2. ALWAYS use modern, punchy colloquial endings (e.g. 'တယ်', 'ခဲ့တယ်', 'သွားတယ်', 'ဖြစ်သွားတာ', 'နော်', 'ဗျာ', 'ရှင့်', 'တာကွာ').
3. Keep the translation concise, punchy, and modern so creators can read it in 1-2 seconds.
4. Use standard Myanmar Unicode (U+1000 - U+109F) exclusively. Zero foreign or invalid characters.
5. Retain slang, emotion, and humor accurately.
6. Return strictly valid JSON array matching this schema:
[
  {
    "id": 0,
    "translated_text": "မနေ့က ရန်ကုန်ကို သွားတုန်း ထူးဆန်းတာတစ်ခု ဖြစ်သွားတယ်"
  }
]
No extra commentary, markdown code fences, or explanations. Only the raw JSON array.
"""

GENERIC_REEL_SYSTEM_PROMPT = """You are an elite short-form video subtitle translator for TikTok, Instagram Reels, and YouTube Shorts.
Translate the provided dialogue segments into natural, modern, conversational {target_language}.
Rules:
1. Punchy, engaging, spoken tone.
2. Keep phrasing short and readable on mobile screens.
3. Return strictly valid JSON array matching:
[
  {
    "id": 0,
    "translated_text": "Translated punchy subtitle here"
  }
]
Only return raw JSON array.
"""

class LLMService:
    @staticmethod
    async def transcribe_audio_gemini(
        audio_path: Path,
        api_key: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Transcribes audio using Gemini Flash with word-level timestamps (0MB server RAM).
        """
        key = api_key or settings.GEMINI_API_KEY
        if not key:
            raise ValueError("GEMINI_API_KEY is required for speech-to-text. Please provide it in settings or request header.")

        audio_bytes = audio_path.read_bytes()
        b64_audio = base64.b64encode(audio_bytes).decode("utf-8")

        prompt = """Listen carefully to this audio recording. 
Transcribe the speech with accurate timestamps and word-level timings.
For short-form reels, segment sentences into punchy bursts (1-5 words or 1-2 seconds each).
Return strictly valid JSON matching this schema:
[
  {
    "id": 0,
    "start": 0.0,
    "end": 2.5,
    "text": "transcribed segment text",
    "words": [
      {"text": "word1", "start": 0.0, "end": 0.5},
      {"text": "word2", "start": 0.5, "end": 1.2}
    ]
  }
]
Return only the JSON array without commentary.
"""

        payload = {
            "contents": [
                {
                    "parts": [
                        {"inlineData": {"mimeType": "audio/mp3", "data": b64_audio}},
                        {"text": prompt}
                    ]
                }
            ],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.1
            }
        }

        last_err = None
        async with httpx.AsyncClient(timeout=90.0) as client:
            for model in CANDIDATE_GEMINI_MODELS:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
                try:
                    res = await client.post(url, json=payload)
                    if res.status_code == 200:
                        raw = res.json()["candidates"][0]["content"]["parts"][0]["text"]
                        return robust_json_loads(raw)
                    else:
                        last_err = res.text
                except Exception as e:
                    last_err = str(e)

        raise RuntimeError(f"Gemini transcription failed: {last_err}")

    @staticmethod
    async def transcribe_audio_groq(
        audio_path: Path,
        api_key: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Groq Whisper STT fallback (if user supplies active Groq key)."""
        key = api_key or settings.GROQ_API_KEY
        if not key or not key.startswith("gsk_"):
            raise ValueError("Valid Groq API Key is required.")

        url = "https://api.groq.com/openai/v1/audio/transcriptions"
        headers = {"Authorization": f"Bearer {key}"}

        with open(audio_path, "rb") as f:
            files = {"file": (audio_path.name, f, "audio/mpeg")}
            data = {
                "model": "whisper-large-v3",
                "response_format": "verbose_json",
                "timestamp_granularities[]": ["word", "segment"]
            }
            async with httpx.AsyncClient(timeout=60.0) as client:
                res = await client.post(url, headers=headers, files=files, data=data)

        if res.status_code != 200:
            raise RuntimeError(f"Groq transcription failed: {res.text}")

        res_json = res.json()
        segments = []
        raw_words = res_json.get("words", [])
        if raw_words:
            burst_size = 4
            for i in range(0, len(raw_words), burst_size):
                chunk = raw_words[i:i + burst_size]
                chunk_start = float(chunk[0].get("start", 0.0))
                chunk_end = float(chunk[-1].get("end", 0.0))
                chunk_text = " ".join(w.get("word", "").strip() for w in chunk)
                seg_words = [
                    {"text": w.get("word", "").strip(), "start": float(w.get("start", chunk_start)), "end": float(w.get("end", chunk_end))}
                    for w in chunk
                ]
                segments.append({
                    "id": i // burst_size,
                    "start": chunk_start,
                    "end": chunk_end,
                    "text": chunk_text,
                    "words": seg_words
                })
        return segments

    @staticmethod
    async def transcribe_audio(
        audio_path: Path,
        gemini_key: Optional[str] = None,
        groq_key: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Unified transcription: attempts Gemini first, falls back to Groq only if valid key provided."""
        gemini_err = None
        if gemini_key or settings.GEMINI_API_KEY:
            try:
                return await LLMService.transcribe_audio_gemini(audio_path, api_key=gemini_key)
            except Exception as e:
                gemini_err = e
                logger.warning(f"Gemini STT failed: {e}")

        # Only attempt Groq if user explicitly configured an active Groq key
        if groq_key and groq_key.startswith("gsk_"):
            try:
                return await LLMService.transcribe_audio_groq(audio_path, api_key=groq_key)
            except Exception as ge:
                logger.warning(f"Groq STT failed: {ge}")

        if gemini_err:
            raise RuntimeError(f"{gemini_err}")

        raise ValueError("No valid Gemini API key configured. Please add your Gemini key in API settings.")

    @staticmethod
    async def translate_segments_gemini(
        segments: List[Dict[str, Any]],
        target_language: str = "Burmese",
        api_key: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Translates subtitles to spoken/colloquial phrasing using Gemini Flash.
        """
        key = api_key or settings.GEMINI_API_KEY
        if not key:
            raise ValueError("GEMINI_API_KEY is required for translation.")

        simplified_segments = [
            {"id": s["id"], "text": s["text"]}
            for s in segments
        ]

        if target_language.lower() in ["burmese", "myanmar"]:
            system_prompt = BURMESE_REEL_SYSTEM_PROMPT
        else:
            system_prompt = GENERIC_REEL_SYSTEM_PROMPT.format(target_language=target_language)

        user_content = (
            f"Translate these {len(simplified_segments)} subtitle segments:\n"
            f"{json.dumps(simplified_segments, ensure_ascii=False)}"
        )

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": system_prompt + "\n\n" + user_content}
                    ]
                }
            ],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.3
            }
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            for model in CANDIDATE_GEMINI_MODELS:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
                try:
                    res = await client.post(url, json=payload)
                    if res.status_code == 200:
                        raw = res.json()["candidates"][0]["content"]["parts"][0]["text"]
                        translations = robust_json_loads(raw)
                        break
                    else:
                        last_err = res.text
                except Exception as e:
                    last_err = str(e)
            else:
                raise RuntimeError(f"Translation failed: {last_err}")

        trans_map = {t["id"]: t["translated_text"] for t in translations if "id" in t and "translated_text" in t}

        enriched_segments = []
        for s in segments:
            sid = s["id"]
            trans_text = trans_map.get(sid, s["text"])
            if target_language.lower() in ["burmese", "myanmar"]:
                trans_text = normalize_myanmar_unicode(trans_text)
            enriched_segments.append({
                **s,
                "text": trans_text
            })

        return enriched_segments
