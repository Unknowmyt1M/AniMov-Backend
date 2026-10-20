import React, { useState, useRef, useEffect } from 'react';
import { 
  X, 
  Play, 
  Pause, 
  Volume2, 
  VolumeX, 
  ThumbsUp, 
  Share2, 
  ChevronUp, 
  ChevronDown, 
  Music,
  ExternalLink
} from 'lucide-react';
import { Short } from '../types';

interface ShortsPlayerModalProps {
  currentShort: Short | null;
  onClose: () => void;
  allShorts: Short[];
  onSelectShort: (short: Short) => void;
  onShowToast: (message: string) => void;
  onWatchEpisode?: (short: Short) => void;
}

export const ShortsPlayerModal: React.FC<ShortsPlayerModalProps> = ({
  currentShort,
  onClose,
  allShorts,
  onSelectShort,
  onShowToast,
  onWatchEpisode,
}) => {
  if (!currentShort) return null;

  const videoRef = useRef<HTMLVideoElement>(null);
  const [isPlaying, setIsPlaying] = useState(true);
  const [isMuted, setIsMuted] = useState(false);
  const [likes, setLikes] = useState(currentShort.likes);
  const [isLiked, setIsLiked] = useState(currentShort.isLiked || false);

  const currentIndex = allShorts.findIndex(s => s.id === currentShort.id);

  useEffect(() => {
    setLikes(currentShort.likes);
    setIsLiked(currentShort.isLiked || false);
    setIsPlaying(true);
    if (videoRef.current) {
      videoRef.current.currentTime = 0;
      videoRef.current.play().catch(() => setIsPlaying(false));
    }
  }, [currentShort]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
      if (e.key === ' ' || e.key === 'k') {
        e.preventDefault();
        togglePlay();
      }
      if (e.key === 'ArrowUp' || e.key === 'k') goToPrev();
      if (e.key === 'ArrowDown' || e.key === 'j') goToNext();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [currentIndex, isPlaying]);

  const togglePlay = () => {
    if (!videoRef.current) return;
    if (isPlaying) {
      videoRef.current.pause();
      setIsPlaying(false);
    } else {
      videoRef.current.play();
      setIsPlaying(true);
    }
  };

  const toggleMute = () => {
    if (!videoRef.current) return;
    const nextMuted = !isMuted;
    setIsMuted(nextMuted);
    videoRef.current.muted = nextMuted;
  };

  const handleLike = () => {
    if (isLiked) {
      setIsLiked(false);
      setLikes(prev => prev - 1);
    } else {
      setIsLiked(true);
      setLikes(prev => prev + 1);
      onShowToast('Added to Liked Shorts');
    }
  };

  const handleShare = () => {
    navigator.clipboard?.writeText(window.location.href);
    onShowToast('Short link copied to clipboard!');
  };

  const goToNext = () => {
    if (currentIndex < allShorts.length - 1) {
      onSelectShort(allShorts[currentIndex + 1]);
    } else {
      onSelectShort(allShorts[0]);
    }
  };

  const goToPrev = () => {
    if (currentIndex > 0) {
      onSelectShort(allShorts[currentIndex - 1]);
    } else {
      onSelectShort(allShorts[allShorts.length - 1]);
    }
  };

  const handleWatchEpisodeClick = () => {
    if (onWatchEpisode) {
      onWatchEpisode(currentShort);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/90 backdrop-blur-md flex items-center justify-center p-2 sm:p-4">
      {/* Close button */}
      <button
        onClick={onClose}
        className="absolute top-4 right-4 sm:top-6 sm:right-6 p-2 rounded-full bg-white/10 hover:bg-white/20 text-white z-50 transition-colors"
      >
        <X className="w-6 h-6" />
      </button>

      {/* Main Shorts Container */}
      <div className="relative flex items-center gap-4 sm:gap-6 max-h-[92vh]">
        {/* 9:16 Video Frame */}
        <div className="relative w-[340px] sm:w-[400px] h-[720px] max-h-[88vh] rounded-3xl overflow-hidden bg-black shadow-2xl border border-white/10 flex items-center justify-center">
          <video
            ref={videoRef}
            src={currentShort.videoUrl}
            loop
            playsInline
            autoPlay
            onClick={togglePlay}
            className="w-full h-full object-cover cursor-pointer"
          />

          {/* Sound toggle button */}
          <button
            onClick={toggleMute}
            className="absolute top-4 right-4 p-2 bg-black/50 hover:bg-black/70 rounded-full text-white backdrop-blur-md transition-colors z-20"
          >
            {isMuted ? <VolumeX className="w-5 h-5 text-red-400" /> : <Volume2 className="w-5 h-5" />}
          </button>

          {/* Pause overlay icon */}
          {!isPlaying && (
            <div
              onClick={togglePlay}
              className="absolute inset-0 flex items-center justify-center bg-black/30 backdrop-blur-[2px] cursor-pointer z-10"
            >
              <div className="w-16 h-16 rounded-full bg-fuchsia-500/90 flex items-center justify-center text-white shadow-lg">
                <Play className="w-8 h-8 fill-white ml-1" />
              </div>
            </div>
          )}

          {/* Bottom Info Overlay */}
          <div className="absolute inset-x-0 bottom-0 p-5 bg-gradient-to-t from-black/95 via-black/60 to-transparent flex flex-col gap-2.5 z-20">
            {/* Channel info */}
            <div className="flex items-center gap-2.5">
              <img
                src={currentShort.channelAvatar}
                alt={currentShort.channel}
                className="w-9 h-9 rounded-full border border-white/20 object-cover"
              />
              <span className="font-bold text-white text-sm">
                @{currentShort.channel}
              </span>
              <button className="px-3 py-1 bg-white text-black hover:bg-gray-200 text-xs font-bold rounded-full ml-1 transition-colors">
                Follow
              </button>
            </div>

            {/* Title */}
            <p className="text-white text-sm font-semibold line-clamp-2 drop-shadow-md">
              {currentShort.title}
            </p>

            {/* Direct CTA: Watch Full Episode */}
            <div className="flex items-center justify-between pt-1">
              <button
                onClick={handleWatchEpisodeClick}
                className="flex items-center gap-1.5 px-4 py-2 rounded-full bg-gradient-to-r from-fuchsia-600 to-pink-600 hover:from-fuchsia-500 hover:to-pink-500 text-white font-black text-xs shadow-[0_0_15px_rgba(217,70,239,0.5)] transition-all hover:scale-105 active:scale-95"
              >
                <Play className="w-3.5 h-3.5 fill-current" />
                <span>Watch Full Episode</span>
              </button>

              <div className="flex items-center gap-1.5 text-[11px] text-gray-300 font-medium">
                <Music className="w-3.5 h-3.5 text-cyan-400" />
                <span className="truncate max-w-[120px]">OST / Clip</span>
              </div>
            </div>
          </div>
        </div>

        {/* Right Floating Action Column (Like, Share, Next, Prev) */}
        <div className="flex flex-col gap-4 items-center">
          {/* Previous Short */}
          <button
            onClick={goToPrev}
            className="p-3 bg-white/10 hover:bg-white/20 rounded-full text-white backdrop-blur-md border border-white/10 transition-transform active:scale-90"
            title="Previous Short (Up Arrow)"
          >
            <ChevronUp className="w-5 h-5" />
          </button>

          {/* Like */}
          <div className="flex flex-col items-center">
            <button
              onClick={handleLike}
              className={`p-3.5 rounded-full backdrop-blur-md border transition-all active:scale-90 ${
                isLiked
                  ? 'bg-fuchsia-500 text-white border-fuchsia-400 shadow-[0_0_15px_rgba(217,70,239,0.5)]'
                  : 'bg-white/10 hover:bg-white/20 text-white border-white/10'
              }`}
            >
              <ThumbsUp className={`w-5 h-5 ${isLiked ? 'fill-current' : ''}`} />
            </button>
            <span className="text-[11px] font-bold text-white mt-1">
              {likes >= 1000 ? `${(likes / 1000).toFixed(0)}K` : likes}
            </span>
          </div>

          {/* Share */}
          <div className="flex flex-col items-center">
            <button
              onClick={handleShare}
              className="p-3.5 bg-white/10 hover:bg-white/20 rounded-full text-white backdrop-blur-md border border-white/10 transition-transform active:scale-90"
            >
              <Share2 className="w-5 h-5" />
            </button>
            <span className="text-[11px] font-bold text-gray-300 mt-1">Share</span>
          </div>

          {/* Next Short */}
          <button
            onClick={goToNext}
            className="p-3 bg-white/10 hover:bg-white/20 rounded-full text-white backdrop-blur-md border border-white/10 transition-transform active:scale-90"
            title="Next Short (Down Arrow)"
          >
            <ChevronDown className="w-5 h-5" />
          </button>
        </div>
      </div>
    </div>
  );
};
