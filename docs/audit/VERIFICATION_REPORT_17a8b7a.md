# Verification Report — Commit `17a8b7a` (Agy's 3rd fix round)

**Verified by:** Conductor (hands-on CLI / live-site ground truth, no code analysis only)
**Date:** 2026-10-06
**Repo:** `Unknowmyt1M/AniMovBackend`, branch `main`
**Commit under test:** `17a8b7a` — *"fix(scrapers): fix DonghuaStream alias/space queries (REG-01), Miruro ID bridge & episodes (NEW-14..16), Anikoto fallback (NEW-17)"*
**Parent (previous verified state):** `0f5f4ad`
**Files changed:** `anime/anikoto/scraper.py`, `anime/miruro/scraper.py`, `donghua/DonghuaStream/scraper.py` (123 insertions / 45 deletions)

**Method:** end-user CLI execution (`py -3.13 -m <domain>.<source>.cli ...`), live-site API ground truth via the site's own HTTP client, in-memory fault injection, and isolated `git worktree` comparisons against `0f5f4ad`. No project source files were edited during verification.

---

## 1. Verdict

| Claimed fix | Severity | Verdict |
|---|---|---|
| **REG-01** DonghuaStream space / alternate-title regression | HIGH | ✅ **FIXED & VERIFIED** (no movie-bias regression) |
| **NEW-14** Miruro AniList↔opaque ID space disconnect | HIGH | ✅ **FIXED & VERIFIED** |
| **NEW-15** Miruro episodes endpoint `kind=regular` → HTTP 400 | HIGH | ✅ **FIXED & VERIFIED** |
| **NEW-16** Miruro `logger` NameError | MED | ⚠️ **PARTIAL** — scraper-side fixed; CLI-side traceback path remains |
| **NEW-17** Anikoto fallback title pollution | MED | ✅ **FIXED & VERIFIED** |

**Regression sweep:** no regressions found in the 15 CLI-backed sources (search, empty-search, bogus-input hygiene, repository hygiene).
**New findings:** `NEW-20`, `NEW-21`, `NEW-23` (all **pre-existing**, none introduced by `17a8b7a`).

---

## 2. Claim-by-claim verification

### 2.1 REG-01 — DonghuaStream space & alternate titles ✅ FIXED

The report's regression matrix (previously all `exit=1` / `None`) is now fully green — **13/13**:

| Query | Result | Episodes |
|---|---|---|
| `renegade-immortal` | Renegade Immortal | 162 |
| `renegade immortal` | Renegade Immortal | 162 |
| `renegade` | Renegade Immortal | 162 |
| `fights-break-sphere` | Battle Through the Heavens | 12 |
| `fights break sphere` | Battle Through the Heavens | 12 |
| `fights` | Battle Through the Heavens | 12 |
| `soul-land` / `soul land` | Soul Land | 3 |
| `shrouding-the-heavens` / `shrouding the heavens` | Shrouding the Heavens Movie | 4 |
| `swallowed-star` / `swallowed star` | Swallowed Star Season 4 | 158 |
| `battle-through-the-heavens1` | Battle Through the Heavens | 12 |

**No movie-bias regression (the `0f5f4ad` Claim 1 still holds):**
- `renegade-immortal` → **Renegade Immortal (series, 162 eps)**, *not* Movie 2.
- Explicit movie queries still select the movie: `renegade immortal movie 2` → *Renegade Immortal Movie 2: Battle of Immortal Slayer* (3), `soul land movie sword master` → *Soul Land Movie Sword Master*, `shrouding the heavens movie` → *Shrouding the Heavens Movie* (4), `swallowed star movie` → *Swallowed Star Movie* (4).
- `battle through the heavens movie` → `None`. **Ground truth: DHS search returns 0 results for that query** — no such movie exists on the site, so `None` is correct, not a bug.

**Negative controls (the re-enabled fallback must not grab garbage) — 8/8 correct:**
`zzzqqqnonexist9999`, `one piece`, `naruto`, `kimetsu no yaiba`, `dragon ball`, `bleach`, `jujutsu kaisen`, `totally fake donghua 12345` → all `None`.

**Site-accuracy spot check** (does the fallback pick *site* results?): `search('a')` returns `['Spare Me Great Lord Season 3', 'Renegade Immortal Movie 2…', 'Spiritual Realm Walker']` and the resolver returned **Spare Me Great Lord Season 3** = the site's own first non-movie hit. `search('the')` returns a *movie* first (`Perfect World Movie…`) and the resolver correctly skipped it to `The Eternal Supreme Li Yunxiao` — the movie penalty is working.

