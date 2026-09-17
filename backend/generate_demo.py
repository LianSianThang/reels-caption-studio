import subprocess
from pathlib import Path

backend_dir = Path(__file__).resolve().parent
uploads_dir = backend_dir / "uploads"
uploads_dir.mkdir(parents=True, exist_ok=True)

wav_path = uploads_dir / "demo_narration.wav"
mp4_path = uploads_dir / "demo_reel.mp4"
mp3_path = uploads_dir / "demo_reel.mp3"

# Generate speech audio using PowerShell System.Speech via subprocess
ps_cmd = (
    f"Add-Type -AssemblyName System.Speech; "
    f"$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
    f"$s.SetOutputToWaveFile('{str(wav_path).replace(chr(92), '/')}'); "
    f"$s.Speak('I went to Yangon yesterday and something really strange happened.'); "
    f"$s.Dispose();"
)

print("Synthesizing narration audio...")
subprocess.run(["powershell", "-Command", ps_cmd], check=True)

print("Combining into 9:16 vertical MP4 video...")
# Generate 9:16 vertical (1080x1920) video with testsrc/gradient and narration audio
cmd_mp4 = [
    "ffmpeg", "-y",
    "-f", "lavfi",
    "-i", "color=c=#111827:s=1080x1920:r=30",
    "-i", str(wav_path),
    "-c:v", "libx264",
    "-preset", "ultrafast",
    "-pix_fmt", "yuv420p",
    "-c:a", "aac",
    "-shortest",
    str(mp4_path)
]
subprocess.run(cmd_mp4, check=True)

# Generate 16kHz mono mp3 for Groq/Gemini STT
cmd_mp3 = [
    "ffmpeg", "-y",
    "-i", str(wav_path),
    "-vn",
    "-acodec", "libmp3lame",
    "-ar", "16000",
    "-ac", "1",
    "-b:a", "64k",
    str(mp3_path)
]
subprocess.run(cmd_mp3, check=True)
print(f"Demo MP4 created at {mp4_path}")
print(f"Demo MP3 created at {mp3_path}")
