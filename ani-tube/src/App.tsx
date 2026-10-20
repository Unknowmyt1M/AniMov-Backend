import React, { useState, useMemo, useEffect } from 'react';
import { Routes, Route, useNavigate, useLocation } from 'react-router-dom';
import { Navbar } from './components/Navbar';
import { Sidebar } from './components/Sidebar';
import { HomePage } from './pages/HomePage';
import { WatchPage } from './pages/WatchPage';
import { AnimeDetailPage } from './pages/AnimeDetailPage';
import { ShortsPlayerModal } from './components/ShortsPlayerModal';
import { UploadModal } from './components/UploadModal';
import { Toast } from './components/Toast';
import { 
  INITIAL_VIDEOS, 
  INITIAL_SHORTS, 
  INITIAL_NOTIFICATIONS 
} from './data/mockData';
import { Video, Short, NotificationItem, WatchProgress } from './types';
import { 
  getStoredWatchProgress, 
  searchAnime, 
  getHomeFeed, 
  searchItemToVideo, 
  SearchItem 
} from './services/api';

export default function App() {
  const navigate = useNavigate();
  const location = useLocation();

  const isWatchPage = location.pathname.startsWith('/watch');

  const [isSidebarOpen, setIsSidebarOpen] = useState(!isWatchPage);
  const [activeTab, setActiveTab] = useState('Home');
  const [selectedCategory, setSelectedCategory] = useState('All');
  const [searchQuery, setSearchQuery] = useState('');

  // Main data state
  const [videos, setVideos] = useState<Video[]>(INITIAL_VIDEOS);
  const [backendTrending, setBackendTrending] = useState<SearchItem[]>([]);
  const [shorts, setShorts] = useState<Short[]>(INITIAL_SHORTS);
  const [notifications, setNotifications] = useState<NotificationItem[]>(INITIAL_NOTIFICATIONS);

  // User state
  const [savedVideoIds, setSavedVideoIds] = useState<Set<number>>(new Set([1]));
  const [historyVideoIds, setHistoryVideoIds] = useState<number[]>([1, 2]);

  // Modal states
  const [activeShort, setActiveShort] = useState<Short | null>(null);
  const [isUploadOpen, setIsUploadOpen] = useState(false);

  // Loading state
  const [isLoadingFeed, setIsLoadingFeed] = useState(false);

  // Continue Watching state from local storage
  const [continueWatchingList, setContinueWatchingList] = useState<Array<{ video: Video; progress: WatchProgress }>>([]);

  // Toast
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => {
      setToastMessage(null);
    }, 3200);
  };

  const toggleSidebar = () => {
    setIsSidebarOpen(prev => !prev);
  };

  // 1. REAL-TIME HOMEPAGE FEED ON MOUNT
  useEffect(() => {
    const fetchRealtimeHome = async () => {
      setIsLoadingFeed(true);
      try {
        const homeData = await getHomeFeed();
        if (homeData.trending && homeData.trending.length > 0) {
          setBackendTrending(homeData.trending);
        }
        if (homeData.latestAiring && homeData.latestAiring.length > 0) {
          const liveVideos = homeData.latestAiring.map((item, idx) => searchItemToVideo(item, (idx % 12) + 1));
          setVideos(liveVideos);
        }
      } catch (err) {
        console.warn('Realtime home feed fetch fallback to initial catalog:', err);
      } finally {
        setIsLoadingFeed(false);
      }
    };

    fetchRealtimeHome();
  }, []);

  // 2. REAL-TIME LIVE SEARCH DEBOUNCE
  useEffect(() => {
    if (!searchQuery.trim()) return;

    if (location.pathname !== '/') {
      navigate('/');
    }

    const timer = setTimeout(async () => {
      try {
        const res = await searchAnime(searchQuery.trim());
        if (res.data && res.data.length > 0) {
          const searchVideos = res.data.map(item => searchItemToVideo(item, 1));
          setVideos(searchVideos);
        }
      } catch (err) {
        console.warn('Live search fallback:', err);
      }
    }, 400);

    return () => clearTimeout(timer);
  }, [searchQuery]);

  // Sync Continue Watching items
  const refreshContinueWatching = () => {
    const stored = getStoredWatchProgress();
    const items: Array<{ video: Video; progress: WatchProgress }> = [];

    Object.values(stored).forEach(progress => {
      if (!progress.completed && progress.currentTime > 5) {
        const found = videos.find(v => 
          (v.animeSlug && v.animeSlug === progress.animeSlug) ||
          v.channel.toLowerCase().replace(/\s+/g, '-') === progress.animeSlug
        );
        if (found) {
          items.push({ video: found, progress });
        }
      }
    });
    setContinueWatchingList(items);
  };

  useEffect(() => {
    refreshContinueWatching();
  }, [videos, location.pathname]);

  // Video Save / Bookmark handler
  const handleToggleSave = (video: Video, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    setSavedVideoIds(prev => {
      const next = new Set(prev);
      if (next.has(video.id)) {
        next.delete(video.id);
        showToast(`Removed "${video.title}" from Watchlist`);
      } else {
        next.add(video.id);
        showToast(`Added "${video.title}" to Watchlist!`);
      }
      return next;
    });
  };

  // Short Play handler
  const handlePlayShort = (short: Short) => {
    setActiveShort(short);
  };

  // Watch Full Episode from Short CTA -> navigates to dedicated watch page
  const handleWatchFromShort = (short: Short) => {
    setActiveShort(null);
    const targetVideo = videos.find(v => 
      v.channel.toLowerCase().includes(short.channel.toLowerCase()) ||
      v.title.toLowerCase().includes(short.title.toLowerCase().split(' ')[0])
    ) || videos[0];
    
    const slug = targetVideo.animeSlug || targetVideo.channel.toLowerCase().replace(/\s+/g, '-');
    const ep = targetVideo.ep || 1;
    navigate(`/watch/${slug}/${ep}`);
  };

  // Add Uploaded Video
  const handleAddVideo = (newVideo: Video) => {
    setVideos(prev => [newVideo, ...prev]);
    setSelectedCategory('All');
    setActiveTab('Home');
    navigate('/');
  };

  // Notifications
  const handleMarkNotificationsRead = () => {
    setNotifications(prev => prev.map(n => ({ ...n, unread: false })));
    showToast('All notifications marked as read');
  };

  const handleSelectNotificationVideo = (title: string) => {
    const found = videos.find(v => v.title.toLowerCase().includes(title.toLowerCase())) || videos[0];
    const slug = found.animeSlug || found.channel.toLowerCase().replace(/\s+/g, '-');
    const ep = found.ep || 1;
    navigate(`/watch/${slug}/${ep}`);
  };

  // Hero video
  const heroVideo = videos[0] || INITIAL_VIDEOS[0];

  // Filtered Videos calculation
  const displayedVideos = useMemo(() => {
    let list = [...videos];

    // Filter by Active Sidebar Tab
    if (activeTab === 'Trending') {
      list.sort((a, b) => b.viewsCount - a.viewsCount);
    } else if (activeTab === 'Watch Later' || activeTab === 'Favorites') {
      list = list.filter(v => savedVideoIds.has(v.id));
    } else if (activeTab === 'History') {
      const historyMap = new Map(historyVideoIds.map((id, index) => [id, index]));
      list = list.filter(v => historyMap.has(v.id)).sort((a, b) => historyMap.get(a.id)! - historyMap.get(b.id)!);
    } else if (activeTab === 'Currently Airing') {
      list = list.filter(v => v.ep !== null);
    } else if (activeTab === 'Movies') {
      list = list.filter(v => v.category === 'Movies' || v.tags.includes('TRAILER'));
    }

    // Filter by Category Pill
    if (selectedCategory !== 'All' && activeTab === 'Home') {
      list = list.filter(v => {
        if (selectedCategory === 'Trending') return v.viewsCount > 1000000;
        if (selectedCategory === 'Recently Added') return v.time.includes('hour') || v.time.includes('day');
        if (selectedCategory === 'Top Rated') return v.likes > 50000;
        if (selectedCategory === 'OVAs') return v.tags.includes('OVA') || v.duration.includes('45');
        return v.category.toLowerCase() === selectedCategory.toLowerCase();
      });
    }

    return list;
  }, [videos, activeTab, selectedCategory, savedVideoIds, historyVideoIds]);

  // Featured Anime Series for the "Trending Anime Series" row
  const trendingAnimeSeries = useMemo(() => {
    if (backendTrending.length > 0) {
      return backendTrending.map(b => ({
        slug: b.slug,
        title: b.display_title || b.english || b.romaji,
        score: b.score || 8.5,
        format: b.format || 'TV',
        episodesCount: 12,
        poster: b.poster || 'https://images.unsplash.com/photo-1578632767115-351597cf2477?w=800&q=80',
        studio: 'Studio',
      }));
    }

    return [
      {
        slug: 'uFxerMrwx6',
        title: 'Chainsaw Man',
        score: 8.6,
        format: 'TV',
        episodesCount: 12,
        poster: 'https://images.unsplash.com/photo-1605806616949-1e87b487cb2a?w=800&q=80',
        studio: 'MAPPA',
      },
      {
        slug: '5xxCxNSHUK',
        title: 'Attack on Titan',
        score: 8.9,
        format: 'TV',
        episodesCount: 25,
        poster: 'https://images.unsplash.com/photo-1578632767115-351597cf2477?w=800&q=80',
        studio: 'Wit Studio',
      },
      {
        slug: 'oui9FXBSdF',
        title: 'Demon Slayer: Kimetsu no Yaiba',
        score: 8.5,
        format: 'TV',
        episodesCount: 26,
        poster: 'https://images.unsplash.com/photo-1563089145-599997674d42?w=800&q=80',
        studio: 'ufotable',
      },
      {
        slug: 'xRCywW7USh',
        title: 'JUJUTSU KAISEN',
        score: 8.7,
        format: 'TV',
        episodesCount: 24,
        poster: 'https://images.unsplash.com/photo-1534447677768-be436bb09401?w=800&q=80',
        studio: 'MAPPA',
      },
      {
        slug: 'ARPEGZW3fK',
        title: 'ONE PIECE',
        score: 8.8,
        format: 'TV',
        episodesCount: 1100,
        poster: 'https://images.unsplash.com/photo-1518709268805-4e9042af9f23?w=800&q=80',
        studio: 'Toei Animation',
      },
    ];
  }, [backendTrending]);

  // Recommended Videos calculation
  const recommendedVideos = useMemo(() => {
    return [...videos].slice(2, 6);
  }, [videos]);

  const resetAllFilters = () => {
    setSelectedCategory('All');
    setSearchQuery('');
    setActiveTab('Home');
    navigate('/');
  };

  return (
    <div className="min-h-screen bg-[#0f0f0f] text-white overflow-x-hidden selection:bg-fuchsia-500 selection:text-white">
      {/* Top Navbar */}
      <Navbar
        toggleSidebar={toggleSidebar}
        searchQuery={searchQuery}
        setSearchQuery={setSearchQuery}
        onOpenUpload={() => setIsUploadOpen(true)}
        notifications={notifications}
        onMarkNotificationsRead={handleMarkNotificationsRead}
        onSelectNotificationVideo={handleSelectNotificationVideo}
        savedCount={savedVideoIds.size}
        historyCount={historyVideoIds.length}
        onNavigateTab={(tab) => {
          setActiveTab(tab);
          setSelectedCategory('All');
          navigate('/');
        }}
      />

      <div className="flex pt-4">
        {/* Mobile Backdrop */}
        {isSidebarOpen && !isWatchPage && (
          <div
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-30 sm:hidden block transition-opacity"
            onClick={() => setIsSidebarOpen(false)}
          />
        )}

        {/* Sidebar: Shown on non-watch pages, or toggleable */}
        {!isWatchPage && (
          <Sidebar
            isOpen={isSidebarOpen}
            activeTab={activeTab}
            setActiveTab={(tab) => {
              setActiveTab(tab);
              if (tab === 'Home') setSelectedCategory('All');
              navigate('/');
            }}
            savedCount={savedVideoIds.size}
            historyCount={historyVideoIds.length}
          />
        )}

        {/* Main Content Area */}
        <main
          className={`flex-1 transition-all duration-300 ${
            !isWatchPage
              ? `px-4 sm:px-6 lg:px-8 pb-16 ${isSidebarOpen ? 'ml-0 sm:ml-64' : 'ml-0 sm:ml-20'}`
              : 'w-full'
          }`}
        >
          <Routes>
            <Route
              path="/"
              element={
                <HomePage
                  videos={videos}
                  displayedVideos={displayedVideos}
                  recommendedVideos={recommendedVideos}
                  trendingAnimeSeries={trendingAnimeSeries}
                  heroVideo={heroVideo}
                  continueWatchingList={continueWatchingList}
                  shorts={shorts}
                  activeTab={activeTab}
                  selectedCategory={selectedCategory}
                  searchQuery={searchQuery}
                  isLoadingFeed={isLoadingFeed}
                  savedVideoIds={savedVideoIds}
                  onToggleSave={handleToggleSave}
                  onPlayShort={handlePlayShort}
                  setSelectedCategory={setSelectedCategory}
                  resetAllFilters={resetAllFilters}
                  onShowToast={showToast}
                />
              }
            />

            <Route
              path="/watch/:slug/:episode"
              element={
                <WatchPage
                  onShowToast={showToast}
                  savedVideoIds={savedVideoIds}
                  onToggleSave={handleToggleSave}
                />
              }
            />

            <Route
              path="/anime/:slug"
              element={
                <AnimeDetailPage
                  onShowToast={showToast}
                />
              }
            />
          </Routes>
        </main>
      </div>

      {/* Shorts Player Modal */}
      <ShortsPlayerModal
        currentShort={activeShort}
        onClose={() => setActiveShort(null)}
        allShorts={shorts}
        onSelectShort={setActiveShort}
        onShowToast={showToast}
        onWatchEpisode={handleWatchFromShort}
      />

      {/* Upload Video Modal */}
      <UploadModal
        isOpen={isUploadOpen}
        onClose={() => setIsUploadOpen(false)}
        onAddVideo={handleAddVideo}
        onShowToast={showToast}
      />

      {/* Toast Notification */}
      <Toast message={toastMessage} />
    </div>
  );
}
