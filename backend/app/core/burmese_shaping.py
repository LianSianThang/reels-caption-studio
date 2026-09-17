import re
from typing import List

# Myanmar Unicode Range: U+1000 - U+109F, U+AA60 - U+AA7F
MYANMAR_REGEX = re.compile(r"[\u1000-\u109F\uAA60-\uAA7F]")

# Myanmar Syllable Break Regex (Unicode compliant)
MY_SYLLABLE_PATTERN = re.compile(
    r"(?<![်္])"  # Not preceded by Asat or Virama
    r"("
    r"[\u1000-\u102A\u104E]"          # Consonant or Independent Vowel
    r"[\u103B-\u103E]*"              # Medials (ya, ra, wa, ha)
    r"[\u102B-\u1035\u1037\u1038]*"  # Dependent Vowels and tones
    r"(?:[\u1039][\u1000-\u1021])*"  # Stacked consonants (virama + consonant)
    r"(?:[\u103A][\u1000-\u1021\u1037\u1038]*)*"  # Asat + killer sequences
    r"|"
    r"[a-zA-Z0-9]+"                  # English words / digits
    r"|"
    r"[။၊,!?…\s]+"                   # Punctuations / spaces
    r")"
)

# Colloquial conjunctions & particles for natural phrase splitting
CLAUSE_BREAKERS = [
    "ဒါပေမဲ့", "သို့သော်", "ကြောင့်", "ဒါကြောင့်", "ဆိုရင်", "ပြီးတော့", 
    "ပြီးရင်", "သောအခါ", "တုန်းက", "တယ်", "တယ်ဗျ", "တယ်ရှင်", "မယ်", 
    "မှာပါ", "ပါဘူး", "ဘူး", "နော်", "လေ", "ပေါ့", "ဗျာ", "ရှင့်"
]

def normalize_myanmar_unicode(text: str) -> str:
    """Sanitize and standardize Myanmar Unicode text to prevent tofu (missing glyphs)."""
    if not text:
        return ""
    
    t = text.strip()
    # Normalize quotes and dashes
    t = t.replace('“', '"').replace('”', '"').replace('‘', "'").replace('’', "'")
    t = t.replace('—', '-').replace('–', '-').replace('…', '...')
    
    # Normalize common Unicode typing errors
    t = t.replace("\u1037\u103A", "\u103A\u1037")  # asat + dot below order
    t = t.replace("\u1031\u103B", "\u103B\u1031")  # medial + vowel 'e' order
    t = t.replace("စိန်းအောင်း", "ကိန်းအောင်း")
    
    # Strip dangerous control chars
    t = re.sub(r"[\u200B-\u200D\uFEFF]", "", t)
    return t

def segment_myanmar_syllables(text: str) -> List[str]:
    """Segment Myanmar Unicode text into syllables and token chunks."""
    normalized = normalize_myanmar_unicode(text)
    raw_tokens = MY_SYLLABLE_PATTERN.findall(normalized)
    tokens = [tok.strip() for tok in raw_tokens if tok.strip()]
    return tokens

def chunk_text_for_reels(text: str, max_tokens: int = 4) -> List[str]:
    """
    Split a sentence into short, punchy 2-4 token bursts optimized for 9:16 Reels.
    If English, splits by words.
    If Burmese, groups syllables into natural phrasing.
    """
    if not text:
        return []
        
    text = normalize_myanmar_unicode(text)
    
    # Check if Burmese
    if MYANMAR_REGEX.search(text):
        syllables = segment_myanmar_syllables(text)
        if not syllables:
            return [text]
            
        chunks = []
        current = []
        
        for syl in syllables:
            current.append(syl)
            # Break if reached token limit or hit punctuation/clause breaker
            if len(current) >= max_tokens or any(syl.endswith(cb) for cb in CLAUSE_BREAKERS):
                chunks.append("".join(current))
                current = []
                
        if current:
            chunks.append("".join(current))
            
        return chunks
    else:
        # Standard space-separated languages (English, etc.)
        words = text.split()
        chunks = []
        for i in range(0, len(words), max_tokens):
            chunks.append(" ".join(words[i:i + max_tokens]))
        return chunks
