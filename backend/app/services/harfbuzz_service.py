import subprocess
import logging
from pathlib import Path
from typing import List, Dict, Any
from PIL import Image, ImageDraw, ImageFilter
import numpy as np
import uharfbuzz as hb
import freetype

from backend.app.core.config import settings
from backend.app.core.burmese_shaping import normalize_myanmar_unicode

logger = logging.getLogger(__name__)

MY_CONJUNCTIONS = [
    "နှင့်", "နှင့်အတူ", "သို့မဟုတ်", "ဒါပေမဲ့", "သို့သော်", "သို့သော်လည်း", 
    "ကြောင့်", "သောကြောင့်", "သဖြင့်", "ထို့ကြောင့်", "ဒါကြောင့်", "ဆိုလျှင်", 
    "လျှင်", "ရင်", "သောအခါ", "သည့်အခါ", "ပြီးနောက်", "ပြီးတော့", "ပြီးရင်", "ပြီး",
    "တယ်", "သည်", "မယ်", "မည်", "ပါ", "ပါသည်", "ပါတယ်", "ပါဘူး", "ဘူး",
    "။", "၊", " "
]

def hex_to_rgb(hex_str: str) -> tuple:
    hex_str = hex_str.lstrip("#")
    if len(hex_str) == 6:
        return (int(hex_str[0:2], 16), int(hex_str[2:4], 16), int(hex_str[4:6], 16), 255)
    return (255, 255, 255, 255)

