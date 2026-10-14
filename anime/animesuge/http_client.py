"""Resilient HTTP Client for AnimeSuge."""

import logging
from typing import Dict, Any, Optional
from curl_cffi import requests, CurlOpt

from .config import (
    ANIMESUGE_RESOLVE_IPS,
    MEGAPLAY_RESOLVE_IPS,
    DEFAULT_HEADERS,
    REQUEST_TIMEOUT,
)

logger = logging.getLogger("animesuge.http_client")


class AnimeSugeHttpClient:
    """HTTP Client with Chrome TLS fingerprinting and DoH IP resolution."""

    def __init__(self, timeout: int = REQUEST_TIMEOUT):
        self.timeout = timeout
        self.session = self._init_session()

    def _init_session(self) -> requests.Session:
        resolve_list = []
        for host in ("animesuge.cz", "www.animesuge.cz"):
            for ip in ANIMESUGE_RESOLVE_IPS:
                resolve_list.extend([f"{host}:443:{ip}", f"{host}:80:{ip}"])

        for host in ("megaplay.buzz", "www.megaplay.buzz"):
            for ip in MEGAPLAY_RESOLVE_IPS:
                resolve_list.extend([f"{host}:443:{ip}", f"{host}:80:{ip}"])

        return requests.Session(
            impersonate="chrome124",
            curl_options={CurlOpt.RESOLVE: resolve_list},
        )

    def get(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
    ) -> requests.Response:
        """Execute GET request with resolve rules and TLS impersonation."""
        req_headers = dict(DEFAULT_HEADERS)
        if headers:
            req_headers.update(headers)

        last_error = None
        for attempt in range(2):
            try:
                response = self.session.get(
                    url,
                    params=params,
                    headers=req_headers,
                    timeout=timeout or self.timeout,
                )
                return response
            except Exception as e:
                last_error = e
                logger.warning(f"GET {url} failed attempt {attempt + 1}: {e}")

        if last_error:
            raise last_error
        raise RuntimeError(f"Failed to fetch {url}")

    def close(self):
        """Close underlying curl session."""
        try:
            self.session.close()
        except Exception:
            pass
