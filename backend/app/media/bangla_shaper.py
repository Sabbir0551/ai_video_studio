import re
from typing import List, Optional
from backend.app.models.timeline import CaptionItem, WordTimestamp


# Bengali digits to standard numerals mapping
BN_DIGITS = {"০": "0", "১": "1", "২": "2", "৩": "3", "৪": "4", "৫": "5", "৬": "6", "৭": "7", "৮": "8", "৯": "9"}
EN_TO_BN_DIGITS = {v: k for k, v in BN_DIGITS.items()}

# Spoken Bengali numbers 0-99
BN_ONES_AND_TEENS = {
    0: "শূন্য", 1: "এক", 2: "দুই", 3: "তিন", 4: "চার", 5: "পাঁচ", 6: "ছয়", 7: "সাত", 8: "আট", 9: "নয়",
    10: "দশ", 11: "এগারো", 12: "বারো", 13: "তেরো", 14: "চৌদ্দ", 15: "পনেরো", 16: "ষোলো", 17: "সতেরো", 18: "আঠারো", 19: "উনিশ",
    20: "বিশ", 21: "একুশ", 22: "বাইশ", 23: "তেইশ", 24: "চব্বিশ", 25: "পঁচিশ", 26: "ছাব্বিশ", 27: "সাতাশ", 28: "আটাশ", 29: "উনত্রিশ",
    30: "ত্রিশ", 31: "একত্রিশ", 32: "বত্রিশ", 33: "তেত্রিশ", 34: "চৌত্রিশ", 35: "পঁয়ত্রিশ", 36: "ছত্রিশ", 37: "সাঁইত্রিশ", 38: "আটত্রিশ", 39: "উনচল্লিশ",
    40: "চল্লিশ", 41: "একচল্লিশ", 42: "বিয়াল্লিশ", 43: "তেতাল্লিশ", 44: "চুয়াল্লিশ", 45: "পঁয়তাল্লিশ", 46: "ছেচল্লিশ", 47: "সাতচল্লিশ", 48: "আটচল্লিশ", 49: "উনপঞ্চাশ",
    50: "পঞ্চাশ", 51: "একান্ন", 52: "বায়ান্ন", 53: "তিপ্পান্ন", 54: "চুয়ান্ন", 55: "পঞ্চান্ন", 56: "ছাপ্পান্ন", 57: "সাতান্ন", 58: "আটান্ন", 59: "উনষাট",
    60: "ষাট", 61: "একষট্টি", 62: "বাষট্টি", 63: "তেষট্টি", 64: "চৌষট্টি", 65: "পঁয়ষট্টি", 66: "ছেষট্টি", 67: "সাতষট্টি", 68: "আটষট্টি", 69: "উনসত্তর",
    70: "সত্তর", 71: "একাত্তর", 72: "বাহাত্তর", 73: "তিয়াত্তর", 74: "চুয়াত্তর", 75: "পঁচাত্তর", 76: "ছিয়াত্তর", 77: "সাতাত্তর", 78: "আটাত্তর", 79: "উনাশি",
    80: "আশি", 81: "একাশি", 82: "বিরাশি", 83: "তিরাশি", 84: "চুরাশি", 85: "পঁচাশি", 86: "ছিয়াশি", 87: "সাতাশি", 88: "আটাশি", 89: "ঊননব্বই",
    90: "নব্বই", 91: "একানব্বই", 92: "বিরানব্বই", 93: "তিরানব্বই", 94: "চুরানব্বই", 95: "পঁচানব্বই", 96: "ছিয়ানব্বই", 97: "সাতানব্বই", 98: "আটানব্বই", 99: "নিরানব্বই"
}


def bangla_int_to_words(num: int) -> str:
    """Convert an integer (0 to 99,99,99,999) to natural spoken Bengali words."""
    if num < 0:
        return "মাইনাস " + bangla_int_to_words(abs(num))
    if num in BN_ONES_AND_TEENS:
        return BN_ONES_AND_TEENS[num]

    parts = []
    crore = num // 10000000
    if crore > 0:
        parts.append(bangla_int_to_words(crore) + " কোটি")
        num %= 10000000

    lakh = num // 100000
    if lakh > 0:
        parts.append(bangla_int_to_words(lakh) + " লাখ")
        num %= 100000

    thousand = num // 1000
    if thousand > 0:
        parts.append(bangla_int_to_words(thousand) + " হাজার")
        num %= 1000

    hundred = num // 100
    if hundred > 0:
        parts.append(bangla_int_to_words(hundred) + " শত")
        num %= 100

    if num > 0:
        parts.append(BN_ONES_AND_TEENS[num])

    return " ".join(parts)


