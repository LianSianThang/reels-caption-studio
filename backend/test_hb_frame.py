import uharfbuzz as hb
import freetype
from PIL import Image, ImageDraw, ImageFilter
import numpy as np
from pathlib import Path

def render_burmese_pill_badge(
    text: str,
    font_path: str = "backend/fonts/mmrtext.ttf",
    font_size: int = 42,
    text_color: tuple = (255, 255, 255, 255),
    highlight_word: str = None,
    highlight_color: tuple = (255, 221, 0, 255),
    video_width: int = 720,
    video_height: int = 1280,
    bottom_margin: int = 180
) -> Image.Image:
    # 1. Setup FreeType and HarfBuzz
    ft_face = freetype.Face(font_path)
    ft_face.set_char_size(font_size * 64)
    
    blob = hb.Blob.from_file_path(font_path)
    hb_face = hb.Face(blob)
    hb_font = hb.Font(hb_face)
    hb_font.scale = (font_size * 64, font_size * 64)

    # 2. Shape with HarfBuzz (explicit Myanmar Unicode script)
    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    buf.script = "Mymr"
    buf.language = "my"
    buf.direction = "ltr"
    hb.shape(hb_font, buf)

    infos = buf.glyph_infos
    positions = buf.glyph_positions

    # Compute bounding box
    total_advance_x = sum(pos.x_advance for pos in positions) / 64.0
    text_w = int(total_advance_x + font_size)
    text_h = int(font_size * 2.2)

    # Render text onto a transparent strip
    text_strip = Image.new("RGBA", (text_w, text_h), (0, 0, 0, 0))
    baseline_y = int(font_size * 1.5)
    current_x = int(font_size * 0.4)

    for info, pos in zip(infos, positions):
        glyph_index = info.codepoint
        ft_face.load_glyph(glyph_index, freetype.FT_LOAD_RENDER | freetype.FT_LOAD_TARGET_NORMAL)
        glyph = ft_face.glyph
        bitmap = glyph.bitmap

        x_pos = int(current_x + (pos.x_offset / 64.0) + glyph.bitmap_left)
        y_pos = int(baseline_y - (pos.y_offset / 64.0) - glyph.bitmap_top)

        if bitmap.width > 0 and bitmap.rows > 0:
            arr = np.array(bitmap.buffer, dtype=np.uint8).reshape((bitmap.rows, bitmap.width))
            glyph_mask = Image.fromarray(arr, mode="L")
            
            # Draw solid color glyph
            glyph_color = Image.new("RGBA", (bitmap.width, bitmap.rows), text_color)
            text_strip.paste(glyph_color, (x_pos, y_pos), glyph_mask)

        current_x += (pos.x_advance / 64.0)

    # Create full-frame canvas for video overlay
    full_frame = Image.new("RGBA", (video_width, video_height), (0, 0, 0, 0))
    
    # Calculate Center-Bottom position (Safe Zone)
    pos_x = (video_width - text_w) // 2
    pos_y = video_height - bottom_margin - text_h

    # Add dark rounded pill box background for contrast
    padding_x = 24
    padding_y = 12
    box_rect = [
        pos_x - padding_x,
        pos_y + int(font_size * 0.4) - padding_y,
        pos_x + text_w + padding_x,
        pos_y + text_h - int(font_size * 0.2) + padding_y
    ]
    
    draw = ImageDraw.Draw(full_frame)
    # Dark semi-transparent pill box
    draw.rounded_rectangle(box_rect, radius=20, fill=(0, 0, 0, 180), outline=(255, 255, 255, 40), width=1)
    
    # Paste shaped text
    full_frame.paste(text_strip, (pos_x, pos_y), text_strip)
    return full_frame

if __name__ == "__main__":
    txt = "ဟေ့ကောင်၊ ငါတို့နာမည်တွေ ပျက်ကုန်ပြီလေ"
    overlay = render_burmese_pill_badge(txt, font_path="backend/fonts/mmrtext.ttf")
    out_path = Path("backend/outputs/harfbuzz_test_frame.png")
    overlay.save(out_path)
    print(f"Saved HarfBuzz frame to {out_path}")
