# Verification Report — Agy's Fix Commit `0f5f4ad`

**Verifier:** OpenCode (hands-on CLI testing, no code reading as evidence)
**Repo:** `AniMovBackend` @ `0f5f4ad` (parent: `83f621b`)
**Method:** Every claim re-run as an end user via `py -3.13 -m <domain>.<source>.cli`, ground-truthed against the live site before assigning blame.
**Date:** 2026-10-06

---

## 0. TL;DR

| | Count |
|---|---|
| Agy's claims verified correct | **6 / 8** |
| Claims partially correct (side effects) | **2 / 8** |
| Regressions introduced by `0f5f4ad` | **1 HIGH** |
| New bugs found (pre-existing, not Agy's) | **4** (1 HIGH, 3 MED) |
| Cross-source contract inconsistencies | **2 MED** |

**Bottom line:** Agy's fixes do what she said. The two HIGH claims both work as advertised. But the DonghuaStream fix traded one bug for another (**regression**), and a previously-untested code path (Miruro `--info`/`--episode`) turned out to be **100% broken**.

---

## 1. Claim-by-Claim Verification

### ✅ Claim 1 (HIGH) — DonghuaStream movie bias
> `--info renegade-immortal` and `--info renegade` now resolve the main TV series (162 eps), not Movie 2.

**VERIFIED — correct.**
```
renegade-immortal  exit=0  -> Renegade Immortal   eps=162
renegade           exit=0  -> Renegade Immortal   eps=162
swallowed-star     exit=0  -> Swallowed Star Season 4  eps=158   (was: Movie, 4 eps)
```
Old commit `83f621b` returned `Renegade Immortal Movie 2: Battle of Immortal Slayer (eps=3)` for both. Scoring fix works.

⚠️ **But introduced a regression — see REG-01.**

---

### ✅ Claim 2 (HIGH) — ReAnime digit titles
> `img.get('alt')` made primary + digit/badge tokens filtered out.

**VERIFIED — correct.**
```
total=30  digit/empty titles=0
   naruto-bjfend                 'Naruto'
   naruto-shippuden-rtyjpy       'Naruto: Shippuden'
   the-last-naruto-the-movie     'The Last: Naruto the Movie'
```
Pre-fix these were `'220'`, `'500'`, `'293'`.

---

### ✅ Claim 3 (MED) — Anikoto episode titles + resolver hardening
> Stray digit prefix removed; short queries (`"a"`) blocked; spaces handled.

**VERIFIED — correct.**
```
Ep 1 title = "I'm used to it"          (was "1I'm used to it")
--detail "a"            exit=1   (blocked, no random match)
--detail "solo leveling" exit=0  -> Solo Leveling
--detail "solo-leveling" exit=0  -> Solo Leveling
```

---

### ⚠️ Claim 4 (MED) — WAW branding / synopsis / absolute URLs
> Branding stripped, `.description` selector added, relative URLs absolutized.

**VERIFIED — but ONLY with `--refresh`.** The fix is real in code and produces correct output:
```
--detail "one-piece" --refresh   -> Synopsis: Barely surviving in a barrel after passing through a terrible...
--episode "solo-leveling-2x5" --refresh -> Title: Solo Leveling 2x5
                                        Server: https://watchanimeworld.one/dub-player/t/14043/
```
Without `--refresh`, the **pre-fix cached row** still returns `Synopsis: N/A` and the branded title. → **NEW-19**.

---

### ✅ Claim 5 (MED) — Exit codes on missing content
> 6 CLIs now `sys.exit(1)` on failure.

**VERIFIED — 15/15 correct, zero tracebacks.**
```
Miruro, Anikoto, ReAnime, Salt, WAW, Suge, AnimeKhor, AnimeCube,
DHS, Lucifer, Bollyflix, HindiL4u, KMMovies, MoviesMod, OneTube
  -> all exit=1 on bad slug, no raw traceback
```
Pre-fix this was 9/15 (NEW-07). Now complete.

---

### ⚠️ Claim 6 (MED) — Empty search
> `--search ""` now prints "No search query provided" + `exit 1`.

**PARTIALLY CORRECT — the behaviour is now split across sources:**

| Behaviour | Sources |
|---|---|
| returns results, exit 0 | ReAnime (36), AnimeSalt (12), WAW (10), AnimeSuge (28) |
| "No search query", exit 1 | Miruro, Anikoto, AnimeKhor, AnimeCube, DHS, Lucifer, HindiL4u, OneTube |
| "No items found.", exit 1 | Bollyflix, KMMovies, MoviesMod |

→ **NEW-18**. Same flag, three different contracts.

---

### ⚠️ Claim 7 (MED) — No raw tracebacks
> try/except added to Miruro, AnimeCube, Lucifer.

**PARTIALLY CORRECT.** AnimeCube, Lucifer, HindiL4u, OneTube all clean now (previously NEW-09/NEW-13). But **Miruro's `--search` traceback remains** on a different code path → **NEW-16**.

---

### ✅ Claim 8 — git hygiene
**VERIFIED.** `.pyc`/`__pycache__` untracked and removed; tree clean.

---

## 2. REGRESSIONS Introduced by `0f5f4ad`

### 🔴 REG-01 — DonghuaStream resolver breaks all space queries and alternate-title queries

**Severity: HIGH** · Confidence: site-verified, reproduced on both commits via isolated `git worktree`

`--info` now returns **nothing** for entire classes of natural user input that **worked on the previous commit**:

| Query | `83f621b` (old) | `0f5f4ad` (new) |
|---|---|---|
| `renegade-immortal` | ❌ Movie 2 (3 eps) | ✅ **Renegade Immortal (162)** |
| `swallowed-star` | ❌ Movie (4 eps) | ✅ **Swallowed Star Season 4 (158)** |
| **`renegade immortal`** (space) | ⚠️ resolved (wrong entry) | 🔴 **`None` / exit 1** |
| **`fights-break-sphere`** | ✅ Battle Through the Heavens (12) | 🔴 **`None` / exit 1** |
| **`fights break sphere`** | ✅ Battle Through the Heavens (12) | 🔴 **`None` / exit 1** |
| **`soul land`** (space) | ⚠️ resolved (wrong entry) | 🔴 **`None` / exit 1** |
| **`shrouding-the-heavens`** | ⚠️ Movie (4 eps) | 🔴 **`None` / exit 1** |

**Repro:**
```powershell
py -3.13 -m donghua.DonghuaStream.cli --info "renegade immortal"     # exit 1
py -3.13 -m donghua.DonghuaStream.cli --info "fights-break-sphere"    # exit 1
py -3.13 -m donghua.DonghuaStream.cli --info "soul land"              # exit 1
```

**Root cause** (`donghua/DonghuaStream/scraper.py`, scoring block added in `0f5f4ad`):
1. `raw_words = set(w for w in raw_clean.split("-") ...)` — splits on **hyphen only**. A space query becomes one token `"renegade immortal"` which can never be a subset of `{"renegade","immortal"}` → word-overlap score 0. Also `cand_clean.startswith(raw_clean)` compares `"renegade-immortal1"` vs `"renegade immortal"` → never matches.
2. The old first-candidate fallback (`if not matched_url and candidates: matched_url = candidates[0].url`) was **removed** and replaced with a hard `score >= 50` threshold. That fallback is what made alternate/alias titles work (site's `search('fights break sphere')` legitimately returns `battle-through-the-heavens1` — verified correct against the site catalog).
3. Asymmetry proof: line 93 does `raw_slug.replace("-", " ")` to build the *search* query (hyphens→spaces) but scoring never normalizes spaces→hyphens.

**Scores measured:** `fights-break-sphere`→`battle-through-the-heavens1` = **0**; `soul land`→`soul-land` = **0** (all three candidates); `renegade immortal` max = 30 (below threshold 50).

**Fix shape:** normalize `raw_clean = raw_slug.lower().replace(" ", "-")` and split words on `[\s-]`; reintroduce a fallback to the single/best candidate when no candidate scores ≥50 (with the movie-penalty retained so Claim 1 doesn't regress).

---

## 3. New Bugs Found

### 🔴 NEW-14 — Miruro: every search result is a dead end (ID-space mismatch)
**Severity: HIGH** · Confidence: site-verified · **Not Agy's** — `anime/miruro/scraper.py` last changed in `b64fca4` (09-30); Agy's two commits only touched its `cli.py`.

Search uses **AniList GraphQL** and returns AniList integer IDs, but `get_series_detail()` calls Miruro's own `/api/v1/anime/{id}` which expects **Miruro's opaque 32-char IDs**.

```
--search "Naruto"  -> id='20'  title='Naruto'
--info 20          -> exit 1  "Anime ID '20' not found on Miruro."
```
Ground truth from live site traffic: `/api/v1/anime/20` → **404**; `/api/v1/anime/W89s7g854PobER8iJIsw61vU_EkyYyOg` → **200** (`Attack on Titan`).

No bridge exists — probed `anilist_id_in`, `id_in`, `mal_id_in`, `search`, `query`, `keyword`, `q` (all → HTTP 400). `_extract_anime_id()` docstring claims *"Extract the 32-character Miruro ID"* but performs **no validation** — an integer passes straight through.

**Impact:** `--info` / `--episode` unreachable from any search result.

---

### 🔴 NEW-15 — Miruro: detail broken even with a correct ID
**Severity: HIGH** · Confidence: site-verified · **Not Agy's** (scraper untouched).

Even supplying a valid opaque ID, `get_series_detail()` fails at step 2:

```python
ep_url = f"{API_BASE}/anime/{anime_id}/episodes?kind=regular&limit=10000"   # -> HTTP 400
```
```
step1 info:            OK  title='Attack on Titan'
step2  kind=regular:   FAIL HTTP 400 "Unsupported catalog request."
step2b no kind:        OK  rows=39
```
`kind=regular` (and every variant/order tried) → 400; `?limit=10000` alone → works. Site-side API change since `08d2688` (09-30).

**Combined with NEW-14: Miruro `--info`/`--episode` is 100% non-functional.**
*(This was an explicit coverage gap in my original audit — §4.1: "`--info`/`--episode` not deeply tested (T2 platform failure)". Not a contradiction; newly-discovered.)*

---

### 🟠 NEW-16 — Miruro: `NameError` raw traceback + dead fallback
**Severity: MEDIUM** · Confidence: reproduced · **Not Agy's** (`b64fca4`).

`anime/miruro/scraper.py:125` calls `logger.warning(...)` but **`logger` is never imported or defined in that module**.

```python
except Exception as e:
    logger.warning(f"AniList GraphQL search failed: {e}")   # NameError
# Fallback to direct catalog endpoint ...   <- unreachable
```

Two consequences:
1. **Raw traceback escapes the CLI.** `cmd_search()` (`cli.py:26`) has no try/except, so any AniList failure dumps a traceback. Reproduced in-memory (AniList forced to fail):
   ```
   File "anime\miruro\cli.py", line 26, in cmd_search
   File "anime\miruro\scraper.py", line 125, in search
   NameError: name 'logger' is not defined
   ```
   Not theoretical — a real `TLSV1_ALERT_DECODE_ERROR` to `graphql.anilist.co` occurred during this session.
2. **The fallback is dead code**, and would fail anyway: its `?q=` endpoint now returns HTTP 400 (the original `08d2688` design, since retired site-side).

---

### 🟠 NEW-17 — Anikoto: search returns polluted titles + empty metadata
**Severity: MEDIUM** · Confidence: site-verified · **Not Agy's.**

When the primary parse path misses (cards that are themselves `<a>` anchors — the site's "latest" fallback shown for no-match queries), line 144's fallback runs `a.get_text(strip=True)` over the whole card:

```
q='zzzqqqnonexist9999'  results=10  polluted=10
    title  = 'Dorohedoro Season 29.75ONA23 min'   <- name+score+type+duration concatenated
    type   = None   eps = None   score = None
```
Site markup has a clean `.name` div (`Dorohedoro Season 2`) and separate `.meta` spans — both ignored by the fallback.

Side effect: a no-match query returns 10 unrelated "latest" items → **exit 0**, so ALL-01 can't signal "nothing found" for this source.

*(For real matches the primary path works: `q='Naruto'` → 26 clean results with type/eps/score populated.)*

---

## 4. Cross-Source Contract Inconsistencies

### 🟠 NEW-18 — Empty search: 3 different behaviours across 15 sources
**Severity: MEDIUM**

`--search ""` → **4 sources return results (exit 0)**, **8 sources say "No search query provided" (exit 1)**, **3 sources say "No items found." (exit 1)**.

`ALL-02`'s original intent was that an empty query returns the latest items (the underlying `search("")` genuinely does). The fix went the other way for 11 sources and left 4 alone — so the same flag has no single contract.

---

### 🟠 NEW-19 — Stale cache masks parser fixes
**Severity: MEDIUM** · observed directly

A row cached **before** a parser fix keeps serving the old (buggy) value until TTL expiry or `--refresh`. WAW synopsis returned `N/A` until `--refresh`, then the full 1081-char synopsis appeared. No cache-versioning/invalidation on parser change — users can see pre-fix data for up to a full TTL.

---

## 5. No-Regression Evidence

- **Search sweep (16 sources):** all pass, no tracebacks. Donghua sources correctly exit 1 for "Naruto" (not a donghua); movie sources return their own results (`Pathaan` → 1 hit each on Bollyflix/KMMovies).
- **Detail sweep with correct slugs:** Anikoto 12 eps, ReAnime 30, WAW 62, AnimeKhor 13, DHS 162, Lucifer 174, Suge 1180, AnimeCube 59, Salt 9, HindiL4u/OneTube/Bollyflix/KMMovies/MoviesMod all resolve.
  *Earlier exit-1s in this sweep were **my wrong slugs** (table cells wrap/truncate), confirmed graceful exit 1 with a clean message — not bugs.*
- **Anikoto gibberish query → exit 0 is site-accurate:** ground truth `/filter?keyword=zzzqqqnonexist9999` returns HTTP 200 with 10 cards (site falls back to latest). Not a scraper bug.
- **`Pathaan` → HTTP 500** is site-side; scraper returns `[]` → clean exit 1.

---

## 6. Priority for Follow-Up

| ID | Sev | Owner | Summary |
|---|---|---|---|
| REG-01 | HIGH | Agy | DHS: space + alternate-title queries → `None` (regression from `0f5f4ad`) |
| NEW-14 | HIGH | Investigate | Miruro: search returns AniList IDs, detail needs Miruro IDs |
| NEW-15 | HIGH | Investigate | Miruro: `kind=regular` → 400; detail broken even with correct ID |
| NEW-16 | MED | Agy | Miruro: `logger` NameError → raw traceback; fallback dead code |
| NEW-17 | MED | Agy | Anikoto: fallback pollutes titles, drops metadata |
| NEW-18 | MED | Design decision | Empty-search contract split 4/11 across 15 sources |
| NEW-19 | MED | Design decision | Cache not invalidated when parser changes |

**Notes:** NEW-14/15/17 pre-date Agy's commits and partly stem from site-side API changes (Miruro retired `?q=` search and `kind=regular`). REG-01 is the one item directly introduced by `0f5f4ad`.
