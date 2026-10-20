import React from 'react';
import { VideoCard } from './VideoCard';
import { Video } from '../types';
import { Film, RotateCcw } from 'lucide-react';

interface VideoGridProps {
  videos: Video[];
  onPlay: (video: Video) => void;
  onToggleSave: (video: Video, e: React.MouseEvent) => void;
  onOpenSeries?: (slug: string, title: string) => void;
  savedVideoIds: Set<number>;
  onResetFilters?: () => void;
}

export const VideoGrid: React.FC<VideoGridProps> = ({
  videos,
  onPlay,
  onToggleSave,
  onOpenSeries,
  savedVideoIds,
  onResetFilters,
}) => {
  if (videos.length === 0) {
    return (
      <div className="py-16 text-center flex flex-col items-center justify-center bg-white/5 rounded-2xl border border-white/10 my-6 p-8">
        <Film className="w-12 h-12 text-gray-500 mb-3" />
        <h3 className="text-xl font-bold text-white mb-1">No anime found</h3>
        <p className="text-sm text-gray-400 max-w-sm mb-4">
          We couldn't find any videos matching your filter or search query.
        </p>
        {onResetFilters && (
          <button
            onClick={onResetFilters}
            className="flex items-center gap-2 px-5 py-2.5 bg-fuchsia-500 hover:bg-fuchsia-600 text-white rounded-full font-semibold text-sm transition-all shadow-md active:scale-95"
          >
            <RotateCcw className="w-4 h-4" /> Reset Filters
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-x-4 gap-y-8">
      {videos.map((video) => (
        <VideoCard
          key={video.id}
          video={video}
          onPlay={onPlay}
          onToggleSave={onToggleSave}
          onOpenSeries={onOpenSeries}
          isSaved={savedVideoIds.has(video.id)}
        />
      ))}
    </div>
  );
};
