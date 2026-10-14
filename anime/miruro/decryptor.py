"""
Cryptographic decoders and deobfuscators for Miruro Anime.

1. Catalog & Playback Decoder:
   - Miruro returns octet-stream payloads for anime metadata, search, and playback.
   - Payload is XOR-obfuscated with key b'miruro/catalog' and Gzip-compressed.
   - Decryptor performs: XOR(data, key) -> Gzip decompress -> UTF-8 JSON.

2. Keeply Proxy Deobfuscator:
   - Stream segments on s1/s2.keeply.top contain encoded upstream master URLs.
   - Segment format: base64url(targetUrl ^ PROXY_OBF_KEY).
   - Decryptor reconstructs the original upstream master .m3u8 playlist URL.
"""
import gzip
import json
import base64
from typing import Dict, Any, Optional

from .config import CATALOG_XOR_KEY, PROXY_OBF_KEY


class MiruroDecryptor:
    @staticmethod
    def decode_catalog_payload(raw_content: bytes) -> Dict[str, Any]:
        """
        Decodes Miruro's XOR-obfuscated and gzip-compressed API responses.
        """
        if not raw_content:
            return {}

        # If already JSON (e.g. error responses like {"type":"about:blank"})
        if raw_content.startswith(b"{") or raw_content.startswith(b"["):
            try:
                return json.loads(raw_content.decode("utf-8"))
            except Exception:
                pass

        # Step 1: XOR with 'miruro/catalog'
        key = CATALOG_XOR_KEY
        key_len = len(key)
        xored = bytearray(raw_content)
        for i in range(len(xored)):
            xored[i] ^= key[i % key_len]

        # Step 2: Gzip decompress
        try:
            decompressed = gzip.decompress(xored)
            return json.loads(decompressed.decode("utf-8"))
        except Exception as e:
            # Fallback in case response was plain gzipped without XOR
            try:
                decompressed = gzip.decompress(raw_content)
                return json.loads(decompressed.decode("utf-8"))
            except Exception:
                raise ValueError(f"Failed to decompress Miruro payload: {e}")

    @staticmethod
    def deobfuscate_keeply_url(keeply_url: str) -> Optional[str]:
        """
        Decodes a keeply proxy URL to recover the original direct upstream .m3u8 stream.
        Example:
          Input: https://s2.keeply.top/zTlM7GtoUr.../pl.m3u8
          Output: https://fetch.nexabloom.top/anime/.../master.m3u8?token=...
        """
        if not keeply_url or "keeply.top" not in keeply_url:
            return None

        try:
            path_part = keeply_url.split("keeply.top/")[1]
            segment = path_part.split("/")[0].split("~")[0]

            pad = len(segment) % 4
            if pad:
                segment += "=" * (4 - pad)

            raw = base64.urlsafe_b64decode(segment)
            key = PROXY_OBF_KEY
            key_len = len(key)

            dec = bytes([b ^ key[i % key_len] for i, b in enumerate(raw)])
            decoded_url = dec.decode("utf-8", errors="replace")

            if decoded_url.startswith("http://") or decoded_url.startswith("https://"):
                return decoded_url
        except Exception:
            pass

        return None
