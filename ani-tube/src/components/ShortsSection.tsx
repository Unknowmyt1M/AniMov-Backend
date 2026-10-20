import React, { useRef } from 'react';
import { Flame, ChevronLeft, ChevronRight, Play } from 'lucide-react';
import { Short } from '../types';

interface ShortsSectionProps {
  shorts: Short[];
  onPlayShort: (short: Short) => void;
}

export const ShortsSection: React.FC<ShortsSectionProps> = ({
  shorts,
  onPlayShort,
}) => {
  const scrollRef = useRef<HTMLDivElement>(null);

  const scroll = (direction: 'left' | 'right') => {
    if (scrollRef.current) {
      scrollRef.current.scrollBy({
        left: direction === 'left' ? -400 : 400,
        behavior: 'smooth',
      });
    }
  };

  return (
    <div className="my-10 border-t border-b border-white/10 py-8 relative">
      <div className="flex items-center gap-2 mb-6 px-2">
        <Flame className="w-6 h-6 text-fuchsia-500" />
        <h2 className="text-2xl font-bold text-white tracking-tight">
          Trending Shorts & AMVs
        </h2>
      </div>

      <div className="relative group">
        {/* Left Scroll Button */}
        <button
          onClick={() => scroll('left')}
          className="absolute left-2 top-1/2 -translate-y-1/2 z-20 p-3 bg-[#1a1a1a]/80 backdrop-blur-md rounded-full text-white hover:bg-fuchsia-500 hidden group-hover:block shadow-xl border border-white/10 transition-colors"
          title="Scroll Left"
        >
          <ChevronLeft className="w-6 h-6" />
        </button>

        {/* Horizontal Track */}
        <div
          ref={scrollRef}
          className="flex gap-4 overflow-x-auto no-scrollbar scroll-smooth px-2 pb-4"
        >
          {shorts.map((short) => (
            <div
              key={short.id}
              onClick={() => onPlayShort(short)}
              className="min-w-[200px] w-[200px] flex-shrink-0 group/short cursor-pointer select-none"
            >
              <div className="relative aspect-[9/16] rounded-xl overflow-hidden mb-3 bg-gray-900 border border-white/5">
                <img
                  src={short.thumbnail}
                  alt={short.title}
                  className="w-full h-full object-cover transition-transform duration-500 group-hover/short:scale-110"
                  loading="lazy"
                />
                <div className="absolute inset-0 bg-gradient-to-b from-transparent via-transparent to-black/90" />

                {/* Info Text */}
                <div className="absolute bottom-3 left-3 right-3">
                  <h4 className="text-white font-semibold line-clamp-2 text-sm mb-1 leading-tight shadow-black drop-shadow-md">
                    {short.title}
                  </h4>
                  <span className="text-gray-300 text-xs font-medium">
                    {short.views} views
                  </span>
                </div>

                {/* Hover Play Button */}
                <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover/short:opacity-100 transition-opacity">
                  <div className="w-12 h-12 bg-black/50 backdrop-blur-sm rounded-full flex items-center justify-center border border-white/20 shadow-[0_0_15px_rgba(217,70,239,0.4)]">
                    <Play className="w-5 h-5 text-white fill-white ml-1" />
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Right Scroll Button */}
        <button
          onClick={() => scroll('right')}
          className="absolute right-2 top-1/2 -translate-y-1/2 z-20 p-3 bg-[#1a1a1a]/80 backdrop-blur-md rounded-full text-white hover:bg-fuchsia-500 hidden group-hover:block shadow-xl border border-white/10 transition-colors"
          title="Scroll Right"
        >
          <ChevronRight className="w-6 h-6" />
        </button>
      </div>
    </div>
  );
};
