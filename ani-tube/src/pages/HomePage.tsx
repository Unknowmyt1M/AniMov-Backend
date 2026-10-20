import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Hero } from '../components/Hero';
import { CategoryPills } from '../components/CategoryPills';
import { VideoGrid } from '../components/VideoGrid';
import { ShortsSection } from '../components/ShortsSection';
import { Video, Short, WatchProgress } from '../types';
import { Sparkles, Bookmark, History as HistoryIcon, Flame, Play, Star, Clock, Loader2 } from 'lucide-react';

interface TrendingSeriesItem {
  slug: string;
  title: string;
  score: number;
  format: string;
  episodesCount: number;
  poster: string;
  studio: string;
}

interface HomePageProps {
  videos: Video[];
  displayedVideos: Video[];
  recommendedVideos: Video[];
  trendingAnimeSeries: TrendingSeriesItem[];
  heroVideo: Video;
  continueWatchingList: Array<{ video: Video; progress: WatchProgress }>;
  shorts: Short[];
  activeTab: string;
  selectedCategory: string;
  searchQuery: string;
  isLoadingFeed: boolean;
  savedVideoIds: Set<number>;
  onToggleSave: (video: Video, e?: React.MouseEvent) => void;
  onPlayShort: (short: Short) => void;
  setSelectedCategory: (cat: string) => void;
  resetAllFilters: () => void;
  onShowToast: (msg: string) => void;
}

