"""JSON export + validation."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .config import Config
from .episode_parser import range_str
from .storage import Storage


def export_json(cfg: Config, store: Storage) -> tuple[str, dict]:
    out_dir = Path(cfg.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    items = []
    for a in store.all_anime():
        eps = []
        for e in store.episodes_for_anime(a["id"]):
            embeds = [{"provider": r["provider"], "url": r["url"],
                       "origin": r["origin"], "server_label": r["server_label"] or ""}
                      for r in store.embeds_for_episode(e["id"])]
            eps.append({
                "episode_number": e["episode_number"], "part": e["part"],
                "episode_type": e["episode_type"], "episode_title": e["episode_title"],
                "raw_label": e["raw_label"],
                "range": (f"{e['range_start']}-{e['range_end']}"
                          if e["range_start"] is not None and e["range_end"] is not None else None),
                "episode_page_url": e["url"], "release_date": e["release_date"] or "",
                "state": e["state"], "embeds": embeds,
            })
        eps.sort(key=lambda x: (x["episode_number"] is None, x["episode_number"] or 0))
        try:
            genres = json.loads(a["genres"] or "[]")
        except Exception:
            genres = []
        try:
            quality = json.loads(a["quality"] or "[]")
        except Exception:
            quality = []
        try:
            audio = json.loads(a["audio"] or "[]")
        except Exception:
            audio = []
        items.append({
            "title": a["title"], "poster_url": a["poster_url"] or "",
            "synopsis": a["synopsis"] or "", "genres": genres,
            "rating": a["rating"] or "", "quality": quality, "audio": audio,
            "detail_page_url": a["url"], "status": a["status"] or "",
            "type": a["anime_type"] or "",
            "site_stated_episode_count": a["site_episode_count"],
            "total_episode_count": len(eps), "state": a["state"],
            "episodes": eps,
        })
    stats = store.stats()
    payload = {"source": cfg.source,
               "scraped_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
               "stats": stats, "items": items}
    errors = validate_payload(payload)
    payload["validation_errors"] = errors
    path = out_dir / "animexin.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path), {"errors": errors, "stats": stats}


def validate_payload(payload: dict) -> list[str]:
    errors: list[str] = []
    seen_anime: set[str] = set()
    for item in payload.get("items", []):
        u = item.get("detail_page_url", "")
        if not u.startswith("http"):
            errors.append(f"bad anime url: {u!r}")
        if u in seen_anime:
            errors.append(f"duplicate anime url: {u}")
        seen_anime.add(u)
        seen_ep: set[str] = set()
        for ep in item.get("episodes", []):
            eu = ep.get("episode_page_url", "")
            if not eu.startswith("http"):
                errors.append(f"bad episode url: {eu!r}")
            if eu in seen_ep:
                errors.append(f"duplicate episode url: {eu}")
            seen_ep.add(eu)
            for em in ep.get("embeds", []):
                if not em.get("url", "").startswith("http"):
                    errors.append(f"bad embed url: {em.get('url')!r}")
                if not em.get("provider"):
                    errors.append(f"missing provider for {em.get('url')}")
    return errors
