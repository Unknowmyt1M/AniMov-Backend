import React, { useRef } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { CATEGORIES } from '../data/mockData';

interface CategoryPillsProps {
  selectedCategory: string;
  onSelectCategory: (category: string) => void;
}

export const CategoryPills: React.FC<CategoryPillsProps> = ({
  selectedCategory,
  onSelectCategory,
}) => {
  const scrollRef = useRef<HTMLDivElement>(null);

  const scroll = (direction: 'left' | 'right') => {
    if (scrollRef.current) {
      scrollRef.current.scrollBy({
        left: direction === 'left' ? -300 : 300,
        behavior: 'smooth',
      });
    }
  };

  return (
    <div className="relative flex items-center mb-6 group">
      {/* Left Gradient & Scroll Button */}
      <div className="absolute left-0 top-0 bottom-0 w-24 bg-gradient-to-r from-[#0f0f0f] to-transparent z-10 pointer-events-none hidden group-hover:block" />
      <button
        onClick={() => scroll('left')}
        className="absolute left-0 z-20 p-2 bg-[#1a1a1a] rounded-full text-white hover:bg-gray-700 hidden group-hover:block shadow-lg border border-white/10 transition-colors"
        title="Scroll Left"
      >
        <ChevronLeft className="w-5 h-5" />
      </button>

      {/* Categories Horizontal Track */}
      <div
        ref={scrollRef}
        className="flex gap-3 overflow-x-auto no-scrollbar scroll-smooth w-full px-2 py-1"
      >
        {CATEGORIES.map((category) => {
          const isActive = selectedCategory === category;
          return (
            <button
              key={category}
              onClick={() => onSelectCategory(category)}
              className={`whitespace-nowrap px-4 py-1.5 rounded-lg text-sm font-medium transition-all ${
                isActive
                  ? 'bg-white text-black shadow-md font-semibold'
                  : 'bg-white/10 text-gray-200 hover:bg-white/20 border border-white/5'
              }`}
            >
              {category}
            </button>
          );
        })}
      </div>

      {/* Right Gradient & Scroll Button */}
      <div className="absolute right-0 top-0 bottom-0 w-24 bg-gradient-to-l from-[#0f0f0f] to-transparent z-10 pointer-events-none hidden group-hover:block" />
      <button
        onClick={() => scroll('right')}
        className="absolute right-0 z-20 p-2 bg-[#1a1a1a] rounded-full text-white hover:bg-gray-700 hidden group-hover:block shadow-lg border border-white/10 transition-colors"
        title="Scroll Right"
      >
        <ChevronRight className="w-5 h-5" />
      </button>
    </div>
  );
};
