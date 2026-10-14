"""MegaPlay Stream Sources Decryptor.

Reverse-engineered from MegaPlay player scripts (e1-player.min.js & newclient.min.js).
Uses AES-256-CBC with null-padded seed keys and PKCS#7 unpadding.
"""

import base64
import json
import logging
from typing import Dict, Any, Optional
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

from .config import MEGAPLAY_KEY_SEED, MEGAPLAY_IV_SEED

logger = logging.getLogger("anikoto.decryptor")


def _seed_to_bytes(seed: str, length: int) -> bytes:
    """Pad or truncate string seed to exactly length bytes with nulls."""
    b = seed.encode("utf-8")
    if len(b) < length:
        return b + b"\x00" * (length - len(b))
    return b[:length]


def decrypt_megaplay_sources(
    enc_payload: str,
    key_seed: str = MEGAPLAY_KEY_SEED,
    iv_seed: str = MEGAPLAY_IV_SEED
) -> Optional[Dict[str, Any]]:
    """Decrypt the 'enc' string returned by MegaPlay /stream/getSourcesNew endpoint.

    Args:
        enc_payload: base64url-encoded AES-CBC ciphertext.
        key_seed: Key string seed (padded to 32 bytes for AES-256).
        iv_seed: IV string seed (padded to 16 bytes).

    Returns:
        Dict containing decoded JSON payload (e.g. {"file": "https://.../master.m3u8"}),
        or None if decryption fails.
    """
    if not enc_payload or not isinstance(enc_payload, str):
        return None

    try:
        key = _seed_to_bytes(key_seed, 32)
        iv = _seed_to_bytes(iv_seed, 16)

        # Base64url padding restoration
        padded = enc_payload + "=" * ((4 - len(enc_payload) % 4) % 4)
        raw_ciphertext = base64.urlsafe_b64decode(padded)

        cipher = AES.new(key, AES.MODE_CBC, iv)
        decrypted_raw = unpad(cipher.decrypt(raw_ciphertext), AES.block_size)
        decoded_text = decrypted_raw.decode("utf-8")

        return json.loads(decoded_text)
    except Exception as e:
        logger.error(f"MegaPlay decryption error: {e}")
        return None
