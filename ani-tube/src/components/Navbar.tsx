import React, { useState, useRef, useEffect } from 'react';
import { Menu, SquarePlay, Search, Mic, Video, Bell, X, Check, Clock, User, Bookmark, History, Sparkles } from 'lucide-react';
import { NotificationItem } from '../types';

interface NavbarProps {
  toggleSidebar: () => void;
  searchQuery: string;
  setSearchQuery: (query: string) => void;
  onOpenUpload: () => void;
  notifications: NotificationItem[];
  onMarkNotificationsRead: () => void;
  onSelectNotificationVideo: (title: string) => void;
  savedCount: number;
  historyCount: number;
  onNavigateTab: (tab: string) => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  toggleSidebar,
  searchQuery,
  setSearchQuery,
  onOpenUpload,
  notifications,
  onMarkNotificationsRead,
  onSelectNotificationVideo,
  savedCount,
  historyCount,
  onNavigateTab
}) => {
  const [showNotifications, setShowNotifications] = useState(false);
  const [showProfileMenu, setShowProfileMenu] = useState(false);
  const [isListening, setIsListening] = useState(false);
  
  const notifRef = useRef<HTMLDivElement>(null);
  const profileRef = useRef<HTMLDivElement>(null);

  const unreadCount = notifications.filter(n => n.unread).length;

  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (notifRef.current && !notifRef.current.contains(e.target as Node)) {
        setShowNotifications(false);
      }
      if (profileRef.current && !profileRef.current.contains(e.target as Node)) {
        setShowProfileMenu(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleVoiceSearch = () => {
    setIsListening(true);
    // Simulate speech recognition
    setTimeout(() => {
      setSearchQuery('Cyber City');
      setIsListening(false);
    }, 1500);
  };

  return (
    <nav className="sticky top-0 z-50 flex items-center justify-between px-4 h-16 bg-[#0f0f0f]/95 backdrop-blur-sm border-b border-white/10">
      {/* Left: Hamburger & Logo */}
      <div className="flex items-center gap-4">
        <button
          onClick={toggleSidebar}
          className="p-2 hover:bg-white/10 rounded-full transition-colors text-white"
          title="Toggle Navigation"
        >
          <Menu className="w-6 h-6 text-white" />
        </button>

        <div
          onClick={() => {
            onNavigateTab('Home');
            setSearchQuery('');
          }}
          className="flex items-center gap-1 cursor-pointer select-none group"
        >
          <div className="w-8 h-8 bg-gradient-to-br from-fuchsia-500 to-cyan-500 rounded-lg flex items-center justify-center shadow-[0_0_12px_rgba(217,70,239,0.3)] group-hover:scale-105 transition-transform">
            <SquarePlay className="w-5 h-5 text-white fill-white" />
          </div>
          <span className="text-xl font-bold tracking-tighter text-white ml-2 hidden sm:block">
            Ani<span className="text-fuchsia-500">Tube</span>
          </span>
        </div>
      </div>

      {/* Center: Search Bar */}
      <div className="flex-1 max-w-2xl px-4 flex items-center gap-2 sm:gap-4">
        <div className="flex flex-1 items-center bg-[#121212] border border-white/10 rounded-full overflow-hidden focus-within:border-fuchsia-500/50 focus-within:ring-1 focus-within:ring-fuchsia-500/50 transition-all">
          <div className="pl-4 pr-2 text-gray-400">
            <Search className="w-5 h-5" />
          </div>
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search anime, episodes, AMVs..."
            className="flex-1 bg-transparent py-2.5 px-2 text-white outline-none placeholder:text-gray-500 text-sm"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              className="p-1 mr-2 text-gray-400 hover:text-white rounded-full transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          )}
          <button
            onClick={() => {}}
            className="px-5 py-2.5 bg-white/5 hover:bg-white/10 border-l border-white/10 transition-colors"
            title="Search"
          >
            <Search className="w-5 h-5 text-gray-300" />
          </button>
        </div>

        <button
          onClick={handleVoiceSearch}
          className={`p-2.5 rounded-full transition-all hidden sm:flex items-center justify-center ${
            isListening ? 'bg-fuchsia-500 text-white animate-pulse' : 'bg-white/5 hover:bg-white/10 text-white'
          }`}
          title={isListening ? "Listening..." : "Search with voice"}
        >
          <Mic className="w-5 h-5" />
        </button>
      </div>

      {/* Right: Actions */}
      <div className="flex items-center gap-2 sm:gap-4 relative">
        {/* Upload Video Button */}
        <button
          onClick={onOpenUpload}
          className="p-2 hover:bg-white/10 rounded-full transition-colors hidden sm:block text-white"
          title="Upload Anime or AMV"
        >
          <Video className="w-6 h-6 text-white" />
        </button>

        {/* Notifications Dropdown */}
        <div className="relative" ref={notifRef}>
          <button
            onClick={() => setShowNotifications(!showNotifications)}
            className="p-2 hover:bg-white/10 rounded-full transition-colors relative text-white"
            title="Notifications"
          >
            <Bell className="w-6 h-6 text-white" />
            {unreadCount > 0 && (
              <span className="absolute top-1.5 right-1.5 w-2.5 h-2.5 bg-fuchsia-500 rounded-full ring-2 ring-[#0f0f0f] animate-pulse" />
            )}
          </button>

          {showNotifications && (
            <div className="absolute right-0 mt-3 w-80 sm:w-96 bg-[#181818] border border-white/10 rounded-2xl shadow-2xl overflow-hidden z-50 backdrop-blur-xl animate-in fade-in zoom-in-95 duration-200">
              <div className="p-4 border-b border-white/10 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <h3 className="font-bold text-white text-base">Notifications</h3>
                  {unreadCount > 0 && (
                    <span className="bg-fuchsia-500/20 text-fuchsia-400 text-xs px-2 py-0.5 rounded-full font-semibold border border-fuchsia-500/30">
                      {unreadCount} new
                    </span>
                  )}
                </div>
                {unreadCount > 0 && (
                  <button
                    onClick={onMarkNotificationsRead}
                    className="text-xs text-gray-400 hover:text-white flex items-center gap-1 transition-colors"
                  >
                    <Check className="w-3.5 h-3.5" /> Mark all read
                  </button>
                )}
              </div>

              <div className="max-h-80 overflow-y-auto divide-y divide-white/5 custom-scrollbar">
                {notifications.length === 0 ? (
                  <div className="p-6 text-center text-gray-400 text-sm">
                    No new notifications right now
                  </div>
                ) : (
                  notifications.map((item) => (
                    <div
                      key={item.id}
                      onClick={() => {
                        onSelectNotificationVideo(item.title);
                        setShowNotifications(false);
                      }}
                      className={`p-3.5 hover:bg-white/5 cursor-pointer flex gap-3 transition-colors ${
                        item.unread ? 'bg-fuchsia-500/5' : ''
                      }`}
                    >
                      {item.thumbnail ? (
                        <img
                          src={item.thumbnail}
                          alt=""
                          className="w-12 h-12 rounded-lg object-cover flex-shrink-0 border border-white/10"
                        />
                      ) : (
                        <div className="w-12 h-12 rounded-lg bg-gradient-to-br from-fuchsia-500/20 to-cyan-500/20 flex items-center justify-center flex-shrink-0 border border-white/10">
                          <Sparkles className="w-5 h-5 text-fuchsia-400" />
                        </div>
                      )}
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-semibold text-white leading-snug line-clamp-1">
                          {item.title}
                        </p>
                        <p className="text-xs text-gray-400 line-clamp-2 mt-0.5">
                          {item.message}
                        </p>
                        <span className="text-[11px] text-gray-500 flex items-center gap-1 mt-1">
                          <Clock className="w-3 h-3" /> {item.time}
                        </span>
                      </div>
                      {item.unread && (
                        <div className="w-2 h-2 rounded-full bg-fuchsia-500 self-center" />
                      )}
                    </div>
                  ))
                )}
              </div>
            </div>
          )}
        </div>

        {/* User Profile Avatar & Menu */}
        <div className="relative" ref={profileRef}>
          <button
            onClick={() => setShowProfileMenu(!showProfileMenu)}
            className="w-8 h-8 rounded-full bg-gradient-to-r from-cyan-500 to-blue-500 overflow-hidden ml-2 border border-white/20 hover:ring-2 hover:ring-fuchsia-500/50 transition-all flex items-center justify-center"
            title="User Profile"
          >
            <img
              src="https://api.dicebear.com/7.x/avataaars/svg?seed=Felix"
              alt="User"
              className="w-full h-full object-cover"
            />
          </button>

          {showProfileMenu && (
            <div className="absolute right-0 mt-3 w-64 bg-[#181818] border border-white/10 rounded-2xl shadow-2xl overflow-hidden z-50 backdrop-blur-xl animate-in fade-in zoom-in-95 duration-200">
              <div className="p-4 border-b border-white/10 flex items-center gap-3">
                <img
                  src="https://api.dicebear.com/7.x/avataaars/svg?seed=Felix"
                  alt="User"
                  className="w-11 h-11 rounded-full border border-fuchsia-500/40"
                />
                <div>
                  <h4 className="font-bold text-white text-sm">Darko</h4>
                  <span className="text-xs text-fuchsia-400 font-medium flex items-center gap-1">
                    <Sparkles className="w-3 h-3" /> Otaku VIP
                  </span>
                </div>
              </div>

              <div className="p-2 border-b border-white/10">
                <div className="grid grid-cols-2 gap-2 text-center p-2 bg-white/5 rounded-xl text-xs">
                  <div>
                    <span className="block font-bold text-white text-sm">{savedCount}</span>
                    <span className="text-gray-400">Saved</span>
                  </div>
                  <div className="border-l border-white/10">
                    <span className="block font-bold text-white text-sm">{historyCount}</span>
                    <span className="text-gray-400">Watched</span>
                  </div>
                </div>
              </div>

              <div className="p-2 space-y-1 text-sm">
                <button
                  onClick={() => {
                    onNavigateTab('Favorites');
                    setShowProfileMenu(false);
                  }}
                  className="w-full flex items-center gap-3 px-3 py-2 text-gray-300 hover:text-white hover:bg-white/5 rounded-xl transition-colors text-left"
                >
                  <Bookmark className="w-4 h-4 text-fuchsia-400" />
                  <span>My Watchlist ({savedCount})</span>
                </button>
                <button
                  onClick={() => {
                    onNavigateTab('History');
                    setShowProfileMenu(false);
                  }}
                  className="w-full flex items-center gap-3 px-3 py-2 text-gray-300 hover:text-white hover:bg-white/5 rounded-xl transition-colors text-left"
                >
                  <History className="w-4 h-4 text-cyan-400" />
                  <span>Watch History</span>
                </button>
                <button
                  onClick={() => {
                    onOpenUpload();
                    setShowProfileMenu(false);
                  }}
                  className="w-full flex items-center gap-3 px-3 py-2 text-gray-300 hover:text-white hover:bg-white/5 rounded-xl transition-colors text-left sm:hidden"
                >
                  <Video className="w-4 h-4 text-green-400" />
                  <span>Upload Anime</span>
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </nav>
  );
};
