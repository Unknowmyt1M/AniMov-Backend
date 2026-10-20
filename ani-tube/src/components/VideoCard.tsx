import React from 'react';
import { Play, Bookmark, Check } from 'lucide-react';
import { Video } from '../types';
import { getEpisodeProgress } from '../services/api';

interface VideoCardProps {
  video: Video;
  onPlay: (video: Video) => void;
  onToggleSave?: (video: Video, e: React.MouseEvent) => void;
  onOpenSeries?: (slug: string, title: string) => void;
  isSaved?: boolean;
}

export const VideoCard: React.FC<VideoCardProps> = ({
  video,
  onPlay,
  onToggleSave,
  onOpenSeries,
  isSaved = false,
}) => {
  const slug = video.animeSlug || video.channel.toLowerCase().replace(/\s+/g, '-');
  const epNum = video.ep || 1;
  const progress = getEpisodeProgress(slug, epNum);

  const progressPercent = progress && progress.duration > 0
    ? Math.min(100, Math.round((progress.currentTime / progress.duration) * 100))
    : 0;

  const handleChannelClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (onOpenSeries) {
      onOpenSeries(slug, video.channel);
    }
  };

  return (
    <div
      onClick={() => onPlay(video)}
      className="flex flex-col gap-3 group cursor-pointer select-none"
    >
      {/* Thumbnail Container */}
      <div className="relative aspect-video rounded-xl overflow-hidden bg-gray-800 shadow-md">
        <img
          src={video.thumbnail}
          alt={video.title}
          className="w-full h-full object-cover transition-transform duration-300 group-hover:scale-105"
          loading="lazy"
        />

        {/* Overlays */}
        <div className="absolute inset-0 bg-black/20 group-hover:bg-transparent transition-colors" />
        <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />

        {/* Play Icon on Hover */}
        <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity scale-75 group-hover:scale-100 duration-300">
          <div className="w-12 h-12 bg-fuchsia-500/90 rounded-full flex items-center justify-center backdrop-blur-sm shadow-[0_0_20px_rgba(217,70,239,0.6)]">
            <Play className="w-6 h-6 text-white fill-white ml-0.5" />
          </div>
        </div>

        {/* Episode Badge */}
        <div className="absolute top-2 left-2 flex gap-1">
          {video.ep && (
            <span className="px-2 py-0.5 bg-black/80 backdrop-blur-md text-white text-[11px] font-black rounded border border-white/10 tracking-wider">
              EP {video.ep}
            </span>
          )}
        </div>

        {/* Tags (SUB / DUB / 4K / TRAILER) */}
        <div className="absolute top-2 right-2 flex gap-1 items-center">
          {video.tags.map((tag, i) => (
            <span
              key={i}
              className={`px-1.5 py-0.5 text-[10px] font-extrabold rounded ${
                tag === 'SUB'
                  ? 'bg-cyan-500/90 text-white'
                  : tag === 'DUB'
                  ? 'bg-fuchsia-500/90 text-white'
                  : 'bg-black/70 text-gray-200'
              }`}
            >
              {tag}
            </span>
          ))}

          {/* Quick Bookmark Button */}
          {onToggleSave && (
            <button
              onClick={(e) => onToggleSave(video, e)}
              className={`p-1 rounded bg-black/70 backdrop-blur-md transition-all hover:scale-110 ${
                isSaved ? 'text-fuchsia-400 bg-black/90' : 'text-gray-300 hover:text-white'
              }`}
              title={isSaved ? "Remove from Watchlist" : "Save to Watchlist"}
            >
              {isSaved ? <Check className="w-3.5 h-3.5" /> : <Bookmark className="w-3.5 h-3.5" />}
            </button>
          )}
        </div>

        {/* Duration */}
        <div className="absolute bottom-2 right-2 px-1.5 py-0.5 bg-black/80 text-white text-[11px] font-semibold rounded">
          {video.duration}
        </div>

        {/* Watch Progress Bar */}
        {progressPercent > 0 && (
          <div className="absolute bottom-0 inset-x-0 h-1 bg-white/20">
            <div
              className="h-full bg-fuchsia-500"
              style={{ width: `${progressPercent}%` }}
            />
          </div>
        )}
      </div>

      {/* Video Details */}
      <div className="flex gap-3 pr-2">
        <img
          src={video.channelAvatar}
          alt={video.channel}
          onClick={handleChannelClick}
          className="w-9 h-9 rounded-full object-cover mt-0.5 border border-white/10 flex-shrink-0 hover:ring-2 hover:ring-fuchsia-500 transition-all cursor-pointer"
          title={`View ${video.channel} page`}
        />
        <div className="flex flex-col min-w-0">
          <h3 className="text-white text-sm font-semibold line-clamp-2 leading-tight group-hover:text-fuchsia-400 transition-colors">
            {video.title}
          </h3>
          <span
            onClick={handleChannelClick}
            className="text-gray-400 text-xs mt-1 hover:text-cyan-400 transition-colors truncate font-medium cursor-pointer"
          >
            {video.channel}
          </span>
          <div className="text-gray-500 text-xs flex items-center gap-1 flex-wrap mt-0.5">
            <span>{video.views} views</span>
            <span className="w-1 h-1 bg-gray-600 rounded-full mx-1" />
            <span>{video.time}</span>
          </div>
        </div>
      </div>
    </div>
  );
};
