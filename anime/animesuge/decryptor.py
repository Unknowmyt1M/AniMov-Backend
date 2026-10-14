"""MegaPlay Stream Sources Decryptor for AnimeSuge.

Uses AES-256-CBC with null-padded seed keys and PKCS#7 unpadding.
"""

import base64
import json
import logging
from typing import Dict, Any, Optional
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

from .config import MEGAPLAY_KEY_SEED, MEGAPLAY_IV_SEED

logger = logging.getLogger("animesuge.decryptor")


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
    """Decrypt the 'enc' string returned by MegaPlay /stream/getSourcesNew endpoint."""
    if not enc_payload or not isinstance(enc_payload, str):
        return None

    try:
        key = _seed_to_bytes(key_seed, 32)
        iv = _seed_to_bytes(iv_seed, 16)

        padded = enc_payload + "=" * ((4 - len(enc_payload) % 4) % 4)
        raw_ciphertext = base64.urlsafe_b64decode(padded)

        cipher = AES.new(key, AES.MODE_CBC, iv)
        decrypted_raw = unpad(cipher.decrypt(raw_ciphertext), AES.block_size)
        decoded_text = decrypted_raw.decode("utf-8")

        return json.loads(decoded_text)
    except Exception as e:
        logger.error(f"MegaPlay decryption error: {e}")
        return None
