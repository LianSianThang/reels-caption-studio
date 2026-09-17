import uharfbuzz as hb
import freetype
from PIL import Image, ImageFilter
import numpy as np
from pathlib import Path

MY_CONJUNCTIONS = [
    "နှင့်", "နှင့်အတူ", "သို့မဟုတ်", "ဒါပေမဲ့", "သို့သော်", "သို့သော်လည်း", 
    "ကြောင့်", "သောကြောင့်", "သဖြင့်", "ထို့ကြောင့်", "ဒါကြောင့်", "ဆိုလျှင်", 
    "လျှင်", "ရင်", "သောအခါ", "သည့်အခါ", "ပြီးနောက်", "ပြီးတော့", "ပြီးရင်", "ပြီး",
    "တယ်", "သည်", "မယ်", "မည်", "ပါ", "ပါသည်", "ပါတယ်", "ပါဘူး", "ဘူး",
    "။", "၊", " "
]

def wrap_text_by_pixels(text: str, hb_font: hb.Font, max_pixel_width: int):
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

def render_stroke_line(
    line: str,
    hb_font: hb.Font,
    ft_face: freetype.Face,
    font_size: int,
    text_color: tuple = (255, 255, 255, 255),
    outline_color: tuple = (0, 0, 0, 255),
    stroke_width: int = 4
) -> tuple[Image.Image, int, int]:
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

    # Canvas for the line with padding
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
    
    # Black outline layer
    outline_img = Image.new("RGBA", (full_w, line_h), outline_color)
    final_line.paste(outline_img, (0, 0), outline_mask)
    
    # Text layer
    text_img = Image.new("RGBA", (full_w, line_h), text_color)
    final_line.paste(text_img, (0, 0), text_mask)

    return final_line, int(cur_x - extra_pad), line_h

def render_web_matched_frame(
    text: str,
    video_width: int = 720,
    video_height: int = 1280,
    font_path: str = "backend/fonts/Padauk-Bold.ttf"
) -> Image.Image:
    # 720p vertical -> font size ~38px
    font_size = 36
    ft_face = freetype.Face(font_path)
    ft_face.set_char_size(font_size * 64)

    blob = hb.Blob.from_file_path(font_path)
    hb_face = hb.Face(blob)
    hb_font = hb.Font(hb_face)
    hb_font.scale = (font_size * 64, font_size * 64)

    max_w = int(video_width * 0.86)
    lines = wrap_text_by_pixels(text, hb_font, max_w)

    line_imgs = []
    total_h = 0
    gap = 4
    for l in lines:
        l_img, l_w, l_h = render_stroke_line(l, hb_font, ft_face, font_size, stroke_width=4)
        line_imgs.append((l_img, l_w, l_h))
        total_h += l_h

    total_h += (len(line_imgs) - 1) * gap

    frame = Image.new("RGBA", (video_width, video_height), (0, 0, 0, 0))
    # Position: bottom ~18% like the web player
    start_y = int(video_height * 0.72)

    cur_y = start_y
    for l_img, l_w, l_h in line_imgs:
        pos_x = (video_width - l_img.width) // 2
        frame.paste(l_img, (pos_x, cur_y), l_img)
        cur_y += l_h - 14  # tight line spacing

    return frame

if __name__ == "__main__":
    txt = "အေးပါကွာ၊ ဒါပေမဲ့ တချို့လူတွေက ငါတို့ကို အရင်လိုမြင်တော့မှာ မဟုတ်ဘူး။ ဒီအပေါ် ဘယ်လိုလုပ်ကြမလဲ"
    img = render_web_matched_frame(txt)
    img.save("backend/outputs/web_matched_test.png")
    print("Saved web_matched_test.png")
