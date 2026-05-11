import re
from pathlib import Path
from typing import Optional


def rtf_to_text(raw: str) -> str:
    """
    Minimal RTF -> plain-text converter for PIAS output files.
    Keeps tabs and newlines; strips RTF control words.
    """
    s = raw.replace("\r\n", "\n").replace("\r", "\n")
    s = s.replace(r"\tab", "\t")
    s = s.replace(r"\cell", " ")
    s = s.replace(r"\row", "\n")
    s = s.replace(r"\par", "\n")
    s = re.sub(r"\\'[0-9a-fA-F]{2}", "", s)
    s = re.sub(r"\\[a-zA-Z]+\d* ?", "", s)
    s = s.replace("{", "").replace("}", "")
    return s


def detect_side(text: str) -> Optional[str]:
    """Extract side (e.g., 'PS', 'SB') from 'Damage at X' pattern."""
    m = re.search(r"Damage at\s+([A-Z]+)", text)
    return m.group(1) if m else None


def parse_float(text: Optional[str]) -> Optional[float]:
    """Convert string to float, handling None and special values."""
    if text is None:
        return None
    t = str(text).strip()
    if not t or t.upper() in ("INF", "-INF", "NAN", "-"):
        return None
    try:
        return float(t)
    except ValueError:
        return None


def parse_int(text: Optional[str]) -> Optional[int]:
    """Convert string to int."""
    if text is None:
        return None
    try:
        return int(str(text).strip())
    except ValueError:
        return None


def slice_trim_block(text: str, block_title: str) -> str:
    """Extract one of the three Trim/GM blocks from the RTF text."""
    start = text.find(block_title)
    if start == -1:
        return ""

    titles = [
        "Light service draft",
        "Partial subdivision draft",
        "Deepest subdivision draft",
        "Details of choices and options",
        "Subdivision length",
    ]
    candidates = []
    for t in titles:
        if t == block_title:
            continue
        idx = text.find(t, start + 1)
        if idx != -1:
            candidates.append(idx)
    end = min(candidates) if candidates else len(text)
    return text[start:end]


def find_float(pattern: str, text: str) -> Optional[float]:
    """Find first float matching regex pattern in text."""
    m = re.search(pattern, text)
    return parse_float(m.group(1)) if m else None
