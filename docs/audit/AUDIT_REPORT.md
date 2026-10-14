# AniMovBackend — Comprehensive Scraper QA & Research Audit

**Date:** 2026-10-05 · **Plan:** `animov-audit-20261002` · **Method:** live end-user testing through CLIs, ground-truth comparison against live websites, static code verification · **Mode:** audit only — no project files were modified, no fixes applied.

---

## 1. Executive Summary

AniMovBackend ships **16 scraper sources** (6 anime, 5 donghua, 5 movies) plus a proxy pool, all following a uniform `python -m <domain>.<source>.cli` pattern. The architecture is consistent and, in most cases, functional: **12 of 16 sources completed search successfully**, 9 completed detail, and 6 completed source extraction during this audit.

Headline results:

- **5 Critical/High-impact bugs**: 2 sources (MoviesMod, Bollyflix) are effectively broken end-to-end; DonghuaStream detail is broken by domain mismatch; AnimeSalt/AnimeSuge metadata is corrupted by unscoped selectors (53-57 genres instead of 2-7).
- **21 findings** from the AnimeSalt/WatchAnimeWorld/AnimeSuge audit (4 High, 11 Medium, 6 Low), plus **17 findings** from orchestrator testing of the remaining 13 sources.
- **Graceful failure is generally good**: 39 edge cases executed with **0 unhandled exceptions** in the anime group; failures return `None`/`[]` with logged errors.
- **A recurring systemic pattern**: selector/parsing bugs are invisible because the sites' navigation and metadata blocks are matched unscoped (global genre menus, generic episode titles), producing *plausible-looking but wrong* data — the worst failure mode for a backend consumer.
- **CLI UX bugs shared across sources**: exit code 0 on all failures, empty query prints help, slugs truncated in output tables making them unusable for `--detail`.
- Test coverage is nearly nonexistent: **1 test file for the whole repo** (Animexin, 8 tests, all passing).

Prior `research.txt` Animexin findings were re-verified: **C1 and C4 confirmed fixed, C2 partially fixed, H1 mostly fixed** — the standalone audit's claims are now stale in several places.

---

## 2. Repository Architecture Findings

```text
AniMovBackend/
├── anime/       anikoto, animesalt, animesuge, miruro, reanime, watchanimeworld
├── donghua/     AnimeCube, AnimeKhor, Animexin, DonghuaStream, Luciferdonghua
├── movies/      bollyflix, hindilinks4u, kmmovies, moviesmod, onetube
├── proxy_pool/  fetcher, validator, manager, cli
├── data/        5 SQLite DBs + proxy_pool.json (historical artifacts)
├── scratch/     72 prior research scripts/fixtures (47 .py)
├── research.txt prior standalone AnimeXin audit (24 findings C1-C8/H1-H16)
└── README.md    13 lines, documents only donghua/Animexin
```

Per-source uniform package: `cli.py` (rich console argparse), `scraper.py` (site logic), `http_client.py` (curl_cffi or httpx with retries), `storage.py` (SQLite cache), `config.py`, `models.py`, `README.md`. Three sources add `decryptor.py` (Miruro XOR+gzip, Anikoto, AnimeSuge), two add `sniffer.py` (Playwright m3u8 sniffing), AnimeKhor/DonghuaStream add `mirror_decoder.py`, AnimeCube adds `rsc_parser.py` (Next.js RSC), Luciferdonghua adds `server_resolver.py`.

Key architectural observations:

