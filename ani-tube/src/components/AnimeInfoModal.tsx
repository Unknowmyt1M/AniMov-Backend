import React from 'react';
import { X, Play, Plus, Check, Star, Calendar, Shield, Film } from 'lucide-react';
import { Video } from '../types';

interface AnimeInfoModalProps {
  isOpen: boolean;
  onClose: () => void;
  video: Video;
  onPlay: (video: Video) => void;
  onToggleSave: (video: Video) => void;
  isSaved: boolean;
}

export const AnimeInfoModal: React.FC<AnimeInfoModalProps> = ({
  isOpen,
  onClose,
  video,
  onPlay,
  onToggleSave,
  isSaved
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/85 backdrop-blur-md flex items-center justify-center p-4">
      <div className="relative w-full max-w-2xl bg-[#141414] border border-white/10 rounded-3xl overflow-hidden shadow-2xl max-h-[90vh] flex flex-col custom-scrollbar">
        {/* Banner Image */}
        <div className="relative h-60 w-full overflow-hidden flex-shrink-0">
          <img
            src="/images/hero-bg.png"
            alt="Neon Horizon"
            className="w-full h-full object-cover"
            onError={(e) => {
              (e.target as HTMLImageElement).src = 'https://images.unsplash.com/photo-1605806616949-1e87b487cb2a?w=1200&q=80';
            }}
          />
          <div className="absolute inset-0 bg-gradient-to-t from-[#141414] via-[#141414]/40 to-transparent" />
          
          <button
            onClick={onClose}
            className="absolute top-4 right-4 p-2.5 rounded-full bg-black/60 hover:bg-black/80 text-white backdrop-blur-md transition-colors"
          >
            <X className="w-5 h-5" />
          </button>

          <div className="absolute bottom-4 left-6">
            <span className="px-2.5 py-1 bg-fuchsia-500 text-white text-xs font-bold rounded shadow-md tracking-wider mr-2">
              PREMIERE FINALE
            </span>
            <span className="text-cyan-400 text-xs font-bold tracking-wider">
              STUDIO TRIGGER
            </span>
            <h2 className="text-2xl sm:text-3xl font-extrabold text-white mt-1">
              Neon Horizon: City of Angels
            </h2>
          </div>
        </div>

        {/* Content Body */}
        <div className="p-6 sm:p-8 space-y-6 overflow-y-auto">
          {/* Rating & Stats Bar */}
          <div className="flex flex-wrap items-center gap-4 text-xs font-semibold pb-4 border-b border-white/10">
            <div className="flex items-center gap-1.5 text-yellow-400 bg-yellow-400/10 px-3 py-1 rounded-full border border-yellow-400/20">
              <Star className="w-4 h-4 fill-yellow-400" />
              <span className="text-sm font-bold text-white">9.4</span>
              <span className="text-gray-400">/ 10</span>
            </div>

            <div className="flex items-center gap-1.5 text-gray-300">
              <Calendar className="w-4 h-4 text-cyan-400" />
              <span>Spring 2026</span>
            </div>

            <div className="flex items-center gap-1.5 text-gray-300">
              <Film className="w-4 h-4 text-fuchsia-400" />
              <span>12 Episodes (Completed)</span>
            </div>

            <div className="flex items-center gap-1.5 text-gray-300">
              <Shield className="w-4 h-4 text-green-400" />
              <span>TV-MA (16+)</span>
            </div>
          </div>

          {/* Genres */}
          <div>
            <h4 className="text-xs uppercase tracking-wider text-gray-400 font-bold mb-2">Genres</h4>
            <div className="flex flex-wrap gap-2">
              {['Cyberpunk', 'Action', 'Sci-Fi', 'Psychological', 'Supernatural', 'Mystery'].map(g => (
                <span key={g} className="px-3 py-1 bg-white/5 hover:bg-white/10 text-gray-200 text-xs rounded-full border border-white/10 transition-colors">
                  {g}
                </span>
              ))}
            </div>
          </div>

          {/* Synopsis */}
          <div>
            <h4 className="text-xs uppercase tracking-wider text-gray-400 font-bold mb-2">Synopsis</h4>
            <p className="text-sm text-gray-300 leading-relaxed">
              In Neo-Shinjuku 2099, towering chrome spires pierce a perpetual neon smog while arcane sigils hum beneath fiber-optic conduits. Detective Ren Arisawa is tasked with investigating a high-profile assassination at the Aether Corporation. As he dives deeper into the subterranean underworld, he uncovers an ancient biomechanical entity capable of rewriting the cognitive code of humanity.
            </p>
          </div>

          {/* Production & Cast */}
          <div className="grid grid-cols-2 gap-4 text-xs">
            <div>
              <span className="text-gray-500 block">Animation Studio</span>
              <span className="text-white font-semibold">Studio Trigger</span>
            </div>
            <div>
              <span className="text-gray-500 block">Director</span>
              <span className="text-white font-semibold">Hiroyuki Imaishi</span>
            </div>
            <div>
              <span className="text-gray-500 block">Music & OST</span>
              <span className="text-white font-semibold">Hiroyuki Sawano</span>
            </div>
            <div>
              <span className="text-gray-500 block">Original Creator</span>
              <span className="text-white font-semibold">Trigger x Arcada</span>
            </div>
          </div>

          {/* Buttons */}
          <div className="flex gap-4 pt-2">
            <button
              onClick={() => {
                onClose();
                onPlay(video);
              }}
              className="flex-1 flex items-center justify-center gap-2 bg-white text-black py-3 rounded-full font-bold hover:bg-gray-200 transition-all active:scale-95 shadow-md text-sm"
            >
              <Play className="w-4 h-4 fill-black" /> Watch Episode 12
            </button>

            <button
              onClick={() => onToggleSave(video)}
              className={`flex-1 flex items-center justify-center gap-2 py-3 rounded-full font-semibold transition-all border text-sm ${
                isSaved
                  ? 'bg-fuchsia-500 text-white border-fuchsia-400 shadow-[0_0_15px_rgba(217,70,239,0.5)]'
                  : 'bg-white/10 hover:bg-white/20 text-white border-white/10'
              }`}
            >
              {isSaved ? (
                <>
                  <Check className="w-4 h-4" /> In Your List
                </>
              ) : (
                <>
                  <Plus className="w-4 h-4" /> Add to List
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
