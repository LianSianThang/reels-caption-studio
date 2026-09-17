import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.app.services.ffmpeg_service import FFmpegService
from backend.app.services.harfbuzz_service import HarfBuzzRenderer

video_id = "9336406d"
src_video = Path(f"backend/uploads/{video_id}.mp4")
out_video = Path(f"backend/outputs/{video_id}_burned.mp4")
ass_path = Path(f"backend/outputs/{video_id}.ass")

# Parse segments from the ASS file that was saved earlier
content = ass_path.read_text(encoding="utf-8")
segments = []
for line in content.splitlines():
    if line.startswith("Dialogue:"):
        parts = line.split(",,")
        if len(parts) >= 2:
            txt = parts[-1].strip()
            # Extract start and end time
            header_parts = parts[0].split(",")
            # Dialogue: 0,0:00:00.00,0:00:00.80,Default,,...
            st_str = header_parts[1]
            et_str = header_parts[2]
            
            def parse_time(ts):
                h, m, s = ts.split(":")
                return int(h)*3600 + int(m)*60 + float(s)

            segments.append({
                "id": len(segments),
                "start": parse_time(st_str),
                "end": parse_time(et_str),
                "text": txt
            })

print(f"Loaded {len(segments)} segments from {ass_path.name}")
meta = FFmpegService.probe_video(src_video)
print(f"Video metadata: {meta}")

print("Rendering with HarfBuzzRenderer...")
HarfBuzzRenderer.burn_video(
    video_path=src_video,
    segments=segments,
    output_video_path=out_video,
    video_width=meta["width"],
    video_height=meta["height"],
    duration=meta["duration"],
    font_size=58,
    position="bottom"
)
print("Burn completed successfully!")