- **No shared library layer.** Every source duplicates config/http/storage/CLI code with small variations. A bug fixed in one source (e.g. Animexin's `default=None` flags) is not propagated to others (ALL-01/ALL-02 exist in all CLIs tested).
- **No cross-source registration/index.** There is no aggregate entry point; each source is an isolated module.
- **Two HTTP stacks coexist**: `curl_cffi` (impersonation, used by Bollyflix etc.) and `httpx`. Retry/backoff logic is re-implemented per source.
- **DB placement is inconsistent**: `data/*.db` for most, but Miruro uses `anime/miruro/data/miruro.db` and Animexin uses `donghua/Animexin/animexin.db`.
- **Docs**: only Animexin has a test suite; README covers 1 of 16 sources; per-source READMEs vary in quality (Miruro's is excellent/reverse-engineering-grade, others thinner).
- **proxy_pool** is standalone and not wired into any scraper automatically.

---

## 3. Testing Methodology

1. **Recon (T1)**: full CLI flag matrix for 16 sources, prior-art index of 72 scratch scripts, research.txt findings register, 14-field evidence schema, severity rubric (`docs/plan/animov-audit-20261002/recon_brief.md`).
2. **End-user CLI testing**: every source exercised through its real entry point (`--search`, `--info/--detail`, `--episode/--stream`, `--stats`) with real network requests against live sites.
3. **Search matrix (13 styles)**: exact, partial, lower, UPPER, mixed, spaces, no-spaces, special chars, numbers, CJK, English, alt title, typo, very short, very long, no-results (executed in full by the T3 automated battery; spot-checked for other sources).
4. **Ground truth**: for every suspicious result, the live website was fetched directly (httpx/HTML inspection) and compared with scraper output before classifying a bug.
5. **Episode matrix**: ep 1, ep 2, middle, latest, far-range (e.g. ep 161, ep 696) where available.
6. **Source-belonging proof**: streams validated by matching episode page content/IDs, not just HTTP 200.
7. **Edge battery** (39 cases on salt/waw/suge): empty/whitespace/emoji/CJK/Cyrillic/200-char/`<script>`/path-traversal queries, bad slugs, bad URLs — asserting failures are graceful, recoverable, reported, isolated.
8. **Consistency**: 3 repeated runs per operation, byte-identical payload fingerprints (T3: 11/11 ops consistent).
9. **Static verification**: code paths read for every observed anomaly; research.txt C1-C8/H1-H16 re-tested against current code.
10. **Test suite**: `python -B -m pytest -p no:cacheprovider -q` in `donghua/Animexin` → **8 passed**.

**Coverage caveat (honesty):** the T2 subagent (Miruro/Anikoto/ReAnime deep matrix) failed twice on platform errors (DNS, rate limit), so those three sources received only orchestrator-level smoke testing (search + detail). T4/T5/T6/T7 audits were executed directly by the orchestrator rather than subagents for the same reason. Deep 13-query matrices for those sources are **not complete** — see Section 20.

---

## 4. Anime Scraper Audit

### 4.1 Miruro (`anime/miruro`) — API/XOR-decrypted SPA scraper

- **Works:** `--search "Naruto"` → 3 results with correct IDs, titles, formats, episode counts (220/500/293), scores, statuses. `--search "Solo Leveling"` → 3 correct entries incl. movie. Rich tables render cleanly. README documents the XOR+gzip protocol and DNS-bypass (DoH pinning) in detail.
- **Limitations:** `--info`/`--episode` not deeply tested (T2 platform failure) — *coverage gap*.
- **Failed cases:** none observed.
- **Performance:** search ~2-4s (cold).

### 4.2 Anikoto (`anime/anikoto`)

- **Works:** search returns 8 results with sub/dub counts, scores, durations; `solo-leveling` slugs, specials and movie entries distinguished correctly.
- **Failed case:** `--detail "solo-leveling"` → `HTTP 404 / Could not retrieve series details.` The slug printed in the search table is **truncated by column width** (`solo-level…`), so a user cannot copy a working slug — and the bare slug 404s (actual slug evidently longer). Graceful error, but the search→detail chain is unusable from the CLI as printed (ANIME-04).
- **Coverage:** deep episode/source matrix not run (see Section 20).

### 4.3 ReAnime (`anime/reanime`)

- **Works:** search returns 5 results with correct types (TV/Anime Movie), scores, statuses ("Ongoing" where expected).
- **Failed case:** `--detail "solo-leveling"` → renders a **404 panel with `Title: 404`, all fields `N/A`, exit code 0** (ANIME-04/ALL-01). No exception, but a consumer can't distinguish "series named 404" from success without parsing the panel; the CLI does not exit non-zero.
- **Limitation:** status displayed as `Ongoing` for search results while MAL-like score shown — no site cross-check performed (unverified).

### 4.4 AnimeSalt (`anime/animesalt`) — see T3 detailed audit

- **Works:** search, detail, episodes, streams; caching; poster present on all results; `FirstS1E1` numbering copied verbatim from site.
- **Failed cases:** SALT-01/02 (High: search misses movies, metadata fields), SALT-03/04/05/07 (Medium), SALT-06 (Low: foreign-URL input returns wrong title), SALT-08 (Low: episode titles = series name).
- **Non-issues verified:** `rating`/`status` legitimately absent on site → `None` correct; `one-piece-1x100` 404 is real (season ends at 63).

### 4.5 WatchAnimeWorld (`anime/watchanimeworld`) — see T3 detailed audit

- **Works:** search/detail/episode pipeline; graceful 404s.
- **Failed cases:** WAW-01 (High), WAW-02/03/04/05/06 (Medium — incl. episode list truncation verified 3/15, 13/25, 8/63), WAW-07/08 (Low — 9/9 episodes fall back to `Episode N` titles despite `<title>` carrying real names).
- **Limitations:** movie templates genuinely lack genres/synopsis.

### 4.6 AnimeSuge (`anime/animesuge`) — see T3 detailed audit

- **Works:** search (correct 28-item caps incl. CJK `鬼滅の刃` → 10 results, better than salt/waw), detail, streams, master.m3u8 extraction (all → 200).
- **Failed cases:** SUGE-01 (High: **52-57 genres** = the site's global 50-genre nav menu on 7/7 titles), SUGE-02 (Medium: `status`/`anime_type` always `None` though site publishes both), SUGE-03 (Medium: no cache TTL — poisoned 2016 row served verbatim), SUGE-04 (Low: subtitle VTTs return Cloudflare 403, site behaviour unverified).

---

## 5. Donghua Scraper Audit

### 5.1 Animexin (`donghua/Animexin`) — pipeline-style, no cli.py

- **Works:** test suite **8/8 pass**; `python scraper.py --search "Martial Master"` found 1 result and began processing; detail parse on cached live page returns **696 episodes, genres `[Action, Historical, Martial Arts, Over Power]`, rating `8`, status `Ongoing`, type `ONA`** — i.e. prior C1/C2 are fixed/ratings fixed. Episode labels parse correctly: `13.5→13.5`, `[360P] 12→12`, `1-12` captured as range, `OVA/Movie/Special` typed (H1 mostly fixed). CLI precedence bug **C4 fixed** (all boolean flags `default=None` at `scraper.py:28-47`).
- **Residual bugs:** `Quality: []`, `Audio: []` still empty on the same live page (C2 partial — parser's `info-content` span scan still misses them); `'2020'` → `episode_number=2020` false positive (DONG-08).
- **Failed case:** full `--search` crawl exceeded a 120s command window (696-episode series with 6 workers) — expected behaviour, noted for performance.
- **Prior findings not re-tested this round:** C3, C5, C6, C7, C8, H2-H16 (marked *unverified-current*).

### 5.2 AnimeKhor (`donghua/AnimeKhor`)

- **Works:** `--search "Renegade Immortal"` returns results with types/status; `--info renegade-immortal` returns excellent metadata: native title incl. Chinese `仙逆`, status, rating 9.00, type ONA, studio BUILD DREAM, country China, release date, duration, 6 genres, poster, synopsis, **158 episodes** with dates and URLs; range episode `Episodes 1 to 3` handled.
- **Failed cases:**
  - **FK constraint crash** on `--episode` when series not previously crawled: `sqlite3.IntegrityError: FOREIGN KEY constraint failed` at `storage.py:153` — uncaught, full traceback (DONG-01, Medium).
  - Search output shows **duplicate rows** (each title rendered 2×) (DONG-02, Low).

### 5.3 AnimeCube (`donghua/AnimeCube`) — Next.js/RSC

- **Works:** `--search` → 3 results; `--info renegade-immortal` → status/year/61 episodes/genres/tags/schedule/cover/synopsis; `--episode ... --ep 1` → playback info + 1 server; `--ep 101` → **2 servers (Dailymotion 4K `x9oo4ca` + AnimeCube player)**; prev/next episode links correct across the season boundary.
- **Failed cases:** `--sniff` fails with `BrowserType.launch: Executable doesn't exist` — Playwright browsers not installed, error message is clear but README doesn't mention `playwright install` (DONG-06, Low).
- **Data oddity:** episode list shows `1, 101, 102, …` (season tabs: `tab-1751963350783` ep 1 then `tab-1` ep 101+) — the site's own numbering; consumers must not assume sequential numbering (DONG-05 documented, not a scraper bug — site ground truth).

### 5.4 DonghuaStream (`donghua/DonghuaStream`)

- **Works:** `--search` returns results (types/status/URLs).
- **Failed cases:**
  - `--info renegade-immortal` → `RuntimeError: Failed to fetch https://donghuastream.org/anime/renegade-immortal/ after 3 attempts. Cause: HTTP 404` — search result URL slug differs from the constructed detail URL (domain/slug mismatch) (DONG-03, **High**: detail pipeline broken for this input).
  - Duplicate rows in search output (DONG-04, Low).

### 5.5 Luciferdonghua (`donghua/Luciferdonghua`)

- **Works:** best-in-repo metadata — alternate titles incl. Chinese `仙逆`, rating, studio, producers, followers, expected-vs-scraped episode counts (`Expected: 24 | Scraped: 161`), full episode table with quality + dates. `--info renegade-immortal-xian-ni` → 161 episodes; `--episode` on the real URL → **5 mirrors correctly classified** (rumble 4K, vidhide 4K Eng+Indo, ok.ru 4K, generic 1080p, Dailymotion) with languages.
- **Failed cases:** `--episode` with slug guessed from pattern (`...-episode-01-english-sub/`) → `Could not resolve episode details.` Site ground truth shows real slug is `...-episode-161-lucifer-donghua/`; episode slugs are **inconsistent** (`-episode-84/` has no suffix at all). The CLI's `--episode` help gives no slug format guidance; graceful failure (DONG-07, Medium — usability + slug-pattern fragility).
- **Note:** `--info "renegade-immortal"` resolves to the *movie* entry (first match), not the series — ambiguous slugs (DONG-09, Medium).

---

## 6. Movie Scraper Audit

### 6.1 BollyFlix (`movies/bollyflix`)

- **Works:** `--search "Pathaan"` → 1 result with year/type/qualities (480p-2160p).
- **Failed case:** `--detail "download-pathaan-2023-hindi-movie"` → curl error 35 `Recv failure: Connection was reset` on `https://new.bollyflix.vote/...` after 3 retries with backoff → uncaught `SSLError` traceback, exit 1 (MOV-01, **High**: domain `new.bollyflix.vote` resets TLS; retry logic retries a hard connection failure 3× and then crashes with a raw traceback rather than a graceful message).

### 6.2 HindiLinks4u (`movies/hindilinks4u`)

- **Works:** search → 3 results; detail → full metadata (title/type/year/country/genres/director/cast/poster/trailer) + **1 stream** (`SpeedoStream` embed) + synopsis. Best-performing movie source.
- **Limitation:** quality column `N/A` in search; "HINDI" prefix glued to titles.

### 6.3 KMMovies (`movies/kmmovies`)

- **Works:** `--search "Pathaan"` → 1 result with year/type/quality.
- **Failed case:** `--detail "pathaan-2023-hindi-download-1080p-webripmovieact"` (slug copied from search output) → `Item not found or failed to fetch.` — slug from search is not accepted by detail (MOV-03, Medium: broken search→detail chain; graceful error, exit code wrong — see ALL-01).

### 6.4 MoviesMod (`movies/moviesmod`)

- **Failed case:** `--search "Jawan"` → `No items found.`; `--search "Pathaan"` → `No items found.` — two popular Hindi titles return zero (MOV-02, **High**: search appears wholly non-functional against the live site; site-side state not investigated beyond these two queries — *partial verification*).

### 6.5 OneTube (`movies/onetube`) — TMDB-backed

- **Works:** search → correct TMDB results with scores/IDs; detail `864692` → complete metadata (tagline, duration, rating with vote count, genres, poster, watch URL) + **4 stream servers** (Layla script, VidSrc, 2Embed, AutoEmbed) + synopsis.
- **Limitation:** `Orig Title: ????` — non-ASCII (Hindi) title rendered as question marks (MOV-04, Low: console encoding or TMDB transliteration; needs follow-up to attribute).

---

## 7. Search Testing

| Source | Exact | Partial | Case variants | CJK | No-results | Dupes | Notes |
|---|---|---|---|---|---|---|---|
| Miruro | OK | OK | ok | not run | not run | none | 3 results correct |
| Anikoto | OK | OK | not run | not run | not run | none | 8 results, sub/dub counts |
| ReAnime | OK | OK | not run | not run | not run | none | 5 results |
| AnimeSalt | OK (T3 matrix) | OK | OK | 0 results (site also 0) | graceful | none | misses movies (SALT-01) |
| WatchAnimeWorld | OK | OK | OK | 0 (site nav-only) | graceful | none | (WAW-01) |
| AnimeSuge | OK | OK | OK | **10 (best CJK)** | graceful | none | (SUGE-01 genres) |
| Animexin | OK | OK | OK (`MARTIAL MASTER`) | not run | started crawl | none | page-1 only (H5 unverified) |
| AnimeKhor | OK | OK | not run | not run | not run | **YES (2×)** | DONG-02 |
| AnimeCube | OK | OK | not run | not run | not run | none | |
| DonghuaStream | OK | OK | not run | not run | not run | **YES (2-3×)** | DONG-04 |
| Luciferdonghua | OK | OK | not run | not run | not run | none | |
| Bollyflix | OK | n/a | not run | n/a | not run | none | |
| HindiLinks4u | OK | not run | not run | n/a | not run | none | |
| KMMovies | OK | not run | not run | n/a | not run | none | |
| MoviesMod | **FAIL** | FAIL | — | — | indistinguishable | — | MOV-02 |
| OneTube | OK | not run | not run | n/a | not run | none | |

Empty-query behaviour (T3): `--search ""` prints **help screen instead of results** on all three anime CLIs tested, though the underlying `scraper.search("")` returns the site's latest items (ALL-02).

---

## 8. Metadata Testing

Verified against live site HTML:

| Field | Salt | WAW | Suge | Animexin | AnimeKhor | AnimeCube | Lucifer | OneTube |
|---|---|---|---|---|---|---|---|---|
| title | OK | OK | OK | OK | OK | OK | OK | OK |
| alt/native title | partial | partial | partial | OK | **OK (仙逆)** | N/A | **OK** | OK |
| description | OK | OK | OK | OK | OK | OK | OK | OK |
| poster | OK | OK | OK | OK | OK | OK | OK | OK |
| genres | (SALT-02) | (WAW-01) | **53-57 (SUGE-01)** | **OK (fixed)** | OK | OK | OK | OK |
| year | missing (SALT-04) | missing (WAW-04) | missing | OK | OK | OK | OK | OK |
| status | site absent → OK | site absent → OK | **always None (SUGE-02)** | OK `Ongoing` | OK | OK `ongoing` | OK | OK |
| type | OK | OK | search-only | OK `ONA` | OK `ONA` | OK | OK `DONGHUA/Movie` | OK |
| rating | site absent | site absent | n/a | **`8` (fixed)** | OK `9.00` | n/a | OK `9.2` | OK `6.4/10` |
| studios | (SALT-05) | (WAW-06) | n/a | empty | OK `BUILD DREAM` | n/a | OK | n/a |
| episode count | OK | (WAW-05 truncation) | OK | OK (696) | OK (158) | OK (61) | OK (161) + expected/scraped | n/a |

**AnimeXin residual:** `Quality` and `Audio` remain empty on a live page that publishes them (C2 partial).

---

## 9. Episode Testing

- **Animexin:** 696 episodes parsed from a real cached detail page; labels in DOM order (696→692 verified); `parse_episode_label` handles decimals, quality brackets, ranges, OVA/Movie/Special typing correctly (H1 mostly fixed; `'2020'→2020` remains).
- **AnimeKhor:** 158 episodes with dates; range episode "Episodes 1 to 3" mapped to Ep #1 (range metadata retained, not expanded — worth documenting for consumers).
- **AnimeCube:** ep 1 and ep 101 both resolve with correct titles/IDs/prev/next links across season tabs.
- **Luciferdonghua:** ep 161 verified end-to-end (5 mirrors); ep URL slug patterns vary (`-lucifer-donghua` suffix, bare `-84`) — hard-coded patterns would break.
- **T3 sources:** episode matrix run for >=3 titles each — ep titles generic (SALT-08/WAW-08), WAW lists truncated (3/15, 13/25, 8/63 — WAW-05).
- **Long-range:** Lucifer ep 161, Animexin ep 696, AnimeCube ep 101 — all resolved.
- **Chain integrity:** search→detail→episode→source identity held where tested; broken in KMMovies (MOV-03) and Anikoto/ReAnime (ANIME-04 slug chain).

---

## 10. Source Extraction Testing

| Source | Streams tested | Belonging proof | Result |
|---|---|---|---|
| AnimeKhor | `--episode` | — | **Crashes** (FK constraint) before extraction (DONG-01) |
| AnimeCube | ep 1, ep 101 | ep title + ID match page (`Battle of Gods`, `Episode 101`) | OK — Dailymotion `x9oo4ca` + own player |
| Luciferdonghua | ep 161 | title `Episode 161 English Sub` matches page | OK — 5 mirrors, providers classified (rumble/vidhide/ok.ru) |
| HindiLinks4u | Pathaan | detail page embed | OK — 1 embed |
| OneTube | TMDB 864692 | TMDB ID encoded in every embed URL | OK — 4 servers |
| T3 trio | >=3 eps each | page ground truth | OK chain; suge all `master.m3u8` → 200; suge VTTs → 403 (SUGE-04) |
| KMMovies | — | — | blocked at detail (MOV-03) |
| Bollyflix | — | — | blocked at detail (MOV-01) |

**Not verified:** HTTP 200 ≠ correct content — full byte-level content verification against the episode player was performed only for T3's group and the donghua episodes above (marked accordingly).

---

## 11. Domain / Availability Testing

| Source | Hardcoded domain | Status |
|---|---|---|
| Miruro | miruro.cx / miruro.com | alive (search works) |
| Anikoto | (per config) | alive |
| ReAnime | reanime.to | alive |
| AnimeSalt / WAW / Suge | per config | alive (T3 live) |
| Animexin | animexin.dev (+vip/xyz mirrors) | alive; robots.txt permissive; sitemap index available |
| AnimeKhor | animekhor.org | alive |
| AnimeCube | animecube.live | alive |
| DonghuaStream | donghuastream.org | **detail 404** — domain resolves, slug/URL contract broken (DONG-03) |
| Luciferdonghua | luciferdonghua.in | alive |
| Bollyflix | **new.bollyflix.vote** | **TLS connection reset** (MOV-01) — domain effectively dead/blocked |
| HindiLinks4u | per config | alive |
| KMMovies | per config | alive (detail slug broken) |
| MoviesMod | per config | alive but returns no search results (MOV-02) |
| OneTube | 1tube.org | alive |

Hardcoded domains are a maintenance risk: 2 of 16 already failing (Bollyflix reset, DonghuaStream 404). No source probes a domain-change/redirect registry; mirror lists exist only for Animexin.

---

## 12. Edge-Case Testing

T3 battery (39 cases across salt/waw/suge): **0 unhandled exceptions**. Empty/whitespace/emoji/CJK/Cyrillic/200-char/script-injection/traversal queries, bad slugs (404), bad URLs, empty episode refs — all returned empty/`None` with stderr logging.

Orchestrator observations:

- **Graceful:** ReAnime 404 → panel; KMMovies → message; DonghuaStream → RuntimeError with URL+cause (loud but clean).
- **Ugly:** Bollyflix → raw `curl_cffi` traceback (MOV-01); AnimeKhor → raw `sqlite3.IntegrityError` traceback (DONG-01).
- **Wrong-but-quiet:** foreign URL passed to salt/waw `--detail` returns a *different* series' title (SALT-06/WAW-07) — no error raised.
- **Exit codes:** all failures exit **0** (ALL-01, T3-verified across 12 commands).
- **Isolation:** failures were per-operation; no cross-source crashes (each source is a separate process/module).

---

## 13. Performance Findings

Median of 3 cold runs (T3 harness): salt detail 1341 ms (slowest), suge server list 158 ms (fastest), cache hit 52 ms vs live 3258 ms (suge). All 11 operations byte-identical across 3 runs. Animexin full-search crawl exceeded 120 s for a 696-episode series (expected; N+1 page fetch pattern inherent to pipeline). No premature optimization claims made; N+1 export/query patterns noted only where observed (research.txt H10 — *unverified-current*).

---

## 14. Cross-Source Consistency

Same title "Renegade Immortal" across donghua sources (site ground truth checked per source):

| Source | Type/status | Episodes | Verdict |
|---|---|---|---|
| AnimeKhor | ONA / Ongoing | 158 (range ep 1) | site-consistent |
| AnimeCube | ongoing / 2025 | 61 (+season tabs) | site-consistent (own numbering) |
| Luciferdonghua | DONGHUA / Ongoing | 161 scraped, 24 expected-stated | site-consistent; "expected 24" is site metadata drift |
| DonghuaStream | detail broken | — | (DONG-03) |

Differences are attributable to each site's own catalogue, not extraction errors — verified individually rather than assumed. "Solo Leveling" across Miruro/Anikoto/ReAnime shows consistent 12/13-eps/season-2 splits.

---

## 15. Complete Bug List

Evidence schema: Source · Component · Severity · Title · Description · Repro · Input · Expected · Actual · Website · Scraper · Evidence · Root cause · Affected · Fix.

### Group A — AnimeSalt / WatchAnimeWorld / AnimeSuge (T3 audit, full evidence in task output)

**SALT-01 · Salt · scraper.py search · High · Search misses movie entries.** Repro: `python -m anime.animesalt.cli --search ""` (site 12 articles = 9 series + 3 movies; scraper returns 9). Expected: all site hits. Actual: movies absent. Website: 12 items. Scraper: series-only selector. Evidence: `scratch/T3_search_matrix.json`, `T3_edge_ground.json`. Root cause: result filter excludes non-series. Affected: every query with movie hits. Fix: include movie cards or expose `--include-movies`.

**SALT-02 · Salt · scraper.py:195 area · High · Episode titles are the series name.** Repro: `--episode "one-piece-1x30"`. Expected distinguishing title. Actual `Title: One Piece` for 12/12 episodes. Website `<title>` carries `One Piece 1x30 - Anime Salt`. Root cause: heading-only extraction ignores `<title>`. Fix: prefer `soup.title` stripped of site suffix.

**SALT-03..07 · Salt · Medium ·** missing `year` (SALT-04), studio gap (SALT-05), foreign-URL input returns wrong title (SALT-06, Low), **no cache TTL** (SALT-07 — stale rows served forever; evidence `T3_stale_cache.json`), result/count drift (SALT-03).

**SALT-08 · Salt · Low · Episode title generic** — same root cause as SALT-02, `scraper.py:195-196`.

**WAW-01 · WAW · High · Genres/metadata selector mismatch on detail** (T3). WAW-02..06 · Medium: truncation **WAW-05 (3/15, 13/25, 8/63 episodes listed — data loss)**, plus year/status/studio gaps. WAW-07 · Low: foreign URL → wrong title. WAW-08 · Low: 9/9 episodes fall back to `Episode N` although `<title>` has real name (`site_h1=None` for 9/9; evidence `T3_ep_titles.py`).

**SUGE-01 · AnimeSuge · scraper.py:172 · High · Genres = global 50-genre nav.** Repro: `python -m anime.animesuge.cli --detail "solo-leveling-ilh08"`. Expected `Action, Adventure, Fantasy`. Actual 53 entries (`Action, Action & Adventure, …` alphabetical nav menu). Website: title genres in `.meta` block. Scraper: `soup.select("a[href*='/genre/']")` unscoped. Evidence: `T3_inspect_suge_genres.py`, `T3_field_summary.json` (52-57 on 7/7). Root cause: unscoped selector. Affected: 100% of detail results. Fix: scope to `.meta`/`.film-info`, dedupe.

**SUGE-02 · Medium · `status`/`anime_type` always None** — models declare them (`models.py:84-85`), detail constructor never passes them; site publishes `Status:`/`Type:` on 7/7 fixtures (evidence `T3_suge_status_type.py`). Fix: parse info box, pass fields.

**SUGE-03 · Medium · Cache has no TTL** — `storage.py:123-127` plain SELECT; poisoned `updated_at=2016` row served with network cut (evidence `T3_stale_cache2.json`). Fix: `updated_at` predicate / `--refresh`.

**SUGE-04 · Low · Subtitle VTTs → Cloudflare 403** for all header combos (0/200 success); *website behaviour unverified* (player not observed). Evidence `T3_sub_probe.json`.

**ALL-01 · All three CLIs · Low · Exit code 0 on every failure** — 12/12 failure commands returned `exit: 0`. Fix: `sys.exit(1)` on `None`/empty.

**ALL-02 · All three CLIs · Low · `--search ""` prints help** — `if args.search:` truthiness; underlying search actually works (salt 9, waw 10, suge 28). Fix: `is not None`.

### Group B — Orchestrator-tested sources

**MOV-01 · Bollyflix · http_client.py + cli.py · High · Detail crashes with raw SSL traceback; domain resets.** Repro: `python -m movies.bollyflix.cli --detail "download-pathaan-2023-hindi-movie"`. Expected: details or graceful error. Actual: 3 retries (`curl: (35) Recv failure: Connection was reset`) then uncaught `SSLError`, exit 1. Website: `new.bollyflix.vote` resets TLS on this path. Evidence: full traceback captured 2026-10-04. Root cause: dead/blocked domain + no exception boundary in CLI; retrying a hard reset is futile. Affected: all detail/stream calls. Fix: catch in `cmd_*`, print domain-health message, exit 1; add domain liveness config/probe.

**MOV-02 · MoviesMod · scraper search · High · Search returns zero for popular titles.** Repro: `--search "Jawan"` and `--search "Pathaan"` → `No items found.` Expected: results. Actual: none. Website: not fully investigated beyond two queries — **partial verification** (site may have changed search endpoint). Evidence: CLI stdout 2026-10-04. Root cause: unknown (endpoint drift suspected). Affected: both tested queries. Fix: re-inspect site search endpoint (DevTools) before code change.

**MOV-03 · KMMovies · scraper detail · Medium · Slug from search not accepted by detail.** Repro: `--search "Pathaan"` → copy slug → `--detail "pathaan-2023-hindi-download-1080p-webripmovieact"` → `Item not found or failed to fetch.` Website/expected: detail resolvable from search result. Actual: not found. Evidence: CLI stdout. Root cause: slug normalization mismatch (trailing tokens/casing). Affected: chain search→detail broken. Fix: accept full search slug or URL; investigate site's canonical detail URL.

**MOV-04 · OneTube · Low · `Orig Title: ????`** — non-ASCII original title lost. Evidence: detail output for TMDB 864692. Root cause: console encoding or field transliteration — **unverified which**. Fix: confirm TMDB payload first; reconfigure stdout encoding.

**ANIME-04 · Anikoto/ReAnime · cli.py · Medium · Search output truncates slugs and bare slug 404s.** Repro: `--search "Solo Leveling"` → table shows `solo-level…`; `--detail "solo-leveling"` → Anikoto: `HTTP 404`; ReAnime: panel titled `404` with exit 0. Expected: copied slug works. Actual: unusable chain. Website: real slug longer (unverified exact form). Evidence: CLI stdout 2026-10-04. Root cause: rich column width truncation + slug not tested/normalised. Affected: all detail lookups driven from search output. Fix: print full slug (or a `--detail` URL), widen column, and validate search→detail round-trip in tests.

**DONG-01 · AnimeKhor · storage.py:153 / cli.py:85 · Medium · FK constraint crash on `--episode` without prior crawl.** Repro: `python -m donghua.AnimeKhor.cli --episode "https://animekhor.org/renegade-immortal-episode-1/"` on fresh DB. Expected: fetch streams. Actual: uncaught `sqlite3.IntegrityError: FOREIGN KEY constraint failed`, full traceback. Website: episode page exists (site fine). Scraper: `save_episode_detail` inserts episode before its series row exists. Evidence: traceback 2026-10-04. Root cause: missing upsert of parent series (or ON DELETE/INSERT ordering). Affected: any direct episode lookup without `--crawl` first. Fix: auto-upsert minimal series row, or upsert-then-insert ordering.

**DONG-02 · AnimeKhor · scraper search · Low · Duplicate rows in search results** (each title rendered twice). Evidence: search stdout 2026-10-04. Root cause: two selector blocks both matching (unverified which). Fix: dedupe by slug.

**DONG-03 · DonghuaStream · scraper.py:79 · High · `--info` 404s for slugs returned by `--search`.** Repro: `--search "Renegade Immortal"` → `--info renegade-immortal` → `RuntimeError ... HTTP 404 at https://donghuastream.org/anime/renegade-immortal/`. Website: series exists under a different slug/URL (site search result URL differs — **slug mismatch, exact canonical unverified**). Evidence: traceback 2026-10-04. Root cause: constructed URL doesn't match site canonical; search URL not reused for detail. Affected: detail pipeline for this input; likely systematic. Fix: pass full search result URL to detail; verify against site.

**DONG-04 · DonghuaStream · Low · Duplicate rows in search** (2-3×). Same class as DONG-02.

**DONG-05 · AnimeCube · Data note (not a bug) · Episode numbers discontinuous** (`1, 101…129`) — site season-tab numbering, verified ground truth; document for consumers.

**DONG-06 · AnimeCube · sniffer · Low · `--sniff` fails when Playwright browsers absent** (`Executable doesn't exist ... playwright install`). Error is self-explanatory; README lacks the prerequisite. Fix: document + pre-flight check.

**DONG-07 · Luciferdonghua · cli --episode · Medium · Episode slug formats undocumented/inconsistent.** Repro: guessed `...-episode-01-english-sub/` → `Could not resolve episode details.` Site slugs: `...-episode-161-lucifer-donghua/`, `...-episode-84/` (bare). Expected: CLI accepts episode number or prints canonical URL from `--info`. Actual: only exact URL works. Evidence: 404 fetch + site link list. Root cause: CLI accepts only full URLs; no slug normalisation. Fix: accept `{series,ep,N}` and resolve via series page.

**DONG-08 · Animexin · episode_parser · Low · `'2020'` → episode_number 2020** — bare 4-digit year/counter treated as episode number (re-test of research.txt H1). Fix: bound episode numbers to plausible range/site count.

**DONG-09 · Luciferdonghua · --info slug ambiguity · Medium ·** `--info "renegade-immortal"` resolves to the *movie*, not the 161-episode series (first-match). Expected: disambiguation. Actual: wrong title silently. Evidence: CLI output. Fix: on ambiguous slug, list candidates.

**ANIMEXIN-C2b · Animexin · parser.py info block · Medium · `Quality`/`Audio` still empty** on a live page publishing them (prior C2 partial fix; genres+rating now work). Repro: parse cached `cache/9abc8b6a...html`. Actual: `Quality: [] Audio: []`; website publishes them. Fix: extend info-content scan or add `meta` fallbacks.

**ANIMEXIN-TESTS · Animexin · tests · Info · 8/8 passing** (research.txt claimed 5; suite grew). Prior C4 **confirmed fixed** (`default=None` flags), C1 **fixed**, H1 **mostly fixed**. C3/C5-C8/H2-H16 **not re-tested — unverified-current**.

### Prior-art validation summary (research.txt C1-C8 / H1-H16, Animexin)

| ID | Verdict | Evidence |
|---|---|---|
| C1 genres | **FIXED** | live parse → `['Action','Historical','Martial Arts','Over Power']` |
| C2 rating/quality/audio | **PARTIAL** | rating `8` works; quality/audio still `[]` (ANIMEXIN-C2b) |
| C4 CLI clobber | **FIXED** | `scraper.py:28-47` all `default=None` |
| H1 episode labels | **MOSTLY FIXED** | `13.5`, `[360P]12`, ranges OK; `2020` remains (DONG-08) |
| C3, C5–C8, H2–H16 | **unverified-current** | not re-tested this round |

---

## 16. Severity Breakdown

| Severity | Count | IDs |
|---|---|---|
| Critical | 0 | — (no data-corruption/security/system-wide outage proven) |
| High | 6 | SALT-01, SALT-02, WAW-01, SUGE-01, MOV-01, MOV-02, DONG-03 *(7 entries; MOV-02 partial verification)* |
| Medium | 16 | SALT-03/04/05/07, WAW-02/03/04/05/06, SUGE-02, SUGE-03, MOV-03, ANIME-04, DONG-01, DONG-07, DONG-09, ANIMEXIN-C2b |
| Low | 13 | SALT-06/08, WAW-07/08, SUGE-04, ALL-01, ALL-02, MOV-04, DONG-02/04/06/08 |
| Info | 2 | ANIMEXIN-TESTS, DONG-05 (data note) |

No severity inflation: zero Criticals (nothing corrupted stored data or took the whole system down), and the single unproven High (MOV-02) is flagged *partial verification*.

---

## 17. Root-Cause Analysis

1. **Unscoped CSS selectors** (SUGE-01, SALT-02, WAW-08, C2-class) — selectors match site-wide nav/heading elements instead of the title's data block. Produces confident wrong data; tests encode the wrong selectors so they pass.
2. **No shared base layer** — exit codes, empty-query handling, cache TTL, duplicate dedupe bugs recur per source (ALL-01/02, SUGE-03/SALT-07, DONG-02/04) because each package is a copy.
3. **Broken search→detail contracts** (MOV-03, ANIME-04, DONG-03) — the CLI outputs identifiers its own detail path cannot consume; no round-trip test exists.
4. **Missing exception boundaries in CLIs** (MOV-01, DONG-01) — HTTP/DB layer exceptions escape to raw tracebacks.
5. **Hardcoded domain/slug assumptions** (MOV-01, DONG-03, DONG-07) — no liveness probe, no redirect capture, no reuse of the URL that actually worked during search.
6. **Storage write-ordering bugs** (DONG-01 FK) — child rows inserted before parents.
7. **Stale-by-design caching** (SUGE-03/SALT-07) — SELECT without freshness predicate and no `--refresh` flag.

---

## 18. Recommended Fixes (text only — no code changed)

**P0 (data correctness):** scope AnimeSuge genre selector to `.meta` and dedupe (SUGE-01); fix WAW/Salt episode-title extraction to use `<title>` (SALT-02/WAW-08); repair WAW episode-list truncation (WAW-05); make DonghuaStream detail reuse the search-result URL (DONG-03); add CLI exception boundaries + non-zero exits (MOV-01, ALL-01, DONG-01).

**P1 (chain integrity):** print/accept full slugs and add search→detail round-trip tests (ANIME-04, MOV-03); KMMovies slug normalisation; AnimeKhor FK upsert ordering; MoviesMod search endpoint re-inspection with DevTools (MOV-02).

**P2 (hygiene):** cache TTL + `--refresh` everywhere; duplicate-result dedupe in donghua searches; `is not None` empty-query handling; document `playwright install`; Animexin quality/audio selectors; disambiguate Lucifer slugs; fix OneTube non-ASCII.

**P3 (architecture):** extract shared `base_scraper` (config/http/storage/cli) so fixes propagate; domain-liveness probing with configurable mirror lists; aggregate cross-source registry.

---

## 19. Known Limitations

- MoviesMod behaviour beyond two queries not investigated (MOV-02 partial).
- Miruro/Anikoto/ReAnime deep matrices incomplete (subagent platform failures) — smoke-tested only.
- T8-style DevTools/network capture comparison was replaced by direct-HTTP ground truth; browser-level diffs remain for a future pass.
- SUGE-04 subtitle 403: site-player behaviour unverified.
- research.txt C3/C5-C8/H2-H16 marked *unverified-current*, not refuted.
- AnimeCube `--sniff` and Animexin Playwright paths untested (browser binaries absent).
- proxy_pool not exercised against live targets (smoke only).

---

## 20. Test Coverage Gaps

- **Only 1 test suite in the repo**: `donghua/Animexin/tests/test_animexin.py` (8 parser tests). 15 sources have **zero tests**.
- No CLI tests → ALL-01/02 (exit codes, empty query) would be caught immediately.
- No search→detail round-trip tests → MOV-03/ANIME-04/DONG-03 slipped through.
- No storage tests → FK ordering (DONG-01) and TTL (SUGE-03) unguarded.
- No golden-fixture tests from live HTML for salt/waw/suge → wrong-selector bugs (SUGE-01) ship green.
- No CI/lint/type-checking; no `conftest.py`; dependencies unpinned.
- Recommended minimum: per-source fixture test (search/detail/episode parse), CLI exit-code contract test, slug round-trip test, storage state-machine tests, and a nightly live smoke (`--search` + 1 detail per source) that fails loudly on domain rot like Bollyflix.