export const HomePage: React.FC<HomePageProps> = ({
  videos: _videos,
  displayedVideos,
  recommendedVideos,
  trendingAnimeSeries,
  heroVideo,
  continueWatchingList,
  shorts,
  activeTab,
  selectedCategory,
  searchQuery,
  isLoadingFeed,
  savedVideoIds,
  onToggleSave,
  onPlayShort,
  setSelectedCategory,
  resetAllFilters,
}) => {
  const navigate = useNavigate();

  // Route to dedicated YouTube Watch Page on click
  const handlePlayVideo = (video: Video) => {
    const slug = video.animeSlug || video.channel.toLowerCase().replace(/\s+/g, '-');
    const ep = video.ep || 1;
    navigate(`/watch/${slug}/${ep}`);
  };

  // Route to dedicated Anime Series Showcase Page on click
  const handleOpenSeries = (slug: string) => {
    navigate(`/anime/${slug}`);
  };

  return (
    <div className="max-w-[1800px] mx-auto pb-16">
      {/* Show Hero banner on Home tab when there is no search query */}
      {activeTab === 'Home' && !searchQuery && (
        <Hero
          heroVideo={heroVideo}
          onPlay={handlePlayVideo}
          onToggleSave={onToggleSave}
          onOpenInfo={() => handleOpenSeries(heroVideo.animeSlug || heroVideo.slug || 'uFxerMrwx6')}
          isSaved={savedVideoIds.has(heroVideo.id)}
        />
      )}

      {/* Continue Watching Row (YouTube Style Resume) */}
      {activeTab === 'Home' && !searchQuery && continueWatchingList.length > 0 && (
        <div className="mb-8 p-4 rounded-2xl bg-gradient-to-r from-fuchsia-950/20 via-black/40 to-transparent border border-fuchsia-500/20">
          <div className="flex items-center gap-2 mb-4">
            <Clock className="w-5 h-5 text-cyan-400" />
            <h2 className="text-xl font-black text-white tracking-tight">
              Continue Watching
            </h2>
          </div>

          <div className="flex items-center gap-4 overflow-x-auto pb-2 custom-scrollbar">
            {continueWatchingList.map(({ video: v, progress }) => {
              const percent = Math.min(100, Math.round((progress.currentTime / progress.duration) * 100));
              return (
                <div
                  key={`cw-${v.id}`}
                  onClick={() => handlePlayVideo(v)}
                  className="flex-shrink-0 w-64 group cursor-pointer bg-[#141414] rounded-xl overflow-hidden border border-white/5 hover:border-fuchsia-500/40 transition-all select-none shadow-md"
                >
                  <div className="relative aspect-video bg-gray-800">
                    <img
                      src={v.thumbnail}
                      alt={v.title}
                      className="w-full h-full object-cover group-hover:scale-105 transition-transform"
                    />
                    <div className="absolute inset-0 bg-black/30 group-hover:bg-transparent transition-colors flex items-center justify-center">
                      <div className="w-9 h-9 rounded-full bg-fuchsia-500 flex items-center justify-center shadow-lg">
                        <Play className="w-4 h-4 text-white fill-current ml-0.5" />
                      </div>
                    </div>
                    <span className="absolute top-2 left-2 px-1.5 py-0.5 rounded bg-black/80 text-[10px] font-bold text-white">
                      EP {progress.episodeNumber}
                    </span>
                    <div className="absolute bottom-0 inset-x-0 h-1.5 bg-white/20">
                      <div className="h-full bg-fuchsia-500" style={{ width: `${percent}%` }} />
                    </div>
                  </div>
                  <div className="p-2.5">
                    <h4 className="text-xs font-bold text-white truncate group-hover:text-fuchsia-400 transition-colors">
                      {v.title}
                    </h4>
                    <div className="flex items-center justify-between text-[11px] text-gray-400 mt-1">
                      <span>{percent}% watched</span>
                      <span className="text-cyan-400 font-semibold">Resume</span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Custom Tab Header when viewing Watch Later, History, etc. */}
      {activeTab !== 'Home' && (
        <div className="mb-6 flex items-center justify-between border-b border-white/10 pb-4">
          <div className="flex items-center gap-3">
            {activeTab === 'Trending' && <Flame className="w-7 h-7 text-fuchsia-500" />}
            {activeTab === 'Watch Later' && <Bookmark className="w-7 h-7 text-fuchsia-500" />}
            {activeTab === 'Favorites' && <Bookmark className="w-7 h-7 text-fuchsia-500" />}
            {activeTab === 'History' && <HistoryIcon className="w-7 h-7 text-cyan-400" />}
            <div>
              <h1 className="text-2xl sm:text-3xl font-extrabold text-white">
                {activeTab}
              </h1>
              <p className="text-xs text-gray-400 mt-0.5">
                {displayedVideos.length} anime videos in this collection
              </p>
            </div>
          </div>

          <button
            onClick={resetAllFilters}
            className="text-xs text-fuchsia-400 hover:text-white font-semibold transition-colors"
          >
            Back to Home
          </button>
        </div>
      )}

      {/* Category Pills (Home or Explore) */}
      {(activeTab === 'Home' || activeTab === 'Explore') && (
        <CategoryPills
          selectedCategory={selectedCategory}
          onSelectCategory={setSelectedCategory}
        />
      )}

      {/* DUAL HYBRID SECTION 1: Trending Anime Series Row (Links to /anime/:slug) */}
      {activeTab === 'Home' && !searchQuery && selectedCategory === 'All' && (
        <div className="mb-10">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-2">
              <Flame className="w-6 h-6 text-fuchsia-500" />
              <h2 className="text-xl sm:text-2xl font-black text-white tracking-tight">
                Trending Anime Series
              </h2>
            </div>
            <span className="text-xs text-gray-400">Click to explore seasons & episodes</span>
          </div>

          <div className="flex items-center gap-4 overflow-x-auto pb-4 custom-scrollbar">
            {trendingAnimeSeries.map((series) => (
              <div
                key={series.slug}
                onClick={() => handleOpenSeries(series.slug)}
                className="flex-shrink-0 w-44 sm:w-52 group cursor-pointer flex flex-col gap-2 select-none"
              >
                <div className="relative aspect-[2/3] rounded-2xl overflow-hidden shadow-lg border border-white/10 bg-gray-800">
                  <img
                    src={series.poster}
                    alt={series.title}
                    className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                    loading="lazy"
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
                  <div className="absolute top-2 right-2 px-2 py-0.5 rounded-lg bg-black/80 backdrop-blur-md border border-yellow-500/40 flex items-center gap-1 text-[11px] font-black text-yellow-400">
                    <Star className="w-3 h-3 fill-current" />
                    <span>{series.score}</span>
                  </div>
                  <span className="absolute bottom-2 left-2 px-2 py-0.5 rounded bg-black/80 text-[10px] font-bold text-white">
                    {series.episodesCount} EPS
                  </span>
                </div>
                <h4 className="text-xs sm:text-sm font-bold text-white truncate group-hover:text-fuchsia-400 transition-colors">
                  {series.title}
                </h4>
                <div className="flex items-center justify-between text-[11px] text-gray-400">
                  <span>{series.studio}</span>
                  <span className="text-cyan-400 font-semibold">{series.format}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* DUAL HYBRID SECTION 2: Latest Airing Episodes (YouTube Grid - Direct Play) */}
      <div className="mb-10">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-2">
            <Play className="w-6 h-6 text-fuchsia-500 fill-current" />
            <h2 className="text-xl sm:text-2xl font-black text-white tracking-tight">
              {searchQuery ? `Search Results for "${searchQuery}"` : 'Latest Released Episodes'}
            </h2>
          </div>
          {isLoadingFeed && (
            <div className="flex items-center gap-2 text-xs text-fuchsia-400">
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>Syncing with AniMov Backend...</span>
            </div>
          )}
        </div>

        <VideoGrid
          videos={displayedVideos}
          onPlay={handlePlayVideo}
          onToggleSave={onToggleSave}
          onOpenSeries={handleOpenSeries}
          savedVideoIds={savedVideoIds}
          onResetFilters={resetAllFilters}
        />
      </div>

      {/* Trending Shorts Section (Show on Home or Trending) */}
      {(activeTab === 'Home' || activeTab === 'Trending') && !searchQuery && (
        <ShortsSection
          shorts={shorts}
          onPlayShort={onPlayShort}
        />
      )}

      {/* Recommended For You Section */}
      {activeTab === 'Home' && !searchQuery && (
        <div className="mt-8">
          <div className="flex items-center gap-2 mb-6">
            <Sparkles className="w-6 h-6 text-cyan-400" />
            <h2 className="text-2xl font-bold text-white tracking-tight">
              Recommended for you
            </h2>
          </div>
          <VideoGrid
            videos={recommendedVideos}
            onPlay={handlePlayVideo}
            onToggleSave={onToggleSave}
            onOpenSeries={handleOpenSeries}
            savedVideoIds={savedVideoIds}
            onResetFilters={resetAllFilters}
          />
        </div>
      )}
    </div>
  );
};
