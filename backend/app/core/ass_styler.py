from typing import List, Dict, Any, Optional
from pathlib import Path

def format_ass_time(seconds: float) -> str:
    """Format seconds into ASS timestamp format: H:MM:SS.cc"""
    if seconds < 0:
        seconds = 0.0
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    cs = int(round((seconds - int(seconds)) * 100))
    if cs >= 100:
        cs = 99
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

def hex_to_ass_color(hex_str: str, alpha: str = "00") -> str:
    """
    Convert #RRGGBB to ASS &HAABBGGRR format (Notice BGR order in ASS).
    Example: #FFDD00 (Yellow) -> &H0000DDFF
    """
    hex_clean = hex_str.lstrip("#")
    if len(hex_clean) == 6:
        r = hex_clean[0:2]
        g = hex_clean[2:4]
        b = hex_clean[4:6]
        return f"&H{alpha}{b}{g}{r}&"
    return f"&H{alpha}FFFFFF&"

class ASSGenerator:
    """Generates styled ASS subtitle files for 9:16 Reels / 1:1 / 16:9 videos."""
    
    ASPECT_RESOLUTIONS = {
        "9:16": (1080, 1920),
        "1:1": (1080, 1080),
        "16:9": (1920, 1080)
    }
    
    DEFAULT_MARGIN_V = {
        "9:16": 340,   # Safe zone above TikTok/Reels bottom metadata
        "1:1": 120,
        "16:9": 90
    }

    @classmethod
    def generate(
        cls,
        segments: List[Dict[str, Any]],
        output_path: Path,
        aspect_ratio: str = "9:16",
        font_name: str = "Myanmar Text",
        font_size: int = 70,
        primary_color_hex: str = "#FFFFFF",
        highlight_color_hex: str = "#FFDD00",
        outline_color_hex: str = "#000000",
        bg_color_hex: str = "#000000",
        style_preset: str = "karaoke",  # "karaoke", "neon_box", "minimal"
        position: str = "bottom",       # "bottom", "center", "top"
    ) -> Path:
        """
        Builds and writes a complete .ass file with styled subtitle events.
        """
        play_x, play_y = cls.ASPECT_RESOLUTIONS.get(aspect_ratio, (1080, 1920))
        
        # Alignment and Vertical Margin
        if position == "center":
            alignment = 5  # Middle center
            margin_v = 0
        elif position == "top":
            alignment = 8  # Top center
            margin_v = 220
        else:  # bottom (default)
            alignment = 2  # Bottom center
            margin_v = cls.DEFAULT_MARGIN_V.get(aspect_ratio, 340)

        # Color conversions
        primary_ass = hex_to_ass_color(primary_color_hex, "00")
        highlight_ass = hex_to_ass_color(highlight_color_hex, "00")
        outline_ass = hex_to_ass_color(outline_color_hex, "00")
        back_ass = hex_to_ass_color(bg_color_hex, "60")  # Semi-transparent

        # Border Style: 1 = Outline + Shadow, 3 = Opaque Box / Pill
        border_style = 3 if style_preset == "neon_box" else 1
        outline_width = 4 if border_style == 1 else 2
        shadow_dist = 2 if border_style == 1 else 0

        # Build ASS Content
        lines = [
            "[Script Info]",
            "Title: Reel AI Studio Captions",
            "ScriptType: v4.00+",
            "WrapStyle: 0",
            "ScaledBorderAndShadow: yes",
            f"PlayResX: {play_x}",
            f"PlayResY: {play_y}",
            "",
            "[V4+ Styles]",
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
            f"Style: Default,{font_name},{font_size},{primary_ass},{highlight_ass},{outline_ass},{back_ass},-1,0,0,0,100,100,0,0,{border_style},{outline_width},{shadow_dist},{alignment},60,60,{margin_v},1",
            "",
            "[Events]",
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"
        ]

        # Generate Dialogue Events
        for seg in segments:
            start_sec = float(seg.get("start", 0.0))
            end_sec = float(seg.get("end", 0.0))
            text = seg.get("text", "").strip()
            words = seg.get("words", [])

            if not text or end_sec <= start_sec:
                continue

            # If segment has word timestamps and preset is karaoke, produce active word highlight
            if style_preset == "karaoke" and len(words) > 1:
                # Word-level highlight slices
                for i, w in enumerate(words):
                    w_start = float(w.get("start", start_sec))
                    w_end = float(w.get("end", end_sec))
                    if w_end <= w_start:
                        continue

                    # Construct text with active word colored in highlight_ass
                    formatted_tokens = []
                    for j, other_w in enumerate(words):
                        w_text = other_w.get("text", "").strip()
                        if not w_text:
                            continue
                        if j == i:
                            # Active highlighted word
                            formatted_tokens.append(f"{{\\c{highlight_ass}\\b1}}{w_text}{{\\c{primary_ass}\\b0}}")
                        else:
                            formatted_tokens.append(w_text)

                    combined_text = " ".join(formatted_tokens)
                    start_str = format_ass_time(w_start)
                    end_str = format_ass_time(w_end)
                    lines.append(f"Dialogue: 0,{start_str},{end_str},Default,,0,0,0,,{combined_text}")
            else:
                # Standard segment display
                start_str = format_ass_time(start_sec)
                end_str = format_ass_time(end_sec)
                lines.append(f"Dialogue: 0,{start_str},{end_str},Default,,0,0,0,,{text}")

        output_path.write_text("\n".join(lines), encoding="utf-8")
        return output_path
