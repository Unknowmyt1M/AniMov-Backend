import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { 
  Play, 
  Bookmark, 
  Check, 
  Share2, 
  Star, 
  ArrowLeft, 
  Calendar, 
  ListVideo, 
  Search,
  GitBranch,
  ChevronRight,
  Loader2
} from 'lucide-react';
import { AnimeSeries, Episode } from '../types';
import { getAnimeDetail } from '../services/api';

interface AnimeDetailPageProps {
  onShowToast: (msg: string) => void;
}

export const AnimeDetailPage: React.FC<AnimeDetailPageProps> = ({ onShowToast }) => {
  const { slug } = useParams<{ slug: string }>();
  const navigate = useNavigate();
  const currentSlug = slug || 'uFxerMrwx6';

  const [series, setSeries] = useState<AnimeSeries | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [episodeSearch, setEpisodeSearch] = useState('');
  const [watchlistStatus, setWatchlistStatus] = useState<'Watching' | 'Plan to Watch' | 'Completed' | null>(null);

  useEffect(() => {
    let isCancelled = false;
    const loadDetail = async () => {
      setIsLoading(true);
      try {
        const data = await getAnimeDetail(currentSlug);
        if (isCancelled) return;
        setSeries(data);
      } catch (err) {
        console.warn('Failed to fetch anime detail:', err);
      } finally {
        if (!isCancelled) setIsLoading(false);
      }
    };

    loadDetail();
    return () => { isCancelled = true; };
  }, [currentSlug]);

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#0f0f0f] flex flex-col items-center justify-center gap-3 text-white">
        <Loader2 className="w-10 h-10 text-fuchsia-500 animate-spin" />
        <p className="text-sm font-bold tracking-wide">Loading Anime Showcase from AniMov...</p>
      </div>
    );
  }

  if (!series) {
    return (
      <div className="min-h-screen bg-[#0f0f0f] flex flex-col items-center justify-center gap-4 text-white p-6">
        <h2 className="text-2xl font-bold">Anime Series Not Found</h2>
        <Link to="/" className="px-5 py-2.5 bg-fuchsia-500 rounded-full font-bold text-xs">
          Return to Home Feed
        </Link>
      </div>
    );
  }

  const filteredEpisodes = series.episodes.filter(ep => {
    return episodeSearch.trim() === '' || 
      ep.number.toString() === episodeSearch.trim() ||
      ep.title.toLowerCase().includes(episodeSearch.toLowerCase());
  });

  const handleShare = () => {
    navigator.clipboard?.writeText(window.location.href);
    onShowToast(`Copied link for ${series.displayTitle}!`);
  };

  const handleWatchlistChange = (status: 'Watching' | 'Plan to Watch' | 'Completed') => {
    setWatchlistStatus(status);
    onShowToast(`Marked as ${status}`);
  };

  return (
    <div className="min-h-screen bg-[#0f0f0f] text-white pb-20">
      {/* Top Breadcrumb Bar */}
      <div className="max-w-[1700px] mx-auto px-4 sm:px-6 py-4 flex items-center justify-between">
        <button
          onClick={() => navigate('/')}
          className="flex items-center gap-2 px-3 py-1.5 rounded-xl bg-white/5 hover:bg-white/10 text-sm font-semibold text-gray-300 hover:text-white transition-all border border-white/10"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Home Feed</span>
        </button>

        <button
          onClick={handleShare}
          className="p-2 rounded-xl bg-white/5 hover:bg-white/10 text-gray-300 hover:text-white transition-colors border border-white/10"
          title="Share"
        >
          <Share2 className="w-4 h-4" />
        </button>
      </div>

      {/* Cinematic Banner Header */}
      <div className="relative w-full max-w-[1700px] mx-auto rounded-3xl overflow-hidden border border-white/10 bg-[#141414] mb-8">
        <div className="absolute inset-0">
          <img
            src={series.banner || series.poster}
            alt={series.displayTitle}
            className="w-full h-full object-cover filter blur-md opacity-30 scale-105"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-[#0f0f0f] via-[#0f0f0f]/80 to-transparent" />
          <div className="absolute inset-0 bg-gradient-to-r from-[#0f0f0f] via-transparent to-transparent" />
        </div>

        <div className="relative z-10 p-6 sm:p-10 flex flex-col md:flex-row gap-8 items-center md:items-end">
          {/* Poster */}
          <div className="relative w-48 sm:w-60 aspect-[2/3] rounded-2xl overflow-hidden shadow-2xl border border-white/20 flex-shrink-0 group">
            <img
              src={series.poster}
              alt={series.displayTitle}
              className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
            />
            {series.score && (
              <div className="absolute top-3 right-3 px-2 py-1 rounded-lg bg-black/80 backdrop-blur-md border border-yellow-500/40 flex items-center gap-1 text-xs font-black text-yellow-400">
                <Star className="w-3.5 h-3.5 fill-current" />
                <span>{series.score.toFixed(1)}</span>
              </div>
            )}
          </div>

          {/* Details */}
          <div className="flex-1 flex flex-col gap-4 text-center md:text-left">
            <div className="flex flex-wrap items-center justify-center md:justify-start gap-2">
              <span className="px-2.5 py-0.5 rounded-full text-xs font-black tracking-wide bg-fuchsia-500/20 text-fuchsia-400 border border-fuchsia-500/40">
                {series.format}
              </span>
              <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-cyan-500/20 text-cyan-400 border border-cyan-500/40">
                {series.status}
              </span>
              {series.releaseYear && (
                <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-white/10 text-gray-300 border border-white/10 flex items-center gap-1">
                  <Calendar className="w-3 h-3" />
                  <span>{series.releaseYear}</span>
                </span>
              )}
            </div>

            <div>
              <h1 className="text-3xl sm:text-5xl font-black text-white tracking-tight leading-tight">
                {series.displayTitle}
              </h1>
              {series.romajiTitle && series.romajiTitle !== series.displayTitle && (
                <p className="text-sm sm:text-base text-gray-400 font-medium italic mt-1">
                  {series.romajiTitle}
                </p>
              )}
            </div>

            {/* Genres */}
            <div className="flex flex-wrap items-center justify-center md:justify-start gap-1.5">
              {series.genres.map((g, idx) => (
                <span
                  key={idx}
                  className="px-2.5 py-1 rounded-lg bg-white/5 hover:bg-white/10 text-xs text-gray-300 border border-white/5 font-medium transition-colors"
                >
                  {g}
                </span>
              ))}
            </div>

            {/* Synopsis */}
            <p className="text-sm sm:text-base text-gray-300 line-clamp-3 max-w-3xl leading-relaxed">
              {series.synopsis}
            </p>

            {/* Actions */}
            <div className="flex flex-wrap items-center justify-center md:justify-start gap-3 pt-2">
              <button
                onClick={() => navigate(`/watch/${series.slug}/1`)}
                className="flex items-center gap-2 px-6 py-3 rounded-full bg-gradient-to-r from-fuchsia-600 to-pink-600 hover:from-fuchsia-500 hover:to-pink-500 text-white font-bold text-sm sm:text-base transition-all shadow-[0_0_25px_rgba(217,70,239,0.5)] hover:scale-105 active:scale-95"
              >
                <Play className="w-5 h-5 fill-current" />
                <span>Watch Episode 1</span>
              </button>

              <div className="flex items-center gap-1 p-1 bg-white/10 border border-white/15 rounded-full">
                {(['Watching', 'Plan to Watch', 'Completed'] as const).map(st => (
                  <button
                    key={st}
                    onClick={() => handleWatchlistChange(st)}
                    className={`px-3 py-1.5 rounded-full text-xs font-bold transition-all ${
                      watchlistStatus === st
                        ? 'bg-white text-black shadow-md'
                        : 'text-gray-300 hover:text-white hover:bg-white/5'
                    }`}
                  >
                    {watchlistStatus === st && <Check className="w-3 h-3 inline mr-1" />}
                    {st}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Main Body */}
      <div className="max-w-[1700px] mx-auto px-4 sm:px-6 flex flex-col gap-10">
        {/* Watch Order Roadmap */}
        <div className="bg-[#141414] rounded-2xl p-6 border border-white/10">
          <div className="flex items-center gap-2 mb-4">
            <GitBranch className="w-5 h-5 text-cyan-400" />
            <h2 className="text-lg font-bold text-white tracking-tight">
              Franchise Chronological Watch Order
            </h2>
          </div>

          <div className="flex items-center gap-3 overflow-x-auto pb-2 custom-scrollbar">
            {(series.relations && series.relations.length > 0 ? series.relations : [
              { slug: `${series.slug}-s1`, title: `${series.displayTitle} Season 1`, format: 'TV' as const, relationType: 'prequel' as const, year: 2022 },
              { slug: series.slug, title: `${series.displayTitle} (Current)`, format: 'TV' as const, relationType: 'sequel' as const, year: 2024 },
              { slug: `${series.slug}-movie`, title: `${series.displayTitle}: The Movie`, format: 'Movie' as const, relationType: 'movie' as const, year: 2025 },
            ]).map((item, index) => (
              <React.Fragment key={item.slug || index}>
                <div
                  onClick={() => navigate(`/anime/${item.slug}`)}
                  className={`flex-shrink-0 w-64 p-3.5 rounded-xl border transition-all cursor-pointer ${
                    item.slug === series.slug
                      ? 'bg-fuchsia-500/15 border-fuchsia-500/50 shadow-lg'
                      : 'bg-white/5 hover:bg-white/10 border-white/10'
                  }`}
                >
                  <div className="flex items-center justify-between text-[11px] font-bold text-gray-400 uppercase tracking-wider mb-1">
                    <span className="text-cyan-400">{item.relationType}</span>
                    <span>{item.year || '2024'}</span>
                  </div>
                  <h4 className="text-sm font-bold text-white truncate">
                    {item.title}
                  </h4>
                  <div className="mt-2 flex items-center justify-between text-xs text-gray-400">
                    <span className="px-1.5 py-0.5 rounded bg-black/60 text-[10px] font-semibold text-gray-300">
                      {item.format}
                    </span>
                    {item.slug === series.slug && (
                      <span className="text-fuchsia-400 font-bold text-[11px]">
                        Current Series
                      </span>
                    )}
                  </div>
                </div>

                {index < (series.relations?.length || 3) - 1 && (
                  <ChevronRight className="w-5 h-5 text-gray-600 flex-shrink-0" />
                )}
              </React.Fragment>
            ))}
          </div>
        </div>

        {/* Episodes Section */}
        <div>
          <div className="flex flex-col sm:row items-start sm:items-center justify-between gap-4 mb-6 pb-4 border-b border-white/10">
            <div className="flex items-center gap-3">
              <ListVideo className="w-6 h-6 text-fuchsia-400" />
              <h2 className="text-2xl font-bold text-white">
                Episodes ({filteredEpisodes.length})
              </h2>
            </div>

            <div className="relative w-full sm:w-72">
              <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
              <input
                type="text"
                placeholder="Find episode (e.g. 12)..."
                value={episodeSearch}
                onChange={(e) => setEpisodeSearch(e.target.value)}
                className="w-full bg-[#181818] border border-white/10 rounded-full pl-9 pr-4 py-1.5 text-xs text-white focus:outline-none focus:border-fuchsia-500 transition-colors"
              />
            </div>
          </div>

          {/* Episode Cards Grid (Clicking navigates to /watch/:slug/:ep) */}
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
            {filteredEpisodes.map((ep) => (
              <div
                key={ep.id}
                onClick={() => navigate(`/watch/${series.slug}/${ep.number}`)}
                className="group flex flex-col bg-[#141414] hover:bg-[#1c1c1c] rounded-xl overflow-hidden border border-white/5 hover:border-white/15 transition-all cursor-pointer shadow-md select-none"
              >
                <div className="relative aspect-video overflow-hidden bg-gray-800">
                  <img
                    src={ep.thumbnail || series.poster}
                    alt={ep.title}
                    className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                    loading="lazy"
                  />
                  <div className="absolute inset-0 bg-black/20 group-hover:bg-transparent transition-colors" />

                  <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity">
                    <div className="w-10 h-10 rounded-full bg-fuchsia-500 flex items-center justify-center shadow-lg">
                      <Play className="w-5 h-5 text-white fill-current ml-0.5" />
                    </div>
                  </div>

                  <span className="absolute top-2 left-2 px-2 py-0.5 rounded bg-black/80 backdrop-blur-sm text-white text-xs font-black">
                    EP {ep.number}
                  </span>

                  <span className="absolute bottom-2 right-2 px-1.5 py-0.5 rounded bg-black/80 text-white text-[10px] font-semibold">
                    {ep.duration}
                  </span>
                </div>

                <div className="p-3 flex flex-col gap-1">
                  <h4 className="text-sm font-semibold text-white group-hover:text-fuchsia-400 transition-colors line-clamp-1">
                    {ep.title}
                  </h4>
                  <p className="text-xs text-gray-400 line-clamp-2 leading-relaxed">
                    {ep.description || `Episode ${ep.number} of ${series.displayTitle}`}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};
