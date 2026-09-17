import subprocess
from pathlib import Path

video_path = Path("backend/outputs/9336406d_burned.mp4").resolve()
# We use the original video from uploads if available
src_matches = list(Path("backend/uploads").glob("9336406d.*"))
video_src = [m for m in src_matches if m.suffix.lower() in [".mp4", ".mov", ".mkv", ".webm"]][0]

fonts_dir = Path("backend/fonts").resolve()
escaped_fonts = str(fonts_dir).replace("\\", "/").replace(":", "\\:")

for font_name, out_name in [
    ("Noto Sans Myanmar", "test_noto.png"),
    ("Padauk", "test_padauk.png"),
    ("Pyidaungsu", "test_pyidaungsu.png"),
    ("Myanmar Text", "test_mmr.png")
]:
    ass_path = Path(f"backend/outputs/test_{out_name}.ass").resolve()
    ass_content = f"""[Script Info]
Title: Test
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font_name},70,&H00FFFFFF&,&H0000DDFF&,&H00000000&,&H60000000&,-1,0,0,0,100,100,0,0,1,4,2,2,60,60,340,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,0:00:10.00,Default,,0,0,0,,ဟေ့ကောင်၊ ငါတို့နာမည်တွေ ပျက်ကုန်ပြီလေ
"""
    ass_path.write_text(ass_content, encoding="utf-8")
    escaped_ass = str(ass_path).replace("\\", "/").replace(":", "\\:")
    
    out_img = Path(f"backend/outputs/{out_name}").resolve()
    vf = f"subtitles='{escaped_ass}':fontsdir='{escaped_fonts}'"
    
    cmd = [
        "ffmpeg", "-y",
        "-ss", "00:00:02.000",
        "-i", str(video_src),
        "-vf", vf,
        "-frames:v", "1",
        str(out_img)
    ]
    subprocess.run(cmd, check=True)
    print(f"Generated {out_img.name}")
