import React from 'react';
import { 
  House, 
  Compass, 
  Flame, 
  SquarePlay, 
  History, 
  Clock, 
  Heart, 
  Tv, 
  Film 
} from 'lucide-react';

interface SidebarProps {
  isOpen: boolean;
  activeTab: string;
  setActiveTab: (tab: string) => void;
  savedCount: number;
  historyCount: number;
}

export const Sidebar: React.FC<SidebarProps> = ({
  isOpen,
  activeTab,
  setActiveTab,
  savedCount,
  historyCount
}) => {
  const navItems = [
    { icon: House, label: "Home" },
    { icon: Compass, label: "Explore" },
    { icon: Flame, label: "Trending" },
    { icon: SquarePlay, label: "Subscriptions" },
    { divider: true },
    { icon: History, label: "History", badge: historyCount > 0 ? historyCount : undefined },
    { icon: Clock, label: "Watch Later", badge: savedCount > 0 ? savedCount : undefined },
    { icon: Heart, label: "Favorites" },
    { divider: true },
    { icon: Tv, label: "Currently Airing" },
    { icon: Film, label: "Movies" },
  ];

  return (
    <aside
      className={`fixed left-0 top-16 bottom-0 bg-[#0f0f0f] overflow-y-auto transition-all duration-300 z-40 ${
        isOpen ? "w-64 translate-x-0" : "w-20 -translate-x-full sm:translate-x-0"
      } border-r border-white/5 custom-scrollbar`}
    >
      <div className="py-3 px-3 flex flex-col gap-1">
        {navItems.map((item, index) => {
          if (item.divider) {
            return <div key={index} className="h-px bg-white/10 my-3 mx-2" />;
          }

          const Icon = item.icon!;
          const isActive = activeTab === item.label;

          return (
            <button
              key={index}
              onClick={() => item.label && setActiveTab(item.label)}
              className={`flex items-center gap-4 p-3 rounded-xl transition-all ${
                isActive
                  ? "bg-white/10 text-white font-medium shadow-sm"
                  : "text-gray-400 hover:bg-white/5 hover:text-white"
              } ${!isOpen ? "sm:justify-center" : "justify-between"}`}
              title={!isOpen ? item.label : undefined}
            >
              <div className="flex items-center gap-4">
                <Icon
                  className={`w-6 h-6 transition-colors ${
                    isActive ? "text-fuchsia-500" : ""
                  }`}
                />
                <span
                  className={`text-sm whitespace-nowrap ${
                    isOpen ? "block" : "sm:hidden"
                  }`}
                >
                  {item.label}
                </span>
              </div>

              {isOpen && item.badge !== undefined && (
                <span className="text-[11px] font-semibold bg-white/10 px-2 py-0.5 rounded-full text-gray-300">
                  {item.badge}
                </span>
              )}
            </button>
          );
        })}
      </div>
    </aside>
  );
};
