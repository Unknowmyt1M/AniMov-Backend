export interface Comment {
  id: string;
  author: string;
  avatar: string;
  text: string;
  time: string;
  likes: number;
  isLiked?: boolean;
  isSpoiler?: boolean;
}

export interface StreamSource {
  providerId: string;       // e.g. 'koto', 'pam', 'wave', 'ken', 'megg'
  serverName: string;       // e.g. 'Vidplay', 'MegaPlay', 'Wave', 'Server 1'
  quality: string;          // '1080p' | '720p' | 'auto'
  url: string;              // .m3u8 or mp4
  isM3u8: boolean;
  streamType: 'sub' | 'dub';
}

export interface SubtitleTrack {
  label: string;            // 'English', 'Spanish', etc.
  file: string;             // .vtt url
  lang: string;
  isDefault?: boolean;
}

export interface Episode {
  id: string;
  animeSlug: string;
  animeTitle: string;
  number: number;
  seasonNumber: number;
  title: string;
  thumbnail: string;
  duration: string;
  durationSeconds: number;
  airDate?: string;
  rating?: number;
  description?: string;
  introStart?: number;      // Seconds timestamp
  introEnd?: number;
  outroStart?: number;
  outroEnd?: number;
  sources: StreamSource[];
  subtitles: SubtitleTrack[];
}

export interface AnimeRelation {
  slug: string;
  title: string;
  format: 'TV' | 'Movie' | 'OVA' | 'Special';
  relationType: 'prequel' | 'sequel' | 'movie' | 'side_story';
  year?: number;
  poster?: string;
}

export interface AnimeSeries {
  slug: string;
  romajiTitle: string;
  englishTitle?: string;
  nativeTitle?: string;
  displayTitle: string;
  poster: string;
  banner?: string;
  synopsis: string;
  genres: string[];
  format: 'TV' | 'Movie' | 'OVA' | 'Special';
  status: 'Airing' | 'Completed' | 'Finished' | 'Upcoming';
  releaseYear?: number;
  score?: number;
  studios: string[];
  totalEpisodes: number;
  episodes: Episode[];
  relations?: AnimeRelation[];
}

// Retaining & extending Video interface for backward compatibility across current components
export interface Video {
  id: number;
  slug?: string;
  animeSlug?: string;
  animeTitle?: string;
  title: string;
  channel: string;
  channelAvatar: string;
  subscribers: string;
  views: string;
  viewsCount: number;
  time: string;
  duration: string;
  durationSeconds?: number;
  ep: number | null;
  seasonNumber?: number;
  tags: string[];
  thumbnail: string;
  videoUrl: string;
  category: string;
  description: string;
  likes: number;
  dislikes: number;
  isLiked?: boolean;
  isDisliked?: boolean;
  isSubscribed?: boolean;
  isSaved?: boolean;
  comments: Comment[];
  // Anime specific stream extensions
  sources?: StreamSource[];
  subtitles?: SubtitleTrack[];
  introStart?: number;
  introEnd?: number;
  outroStart?: number;
  outroEnd?: number;
}

export interface Short {
  id: number;
  title: string;
  views: string;
  thumbnail: string;
  videoUrl: string;
  channel: string;
  channelAvatar: string;
  likes: number;
  isLiked?: boolean;
  episodeId?: string;
  animeSlug?: string;
  episodeNumber?: number;
}

export interface NotificationItem {
  id: string;
  title: string;
  message: string;
  time: string;
  unread: boolean;
  thumbnail?: string;
  type: 'episode' | 'amv' | 'announcement';
  animeSlug?: string;
  episodeNumber?: number;
}

export interface WatchProgress {
  animeSlug: string;
  episodeNumber: number;
  currentTime: number;
  duration: number;
  completed: boolean;
  lastWatchedAt: string;
}