> Note (informational): generic single-word queries (`the`, `a`, `of`, `new`) now resolve to *some* site candidate instead of `None`. Behaviour matches the site's own fuzzy results, and matches pre-`0f5f4ad` behaviour, but the confidence of these matches is low.

### 2.2 NEW-14 — Miruro ID-space disconnect ✅ FIXED

- `--search "Naruto"` now prints genuine **32-character Miruro IDs**: `mxgbmPBIfqFpcH6qk0NmYu4n4eqpAiTH` (Naruto), `nXGGeY995cEL1QUBp4OEZlRnTYt6ZxhW` (Shippuden), `tW6L11U7xwFq_84coEjmXH3CTMyB3IgM` (Boruto). All `len == 32`.
- **search → detail chain works:** `get_series_detail(<first search hit>)` → *Naruto*, 222 episodes, ep1 = *Enter: Naruto Uzumaki!*
- **AniList integer auto-resolution works:** `--info 16498` → *Attack on Titan* (39 eps); `--info 20` → *Naruto* (222 eps).
- **Bare title / URL auto-resolution works:** `naruto` → *Naruto* 222; `attack on titan` → *AoT* 39; `https://www.miruro.cx/watch/mxgbmPBI…/naruto` → *Naruto* 222.
- **Bad ID:** `--info definitely_not_exist_xyz123` → `Error fetching series details: Anime ID '…' not found on Miruro.` **exit=1, no traceback.**
- Bridge mechanism confirmed against the live API: `GET /api/v1/anime?anilist_id_in=16498,20&limit=100` returns `external_ids.anilist` as a **list** (`['16498']`, `['20']`) mapped to the 32-char `id` — so Agy's `for al_id in …['anilist']` loop is type-correct.

### 2.3 NEW-15 — `kind=regular` → HTTP 400 ✅ FIXED

- `episodes?limit=10000` (without `kind=regular`) → *Attack on Titan*, **39 episodes**.
- Full episode path: `--episode W89s7g854PobER8iJIsw61vU_EkyYyOg --ep 1` → **exit=0, no traceback**, panel reports **27 mirrors / 18 subtitle tracks / 9 downloads**, matching Agy's claim exactly.
- Model desync fix verified: `genres`/`tags`/`studios` (API returns dicts) are normalized to strings — `SeriesDetail` construction no longer raises.
- Guardrail check: a structurally-valid-but-nonexistent 32-char ID → `HTTP 400 … "Anime identity is invalid"` → **exit=1, clean message.**

### 2.4 NEW-16 — `logger` NameError ⚠️ PARTIAL

**Fixed (scraper side):**
- `anime.miruro.scraper` now defines `logger` (`Logger` instance); `search()` references it.
- Fault-injected bridge failure logs `WARNING Miruro opaque ID batch lookup failed: …` instead of raising `NameError`. The previously-dead `?q=` fallback is no longer reached via a crash.

**Not fixed (CLI side):** `anime/miruro/cli.py::cmd_search` (lines 23–31) still has **no `try/except`** — any exception raised by `scraper.search()` (network timeout, GraphQL failure) escapes to the interpreter and prints a raw traceback. `cmd_info` and `cmd_episode` *are* guarded. This is the CLI half of NEW-16 and remains open (see NEW-23).

### 2.5 NEW-17 — Anikoto fallback pollution ✅ FIXED

- No-match query `zzzqqqnonexist9999` → **`No anime found matching your query.` exit=1** (previously 10 polluted rows, exit 0).
- 10 real titles (`Naruto`, `One Piece`, `Bleach`, `Attack on Titan`, `Death Note`, `Solo Leveling`, `Jujutsu Kaisen`, `Demon Slayer`, `Fullmetal Alchemist`, `Chainsaw Man`) → **0 glued-title rows** (heuristic: digits fused to `ONA/OVA/TV/Movie`), hit counts 8–30.
- Titles are clean: `Naruto`, `Naruto x UT`, `Naruto: Shippuden` (no `29.75ONA23 min` style debris).
- **Detail still works after the change:** `get_series_detail('naruto-eybxz')` → *Naruto*, **220 episodes**.
- Empty search → `No search query provided.` exit=1 (unchanged).

---

