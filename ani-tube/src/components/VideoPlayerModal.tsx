import React, { useState, useRef, useEffect, useMemo } from 'react';
import Hls from 'hls.js';
import { 
  X, 
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
  Subtitles
} from 'lucide-react';
import { Video, Comment } from '../types';
import { saveWatchProgress, fetchLiveEpisodeStream, StreamResolutionResult } from '../services/api';
import { PlayerSettingsMenu, QualityOption } from './PlayerSettingsMenu';

interface VideoPlayerModalProps {
  video: Video | null;
  onClose: () => void;
  onPlayNext: (video: Video) => void;
  allVideos: Video[];
  onToggleSave: (video: Video) => void;
  isSaved: boolean;
  onShowToast: (message: string) => void;
}

export const VideoPlayerModal: React.FC<VideoPlayerModalProps> = ({
  video,
  onClose,
  onPlayNext,
  allVideos,
  onToggleSave,
  isSaved,
  onShowToast
}) => {
  if (!video) return null;

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

  // Stream Resolution & Loading state
  const [isLoadingStream, setIsLoadingStream] = useState(true);
  const [streamError, setStreamError] = useState<string | null>(null);
  const [activeStreamUrl, setActiveStreamUrl] = useState<string>('');
  const [streamData, setStreamData] = useState<StreamResolutionResult | null>(null);

  // Anime specific controls state
  const [audioLang, setAudioLang] = useState<'SUB' | 'DUB'>('SUB');
  const [selectedServer, setSelectedServer] = useState('HD-1 (Megaplay)');
  const [autoSkipIntro, setAutoSkipIntro] = useState(false);
  const [autoSkipOutro, setAutoSkipOutro] = useState(false);
  const [ambientMode, setAmbientMode] = useState(true);
  const [selectedSubtitle, setSelectedSubtitle] = useState('Off');

  // Intro / Outro markers
  const [introRange, setIntroRange] = useState<{ start: number; end: number } | null>(null);
  const [outroRange, setOutroRange] = useState<{ start: number; end: number } | null>(null);

  // Right sidebar tab state: 'episodes' | 'recommendations'
  const [sidebarTab, setSidebarTab] = useState<'episodes' | 'recommendations'>('episodes');

  // Likes & subscription state
  const [likesCount, setLikesCount] = useState(video.likes);
  const [isLiked, setIsLiked] = useState(video.isLiked || false);
  const [isDisliked, setIsDisliked] = useState(video.isDisliked || false);
  const [isSubscribed, setIsSubscribed] = useState(video.isSubscribed || false);

  // Description expand/collapse
  const [isDescExpanded, setIsDescExpanded] = useState(false);

  // Episode state
  const [currentEp, setCurrentEp] = useState(video.ep || 1);

  // Comments state
  const [comments, setComments] = useState<Comment[]>(video.comments || []);
  const [newCommentText, setNewCommentText] = useState('');

  // 1. LIVE ON-DEMAND STREAM RESOLUTION FROM BACKEND
  useEffect(() => {
    let isCancelled = false;
    const animeSlug = video.animeSlug || video.slug || video.channel.toLowerCase().replace(/\s+/g, '-');

    const resolveStream = async () => {
      setIsLoadingStream(true);
      setStreamError(null);

      try {
        const result = await fetchLiveEpisodeStream(animeSlug, currentEp, audioLang.toLowerCase() as 'sub' | 'dub');
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
          // Use proxied m3u8 url to guarantee zero CORS/referer blocks
          const bestSource = result.sources[0];
          setSelectedServer(bestSource.serverName || 'HD-1');
          setActiveStreamUrl(bestSource.proxyUrl || bestSource.url);
        } else if (video.videoUrl) {
          // Fallback to initial video url if provider had no sources
          setActiveStreamUrl(video.videoUrl);
        } else {
          setStreamError('No live stream sources available for this episode.');
        }
      } catch (err: any) {
        if (isCancelled) return;
        console.warn('Live stream fetch fallback:', err);
        if (video.videoUrl) {
          setActiveStreamUrl(video.videoUrl);
        } else {
          setStreamError('Could not connect to AniMov stream resolver.');
        }
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
  }, [video, currentEp, audioLang]);

  // Background poll for all secondary server mirrors without restarting video playback
  useEffect(() => {
    if (!streamData?.hasMore) return;
    const animeSlug = video.animeSlug || video.slug || video.channel.toLowerCase().replace(/\s+/g, '-');
    const timer = setTimeout(async () => {
      try {
        const fullResult = await fetchLiveEpisodeStream(animeSlug, currentEp, audioLang.toLowerCase() as 'sub' | 'dub');
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
  }, [streamData?.hasMore, video, currentEp, audioLang]);

  // 2. HLS STREAM ATTACH & PLAYBACK
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

          const map = new Map<string, QualityOption>();
          for (const it of items) {
            if (!map.has(it.label) || (it.bitrate || 0) > (map.get(it.label)?.bitrate || 0)) {
              map.set(it.label, it);
            }
          }
          const uniqueItems = Array.from(map.values());
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

  // Sync state when video prop changes
  useEffect(() => {
    setLikesCount(video.likes);
    setIsLiked(video.isLiked || false);
    setIsDisliked(video.isDisliked || false);
    setIsSubscribed(video.isSubscribed || false);
    setCurrentEp(video.ep || 1);
    setComments(video.comments || []);
    setIsPlaying(true);
    setCurrentTime(0);
  }, [video]);

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

    // 2. HLS Embedded Subtitle Tracks (if any)
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
      if (e.key === 'Escape') onClose();
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

  // Watch progress sync
  useEffect(() => {
    if (currentTime > 5 && duration > 0) {
      saveWatchProgress({
        animeSlug: video.animeSlug || video.slug || video.channel.toLowerCase().replace(/\s+/g, '-'),
        episodeNumber: currentEp,
        currentTime,
        duration,
        completed: currentTime / duration > 0.9,
        lastWatchedAt: new Date().toISOString(),
      });
    }
  }, [currentTime, duration, currentEp, video]);

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

      // Auto skip intro if toggled
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
    const container = document.getElementById('anime-player-container');
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
        hlsRef.current.currentLevel = -1;
        const activeLabel = currentActiveHeight ? ` (${currentActiveHeight}p)` : '';
        setQuality(`Auto${activeLabel}`);
        onShowToast('Quality set to Auto (Adaptive bitrate)');
      } else {
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
    onShowToast(next ? `Subscribed to ${video.channel}!` : `Unsubscribed from ${video.channel}`);
  };

  const handleShare = () => {
    navigator.clipboard?.writeText(window.location.href);
    onShowToast('Link copied to clipboard!');
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

  const toggleCommentLike = (commentId: string) => {
    setComments(prev =>
      prev.map(c => {
        if (c.id === commentId) {
          const isLikedNow = !c.isLiked;
          return {
            ...c,
            isLiked: isLikedNow,
            likes: isLikedNow ? c.likes + 1 : c.likes - 1,
          };
        }
        return c;
      })
    );
  };

  const formatTime = (secs: number) => {
    const m = Math.floor(secs / 60);
    const s = Math.floor(secs % 60);
    return `${m}:${s < 10 ? '0' : ''}${s}`;
  };

  // Season episodes calculation
  const seasonEpisodes = useMemo(() => {
    const currentAnimeName = video.channel || video.animeTitle || video.title.split(' - ')[0];
    const list: Array<{ id: number; number: number; title: string; duration: string; thumbnail: string; active?: boolean }> = [];
    
    const totalEps = 12;
    for (let i = 1; i <= totalEps; i++) {
      list.push({
        id: video.id * 100 + i,
        number: i,
        title: i === currentEp ? video.title : `${currentAnimeName} - Episode ${i}`,
        duration: '24:00',
        thumbnail: video.thumbnail,
        active: i === currentEp,
      });
    }
    return list;
  }, [video, currentEp]);

  const handlePlayNextEpisode = () => {
    const nextEpNum = currentEp + 1;
    setCurrentEp(nextEpNum);
    onShowToast(`Resolving Episode ${nextEpNum}...`);
  };

  const handleSelectEpisode = (epNum: number) => {
    setCurrentEp(epNum);
    onShowToast(`Resolving Episode ${epNum}...`);
  };

  // Recommendations
  const recommendedVideos = useMemo(() => {
    return allVideos.filter(v => v.id !== video.id).slice(0, 8);
  }, [allVideos, video.id]);

  // Intro & Outro button flags
  const showSkipIntroButton = introRange
    ? currentTime >= introRange.start && currentTime < introRange.end
    : currentTime < 85;

  const showSkipOutroButton = outroRange
    ? currentTime >= outroRange.start
    : duration > 120 && currentTime > duration - 90;

  return (
    <div className="fixed inset-0 z-50 bg-[#0a0a0a]/95 backdrop-blur-md overflow-y-auto flex flex-col items-center">
      {/* Top Header Bar */}
      <div className="w-full max-w-[1700px] h-14 flex items-center justify-between px-4 sm:px-6 border-b border-white/10 flex-shrink-0">
        <div className="flex items-center gap-3">
          <span className="px-2.5 py-0.5 rounded-full text-xs font-black tracking-wide bg-fuchsia-600/30 text-fuchsia-400 border border-fuchsia-500/30">
            EPISODE {currentEp} [{audioLang}]
          </span>
          <h2 className="text-sm sm:text-base font-bold text-white truncate max-w-xs sm:max-w-xl">
            {video.title}
          </h2>
        </div>

        <button
          onClick={onClose}
          className="p-2 rounded-full hover:bg-white/10 text-gray-400 hover:text-white transition-colors"
        >
          <X className="w-6 h-6" />
        </button>
      </div>

      {/* Main Content Area */}
      <div className="w-full max-w-[1700px] flex-1 flex flex-col lg:flex-row gap-6 p-4 sm:p-6">
        {/* Left Column: Player & Info */}
        <div className="flex-1 min-w-0 flex flex-col gap-4 relative">
          {/* YouTube-style Ambient Lighting Glow */}
          {ambientMode && (
            <div className="absolute top-0 left-0 right-0 h-[480px] bg-gradient-to-tr from-fuchsia-600/25 via-purple-600/15 to-cyan-500/25 blur-3xl rounded-3xl -z-10 pointer-events-none transition-opacity duration-700" />
          )}

          {/* Video Player Container */}
          <div
            id="anime-player-container"
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
                  Episode {currentEp} • {audioLang}
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
                  onClick={() => setCurrentEp(currentEp)}
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

            {/* In-Player Overlay: Skip Intro Button */}
            {showSkipIntroButton && !isLoadingStream && (
              <button
                onClick={skipIntro}
                className="absolute top-4 right-4 z-20 flex items-center gap-1.5 px-3.5 py-2 rounded-full bg-black/80 hover:bg-fuchsia-600 text-white border border-fuchsia-500/40 text-xs font-bold transition-all shadow-lg hover:scale-105 active:scale-95"
              >
                <FastForward className="w-4 h-4 text-fuchsia-400 group-hover:text-white" />
                <span>Skip Intro {introRange ? `(${formatTime(introRange.end)})` : '(+85s)'}</span>
              </button>
            )}

            {/* In-Player Overlay: Skip Outro Button */}
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
                  {/* Next Episode Button */}
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

                  {/* Settings Menu Button & YouTube-Style Multi-Level Modal */}
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

                  {/* Fullscreen Button */}
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
              {video.title}
            </h1>

            {/* Channel, Subscribe & Actions Row */}
            <div className="flex flex-wrap items-center justify-between gap-4 pb-2 border-b border-white/10">
              <div className="flex items-center gap-3">
                <img
                  src={video.channelAvatar}
                  alt={video.channel}
                  className="w-11 h-11 rounded-full object-cover border border-white/10"
                />
                <div>
                  <h3 className="font-bold text-white text-sm sm:text-base leading-tight hover:text-fuchsia-400 cursor-pointer">
                    {video.channel}
                  </h3>
                  <p className="text-xs text-gray-400">
                    {video.subscribers} followers
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

              {/* Action Buttons (Like, Dislike, Share, Save) */}
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
                  onClick={() => onToggleSave(video)}
                  className={`flex items-center gap-2 px-4 py-2 border rounded-full text-sm font-semibold transition-all ${
                    isSaved
                      ? 'bg-fuchsia-500 text-white border-fuchsia-400'
                      : 'bg-white/5 hover:bg-white/10 border-white/10 text-white'
                  }`}
                >
                  {isSaved ? <Check className="w-4 h-4" /> : <Bookmark className="w-4 h-4" />}
                  <span>{isSaved ? 'In Watchlist' : 'Watchlist'}</span>
                </button>
              </div>
            </div>
          </div>

          {/* Description Box */}
          <div className="bg-[#181818] rounded-2xl p-4 border border-white/5">
            <div className="flex items-center gap-3 text-sm font-semibold text-gray-300 mb-2">
              <span>{video.views} views</span>
              <span>•</span>
              <span>{video.time}</span>
              <span>•</span>
              <span className="text-cyan-400 font-bold">{video.category}</span>
            </div>

            <p className={`text-gray-300 text-sm leading-relaxed ${isDescExpanded ? '' : 'line-clamp-2'}`}>
              {video.description}
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

            {/* Post New Comment */}
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
                  placeholder="Share your thoughts or theories on this episode..."
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

            {/* Comments List */}
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
                        onClick={() => toggleCommentLike(c.id)}
                        className={`flex items-center gap-1.5 text-xs transition-colors ${
                          c.isLiked ? 'text-fuchsia-400 font-bold' : 'text-gray-400 hover:text-white'
                        }`}
                      >
                        <ThumbsUp className={`w-3.5 h-3.5 ${c.isLiked ? 'fill-current' : ''}`} />
                        <span>{c.likes > 0 ? c.likes : 'Like'}</span>
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
          {/* Tabs Selector Bar */}
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
              <span>Episodes ({seasonEpisodes.length})</span>
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
            <div className="flex flex-col gap-2 max-h-[750px] overflow-y-auto custom-scrollbar pr-1">
              <div className="flex items-center justify-between px-1 text-xs text-gray-400 font-semibold mb-1">
                <span>Season 1</span>
                <span>Auto-next ON</span>
              </div>

              {seasonEpisodes.map((ep) => (
                <div
                  key={ep.id}
                  onClick={() => handleSelectEpisode(ep.number)}
                  className={`flex gap-3 group cursor-pointer p-2 rounded-xl transition-all border ${
                    ep.number === currentEp
                      ? 'bg-fuchsia-500/15 border-fuchsia-500/40'
                      : 'hover:bg-white/5 border-transparent'
                  }`}
                >
                  <div className="relative w-32 aspect-video rounded-lg overflow-hidden flex-shrink-0 bg-gray-800">
                    <img
                      src={ep.thumbnail}
                      alt={ep.title}
                      className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                    />
                    <span className="absolute bottom-1 right-1 px-1 bg-black/80 text-[10px] text-white rounded font-medium">
                      {ep.duration}
                    </span>
                    {ep.number === currentEp && (
                      <div className="absolute inset-0 bg-fuchsia-500/30 flex items-center justify-center">
                        <Play className="w-5 h-5 text-white fill-current animate-pulse" />
                      </div>
                    )}
                  </div>
                  <div className="flex-1 min-w-0 flex flex-col justify-center">
                    <div className="flex items-center gap-1.5">
                      <span className={`text-xs font-extrabold ${ep.number === currentEp ? 'text-fuchsia-400' : 'text-gray-400'}`}>
                        EP {ep.number}
                      </span>
                      {ep.number === currentEp && (
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
              ))}
            </div>
          )}

          {/* TAB 2: Recommended Anime Videos */}
          {sidebarTab === 'recommendations' && (
            <div className="flex flex-col gap-3 max-h-[750px] overflow-y-auto custom-scrollbar pr-1">
              {recommendedVideos.map((item) => (
                <div
                  key={item.id}
                  onClick={() => onPlayNext(item)}
                  className="flex gap-3 group cursor-pointer p-2 rounded-xl hover:bg-white/5 transition-colors border border-transparent hover:border-white/5"
                >
                  <div className="relative w-36 aspect-video rounded-lg overflow-hidden flex-shrink-0 bg-gray-800">
                    <img
                      src={item.thumbnail}
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
                      {item.channel}
                    </p>
                    <p className="text-[11px] text-gray-500 mt-0.5">
                      {item.views} • {item.time}
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
