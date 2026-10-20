import React from 'react';
import { Play, Plus, Check, Info } from 'lucide-react';
import { Video } from '../types';

interface HeroProps {
  heroVideo: Video;
  onPlay: (video: Video) => void;
  onToggleSave: (video: Video) => void;
  onOpenInfo: () => void;
  isSaved: boolean;
}

export const Hero: React.FC<HeroProps> = ({
  heroVideo,
  onPlay,
  onToggleSave,
  onOpenInfo,
  isSaved
}) => {
  return (
    <div className="relative w-full h-[400px] sm:h-[500px] rounded-2xl overflow-hidden mb-8 group shadow-2xl">
      {/* Background Image with Fallback */}
      <div
        className="absolute inset-0 bg-cover bg-center transition-transform duration-700 group-hover:scale-105"
        style={{
          backgroundImage: "url(/images/hero-bg.png), url('https://images.unsplash.com/photo-1605806616949-1e87b487cb2a?w=1600&q=80')"
        }}
      />
      <div className="absolute inset-0 bg-gradient-to-t from-[#0f0f0f] via-[#0f0f0f]/50 to-transparent" />
      <div className="absolute inset-0 bg-gradient-to-r from-[#0f0f0f] via-[#0f0f0f]/80 to-transparent w-full sm:w-2/3" />

      {/* Content */}
      <div className="absolute bottom-0 left-0 p-6 sm:p-12 max-w-2xl z-10">
        <div className="flex items-center gap-3 mb-4">
          <span className="px-2 py-1 bg-fuchsia-500 text-white text-xs font-bold rounded shadow-md tracking-wider">
            PREMIERE
          </span>
          <span className="text-cyan-400 text-sm font-semibold tracking-wider">
            NEW EPISODE
          </span>
        </div>

        <h1 className="text-4xl sm:text-6xl font-bold text-white mb-4 leading-tight tracking-tight drop-shadow-lg">
          Neon Horizon: <br /> City of Angels
        </h1>

        <p className="text-gray-300 text-sm sm:text-base mb-8 line-clamp-2 sm:line-clamp-3 max-w-xl leading-relaxed">
          In a cyberpunk metropolis where magic meets machinery, a young detective uncovers a conspiracy that threatens the very fabric of reality. The highly anticipated season finale is finally here.
        </p>

        <div className="flex flex-wrap items-center gap-4">
          <button
            onClick={() => onPlay(heroVideo)}
            className="flex items-center gap-2 bg-white text-black px-6 py-3 rounded-full font-bold hover:bg-gray-200 transition-all hover:scale-105 shadow-[0_0_20px_rgba(255,255,255,0.4)] active:scale-95"
          >
            <Play className="w-5 h-5 fill-black text-black" />
            Play Episode 12
          </button>

          <button
            onClick={() => onToggleSave(heroVideo)}
            className={`flex items-center gap-2 px-6 py-3 rounded-full font-semibold backdrop-blur-md transition-all border ${
              isSaved
                ? 'bg-fuchsia-500 text-white border-fuchsia-400 shadow-[0_0_15px_rgba(217,70,239,0.5)]'
                : 'bg-white/10 text-white hover:bg-white/20 border-white/10'
            }`}
          >
            {isSaved ? (
              <>
                <Check className="w-5 h-5" />
                In Your List
              </>
            ) : (
              <>
                <Plus className="w-5 h-5" />
                Add to List
              </>
            )}
          </button>

          <button
            onClick={onOpenInfo}
            className="p-3 rounded-full bg-white/5 hover:bg-white/15 text-white transition-colors border border-white/10"
            title="Anime Details & Synopsis"
          >
            <Info className="w-5 h-5" />
          </button>
        </div>
      </div>
    </div>
  );
};
