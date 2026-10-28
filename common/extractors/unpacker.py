"""
Dean Edwards JavaScript Packer Deobfuscator.
Fast, pure-Python unpacker for `eval(function(p,a,c,k,e,d)...)` blocks.
Compatible with Zephyrix, Vtbe, FileMoon, StreamWish, VidHide, etc.
"""

import re
from typing import List, Optional, Dict


ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"


def _base_encode(num: int, radix: int) -> str:
    """Encode an integer into the given radix (up to 62)."""
    if num == 0:
        return "0"
    digits = []
    while num > 0:
        digits.append(ALPHABET[num % radix])
        num //= radix
    return "".join(reversed(digits))


def unpack(p: str, a: int, c: int, k: List[str]) -> str:
    """
    Unpack a Dean Edwards packed JavaScript payload.
    :param p: Packed payload template string
    :param a: Radix (base)
    :param c: Total count of replacement tokens
    :param k: Dictionary of replacement words
    :return: Unpacked cleartext JavaScript
    """
    lookup: Dict[str, str] = {}
    for i in range(c):
        token = _base_encode(i, a)
        lookup[token] = k[i] if i < len(k) and k[i] else token

    # Replace word tokens
    pattern = re.compile(r"\b[0-9a-zA-Z]+\b")
    return pattern.sub(lambda m: lookup.get(m.group(0), m.group(0)), p)


def unpack_js(script_text: str) -> Optional[str]:
    """
    Find and unpack the first Dean Edwards packed block in JavaScript/HTML text.
    """
    # Regex handles single and double quoted packed blocks
    match = re.search(
        r"}\s*\(\s*['\"](.*?)['\"]\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*['\"](.*?)['\"]\s*\.split\s*\(\s*['\"]\|['\"]\s*\)",
        script_text,
        re.DOTALL,
    )
    if not match:
        return None

    p, a, c, k = match.groups()
    return unpack(p, int(a), int(c), k.split("|"))


def unpack_all(text: str) -> List[str]:
    """
    Find and unpack all Dean Edwards packed blocks in the provided text.
    """
    results: List[str] = []
    pattern = re.compile(
        r"}\s*\(\s*['\"](.*?)['\"]\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*['\"](.*?)['\"]\s*\.split\s*\(\s*['\"]\|['\"]\s*\)",
        re.DOTALL,
    )
    for match in pattern.finditer(text):
        p, a, c, k = match.groups()
        try:
            unpacked = unpack(p, int(a), int(c), k.split("|"))
            if unpacked:
                results.append(unpacked)
        except Exception:
            continue
    return results


def is_packed(text: str) -> bool:
    """Check if the text contains a Dean Edwards packed JS block."""
    return "eval(function(p,a,c,k,e,d)" in text or "eval(function(p,a,c,k,e,r)" in text