class HarfBuzzRenderer:
    """
    Pixel-perfect OpenType text shaper with auto-wrapping for Myanmar Unicode.
    Renders identical to the web preview (bold text + deep black stroke outline, zero cut off).
    """

    @staticmethod
    def wrap_text_by_pixels(text: str, hb_font: hb.Font, max_pixel_width: int) -> List[str]:
        """Wraps text into balanced lines strictly within max_pixel_width using HarfBuzz."""
        if not text:
            return []

        def measure_w(txt: str) -> int:
            b = hb.Buffer()
            b.add_str(txt)
            b.guess_segment_properties()
            b.script = "Mymr"
            b.language = "my"
            b.direction = "ltr"
            hb.shape(hb_font, b)
            return int(sum(pos.x_advance for pos in b.glyph_positions) / 64.0)

        total_w = measure_w(text)
        if total_w <= max_pixel_width:
            return [text]

        # Break text at conjunctions or whitespace
        tokens = []
        curr = ""
        i = 0
        while i < len(text):
            matched = False
            for c in sorted(MY_CONJUNCTIONS, key=len, reverse=True):
                if text[i:].startswith(c):
                    if curr:
                        tokens.append(curr)
                        curr = ""
                    tokens.append(c)
                    i += len(c)
                    matched = True
                    break
            if not matched:
                curr += text[i]
                i += 1
        if curr:
            tokens.append(curr)

        lines = []
        current_line = ""
        for tok in tokens:
            test_line = current_line + tok
            test_w = measure_w(test_line)
            if test_w <= max_pixel_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line.strip())
                    current_line = tok.lstrip()
                else:
                    lines.append(tok.strip())
                    current_line = ""

        if current_line.strip():
            lines.append(current_line.strip())

        return lines if lines else [text]

    @staticmethod
    def render_stroke_line(
        line: str,
        hb_font: hb.Font,
        ft_face: freetype.Face,
        font_size: int,
        text_color: tuple = (255, 255, 255, 255),
        outline_color: tuple = (0, 0, 0, 255),
        stroke_width: int = 4
    ) -> tuple[Image.Image, int, int]:
        """Renders a shaped line with a bold black stroke outline matching the web player."""
        buf = hb.Buffer()
        buf.add_str(line)
        buf.guess_segment_properties()
        buf.script = "Mymr"
        buf.language = "my"
        buf.direction = "ltr"
        hb.shape(hb_font, buf)

        infos = buf.glyph_infos
        positions = buf.glyph_positions

        line_w = int(sum(pos.x_advance for pos in positions) / 64.0)
        extra_pad = stroke_width * 3
        line_h = int(font_size * 1.6) + extra_pad * 2

        full_w = line_w + font_size + extra_pad * 2
        text_mask = Image.new("L", (full_w, line_h), 0)
        baseline_y = int(font_size * 1.15) + extra_pad
        cur_x = extra_pad + int(font_size * 0.1)

        for info, pos in zip(infos, positions):
            glyph_idx = info.codepoint
            ft_face.load_glyph(glyph_idx, freetype.FT_LOAD_RENDER | freetype.FT_LOAD_TARGET_NORMAL)
            glyph = ft_face.glyph
            bitmap = glyph.bitmap

            x_pos = int(cur_x + (pos.x_offset / 64.0) + glyph.bitmap_left)
            y_pos = int(baseline_y - (pos.y_offset / 64.0) - glyph.bitmap_top)

            if bitmap.width > 0 and bitmap.rows > 0:
                arr = np.array(bitmap.buffer, dtype=np.uint8).reshape((bitmap.rows, bitmap.width))
                glyph_img = Image.fromarray(arr, mode="L")
                text_mask.paste(glyph_img, (x_pos, y_pos), glyph_img)

            cur_x += (pos.x_advance / 64.0)

        # 1. Create Outline by dilating the mask
        outline_mask = text_mask.filter(ImageFilter.MaxFilter(stroke_width * 2 + 1))

        # 2. Combine into final RGBA image: Black Outline + White Fill
        final_line = Image.new("RGBA", (full_w, line_h), (0, 0, 0, 0))
        outline_img = Image.new("RGBA", (full_w, line_h), outline_color)
        final_line.paste(outline_img, (0, 0), outline_mask)

        text_img = Image.new("RGBA", (full_w, line_h), text_color)
        final_line.paste(text_img, (0, 0), text_mask)

        return final_line, int(cur_x - extra_pad), line_h

    @classmethod
    def burn_video(
        cls,
        video_path: Path,
        segments: List[Dict[str, Any]],
        output_video_path: Path,
        video_width: int,
        video_height: int,
        duration: float,
        font_name: str = "Padauk",
        font_size: int = 58,
        primary_color_hex: str = "#FFFFFF",
        highlight_color_hex: str = "#FFDD00",
        style_preset: str = "karaoke",
        position: str = "bottom",
        fonts_dir: Path = settings.FONTS_DIR
    ) -> Path:
        # Pick font file (Padauk-Bold gives cleanest Burmese typography with stroke)
        font_candidates = [
            fonts_dir / "Padauk-Bold.ttf",
            fonts_dir / "NotoSansMyanmar-Bold.ttf",
            fonts_dir / "mmrtext.ttf",
            Path("C:/Windows/Fonts/mmrtext.ttf")
        ]
        chosen_font = None
        for fc in font_candidates:
            if fc.exists():
                chosen_font = fc
                break
        if not chosen_font:
            chosen_font = Path("C:/Windows/Fonts/mmrtext.ttf")

        # Proportional font size for mobile reels
        scale_ratio = video_width / 1080.0
        # Comfortable font size: ~36px on 720p, ~52px on 1080p
        effective_font_size = max(26, min(56, int(font_size * scale_ratio * 0.85)))
        stroke_width = max(3, int(4 * scale_ratio))

        # Setup HarfBuzz & FreeType
        ft_face = freetype.Face(str(chosen_font))
        ft_face.set_char_size(effective_font_size * 64)

        blob = hb.Blob.from_file_path(str(chosen_font))
        hb_face = hb.Face(blob)
        hb_font = hb.Font(hb_face)
        hb_font.scale = (effective_font_size * 64, effective_font_size * 64)

        text_color = hex_to_rgb(primary_color_hex)
        max_allowed_w = int(video_width * 0.86)  # 86% max width matching web player

        temp_dir = settings.OUTPUT_DIR / "temp_slices"
        temp_dir.mkdir(parents=True, exist_ok=True)

        blank_img = Image.new("RGBA", (video_width, video_height), (0, 0, 0, 0))
        blank_path = temp_dir / "blank.png"
        blank_img.save(blank_path)

        # Build timeline slices
        time_points = {0.0, round(duration, 3)}
        for s in segments:
            st = float(s.get("start", 0.0))
            et = float(s.get("end", 0.0))
            if et > st:
                time_points.add(round(st, 3))
                time_points.add(round(et, 3))

        sorted_pts = sorted(list(time_points))
        timeline_slices = []
        for i in range(len(sorted_pts) - 1):
            t_start = sorted_pts[i]
            t_end = sorted_pts[i + 1]
            dur = round(t_end - t_start, 3)
            if dur <= 0.01:
                continue
            t_mid = (t_start + t_end) / 2.0

            active_seg = None
            for s in segments:
                if float(s["start"]) <= t_mid <= float(s["end"]):
                    active_seg = s
                    break

            timeline_slices.append({
                "start": t_start,
                "end": t_end,
                "duration": dur,
                "active_seg": active_seg
            })

        concat_lines = []
        for idx, sl in enumerate(timeline_slices):
            seg = sl["active_seg"]
            dur = sl["duration"]

            if not seg:
                concat_lines.append(f"file '{blank_path.resolve().as_posix()}'\n")
                concat_lines.append(f"duration {dur:.3f}\n")
                continue

            raw_text = seg.get("text", "").strip()
            raw_text = normalize_myanmar_unicode(raw_text)
            if not raw_text:
                concat_lines.append(f"file '{blank_path.resolve().as_posix()}'\n")
                concat_lines.append(f"duration {dur:.3f}\n")
                continue

            # Auto-wrap text within max_allowed_w
            wrapped_lines = cls.wrap_text_by_pixels(raw_text, hb_font, max_allowed_w)

            rendered_lines = []
            max_line_w = 0
            for w_line in wrapped_lines:
                l_img, l_w, l_h = cls.render_stroke_line(
                    w_line, hb_font, ft_face, effective_font_size, text_color, stroke_width=stroke_width
                )
                rendered_lines.append((l_img, l_w, l_h))
                max_line_w = max(max_line_w, l_w)

            # Assemble lines onto full video frame
            frame_canvas = Image.new("RGBA", (video_width, video_height), (0, 0, 0, 0))
            line_gap = int(2 * scale_ratio)
            total_text_h = sum(h for _, _, h in rendered_lines) + (len(rendered_lines) - 1) * line_gap

            # Position on Video Canvas matching Web Player
            if position == "top":
                start_y = int(video_height * 0.15)
            elif position == "center":
                start_y = (video_height - total_text_h) // 2
            else:  # bottom (Reels safe zone)
                # Bottom ~18% like the web player
                start_y = int(video_height * 0.73)

            # If neon_box preset is chosen, draw the dark pill behind lines
            if style_preset == "neon_box":
                pad_x = int(22 * scale_ratio)
                pad_y = int(14 * scale_ratio)
                badge_w = min(max_allowed_w + pad_x * 2, max_line_w + pad_x * 2)
                badge_rect = [
                    (video_width - badge_w) // 2,
                    start_y - pad_y,
                    (video_width + badge_w) // 2,
                    start_y + total_text_h + pad_y
                ]
                draw = ImageDraw.Draw(frame_canvas)
                draw.rounded_rectangle(badge_rect, radius=int(18 * scale_ratio), fill=(0, 0, 0, 190), outline=(255, 255, 255, 40), width=1)

            # Paste each line centered horizontally
            cur_y = start_y
            for l_img, l_w, l_h in rendered_lines:
                pos_x = (video_width - l_img.width) // 2
                frame_canvas.paste(l_img, (pos_x, cur_y), l_img)
                cur_y += l_h - int(12 * scale_ratio)  # snug baseline line height

            slice_file = temp_dir / f"sl_{idx:04d}.png"
            frame_canvas.save(slice_file)
            concat_lines.append(f"file '{slice_file.resolve().as_posix()}'\n")
            concat_lines.append(f"duration {dur:.3f}\n")

        concat_lines.append(f"file '{blank_path.resolve().as_posix()}'\n")
        concat_file = temp_dir / "concat_burn.txt"
        with open(concat_file, "w", encoding="utf-8") as f:
            f.writelines(concat_lines)

        # Run FFmpeg overlay
        cmd = [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_file),
            "-filter_complex", "[0:v][1:v]overlay=0:0:eof_action=pass[vfinal]",
            "-map", "[vfinal]",
            "-map", "0:a?",
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "22",
            "-c:a", "copy",
            "-threads", str(settings.FFMPEG_THREADS),
            str(output_video_path)
        ]
        logger.info(f"Executing HarfBuzz overlay burn: {' '.join(cmd)}")
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            raise RuntimeError(f"HarfBuzz video overlay failed: {res.stderr}")

        return output_video_path