def normalize_bangla_digits_to_en(text: str) -> str:
    """Convert Bengali numerical characters (০-৯) to Arabic numerals (0-9)."""
    return "".join(BN_DIGITS.get(c, c) for c in text)


def normalize_bangla_text_for_speech(text: str) -> str:
    """Normalize raw text with symbols, abbreviations, and numbers into natural spoken Bengali."""
    # Common abbreviations
    abbreviations = [
        (r"(?:(?<=\s)|^|\b)ডা\.(?=\s|$|\b)", "ডাক্তার "),
        (r"(?:(?<=\s)|^|\b)মো\.(?=\s|$|\b)", "মোহাম্মদ "),
        (r"(?:(?<=\s)|^|\b)ইত্যাদি(?=\s|$|\b)", "ইত্যাদি"),
        (r"(?:(?<=\s)|^|\b)BDT(?=\s|$|\b)", "টাকা"),
        (r"\%", " শতাংশ"),
        (r"\$", " ডলার"),
    ]
    for pattern, repl in abbreviations:
        text = re.sub(pattern, repl, text)

    # Convert Bengali digits inside text to standard digits for parsing
    # Look for groups of digits (e.g. ২০২৬ or 2026)
    def replace_num(match):
        raw = match.group(0)
        norm_digits = normalize_bangla_digits_to_en(raw)
        try:
            val = int(norm_digits)
            if 1900 <= val <= 2099:
                # Year format: e.g. 2026 -> দুই হাজার ছাব্বিশ
                return bangla_int_to_words(val)
            return bangla_int_to_words(val)
        except ValueError:
            return raw

    # Match both Bengali digits and Latin digits
    text = re.sub(r"[০-৯0-9]+", replace_num, text)
    return re.sub(r"\s+", " ", text).strip()


def format_ass_time(seconds: float) -> str:
    """Convert float seconds to ASS timestamp format H:MM:SS.cs"""
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    centis = int(round((seconds - int(seconds)) * 100))
    if centis >= 100:
        centis = 99
    return f"{hrs}:{mins:02d}:{secs:02d}.{centis:02d}"


def generate_ass_subtitle_file(
    captions: List[CaptionItem],
    output_path: str,
    font_name: str = "Noto Sans Bengali",
    font_size: int = 54,
    play_res_x: int = 1920,
    play_res_y: int = 1080,
    margin_v: int = 50,
    highlight_active_word: bool = True
) -> str:
    """Generate an Advanced SubStation Alpha (ASS) file with full HarfBuzz styling for Bengali text."""
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {play_res_x}
PlayResY: {play_res_y}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font_name},{font_size},&H00FFFFFF,&H0000FFFF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,3.5,1.5,2,40,40,{margin_v},1
Style: Highlight,{font_name},{font_size},&H0000E5FF,&H000000FF,&H00000000,&H80000000,1,0,0,0,100,100,0,0,1,4.0,2.0,2,40,40,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    dialogues = []
    for cap in captions:
        start_ts = format_ass_time(cap.start)
        end_ts = format_ass_time(cap.end)

        if highlight_active_word and cap.words and len(cap.words) > 0:
            # Generate karaoke or sequential word highlights
            # Create sub-events for each word window to render dynamic highlight
            for active_idx, target_word in enumerate(cap.words):
                w_start = format_ass_time(target_word.start)
                w_end = format_ass_time(target_word.end)
                
                # Compose line with active word wrapped in bright color tag
                line_parts = []
                for idx, w in enumerate(cap.words):
                    if idx == active_idx:
                        line_parts.append(r"{\c&H0000E5FF\b1}" + w.word + r"{\c&H00FFFFFF\b0}")
                    else:
                        line_parts.append(w.word)
                composed_text = " ".join(line_parts)
                dialogues.append(f"Dialogue: 0,{w_start},{w_end},Default,,0,0,0,,{composed_text}")
        else:
            # Clean static line
            clean_text = cap.text.replace("\n", r"\N")
            dialogues.append(f"Dialogue: 0,{start_ts},{end_ts},Default,,0,0,0,,{clean_text}")

    full_content = header + "\n".join(dialogues) + "\n"
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(full_content)
    return output_path
