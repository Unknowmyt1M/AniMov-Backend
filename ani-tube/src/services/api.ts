import { AnimeSeries, Episode, StreamSource, WatchProgress, Video } from '../types';

const API_BASE = '/api';

export interface SearchItem {
  slug: string;
  romaji: string;
  english?: string;
  native?: string;
  display_title: string;
  poster?: string;
  format?: string;
  status?: string;
  score?: number;
  genres: string[];
}

export interface SearchResponse {
  data: SearchItem[];
  query?: string;
  page: number;
}

export interface HomeFeedResponse {
  trending: SearchItem[];
  latestAiring: SearchItem[];
}

export async function getHomeFeed(): Promise<HomeFeedResponse> {
  const res = await fetch(`${API_BASE}/anime/home`);
  if (!res.ok) throw new Error(`Home feed fetch failed: ${res.statusText}`);
  return res.json();
}

export async function searchAnime(query: string, page = 1): Promise<SearchResponse> {
  const res = await fetch(`${API_BASE}/anime/search?q=${encodeURIComponent(query)}&page=${page}`);
  if (!res.ok) throw new Error(`Search failed: ${res.statusText}`);
  return res.json();
}

export async function getTrendingAnime(page = 1, sort = 'trending'): Promise<SearchResponse> {
  const res = await fetch(`${API_BASE}/anime/trending?page=${page}&sort=${sort}`);
  if (!res.ok) throw new Error(`Trending fetch failed: ${res.statusText}`);
  return res.json();
}

export async function getAnimeDetail(slug: string): Promise<AnimeSeries> {
  const res = await fetch(`${API_BASE}/anime/detail/${encodeURIComponent(slug)}`);
  if (!res.ok) throw new Error(`Detail fetch failed: ${res.statusText}`);
  const json = await res.json();
  const raw = json.data;

  const episodes: Episode[] = (raw.episodes || []).map((ep: any) => ({
    id: ep.id || `${slug}-ep-${ep.number}`,
    animeSlug: slug,
    animeTitle: raw.display_title || raw.english || raw.romaji,
    number: ep.number,
    seasonNumber: ep.season_number || 1,
    title: ep.title || `Episode ${ep.number}`,
    thumbnail: ep.thumbnail || raw.poster || 'https://images.unsplash.com/photo-1578632767115-351597cf2477?w=800&q=80',
    duration: '24:00',
    durationSeconds: 1440,
    airDate: ep.air_date,
    rating: ep.rating,
    description: ep.description || `Episode ${ep.number} of ${raw.display_title || raw.english || raw.romaji}`,
    sources: [],
    subtitles: [],
  }));

  return {
    slug: raw.slug,
    romajiTitle: raw.romaji,
    englishTitle: raw.english,
    nativeTitle: raw.native,
    displayTitle: raw.display_title || raw.english || raw.romaji,
    poster: raw.poster || 'https://images.unsplash.com/photo-1578632767115-351597cf2477?w=800&q=80',
    banner: raw.banner,
    synopsis: raw.synopsis || 'No synopsis available.',
    genres: raw.genres || [],
    format: raw.format || 'TV',
    status: raw.status || 'Finished',
    releaseYear: raw.year,
    score: raw.score,
    studios: [],
    totalEpisodes: raw.total_episodes || episodes.length,
    episodes: episodes,
    relations: [
      { slug: `${raw.slug}-s1`, title: `${raw.display_title || raw.romaji} (Prequel)`, format: 'TV', relationType: 'prequel', year: raw.year ? raw.year - 1 : 2023 },
      { slug: raw.slug, title: `${raw.display_title || raw.romaji} (Current)`, format: 'TV', relationType: 'sequel', year: raw.year || 2024 },
      { slug: `${raw.slug}-movie`, title: `${raw.display_title || raw.romaji}: The Movie`, format: 'Movie', relationType: 'movie', year: raw.year ? raw.year + 1 : 2025 },
    ],
  };
}

export interface StreamResolutionResult {
  slug: string;
  episode: number;
  lang: string;
  hasMore?: boolean;
  intro?: { start: number; end: number };
  outro?: { start: number; end: number };
  sources: Array<{
    providerId: string;
    serverName: string;
    quality: string;
    url: string;
    proxyUrl: string;
    directUrl: string;
    isM3u8: boolean;
    streamType: string;
  }>;
  subtitles: Array<{
    label: string;
    file: string;
    proxyUrl?: string;
    directUrl?: string;
    lang: string;
    default?: boolean;
    kind?: string;
  }>;
  thumbnails?: string;
}

export async function fetchLiveEpisodeStream(
  slug: string,
  episodeNumber: number,
  lang: 'sub' | 'dub' = 'sub',
  waitForAll = false
): Promise<StreamResolutionResult> {
  const waitParam = waitForAll ? '&wait_for_all=true' : '';
  const res = await fetch(`${API_BASE}/anime/stream/${encodeURIComponent(slug)}/${episodeNumber}?lang=${lang}${waitParam}`);
  if (!res.ok) throw new Error(`Stream fetch failed: ${res.statusText}`);
  return res.json();
}

// Convert SearchItem into Video item
export function searchItemToVideo(item: SearchItem, epNum = 1): Video {
  return {
    id: Math.abs(item.slug.split('').reduce((acc, char) => (acc << 5) - acc + char.charCodeAt(0), 0)),
    slug: item.slug,
    animeSlug: item.slug,
    animeTitle: item.display_title || item.english || item.romaji,
    title: `${item.display_title || item.english || item.romaji} - Episode ${epNum}`,
    channel: item.display_title || item.english || item.romaji,
    channelAvatar: item.poster || 'https://images.unsplash.com/photo-1578632767115-351597cf2477?w=800&q=80',
    subscribers: `${(item.score ? (item.score * 100).toFixed(0) : '850')}K`,
    views: `${((item.score || 8.0) * 150).toFixed(0)}K`,
    viewsCount: Math.round((item.score || 8.0) * 150000),
    time: item.status || 'Finished',
    duration: '24:00',
    ep: epNum,
    tags: ['SUB', '1080p'],
    thumbnail: item.poster || 'https://images.unsplash.com/photo-1578632767115-351597cf2477?w=800&q=80',
    videoUrl: '', // Will be fetched live on-demand when clicked
    category: item.genres?.[0] || 'Anime',
    description: `Watch ${item.display_title || item.english || item.romaji} Episode ${epNum} in 1080p with Japanese audio and English subtitles.`,
    likes: Math.round((item.score || 8.0) * 10000),
    dislikes: 120,
    isLiked: false,
    isDisliked: false,
    isSubscribed: false,
    isSaved: false,
    comments: [],
  };
}

// Local Storage Watch Progress
const PROGRESS_KEY = 'anitube_watch_progress';

export function saveWatchProgress(progress: WatchProgress) {
  try {
    const existing = getStoredWatchProgress();
    const key = `${progress.animeSlug}_${progress.episodeNumber}`;
    existing[key] = progress;
    localStorage.setItem(PROGRESS_KEY, JSON.stringify(existing));
  } catch (e) {
    console.error('Failed to save watch progress', e);
  }
}

export function getStoredWatchProgress(): Record<string, WatchProgress> {
  try {
    const raw = localStorage.getItem(PROGRESS_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

export function getEpisodeProgress(animeSlug: string, episodeNumber: number): WatchProgress | null {
  const all = getStoredWatchProgress();
  return all[`${animeSlug}_${episodeNumber}`] || null;
}
