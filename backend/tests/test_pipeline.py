import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.app.core.burmese_shaping import segment_myanmar_syllables, chunk_text_for_reels
from backend.app.core.ass_styler import ASSGenerator

def test_burmese():
    txt = "မနေ့က ရန်ကုန်ကို ကျွန်တော်သွားခဲ့တယ်"
    tokens = segment_myanmar_syllables(txt)
    chunks = chunk_text_for_reels(txt, max_tokens=3)
    assert len(tokens) > 0
    assert len(chunks) > 0
    print(f"PASS: Syllable count = {len(tokens)}, Chunks count = {len(chunks)}")

    segs = [{
        "id": 0,
        "start": 0.5,
        "end": 2.5,
        "text": txt,
        "words": [{"text": c, "start": 0.5 + i*0.5, "end": 0.5 + (i+1)*0.5} for i, c in enumerate(chunks)]
    }]
    out_ass = Path(__file__).resolve().parent.parent / "outputs" / "test.ass"
    ASSGenerator.generate(segs, out_ass, aspect_ratio="9:16", style_preset="karaoke")
    assert out_ass.exists()
    content = out_ass.read_text(encoding="utf-8")
    assert "PlayResX: 1080" in content
    assert "PlayResY: 1920" in content
    assert "Dialogue:" in content
    print(f"PASS: ASS generated successfully with {len(content.splitlines())} lines.")

if __name__ == "__main__":
    test_burmese()
