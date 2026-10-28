# AniMov Frontend & Backend Redesign Changelog

## [Audit & Analysis] - Initial State Inspection

### 1. Identified Fake / Hardcoded Data
- **Mock Data (`mockData.ts`)**: Contained static dummy anime videos with hardcoded Blender open movies (`TearsOfSteel.mp4`, `Sintel.mp4`), fake subscriber counts (`3.4M`), fake view counts (`1.2M`), fake likes, and simulated comments.
- **Fabricated Relations (`api.ts` & `AnimeDetailPage.tsx`)**: Hardcoded fake prequels, sequels, and movies using template strings (`${slug}-s1`, `${slug}-movie`).
- **Fake Video Duration & Studios**: Hardcoded `24:00` and `MAPPA`/`Wit Studio` when metadata was missing.
- **Upload Modal (`UploadModal.tsx`)**: Fictitious YouTube "Upload Video" dialog irrelevant to an anime streaming platform.
- **Watch Page Fallbacks**: Fallback to `TearsOfSteel.mp4` on stream error instead of presenting a proper retry UI.

### 2. Upstream Backend Capabilities Discovered
- **Anikage `/browse` API**:
  - Supports native query params: `sort` (`trending`, `popularity`, `updated`), `genre`, `format` (`TV`, `MOVIE`, `OVA`), `season`, `year`, `page`, `limit`.
- **Anikage `/media/anime/{slug}` API**:
  - Contains real franchise `relations` with target slug, title, format, relationType (`SEQUEL`, `PREQUEL`, `SIDE_STORY`, `ALTERNATIVE`, `SUMMARY`, etc.).
  - Contains real `studios` list with `isAnimationStudio: true`.
  - Contains real episode `duration` (in minutes).
  - Contains real upstream `recommendations` list.
- **Anikage `/media/anime/{slug}/episodes` API**:
  - Returns real episode titles, TVDB episode thumbnails, release dates, ratings, and episode numbers.

### 3. Redesign Plan
- **Backend Enhancements (`anime/anikage/models.py`, `anime/anikage/scraper.py`, `api/main.py`)**:
  - Expose real `relations`, `studios`, `duration`, `recommendations` in `AnikageDetail`.
  - Add `/api/anime/catalog` endpoint supporting `genre`, `format_filter`, `sort`, `year`, `season`, `page`, `limit`.
- **Frontend Core Types & API (`types.ts`, `api.ts`)**:
  - Update data models to match real backend responses.
  - Implement real catalog fetching, genre filtering, seasonal browse, and verified franchise relations.
  - Remove all fake statistics, subscriber counters, and fake upload flows.
- **Premium UI Redesign**:
  - Redesign Header/Navbar with functional search, active tab navigation, and library counter.
  - Redesign Sidebar with clean collapsible navigation.
  - Modernize Homepage with:
    1. Hero Anime Spotlight with real banners and 1-click play.
    2. Continue Watching shelf with exact progress percentage and resume action.
    3. Trending Anime Carousel & Grid.
    4. Latest Airing Episodes with real TVDB episode thumbnails.
    5. Genre Discovery pills with server-side catalog updates.
    6. Seasonal / Top Rated section.
  - Redesign Anime Details Page (`/anime/:slug`):
    - Real metadata (Studios, Score, Format, Status, Duration, Year, Genres).
    - Verified Chronological Franchise Relations list (Prequels, Sequels, Movies) with direct links.
    - Searchable, paginated Episode Grid with episode titles and real thumbnails.
    - Verified Anime Recommendations grid.
  - Redesign Watch Page (`/watch/:slug/:episode`):
    - Premium cinema player with ambient lighting effect.
    - Reliable HLS playback with 2-stage instant streaming.
    - Server switcher (`HD-1 Multi-Quality`, `HD-2 Ken`, `HD-3 Wave`, `MegaPlay`).
    - Subtitle track selector.
    - Dynamic resolution picker (Auto, 1080p, 720p, 480p).
    - Episode navigation drawer with search & auto-scroll to current episode.
    - Next episode autoplay countdown.
    - Auto-skip intro & outro toggles with markers.
    - Theater mode & Fullscreen mode.
    - Proper error handling with "Retry Stream" and "Switch Server" options.
  - Dedicated Library Page (`/library`):
    - Watchlist, Watching, Plan to Watch, Completed, and History tabs.
    - Persistent LocalStorage sync with ability to update status and remove items.