## 3. New findings (all pre-existing — none introduced by `17a8b7a`)

### NEW-20 (MED) — Miruro: search silently degrades to unusable IDs when the ID bridge fails

`search()` falls back to `anilist_to_miruro.get(al_id_str) or al_id_str`. With the bridge call fault-injected (`anilist_id_in` URLs raise):

```
results=20  →  INTEGER (unusable) ids: 20/20
  id=20    title='Naruto'
  id=1735  title='Naruro: Shippuden'   ...
detail on first → ValueError: Anime ID '20' not found on Miruro.
```

The CLI still prints a confident `Miruro Search Results (20)` table with **exit=0**, so the user gets 20 dead IDs and only a log-level warning explains why. Before `17a8b7a` *all* IDs were integers, so this is a **residual degradation path, not a regression** — but the new failure mode is misleading (looks successful). Suggested shape: mark unresolved rows (or degrade to `exit=1`) when `anilist_to_miruro` is empty while AniList returned results.

**Also note:** `external_ids.anilist` is a list of strings; a future API change to a scalar would break the loop (caught by the broad `except`, i.e. would fall into exactly this state).

### NEW-21 (MED) — Miruro: `--episode <garbage ID>` exits 0 and fabricates a stream

```
py -3.13 -m anime.miruro.cli --episode bogus_id_123 --ep 1   → exit=0
  Anime ID: bogus_id_123 | Subtitles: 0 | Streaming Servers: 1  (Miruro Web Player)
```

**Root cause (chain):**
1. `http_client.get_bytes` returns `b""` for **404/410** (line 78–79) instead of raising.
2. `get_decoded_json` maps empty bytes → `{}` (line 94–95).
3. `get_episode_detail` never validates `play_data` → zero tracks parsed.
4. Lines 355–365 **always** append the `Miruro Web Player` fallback mirror → a non-empty `EpisodeDetail` → CLI prints it and exits 0.

Ground truth: `GET …/anime/bogus_id_123/episodes/1/play` → **404 HTML SPA page**; `…/zzz…zzz` (32 chars) → **400 JSON**; only a real opaque ID → 200. Hence the inconsistency: 32-char garbage exits 1, other garbage exits 0.

**Regression proof:** identical behaviour reproduced at `0f5f4ad` in an isolated worktree (`exit=0`, same panel) → **pre-existing, not Agy's**.
Suggested shape: raise on 404 in `get_decoded_json` (or treat `play_data == {}` as "not found") and only append the web-player mirror when the episode was actually resolved.

### NEW-23 (MED, systemic) — 13/15 CLIs leak raw Python tracebacks on scraper failure

Fault-injected `search()` failure (`RuntimeError("SIMULATED network failure")`), invoked through each CLI's real `main()`:

| Handled (clean exit) | **Escaped → raw traceback** |
|---|---|
| `donghua.Luciferdonghua`, `movies.bollyflix` | `anime.anikoto`, `animesalt`, `animesuge`, `miruro`, `reanime`, `watchanimeworld`, `donghua.AnimeCube`, `AnimeKhor`, `DonghuaStream`, `movies.kmmovies`, `moviesmod`, `onetube`, `hindilinks4u` |

**13/15 escape.** Anikoto's `main()` uses `try:` … `finally:` with **no `except` clause at all** (only 1 `except` in the whole file, on an unrelated import) — so any scraper exception becomes a raw traceback.

**Observed in the wild (not just injected):** during this verification, `--search "One Piece"` and `--search "Bleach"` each produced a transient traceback once (network timeout), then **6/6 clean reruns** (`exit=0`, 30 hits). Confidence: *systemic + transient-network*.

This qualifies the earlier "zero tracebacks" claim: that holds for the **empty-search / bad-input paths Agy fixed**, but not for network-failure paths, which were never in scope of `0f5f4ad`/`17a8b7a`.

---

## 4. Regression sweep (evidence of *no* new breakage)

**Search sweep, 15 CLI-backed sources — zero tracebacks, zero module errors:**

| Source | exit | hits | | Source | exit | hits |
|---|---|---|---|---|---|---|
| anime.anikoto | 0 | 26 | | donghua.AnimeCube | 0 | ok |
| anime.animesalt | 0 | 3 | | donghua.AnimeKhor | 0 | ok |
| anime.animesuge | 0 | 26 | | donghua.DonghuaStream | 0 | ok |
| anime.miruro | 0 | 15 | | donghua.Luciferdonghua | 0 | 2023 |
| anime.reanime | 0 | 30 | | movies.kmmovies | 0 | 1 |
| anime.watchanimeworld | 0 | 2 | | movies.moviesmod | 1 | `No items found.` |
| | | | | movies.onetube | 0 | 2 |

