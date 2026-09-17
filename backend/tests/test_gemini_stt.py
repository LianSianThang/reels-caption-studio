import os
import base64
import json
import httpx
from pathlib import Path

key = os.getenv("GEMINI_API_KEY", "")
audio_path = Path(__file__).resolve().parent.parent / "uploads" / "demo_reel.mp3"

audio_bytes = audio_path.read_bytes()
b64_audio = base64.b64encode(audio_bytes).decode("utf-8")

prompt = """Listen carefully to this audio recording. 
Transcribe the speech with timestamps and word-level timings.
Return valid JSON matching this schema:
[
  {
    "id": 0,
    "start": 0.0,
    "end": 4.2,
    "text": "full transcribed sentence",
    "words": [
      {"text": "word", "start": 0.0, "end": 0.5}
    ]
  }
]
Only return JSON.
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

print(f"Sending {audio_path.name} to Gemini Flash for STT...")
url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash:generateContent?key={key}"
res = httpx.post(url, json=payload, timeout=60.0)
print("STT Status:", res.status_code)
if res.status_code == 200:
    out_file = Path(__file__).resolve().parent / "gemini_stt.json"
    content = res.json()["candidates"][0]["content"]["parts"][0]["text"]
    out_file.write_text(content, encoding="utf-8")
    print(f"SUCCESS! Wrote audio STT to {out_file.name}")
else:
    print("Failed:", res.text)
