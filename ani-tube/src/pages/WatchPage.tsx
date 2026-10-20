import React, { useState, useRef, useEffect, useMemo } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import Hls from 'hls.js';
import { 
  Play, 
  Pause, 
  Volume2, 
  VolumeX, 
  Maximize, 
  Minimize, 
  RotateCcw, 
  ThumbsUp, 
  ThumbsDown, 
  Share2, 
  Bookmark, 
  Check, 
  Send, 
  ChevronDown, 
  ChevronUp, 
  Settings, 
  ListVideo, 
  Sparkles, 
  FastForward, 
  Server, 
  Loader2, 
  AlertCircle,
  ArrowLeft,
  Subtitles
} from 'lucide-react';
import { Video, Comment, Episode } from '../types';
import { saveWatchProgress, fetchLiveEpisodeStream, getAnimeDetail, StreamResolutionResult } from '../services/api';
import { PlayerSettingsMenu, QualityOption } from '../components/PlayerSettingsMenu';

interface WatchPageProps {
  onShowToast: (msg: string) => void;
  savedVideoIds: Set<number>;
  onToggleSave: (video: Video) => void;
}

export const WatchPage: React.FC<WatchPageProps> = ({
  onShowToast,
  savedVideoIds,
  onToggleSave,
}) => {
  const { slug, episode } = useParams<{ slug: string; episode: string }>();
  const navigate = useNavigate();

  const currentSlug = slug || 'uFxerMrwx6';
  const currentEpNum = parseInt(episode || '1', 10);

  const videoRef = useRef<HTMLVideoElement>(null);
  const hlsRef = useRef<Hls | null>(null);

  // Playback state
  const [isPlaying, setIsPlaying] = useState(true);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [volume, setVolume] = useState(0.8);
  const [isMuted, setIsMuted] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [speed, setSpeed] = useState(1);
  const [showSettings, setShowSettings] = useState(false);
  const [quality, setQuality] = useState('Auto');
  const [availableQualities, setAvailableQualities] = useState<QualityOption[]>([]);
  const [selectedQualityIndex, setSelectedQualityIndex] = useState<number>(-1);
  const [currentActiveHeight, setCurrentActiveHeight] = useState<number | null>(null);

  // Anime & Stream metadata state
  const [animeTitle, setAnimeTitle] = useState('');
  const [animePoster, setAnimePoster] = useState('');
  const [animeSynopsis, setAnimeSynopsis] = useState('');
  const [seasonEpisodes, setSeasonEpisodes] = useState<Episode[]>([]);
  const [isLoadingAnime, setIsLoadingAnime] = useState(true);
  const [isLoadingStream, setIsLoadingStream] = useState(true);
  const [streamError, setStreamError] = useState<string | null>(null);
  const [activeStreamUrl, setActiveStreamUrl] = useState<string>('');
  const [streamData, setStreamData] = useState<StreamResolutionResult | null>(null);

  // Controls state
  const [audioLang, setAudioLang] = useState<'SUB' | 'DUB'>('SUB');
  const [selectedServer, setSelectedServer] = useState('HD-1 (Megaplay)');
  const [autoSkipIntro, setAutoSkipIntro] = useState(false);
  const [autoSkipOutro, setAutoSkipOutro] = useState(false);
  const [ambientMode, setAmbientMode] = useState(true);
  const [selectedSubtitle, setSelectedSubtitle] = useState('Off');

  // Intro / Outro timestamps
  const [introRange, setIntroRange] = useState<{ start: number; end: number } | null>(null);
  const [outroRange, setOutroRange] = useState<{ start: number; end: number } | null>(null);

  // Right sidebar tab state: 'episodes' | 'recommendations'
  const [sidebarTab, setSidebarTab] = useState<'episodes' | 'recommendations'>('episodes');

  // Engagement state
  const [likesCount, setLikesCount] = useState(48200);
  const [isLiked, setIsLiked] = useState(false);
  const [isDisliked, setIsDisliked] = useState(false);
  const [isSubscribed, setIsSubscribed] = useState(false);
  const [isDescExpanded, setIsDescExpanded] = useState(false);

  // Comments state
  const [comments, setComments] = useState<Comment[]>([
    {
      id: 'c1',
      author: 'Aoi_Sakura',
      avatar: 'https://api.dicebear.com/7.x/avataaars/svg?seed=Aoi',
      text: 'The fight sakuga at 12:45 gave me literal goosebumps! Studio Trigger & MAPPA never miss.',
      time: '2 hours ago',
      likes: 420,
    },
    {
      id: 'c2',
      author: 'CyberOtaku99',
      avatar: 'https://api.dicebear.com/7.x/avataaars/svg?seed=CyberOtaku',
      text: 'Soundtrack during the final clash was peak orchestral synthwave. 10/10 masterclass episode!',
      time: '4 hours ago',
      likes: 185,
    },
  ]);
  const [newCommentText, setNewCommentText] = useState('');

  // 1. FETCH ANIME DETAIL (Title, Poster, Episodes)
  useEffect(() => {
    let isCancelled = false;
    const loadAnimeData = async () => {
      setIsLoadingAnime(true);
      try {
        const detail = await getAnimeDetail(currentSlug);
        if (isCancelled) return;
        setAnimeTitle(detail.displayTitle || detail.romajiTitle || currentSlug);
        setAnimePoster(detail.poster || '');
        setAnimeSynopsis(detail.synopsis || '');
        if (detail.episodes && detail.episodes.length > 0) {
          setSeasonEpisodes(detail.episodes);
        } else {
          // Generate 12 fallback episodes
          const fallbackEps: Episode[] = Array.from({ length: 12 }, (_, i) => ({
            id: `${currentSlug}-ep-${i + 1}`,
            animeSlug: currentSlug,
            animeTitle: detail.displayTitle,
            number: i + 1,
            seasonNumber: 1,
            title: `${detail.displayTitle} - Episode ${i + 1}`,
            thumbnail: detail.poster,
            duration: '24:00',
            durationSeconds: 1440,
            sources: [],
            subtitles: [],
          }));
          setSeasonEpisodes(fallbackEps);
        }
      } catch (e) {
        console.warn('Failed to load anime details for watch page:', e);
      } finally {
        if (!isCancelled) {
          setIsLoadingAnime(false);
        }
      }
    };

    loadAnimeData();
    return () => { isCancelled = true; };
  }, [currentSlug]);

  // 2. LIVE ON-DEMAND STREAM RESOLUTION FROM BACKEND
  useEffect(() => {
    let isCancelled = false;

    const resolveStream = async () => {
      setIsLoadingStream(true);
      setStreamError(null);
      setCurrentTime(0);

      try {
        const result = await fetchLiveEpisodeStream(currentSlug, currentEpNum, audioLang.toLowerCase() as 'sub' | 'dub');
        if (isCancelled) return;

        setStreamData(result);

        if (result.intro) setIntroRange(result.intro);
        if (result.outro) setOutroRange(result.outro);

        // Auto-select subtitle based on streamData and audio language
        if (result.subtitles && result.subtitles.length > 0) {
          if (audioLang === 'SUB') {
            const defSub = result.subtitles.find(s => s.default) || 
                           result.subtitles.find(s => s.label.toLowerCase().includes('en')) || 
                           result.subtitles[0];
            setSelectedSubtitle(defSub.label);
          } else {
            setSelectedSubtitle('Off');
          }
        } else {
          setSelectedSubtitle('Off');
        }

        if (result.sources && result.sources.length > 0) {
          const bestSource = result.sources[0];
          setSelectedServer(bestSource.serverName || 'HD-1');
          setActiveStreamUrl(bestSource.proxyUrl || bestSource.url);
        } else {
          // Fallback to sample video
          setActiveStreamUrl('https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/TearsOfSteel.mp4');
        }
      } catch (err: any) {
        if (isCancelled) return;
        console.warn('Live stream fetch error:', err);
        setActiveStreamUrl('https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/TearsOfSteel.mp4');
      } finally {
        if (!isCancelled) {
          setIsLoadingStream(false);
        }
      }
    };

    resolveStream();

    return () => {
      isCancelled = true;
    };
  }, [currentSlug, currentEpNum, audioLang]);

  // Background poll for all secondary server mirrors without restarting video playback
  useEffect(() => {
    if (!streamData?.hasMore) return;
    const timer = setTimeout(async () => {
      try {
        const fullResult = await fetchLiveEpisodeStream(currentSlug, currentEpNum, audioLang.toLowerCase() as 'sub' | 'dub');
        if (fullResult.sources && fullResult.sources.length > (streamData?.sources?.length || 0)) {
          setStreamData(prev => prev ? {
            ...prev,
            sources: fullResult.sources,
            hasMore: fullResult.hasMore,
          } : fullResult);
        }
      } catch (e) {
        console.debug('Background server poll error', e);
      }
    }, 2000);
    return () => clearTimeout(timer);
  }, [currentSlug, currentEpNum, audioLang, streamData?.hasMore, streamData?.sources?.length]);

  // 3. HLS STREAM ATTACH & PLAYBACK
  useEffect(() => {
    if (!videoRef.current || !activeStreamUrl) return;

    if (hlsRef.current) {
      hlsRef.current.destroy();
      hlsRef.current = null;
    }

    if ((activeStreamUrl.includes('.m3u8') || activeStreamUrl.includes('/api/stream/proxy')) && Hls.isSupported()) {
      const hls = new Hls({
        enableWorker: true,
        lowLatencyMode: true,
        backBufferLength: 90,
      });

      hls.loadSource(activeStreamUrl);
      hls.attachMedia(videoRef.current);

      hls.on(Hls.Events.MANIFEST_PARSED, (_event, data) => {
        const extracted: QualityOption[] = [
          { label: 'Auto', value: 'auto', levelIndex: -1 }
        ];

        if (data.levels && data.levels.length > 0) {
          const items: QualityOption[] = data.levels.map((lvl, idx) => {
            const h = lvl.height;
            const label = h > 0 ? `${h}p` : (lvl.name || `Level ${idx + 1}`);
            return {
              label,
              value: label.toLowerCase(),
              levelIndex: idx,
              height: h,
              bitrate: lvl.bitrate,
            };
          });

          // Deduplicate by label, keeping highest bitrate
          const map = new Map<string, QualityOption>();
          for (const it of items) {
            if (!map.has(it.label) || (it.bitrate || 0) > (map.get(it.label)?.bitrate || 0)) {
              map.set(it.label, it);
            }
          }
          const uniqueItems = Array.from(map.values());
          // Sort descending by height / resolution
          uniqueItems.sort((a, b) => (b.height || 0) - (a.height || 0));
          extracted.push(...uniqueItems);
        }

        setAvailableQualities(extracted);

        if (selectedQualityIndex === -1 && data.levels && data.levels.length > 0) {
          const firstH = data.levels[0].height;
          setQuality(firstH ? `Auto (${firstH}p)` : 'Auto');
        }

        videoRef.current?.play().catch(() => setIsPlaying(false));
      });

      hls.on(Hls.Events.LEVEL_SWITCHED, (_event, data) => {
        if (hls.levels && hls.levels[data.level]) {
          const lvl = hls.levels[data.level];
          if (lvl.height) {
            setCurrentActiveHeight(lvl.height);
            if (selectedQualityIndex === -1) {
              setQuality(`Auto (${lvl.height}p)`);
            }
          }
        }
      });

      hls.on(Hls.Events.ERROR, (_event, data) => {
        if (data.fatal) {
          switch (data.type) {
            case Hls.ErrorTypes.NETWORK_ERROR:
              hls.startLoad();
              break;
            case Hls.ErrorTypes.MEDIA_ERROR:
              hls.recoverMediaError();
              break;
            default:
              hls.destroy();
              break;
          }
        }
      });

      hlsRef.current = hls;
    } else {
      videoRef.current.src = activeStreamUrl;
      videoRef.current.play().catch(() => setIsPlaying(false));
    }

    return () => {
      if (hlsRef.current) {
        hlsRef.current.destroy();
        hlsRef.current = null;
      }
    };
  }, [activeStreamUrl]);

  // Synchronize Text Tracks / Subtitles with HTML5 video element & HLS engine
  useEffect(() => {
    if (!videoRef.current) return;
    const textTracks = videoRef.current.textTracks;

    // 1. Native HTML5 TextTracks (from <track> tags)
    if (textTracks && textTracks.length > 0) {
      for (let i = 0; i < textTracks.length; i++) {
        const track = textTracks[i];
        if (selectedSubtitle === 'Off') {
          track.mode = 'disabled';
        } else if (
          track.label.toLowerCase() === selectedSubtitle.toLowerCase() ||
          track.language.toLowerCase() === selectedSubtitle.toLowerCase()
        ) {
          track.mode = 'showing';
        } else {
          track.mode = 'disabled';
        }
      }
    }

    // 2. HLS Embedded Subtitle Tracks (if any stream contains internal subtitle tracks)
    if (hlsRef.current && hlsRef.current.subtitleTracks && hlsRef.current.subtitleTracks.length > 0) {
      if (selectedSubtitle === 'Off') {
        hlsRef.current.subtitleTrack = -1;
      } else {
        const subIdx = hlsRef.current.subtitleTracks.findIndex(
          t => t.name.toLowerCase() === selectedSubtitle.toLowerCase() ||
               t.lang?.toLowerCase() === selectedSubtitle.toLowerCase()
        );
        if (subIdx !== -1) {
          hlsRef.current.subtitleTrack = subIdx;
        }
      }
    }
  }, [selectedSubtitle, streamData]);

  const toggleSubtitleQuick = () => {
    if (selectedSubtitle !== 'Off') {
      setSelectedSubtitle('Off');
      onShowToast('Subtitles turned off');
    } else {
      const firstSub = streamData?.subtitles?.find(s => s.default) || 
                       streamData?.subtitles?.find(s => s.label.toLowerCase().includes('en')) || 
                       streamData?.subtitles?.[0];
      if (firstSub) {
        setSelectedSubtitle(firstSub.label);
        onShowToast(`Subtitles: ${firstSub.label}`);
      } else {
        onShowToast('No subtitles available for this stream');
      }
    }
  };

  // Handle keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (['input', 'textarea'].includes((e.target as HTMLElement).tagName.toLowerCase())) {
        return;
      }
      if (e.key === ' ' || e.key === 'k') {
        e.preventDefault();
        togglePlay();
      }
      if (e.key === 'f') toggleFullscreen();
      if (e.key === 'm') toggleMute();
      if (e.key === 'n') handlePlayNextEpisode();
      if (e.key === 'c' || e.key === 'C') {
        e.preventDefault();
        toggleSubtitleQuick();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isPlaying, isFullscreen, isMuted, selectedSubtitle, streamData]);

  // Save progress
  useEffect(() => {
    if (currentTime > 5 && duration > 0) {
      saveWatchProgress({
        animeSlug: currentSlug,
        episodeNumber: currentEpNum,
        currentTime,
        duration,
        completed: currentTime / duration > 0.9,
        lastWatchedAt: new Date().toISOString(),
      });
    }
  }, [currentTime, duration, currentEpNum, currentSlug]);

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

  const handleTimeUpdate = () => {
    if (videoRef.current) {
      const cur = videoRef.current.currentTime;
      setCurrentTime(cur);
      setDuration(videoRef.current.duration || 0);

      // Auto skip intro
      const targetEnd = introRange?.end || 85;
      if (autoSkipIntro && cur >= 5 && cur < targetEnd) {
        skipIntro();
      }
    }
  };

  const handleSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
    const time = parseFloat(e.target.value);
    setCurrentTime(time);
    if (videoRef.current) {
      videoRef.current.currentTime = time;
    }
  };

  const handleVolumeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = parseFloat(e.target.value);
    setVolume(val);
    if (videoRef.current) {
      videoRef.current.volume = val;
      videoRef.current.muted = val === 0;
      setIsMuted(val === 0);
    }
  };

  const toggleMute = () => {
    if (!videoRef.current) return;
    const nextMuted = !isMuted;
    setIsMuted(nextMuted);
    videoRef.current.muted = nextMuted;
  };

  const toggleFullscreen = () => {
    const container = document.getElementById('dedicated-player-container');
    if (!container) return;

    if (!document.fullscreenElement) {
      container.requestFullscreen().then(() => setIsFullscreen(true)).catch(() => {});
    } else {
      document.exitFullscreen().then(() => setIsFullscreen(false)).catch(() => {});
    }
  };

  const handleSpeedChange = (newSpeed: number) => {
    setSpeed(newSpeed);
    if (videoRef.current) {
      videoRef.current.playbackRate = newSpeed;
    }
    setShowSettings(false);
    onShowToast(`Speed set to ${newSpeed}x`);
  };

  const handleQualityChange = (opt: QualityOption) => {
    setSelectedQualityIndex(opt.levelIndex);
    
    if (hlsRef.current) {
      if (opt.levelIndex === -1) {
        // Auto adaptive switching
        hlsRef.current.currentLevel = -1;
        const activeLabel = currentActiveHeight ? ` (${currentActiveHeight}p)` : '';
        setQuality(`Auto${activeLabel}`);
        onShowToast('Quality set to Auto (Adaptive bitrate)');
      } else {
        // Explicit resolution lock
        hlsRef.current.currentLevel = opt.levelIndex;
        hlsRef.current.loadLevel = opt.levelIndex;
        setQuality(opt.label);
        onShowToast(`Switched resolution to ${opt.label}`);
      }
    } else {
      setQuality(opt.label);
      onShowToast(`Quality set to ${opt.label}`);
    }
  };

  const handleVideoLoadedMetadata = () => {
    if (!hlsRef.current && videoRef.current) {
      const h = videoRef.current.videoHeight;
      if (h > 0) {
        const label = h >= 1080 ? '1080p' : h >= 720 ? '720p' : h >= 480 ? '480p' : `${h}p`;
        setAvailableQualities([
          { label: 'Auto', value: 'auto', levelIndex: -1 },
          { label: `${label}`, value: label.toLowerCase(), levelIndex: 0, height: h }
        ]);
        setQuality(label);
      }
    }
  };

  const handleServerChange = (src: any) => {
    setSelectedServer(src.serverName);
    const savedTime = videoRef.current?.currentTime || currentTime || 0;
    setActiveStreamUrl(src.proxyUrl || src.url);
    setShowSettings(false);
    onShowToast(`Switched server to ${src.serverName}`);

    // Restore exact playback timestamp on new stream
    setTimeout(() => {
      if (videoRef.current && savedTime > 0) {
        videoRef.current.currentTime = savedTime;
      }
    }, 250);
  };

  const toggleAudioLang = () => {
    const nextLang = audioLang === 'SUB' ? 'DUB' : 'SUB';
    setAudioLang(nextLang);
    onShowToast(`Resolving ${nextLang} stream...`);
  };

  const skipIntro = () => {
    const target = introRange?.end || 85;
    if (videoRef.current) {
      videoRef.current.currentTime = target;
      setCurrentTime(target);
      onShowToast(`Skipped Intro to ${formatTime(target)}`);
    }
  };

  const skipOutro = () => {
    if (videoRef.current && duration > 0) {
      const target = duration - 5;
      videoRef.current.currentTime = target;
      setCurrentTime(target);
      onShowToast('Skipped Outro');
    }
  };

  const handlePlayNextEpisode = () => {
    const nextEp = currentEpNum + 1;
    navigate(`/watch/${currentSlug}/${nextEp}`);
    onShowToast(`Playing Episode ${nextEp}`);
  };

  const handleSelectEpisode = (epNum: number) => {
    navigate(`/watch/${currentSlug}/${epNum}`);
    onShowToast(`Switched to Episode ${epNum}`);
  };

  const handleLike = () => {
    if (isLiked) {
      setIsLiked(false);
      setLikesCount(prev => prev - 1);
    } else {
      setIsLiked(true);
      setLikesCount(prev => prev + 1);
      if (isDisliked) setIsDisliked(false);
      onShowToast('Added to Liked Videos');
    }
  };

  const handleDislike = () => {
    if (isDisliked) {
      setIsDisliked(false);
    } else {
      setIsDisliked(true);
      if (isLiked) {
        setIsLiked(false);
        setLikesCount(prev => prev - 1);
      }
    }
  };

  const handleSubscribe = () => {
    const next = !isSubscribed;
    setIsSubscribed(next);
    onShowToast(next ? `Subscribed to ${animeTitle}!` : `Unsubscribed from ${animeTitle}`);
  };

  const handleShare = () => {
    navigator.clipboard?.writeText(window.location.href);
    onShowToast('Video link copied to clipboard!');
  };

  const handleAddComment = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newCommentText.trim()) return;

    const newComment: Comment = {
      id: `c_${Date.now()}`,
      author: 'Darko',
      avatar: 'https://api.dicebear.com/7.x/avataaars/svg?seed=Darko',
      text: newCommentText.trim(),
      time: 'Just now',
      likes: 0,
      isLiked: false,
    };

    setComments(prev => [newComment, ...prev]);
    setNewCommentText('');
    onShowToast('Comment posted!');
  };

  const formatTime = (secs: number) => {
    const m = Math.floor(secs / 60);
    const s = Math.floor(secs % 60);
    return `${m}:${s < 10 ? '0' : ''}${s}`;
  };

  const currentEpisodeObj = seasonEpisodes.find(ep => ep.number === currentEpNum);
  const currentEpisodeTitle = currentEpisodeObj?.title || (animeTitle ? `${animeTitle} - Episode ${currentEpNum}` : `Episode ${currentEpNum}`);

  const showSkipIntroButton = introRange
    ? currentTime >= introRange.start && currentTime < introRange.end
    : currentTime < 85;

  const showSkipOutroButton = outroRange
    ? currentTime >= outroRange.start
    : duration > 120 && currentTime > duration - 90;

  return (
    <div className="min-h-screen bg-[#0f0f0f] text-white pt-4 pb-20">
      <div className="max-w-[1850px] mx-auto px-4 sm:px-6 lg:px-8 flex flex-col lg:flex-row gap-6">
        {/* Left Column: Player, Metadata, Comments */}
        <div className="flex-1 min-w-0 flex flex-col gap-4 relative">
          {/* YouTube-style Ambient Lighting Glow */}
          {ambientMode && (
            <div className="absolute top-0 left-0 right-0 h-[500px] bg-gradient-to-tr from-fuchsia-600/25 via-purple-600/15 to-cyan-500/25 blur-3xl rounded-3xl -z-10 pointer-events-none transition-opacity duration-700" />
          )}

          {/* Video Player Container */}
          <div
            id="dedicated-player-container"
            className="relative w-full aspect-video bg-black rounded-2xl overflow-hidden shadow-2xl border border-white/10 group select-none flex items-center justify-center"
          >
            {/* Live Loading Overlay */}
            {isLoadingStream && (
              <div className="absolute inset-0 z-30 bg-black/80 backdrop-blur-sm flex flex-col items-center justify-center gap-3">
                <Loader2 className="w-10 h-10 text-fuchsia-500 animate-spin" />
                <p className="text-sm font-bold text-white tracking-wide">
                  Decrypting & Streaming live HLS from AniMov Backend...
                </p>
                <span className="text-xs text-cyan-400">
                  Episode {currentEpNum} • {audioLang}
                </span>
              </div>
            )}

            {/* Error Message */}
            {streamError && !isLoadingStream && (
              <div className="absolute inset-0 z-30 bg-black/90 flex flex-col items-center justify-center gap-3 p-6 text-center">
                <AlertCircle className="w-10 h-10 text-red-500" />
                <h3 className="text-lg font-bold text-white">Stream Error</h3>
                <p className="text-sm text-gray-400 max-w-md">{streamError}</p>
                <button
                  onClick={() => navigate(0)}
                  className="px-4 py-2 rounded-full bg-fuchsia-500 text-white font-bold text-xs"
                >
                  Retry Stream
                </button>
              </div>
            )}

            <video
              ref={videoRef}
              crossOrigin="anonymous"
              onTimeUpdate={handleTimeUpdate}
              onLoadedMetadata={handleVideoLoadedMetadata}
              onEnded={handlePlayNextEpisode}
              onClick={togglePlay}
              className="w-full h-full object-contain cursor-pointer"
              playsInline
            >
              {streamData?.subtitles?.map((sub, idx) => (
                <track
                  key={`${sub.label}-${idx}`}
                  kind="subtitles"
                  label={sub.label}
                  srcLang={sub.lang || 'en'}
                  src={sub.proxyUrl || sub.file}
                  default={selectedSubtitle.toLowerCase() === sub.label.toLowerCase()}
                />
              ))}
            </video>

            {/* Skip Intro Floating Button */}
            {showSkipIntroButton && !isLoadingStream && (
              <button
                onClick={skipIntro}
                className="absolute top-4 right-4 z-20 flex items-center gap-1.5 px-3.5 py-2 rounded-full bg-black/80 hover:bg-fuchsia-600 text-white border border-fuchsia-500/40 text-xs font-bold transition-all shadow-lg hover:scale-105 active:scale-95"
              >
                <FastForward className="w-4 h-4 text-fuchsia-400 group-hover:text-white" />
                <span>Skip Intro {introRange ? `(${formatTime(introRange.end)})` : '(+85s)'}</span>
              </button>
            )}

            {/* Skip Outro Floating Button */}
            {showSkipOutroButton && !isLoadingStream && (
              <button
                onClick={skipOutro}
                className="absolute top-4 right-4 z-20 flex items-center gap-1.5 px-3.5 py-2 rounded-full bg-black/80 hover:bg-cyan-600 text-white border border-cyan-500/40 text-xs font-bold transition-all shadow-lg hover:scale-105 active:scale-95"
              >
                <FastForward className="w-4 h-4 text-cyan-400 group-hover:text-white" />
                <span>Skip Outro</span>
              </button>
            )}

            {/* In-Player Floating Server Badge (Top Left) */}
            <div className="absolute top-4 left-4 z-20 hidden sm:flex items-center gap-2 px-2.5 py-1 rounded-full bg-black/70 border border-white/10 text-[11px] text-gray-300 backdrop-blur-sm">
              <Server className="w-3.5 h-3.5 text-cyan-400" />
              <span>{selectedServer}</span>
              <span className="text-gray-500">•</span>
              <span className="text-fuchsia-400 font-semibold">{quality}</span>
            </div>

            {/* In-Player Bottom Control Bar */}
            <div className={`absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/95 via-black/60 to-transparent p-4 transition-opacity flex flex-col gap-2 z-30 ${showSettings ? 'opacity-100' : 'opacity-0 group-hover:opacity-100'}`}>
              {/* Progress Seek Bar */}
              <div className="relative flex items-center group/scrubber cursor-pointer">
                <input
                  type="range"
                  min={0}
                  max={duration || 100}
                  value={currentTime}
                  onChange={handleSeek}
                  className="w-full h-1.5 bg-white/20 hover:h-2.5 rounded-lg appearance-none cursor-pointer accent-fuchsia-500 transition-all"
                />
              </div>

              {/* Controls Row */}
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <button
                    onClick={togglePlay}
                    className="p-1.5 hover:bg-white/20 rounded-full text-white transition-colors"
                  >
                    {isPlaying ? <Pause className="w-5 h-5" /> : <Play className="w-5 h-5 fill-current" />}
                  </button>

                  <button
                    onClick={() => {
                      if (videoRef.current) videoRef.current.currentTime = Math.max(0, currentTime - 10);
                    }}
                    className="p-1.5 hover:bg-white/20 rounded-full text-gray-300 hover:text-white transition-colors"
                  >
                    <RotateCcw className="w-4 h-4" />
                  </button>

                  {/* Volume Slider */}
                  <div className="flex items-center gap-2 group/volume">
                    <button
                      onClick={toggleMute}
                      className="p-1.5 hover:bg-white/20 rounded-full text-white transition-colors"
                    >
                      {isMuted || volume === 0 ? <VolumeX className="w-5 h-5 text-red-400" /> : <Volume2 className="w-5 h-5" />}
                    </button>
                    <input
                      type="range"
                      min={0}
                      max={1}
                      step={0.05}
                      value={isMuted ? 0 : volume}
                      onChange={handleVolumeChange}
                      className="w-14 sm:w-20 h-1 bg-white/20 rounded-lg appearance-none cursor-pointer accent-fuchsia-500"
                    />
                  </div>

                  {/* Time Display */}
                  <div className="text-xs font-medium text-gray-300">
                    <span>{formatTime(currentTime)}</span>
                    <span className="mx-1 text-gray-500">/</span>
                    <span>{formatTime(duration)}</span>
                  </div>

                  {/* SUB / DUB Toggle Pill */}
                  <button
                    onClick={toggleAudioLang}
                    className={`ml-2 px-2.5 py-0.5 rounded-full text-xs font-extrabold tracking-wider transition-all border ${
                      audioLang === 'SUB'
                        ? 'bg-fuchsia-500/20 text-fuchsia-400 border-fuchsia-500/50 hover:bg-fuchsia-500/30'
                        : 'bg-cyan-500/20 text-cyan-400 border-cyan-500/50 hover:bg-cyan-500/30'
                    }`}
                  >
                    {audioLang}
                  </button>
                </div>

                {/* Right Player Buttons */}
                <div className="flex items-center gap-2">
                  <button
                    onClick={handlePlayNextEpisode}
                    title="Next Episode (N)"
                    className="hidden sm:flex items-center gap-1 px-2.5 py-1 rounded-lg hover:bg-white/10 text-xs font-semibold text-gray-300 hover:text-white transition-colors"
                  >
                    <FastForward className="w-4 h-4 text-cyan-400" />
                    <span>Next EP</span>
                  </button>

                  {/* YouTube-Style Subtitles / CC Quick Toggle */}
                  <button
                    onClick={toggleSubtitleQuick}
                    title={selectedSubtitle !== 'Off' ? `Subtitles: ${selectedSubtitle} (C to toggle)` : 'Subtitles Off (C to turn on)'}
                    className={`relative p-1.5 rounded-full transition-colors flex items-center justify-center ${
                      selectedSubtitle !== 'Off'
                        ? 'text-fuchsia-400 hover:text-fuchsia-300 hover:bg-white/10'
                        : 'text-gray-400 hover:text-white hover:bg-white/10'
                    }`}
                  >
                    <Subtitles className="w-5 h-5" />
                    {selectedSubtitle !== 'Off' && (
                      <span className="absolute bottom-1 w-3.5 h-[2px] bg-fuchsia-500 rounded-full" />
                    )}
                  </button>

                  {/* YouTube Multi-Level Settings */}
                  <div className="relative">
                    <button
                      onClick={() => setShowSettings(!showSettings)}
                      className="p-1.5 hover:bg-white/20 rounded-full text-gray-300 hover:text-white transition-colors"
                      title="Settings"
                    >
                      <Settings className="w-5 h-5" />
                    </button>

                    <PlayerSettingsMenu
                      isOpen={showSettings}
                      onClose={() => setShowSettings(false)}
                      speed={speed}
                      onSpeedChange={handleSpeedChange}
                      quality={quality}
                      selectedQualityIndex={selectedQualityIndex}
                      availableQualities={availableQualities}
                      onQualityChange={handleQualityChange}
                      selectedServer={selectedServer}
                      availableServers={(streamData?.sources || []).map(s => ({
                        name: s.serverName,
                        quality: s.quality,
                        raw: s,
                      }))}
                      onServerChange={handleServerChange}
                      audioLang={audioLang}
                      onAudioChange={(lang) => {
                        setAudioLang(lang);
                        onShowToast(`Switched audio to ${lang}`);
                      }}
                      autoSkipIntro={autoSkipIntro}
                      onToggleAutoSkipIntro={() => setAutoSkipIntro(!autoSkipIntro)}
                      autoSkipOutro={autoSkipOutro}
                      onToggleAutoSkipOutro={() => setAutoSkipOutro(!autoSkipOutro)}
                      ambientMode={ambientMode}
                      onToggleAmbientMode={() => setAmbientMode(!ambientMode)}
                      availableSubtitles={streamData?.subtitles || []}
                      selectedSubtitle={selectedSubtitle}
                      onSubtitleChange={(sub) => {
                        setSelectedSubtitle(sub);
                        onShowToast(sub === 'Off' ? 'Subtitles turned off' : `Subtitles set to ${sub}`);
                      }}
                    />
                  </div>

                  <button
                    onClick={toggleFullscreen}
                    className="p-1.5 hover:bg-white/20 rounded-full text-white transition-colors"
                  >
                    {isFullscreen ? <Minimize className="w-5 h-5" /> : <Maximize className="w-5 h-5" />}
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* Episode Title & Metadata Header */}
          <div className="flex flex-col gap-3">
            <h1 className="text-xl sm:text-2xl font-black text-white leading-tight">
              {currentEpisodeTitle}
            </h1>

            {/* Channel, Subscribe & Actions Row */}
            <div className="flex flex-wrap items-center justify-between gap-4 pb-2 border-b border-white/10">
              <div className="flex items-center gap-3">
                <Link to={`/anime/${currentSlug}`}>
                  <img
                    src={animePoster || 'https://images.unsplash.com/photo-1578632767115-351597cf2477?w=800&q=80'}
                    alt={animeTitle}
                    className="w-11 h-11 rounded-full object-cover border border-white/10 hover:ring-2 hover:ring-fuchsia-500 transition-all cursor-pointer"
                  />
                </Link>
                <div>
                  <Link 
                    to={`/anime/${currentSlug}`}
                    className="font-bold text-white text-sm sm:text-base leading-tight hover:text-fuchsia-400 cursor-pointer transition-colors"
                  >
                    {animeTitle}
                  </Link>
                  <p className="text-xs text-gray-400">
                    Official Franchise
                  </p>
                </div>

                <button
                  onClick={handleSubscribe}
                  className={`ml-3 px-5 py-2 rounded-full font-bold text-sm transition-all shadow-md active:scale-95 ${
                    isSubscribed
                      ? 'bg-white/10 hover:bg-white/20 text-gray-300'
                      : 'bg-white text-black hover:bg-gray-200 shadow-white/20'
                  }`}
                >
                  {isSubscribed ? 'Following' : 'Follow Anime'}
                </button>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center gap-2 flex-wrap">
                <div className="flex items-center bg-white/5 border border-white/10 rounded-full overflow-hidden">
                  <button
                    onClick={handleLike}
                    className={`flex items-center gap-2 px-4 py-2 text-sm font-semibold transition-colors hover:bg-white/10 ${
                      isLiked ? 'text-fuchsia-400 bg-fuchsia-500/10' : 'text-white'
                    }`}
                  >
                    <ThumbsUp className={`w-4 h-4 ${isLiked ? 'fill-current' : ''}`} />
                    <span>{likesCount.toLocaleString()}</span>
                  </button>
                  <div className="w-px h-5 bg-white/10" />
                  <button
                    onClick={handleDislike}
                    className={`px-3 py-2 text-sm font-semibold transition-colors hover:bg-white/10 ${
                      isDisliked ? 'text-fuchsia-400 bg-fuchsia-500/10' : 'text-white'
                    }`}
                  >
                    <ThumbsDown className={`w-4 h-4 ${isDisliked ? 'fill-current' : ''}`} />
                  </button>
                </div>

                <button
                  onClick={handleShare}
                  className="flex items-center gap-2 px-4 py-2 bg-white/5 hover:bg-white/10 border border-white/10 rounded-full text-sm font-semibold text-white transition-colors"
                >
                  <Share2 className="w-4 h-4" />
                  <span className="hidden sm:inline">Share</span>
                </button>

                <button
                  onClick={() => onShowToast('Saved to Watchlist!')}
                  className="flex items-center gap-2 px-4 py-2 bg-white/5 hover:bg-white/10 border border-white/10 rounded-full text-sm font-semibold text-white transition-all"
                >
                  <Bookmark className="w-4 h-4" />
                  <span>Watchlist</span>
                </button>
              </div>
            </div>
          </div>

          {/* Description Box */}
          <div className="bg-[#181818] rounded-2xl p-4 border border-white/5">
            <div className="flex items-center gap-3 text-sm font-semibold text-gray-300 mb-2">
              <span>Episode {currentEpNum}</span>
              <span>•</span>
              <span className="text-cyan-400 font-bold">{audioLang} [1080p]</span>
              <span>•</span>
              <span>AniMov Stream Engine</span>
            </div>

            <p className={`text-gray-300 text-sm leading-relaxed ${isDescExpanded ? '' : 'line-clamp-2'}`}>
              {animeSynopsis || `Watch ${animeTitle} Episode ${currentEpNum} with decrypted HLS streams on AniTube.`}
            </p>

            <button
              onClick={() => setIsDescExpanded(!isDescExpanded)}
              className="mt-2 text-xs font-bold text-fuchsia-400 hover:text-fuchsia-300 flex items-center gap-1 transition-colors"
            >
              {isDescExpanded ? (
                <>Show less <ChevronUp className="w-3.5 h-3.5" /></>
              ) : (
                <>Show more <ChevronDown className="w-3.5 h-3.5" /></>
              )}
            </button>
          </div>

          {/* Comments Section */}
          <div className="mt-4">
            <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
              <span>{comments.length} Comments</span>
            </h3>

            <form onSubmit={handleAddComment} className="flex gap-3 mb-6">
              <img
                src="https://api.dicebear.com/7.x/avataaars/svg?seed=Darko"
                alt="Darko"
                className="w-10 h-10 rounded-full border border-white/10 flex-shrink-0"
              />
              <div className="flex-1 flex flex-col gap-2">
                <input
                  type="text"
                  value={newCommentText}
                  onChange={(e) => setNewCommentText(e.target.value)}
                  placeholder="Share your thoughts on this episode..."
                  className="w-full bg-[#141414] border-b border-white/20 focus:border-fuchsia-500 text-sm text-white px-3 py-2 outline-none rounded-lg transition-colors placeholder:text-gray-500"
                />
                {newCommentText && (
                  <div className="flex justify-end gap-2">
                    <button
                      type="button"
                      onClick={() => setNewCommentText('')}
                      className="px-3 py-1.5 text-xs text-gray-400 hover:text-white"
                    >
                      Cancel
                    </button>
                    <button
                      type="submit"
                      className="px-4 py-1.5 bg-fuchsia-500 hover:bg-fuchsia-600 text-white rounded-full text-xs font-bold transition-all shadow-md flex items-center gap-1"
                    >
                      <Send className="w-3 h-3" /> Comment
                    </button>
                  </div>
                )}
              </div>
            </form>

            <div className="space-y-4">
              {comments.map((c) => (
                <div key={c.id} className="flex gap-3">
                  <img
                    src={c.avatar}
                    alt={c.author}
                    className="w-9 h-9 rounded-full object-cover border border-white/10 flex-shrink-0"
                  />
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-semibold text-white">
                        {c.author}
                      </span>
                      <span className="text-xs text-gray-500">
                        {c.time}
                      </span>
                    </div>
                    <p className="text-sm text-gray-300 mt-1 leading-snug">
                      {c.text}
                    </p>
                    <div className="flex items-center gap-3 mt-2">
                      <button
                        className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-white transition-colors"
                      >
                        <ThumbsUp className="w-3.5 h-3.5" />
                        <span>{c.likes}</span>
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right Column: Tabbed Hybrid Sidebar (Episodes + Recommendations) */}
        <div className="w-full lg:w-96 flex-shrink-0 flex flex-col gap-3">
          <div className="flex items-center p-1 bg-white/5 border border-white/10 rounded-xl">
            <button
              onClick={() => setSidebarTab('episodes')}
              className={`flex-1 flex items-center justify-center gap-2 py-2 rounded-lg text-xs font-bold transition-all ${
                sidebarTab === 'episodes'
                  ? 'bg-fuchsia-500 text-white shadow-md'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              <ListVideo className="w-4 h-4" />
              <span>Episodes {isLoadingAnime ? '...' : `(${seasonEpisodes.length})`}</span>
            </button>

            <button
              onClick={() => setSidebarTab('recommendations')}
              className={`flex-1 flex items-center justify-center gap-2 py-2 rounded-lg text-xs font-bold transition-all ${
                sidebarTab === 'recommendations'
                  ? 'bg-fuchsia-500 text-white shadow-md'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              <Sparkles className="w-4 h-4" />
              <span>Recommended</span>
            </button>
          </div>

          {/* TAB 1: Episodes List */}
          {sidebarTab === 'episodes' && (
            <div className="flex flex-col gap-2 max-h-[800px] overflow-y-auto custom-scrollbar pr-1">
              <div className="flex items-center justify-between px-1 text-xs text-gray-400 font-semibold mb-1">
                <span>Season 1</span>
                <span>Auto-next ON</span>
              </div>

              {isLoadingAnime ? (
                <div className="flex flex-col gap-2">
                  {[1, 2, 3, 4, 5, 6].map(n => (
                    <div key={n} className="flex gap-3 p-2 rounded-xl border border-white/5 bg-white/5 animate-pulse">
                      <div className="w-32 aspect-video rounded-lg bg-white/10 flex-shrink-0" />
                      <div className="flex-1 flex flex-col justify-center gap-2">
                        <div className="h-4 bg-white/10 rounded w-3/4" />
                        <div className="h-3 bg-white/10 rounded w-1/2" />
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                seasonEpisodes.map((ep) => (
                <div
                  key={ep.id}
                  onClick={() => handleSelectEpisode(ep.number)}
                  className={`flex gap-3 group cursor-pointer p-2 rounded-xl transition-all border ${
                    ep.number === currentEpNum
                      ? 'bg-fuchsia-500/15 border-fuchsia-500/40'
                      : 'hover:bg-white/5 border-transparent'
                  }`}
                >
                  <div className="relative w-32 aspect-video rounded-lg overflow-hidden flex-shrink-0 bg-gray-800">
                    <img
                      src={ep.thumbnail || animePoster}
                      alt={ep.title}
                      className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                    />
                    <span className="absolute bottom-1 right-1 px-1 bg-black/80 text-[10px] text-white rounded font-medium">
                      {ep.duration}
                    </span>
                    {ep.number === currentEpNum && (
                      <div className="absolute inset-0 bg-fuchsia-500/30 flex items-center justify-center">
                        <Play className="w-5 h-5 text-white fill-current animate-pulse" />
                      </div>
                    )}
                  </div>
                  <div className="flex-1 min-w-0 flex flex-col justify-center">
                    <div className="flex items-center gap-1.5">
                      <span className={`text-xs font-extrabold ${ep.number === currentEpNum ? 'text-fuchsia-400' : 'text-gray-400'}`}>
                        EP {ep.number}
                      </span>
                      {ep.number === currentEpNum && (
                        <span className="text-[10px] px-1.5 py-0.2 rounded bg-fuchsia-500 text-white font-bold">
                          PLAYING
                        </span>
                      )}
                    </div>
                    <h4 className="text-xs font-semibold text-white line-clamp-1 mt-0.5 group-hover:text-fuchsia-400 transition-colors">
                      {ep.title}
                    </h4>
                    <p className="text-[11px] text-gray-500 mt-0.5">
                      SUB / DUB • 1080p
                    </p>
                  </div>
                </div>
              ))
              )}
            </div>
          )}

          {/* TAB 2: Recommended Anime Videos */}
          {sidebarTab === 'recommendations' && (
            <div className="flex flex-col gap-3 max-h-[800px] overflow-y-auto custom-scrollbar pr-1">
              {[
                { slug: '5xxCxNSHUK', title: 'Attack on Titan Season 3', ep: 1, duration: '24:00', poster: 'https://images.unsplash.com/photo-1578632767115-351597cf2477?w=800&q=80' },
                { slug: 'oui9FXBSdF', title: 'Demon Slayer: Kimetsu no Yaiba', ep: 1, duration: '23:45', poster: 'https://images.unsplash.com/photo-1563089145-599997674d42?w=800&q=80' },
                { slug: 'xRCywW7USh', title: 'JUJUTSU KAISEN Season 2', ep: 1, duration: '24:12', poster: 'https://images.unsplash.com/photo-1534447677768-be436bb09401?w=800&q=80' },
                { slug: 'ARPEGZW3fK', title: 'ONE PIECE: Egghead Arc', ep: 1100, duration: '23:50', poster: 'https://images.unsplash.com/photo-1518709268805-4e9042af9f23?w=800&q=80' },
              ].map((item) => (
                <div
                  key={item.slug}
                  onClick={() => navigate(`/watch/${item.slug}/${item.ep}`)}
                  className="flex gap-3 group cursor-pointer p-2 rounded-xl hover:bg-white/5 transition-colors border border-transparent hover:border-white/5"
                >
                  <div className="relative w-36 aspect-video rounded-lg overflow-hidden flex-shrink-0 bg-gray-800">
                    <img
                      src={item.poster}
                      alt={item.title}
                      className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                    />
                    <span className="absolute bottom-1 right-1 px-1 bg-black/80 text-[10px] text-white rounded font-medium">
                      {item.duration}
                    </span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <h4 className="text-xs sm:text-sm font-semibold text-white line-clamp-2 leading-tight group-hover:text-fuchsia-400 transition-colors">
                      {item.title}
                    </h4>
                    <p className="text-xs text-gray-400 mt-1 truncate">
                      Episode {item.ep}
                    </p>
                    <p className="text-[11px] text-gray-500 mt-0.5">
                      1.2M views • Recently aired
                    </p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