`anime.animexin` has **no `cli.py`** (modular package `animexin_scraper/` + `scraper.py` only) → `ModuleNotFoundError` is structural, pre-existing, and unrelated to this commit.

**Empty-search matrix (unchanged from `0f5f4ad`, NEW-18 still open by design):**
- `No search query provided.` → exit 1: anikoto, miruro, AnimeCube, AnimeKhor, DonghuaStream, Luciferdonghua, onetube, hindilinks4u
- `No items found.` → exit 1: kmmovies, moviesmod, bollyflix
- results → exit 0: animesalt, animesuge (and reanime, which returned its usual **36 rows / exit 0** on a clean rerun)

**Bogus-input hygiene (the 3 changed sources):**

| Command | exit | traceback |
|---|---|---|
| DHS `--info zzz-not-exist-999` | 1 | clean |
| Miruro `--info definitely_not_exist_xyz123` | 1 | clean |
| Miruro `--episode zzzz…zzz --ep 1` (32-char) | 1 | clean |
| Anikoto `--search ""` | 1 | clean |
| Miruro `--episode bogus_id_123 --ep 1` | **0** | clean — see **NEW-21** |
| Miruro/DHS `--info ""` | 0 | prints usage/help (pre-existing) |
| Anikoto `--info …` | 2 | `unrecognized arguments` (Anikoto has no `--info`; pre-existing) |

**`0f5f4ad` claims re-checked (no backslide):** ReAnime digit-glued titles **0**; DHS `renegade-immortal` → *Renegade Immortal* **162 eps**; Anikoto stray-digit query → clean exit 1.

**Repository hygiene:** `git show 17a8b7a --stat` = exactly 3 `.py` files. No `.db`, no `__pycache__`/`.pyc`, no stray scripts. Local `anime/miruro/data/miruro.db` churn is runtime cache only (never committed).

---

## 5. Priority table

| ID | Sev | Source | Introduced by | Status |
|---|---|---|---|---|
| REG-01 | HIGH | DonghuaStream | `0f5f4ad` | ✅ Fixed in `17a8b7a`, verified 13/13 + 8 negatives |
| NEW-14 | HIGH | Miruro | pre-`0f5f4ad` | ✅ Fixed in `17a8b7a`, verified end-to-end |
| NEW-15 | HIGH | Miruro | pre-`0f5f4ad` | ✅ Fixed in `17a8b7a`, verified 39 eps / 27 srv / 18 sub |
| NEW-16 | MED | Miruro | pre-`0f5f4ad` | ⚠️ Partial — scraper `logger` fixed; `cmd_search` still unguarded |
| NEW-17 | MED | Anikoto | pre-`0f5f4ad` | ✅ Fixed in `17a8b7a`, verified clean titles + exit 1 |
| NEW-20 | MED | Miruro | pre-existing (masked before `17a8b7a`) | 🔴 Open — bridge outage ⇒ 20/20 dead IDs, exit 0 |
| NEW-21 | MED | Miruro | pre-existing (proven at `0f5f4ad`) | 🔴 Open — 404→`{}`→phantom stream, exit 0 |
| NEW-23 | MED | 13/15 CLIs | pre-existing | 🔴 Open — raw traceback on scraper failure |
| NEW-18 | MED | cross-source | design | ⚠️ 3 empty-search behaviours (unchanged) |
| NEW-19 | MED | cross-source | design | ⚠️ stale cache masks parser fixes until `--refresh` |
| NEW-12 / NEW-13 | LOW | DB lock / timeouts | intermittent | ⚠️ low confidence, transient |

---

## 6. Bottom line

Agy's `17a8b7a` delivers on its four headline fixes: **REG-01, NEW-14, NEW-15 and NEW-17 are genuinely fixed and verified end-to-end**, with the movie-bias protection from `0f5f4ad` intact and no regressions found across 15 sources. **NEW-16 is half-done**: the `NameError` is gone, but `miruro.cli.cmd_search` still has no exception guard.

Three follow-ups remain (**NEW-20, NEW-21, NEW-23**) — all pre-existing, so they belong in the next fix round rather than blocking this one.
