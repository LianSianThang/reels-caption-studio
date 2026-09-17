import sys
from pathlib import Path
sys.path.insert(0, "d:/Project 101/movie-translator")
from backend.services.translation_service import call_gemini_api

print("Calling Gemini API...")
try:
    res = call_gemini_api(
        "Translate: I went to Yangon yesterday and something strange happened.",
        "You are an elite short-form video translator. Translate into natural conversational Burmese. Return JSON array with 'translated_text'."
    )
    print("Gemini Response:\n", res)
except Exception as e:
    print("Gemini Error:", e)
