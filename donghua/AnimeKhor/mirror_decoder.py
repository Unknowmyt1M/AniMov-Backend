"""
Base64 mirror decoder and stream server resolver for AnimeKhor.
"""
import base64
import html
import re
from typing import List
from bs4 import BeautifulSoup
from .models import StreamServer, DownloadOption


class MirrorDecoder:
    PROVIDER_PATTERNS = [
        (r'dailymotion\.com|geo\.dailymotion', 'dailymotion'),
        (r'rumble\.com', 'rumble'),
        (r'ok\.ru', 'ok.ru'),
        (r'd\.tube', 'dtube'),
        (r'turbovidhls', 'turbovid'),
        (r'upns\.live', 'cloudplayer'),
        (r'p2pstream', 'fileplayer'),
        (r'vidara\.to', 'vidara'),
        (r'bysekoze', 'vgplayer'),
        (r'abyssplayer', 'abyssplayer'),
        (r'streamplay', 'streamplay'),
        (r'vidhide|yurn\.org', 'vidhide'),
        (r'mp4upload', 'mp4upload'),
        (r'filelions', 'filelions'),
        (r'streamwish', 'streamwish'),
        (r'gofile\.io', 'gofile'),
        (r'mega\.nz', 'mega')
    ]

    @classmethod
    def identify_provider(cls, url: str, server_name: str = "") -> str:
        combined = f"{url} {server_name}".lower()
        for pattern, name in cls.PROVIDER_PATTERNS:
            if re.search(pattern, combined):
                return name
        return "generic"

    @classmethod
    def extract_quality(cls, text: str) -> str:
        m = re.search(r'\b(4k|2160p|1080p|720p|480p|360p)\b', text, re.I)
        return m.group(1).upper() if m else "Auto"

    @classmethod
    def extract_languages(cls, text: str) -> List[str]:
        languages = []
        low = text.lower()
        if "eng" in low or "english" in low:
            languages.append("English")
        if "indo" in low or "indonesian" in low:
            languages.append("Indonesian")
        if "multi" in low or "all sub" in low:
            languages.append("Multi-Sub")
        if "chinese" in low or "raw" in low:
            languages.append("Chinese (Raw)")
        if not languages:
            languages.append("Subtitled")
        return list(dict.fromkeys(languages))

    @classmethod
    def decode_mirror_value(cls, b64_value: str) -> str:
        """
        Decodes base64 option value to extract iframe src or player URL.
        """
        clean_val = b64_value.strip()
        if not clean_val:
            return ""

        try:
            padding = len(clean_val) % 4
            if padding:
                clean_val += "=" * (4 - padding)

            decoded_bytes = base64.b64decode(clean_val)
            decoded_text = decoded_bytes.decode("utf-8", errors="ignore")
            decoded_text = html.unescape(decoded_text)

            # Extract iframe src
            iframe_match = re.search(r'src=["\']([^"\']+)["\']', decoded_text, re.IGNORECASE)
            if iframe_match:
                src = iframe_match.group(1).strip()
                if src.startswith("//"):
                    src = "https:" + src
                return src

            # Standalone URL match
            url_match = re.search(r'https?://[^\s"\'<>]+', decoded_text)
            if url_match:
                return url_match.group(0).strip()

            return decoded_text.strip()
        except Exception:
            return ""

    @classmethod
    def extract_servers(cls, soup: BeautifulSoup) -> List[StreamServer]:
        servers: List[StreamServer] = []
        options = soup.select("select.mirror option")

        for opt in options:
            server_name = opt.get_text(strip=True)
            if not server_name or "select video" in server_name.lower() or "server" == server_name.lower():
                continue

            val = opt.get("value", "").strip()
            embed_url = cls.decode_mirror_value(val)
            if not embed_url:
                continue

            provider = cls.identify_provider(embed_url, server_name)
            quality = cls.extract_quality(server_name)
            languages = cls.extract_languages(server_name)

            servers.append(
                StreamServer(
                    server_name=server_name,
                    provider=provider,
                    embed_url=embed_url,
                    quality=quality,
                    languages=languages
                )
            )

        if not servers:
            for ifr in soup.select("#pembed iframe, .player-embed iframe, .entry-content iframe"):
                src = ifr.get("src", "").strip()
                if src:
                    if src.startswith("//"):
                        src = "https:" + src
                    servers.append(
                        StreamServer(
                            server_name="Default Player",
                            provider=cls.identify_provider(src),
                            embed_url=src,
                            quality="Auto",
                            languages=["Subtitled"]
                        )
                    )

        return servers

    @classmethod
    def extract_downloads(cls, soup: BeautifulSoup) -> List[DownloadOption]:
        downloads: List[DownloadOption] = []
        dl_elements = soup.select(".soradl a, .soraurlx a, .boto a, .misterdonghua a, a[href*='download'], .dlx a")

        for el in dl_elements:
            href = el.get("href", "").strip()
            text = el.get_text(strip=True)
            if not href or href.startswith("#") or "javascript" in href.lower():
                continue

            host = None
            for p, name in cls.PROVIDER_PATTERNS:
                if re.search(p, href):
                    host = name
                    break
            if not host:
                host = "Direct/Portal"

            downloads.append(
                DownloadOption(
                    title=text or "Download",
                    host=host,
                    url=href,
                    quality=cls.extract_quality(text)
                )
            )

        return downloads
