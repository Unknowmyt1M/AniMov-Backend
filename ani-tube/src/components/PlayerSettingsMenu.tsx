import React, { useState } from 'react';
import { 
  ChevronRight, 
  ChevronLeft, 
  Check, 
  Gauge, 
  Sliders, 
  Server, 
  Headphones, 
  Subtitles, 
  FastForward, 
  Sparkles
} from 'lucide-react';

export type SettingsSubmenu = 'main' | 'speed' | 'quality' | 'server' | 'audio' | 'subtitles';

export interface QualityOption {
  label: string;
  value: string;
  levelIndex: number;
  height?: number;
  bitrate?: number;
}

interface PlayerSettingsMenuProps {
  isOpen: boolean;
  onClose: () => void;
  speed: number;
  onSpeedChange: (speed: number) => void;
  quality: string;
  selectedQualityIndex?: number;
  availableQualities?: QualityOption[];
  onQualityChange: (option: QualityOption) => void;
  selectedServer: string;
  availableServers: Array<{ name: string; quality?: string; raw: any }>;
  onServerChange: (serverObj: any) => void;
  audioLang: 'SUB' | 'DUB';
  onAudioChange: (lang: 'SUB' | 'DUB') => void;
  autoSkipIntro: boolean;
  onToggleAutoSkipIntro: () => void;
  autoSkipOutro: boolean;
  onToggleAutoSkipOutro: () => void;
  ambientMode?: boolean;
  onToggleAmbientMode?: () => void;
  availableSubtitles?: Array<{ label: string; file: string; lang: string }>;
  selectedSubtitle?: string;
  onSubtitleChange?: (sub: string) => void;
}

export const PlayerSettingsMenu: React.FC<PlayerSettingsMenuProps> = ({
  isOpen,
  onClose,
  speed,
  onSpeedChange,
  quality,
  selectedQualityIndex = -1,
  availableQualities = [],
  onQualityChange,
  selectedServer,
  availableServers,
  onServerChange,
  audioLang,
  onAudioChange,
  autoSkipIntro,
  onToggleAutoSkipIntro,
  autoSkipOutro,
  onToggleAutoSkipOutro,
  ambientMode = true,
  onToggleAmbientMode,
  availableSubtitles = [],
  selectedSubtitle = 'Off',
  onSubtitleChange,
}) => {
  const [currentView, setCurrentView] = useState<SettingsSubmenu>('main');

  if (!isOpen) return null;

  const speedOptions = [
    { label: '0.25x', value: 0.25 },
    { label: '0.5x', value: 0.5 },
    { label: '0.75x', value: 0.75 },
    { label: 'Normal (1x)', value: 1.0 },
    { label: '1.25x', value: 1.25 },
    { label: '1.5x', value: 1.5 },
    { label: '1.75x', value: 1.75 },
    { label: '2x', value: 2.0 },
  ];

  const audioOptions: Array<{ label: string; value: 'SUB' | 'DUB' }> = [
    { label: 'Japanese [Original] (SUB)', value: 'SUB' },
    { label: 'English (DUB)', value: 'DUB' },
  ];

  const formatSpeedLabel = (s: number) => {
    return s === 1 ? 'Normal' : `${s}x`;
  };

  return (
    <div 
      onClick={(e) => e.stopPropagation()}
      className="absolute right-0 bottom-14 w-72 sm:w-80 bg-[#1a1a1e]/95 backdrop-blur-xl border border-white/10 rounded-2xl shadow-2xl p-2 z-40 text-white font-sans text-xs select-none animate-in fade-in zoom-in-95 duration-150"
    >
      {/* 1. MAIN MENU VIEW */}
      {currentView === 'main' && (
        <div className="flex flex-col gap-0.5">
          {/* Quality Row */}
          <div
            onClick={() => setCurrentView('quality')}
            className="flex items-center justify-between px-3 py-2.5 rounded-xl hover:bg-white/10 cursor-pointer transition-colors"
          >
            <div className="flex items-center gap-3 text-gray-200">
              <Sliders className="w-4 h-4 text-gray-400" />
              <span className="font-medium text-xs">Quality</span>
            </div>
            <div className="flex items-center gap-1.5 text-gray-400">
              <span className="font-semibold text-fuchsia-400">{quality}</span>
              <ChevronRight className="w-3.5 h-3.5" />
            </div>
          </div>

          {/* Playback Speed Row */}
          <div
            onClick={() => setCurrentView('speed')}
            className="flex items-center justify-between px-3 py-2.5 rounded-xl hover:bg-white/10 cursor-pointer transition-colors"
          >
            <div className="flex items-center gap-3 text-gray-200">
              <Gauge className="w-4 h-4 text-gray-400" />
              <span className="font-medium text-xs">Playback speed</span>
            </div>
            <div className="flex items-center gap-1.5 text-gray-400">
              <span className="font-semibold">{formatSpeedLabel(speed)}</span>
              <ChevronRight className="w-3.5 h-3.5" />
            </div>
          </div>

          {/* Audio Language (SUB / DUB) Row */}
          <div
            onClick={() => setCurrentView('audio')}
            className="flex items-center justify-between px-3 py-2.5 rounded-xl hover:bg-white/10 cursor-pointer transition-colors"
          >
            <div className="flex items-center gap-3 text-gray-200">
              <Headphones className="w-4 h-4 text-gray-400" />
              <span className="font-medium text-xs">Audio track</span>
            </div>
            <div className="flex items-center gap-1.5 text-gray-400">
              <span className="font-semibold">{audioLang === 'SUB' ? 'Japanese (SUB)' : 'English (DUB)'}</span>
              <ChevronRight className="w-3.5 h-3.5" />
            </div>
          </div>

          {/* Server / Mirror Selector Row */}
          <div
            onClick={() => setCurrentView('server')}
            className="flex items-center justify-between px-3 py-2.5 rounded-xl hover:bg-white/10 cursor-pointer transition-colors"
          >
            <div className="flex items-center gap-3 text-gray-200">
              <Server className="w-4 h-4 text-gray-400" />
              <span className="font-medium text-xs">Mirror server</span>
            </div>
            <div className="flex items-center gap-1.5 text-gray-400">
              <span className="font-semibold truncate max-w-[110px]">{selectedServer}</span>
              <ChevronRight className="w-3.5 h-3.5" />
            </div>
          </div>

          {/* Subtitles Row */}
          {onSubtitleChange && (
            <div
              onClick={() => setCurrentView('subtitles')}
              className="flex items-center justify-between px-3 py-2.5 rounded-xl hover:bg-white/10 cursor-pointer transition-colors"
            >
              <div className="flex items-center gap-3 text-gray-200">
                <Subtitles className="w-4 h-4 text-gray-400" />
                <span className="font-medium text-xs">Subtitles / CC</span>
              </div>
              <div className="flex items-center gap-1.5 text-gray-400">
                <span className="font-semibold">{selectedSubtitle}</span>
                <ChevronRight className="w-3.5 h-3.5" />
              </div>
            </div>
          )}

          <div className="h-px bg-white/10 my-1" />

          {/* Auto-skip Intro Toggle Row */}
          <div 
            onClick={onToggleAutoSkipIntro}
            className="flex items-center justify-between px-3 py-2.5 rounded-xl hover:bg-white/10 cursor-pointer transition-colors"
          >
            <div className="flex items-center gap-3 text-gray-200">
              <FastForward className="w-4 h-4 text-fuchsia-400" />
              <span className="font-medium text-xs">Auto-skip Intro (OP)</span>
            </div>
            <div className={`w-9 h-5 rounded-full p-0.5 transition-colors ${
              autoSkipIntro ? 'bg-fuchsia-500' : 'bg-white/20'
            }`}>
              <div className={`w-4 h-4 rounded-full bg-white transition-transform ${
                autoSkipIntro ? 'translate-x-4' : 'translate-x-0'
              }`} />
            </div>
          </div>

          {/* Auto-skip Outro Toggle Row */}
          <div 
            onClick={onToggleAutoSkipOutro}
            className="flex items-center justify-between px-3 py-2.5 rounded-xl hover:bg-white/10 cursor-pointer transition-colors"
          >
            <div className="flex items-center gap-3 text-gray-200">
              <FastForward className="w-4 h-4 text-cyan-400" />
              <span className="font-medium text-xs">Auto-skip Outro (ED)</span>
            </div>
            <div className={`w-9 h-5 rounded-full p-0.5 transition-colors ${
              autoSkipOutro ? 'bg-cyan-500' : 'bg-white/20'
            }`}>
              <div className={`w-4 h-4 rounded-full bg-white transition-transform ${
                autoSkipOutro ? 'translate-x-4' : 'translate-x-0'
              }`} />
            </div>
          </div>

          {/* Ambient Lighting Toggle */}
          {onToggleAmbientMode && (
            <div 
              onClick={onToggleAmbientMode}
              className="flex items-center justify-between px-3 py-2.5 rounded-xl hover:bg-white/10 cursor-pointer transition-colors"
            >
              <div className="flex items-center gap-3 text-gray-200">
                <Sparkles className="w-4 h-4 text-yellow-400" />
                <span className="font-medium text-xs">Ambient lighting</span>
              </div>
              <div className={`w-9 h-5 rounded-full p-0.5 transition-colors ${
                ambientMode ? 'bg-fuchsia-500' : 'bg-white/20'
              }`}>
                <div className={`w-4 h-4 rounded-full bg-white transition-transform ${
                  ambientMode ? 'translate-x-4' : 'translate-x-0'
                }`} />
              </div>
            </div>
          )}
        </div>
      )}

      {/* 2. PLAYBACK SPEED SUBMENU */}
      {currentView === 'speed' && (
        <div className="flex flex-col">
          <button
            onClick={() => setCurrentView('main')}
            className="flex items-center gap-2 px-2 py-2 text-xs font-bold text-gray-300 hover:text-white hover:bg-white/10 rounded-lg transition-colors mb-1"
          >
            <ChevronLeft className="w-4 h-4" />
            <span>Playback speed</span>
          </button>
          <div className="h-px bg-white/10 mb-1" />
          <div className="flex flex-col max-h-64 overflow-y-auto custom-scrollbar">
            {speedOptions.map((opt) => (
              <button
                key={opt.value}
                onClick={() => {
                  onSpeedChange(opt.value);
                  onClose();
                }}
                className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-xs transition-colors ${
                  speed === opt.value
                    ? 'bg-fuchsia-500/20 text-fuchsia-400 font-bold'
                    : 'text-gray-300 hover:bg-white/10'
                }`}
              >
                <span>{opt.label}</span>
                {speed === opt.value && <Check className="w-4 h-4 text-fuchsia-400" />}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* 3. QUALITY SUBMENU (DYNAMIC EXTRACTED STREAMS ONLY) */}
      {currentView === 'quality' && (
        <div className="flex flex-col">
          <button
            onClick={() => setCurrentView('main')}
            className="flex items-center gap-2 px-2 py-2 text-xs font-bold text-gray-300 hover:text-white hover:bg-white/10 rounded-lg transition-colors mb-1"
          >
            <ChevronLeft className="w-4 h-4" />
            <span>Quality</span>
          </button>
          <div className="h-px bg-white/10 mb-1" />
          <div className="flex flex-col max-h-60 overflow-y-auto custom-scrollbar">
            {availableQualities.length === 0 ? (
              <div className="px-3 py-3 text-gray-400 text-xs italic">
                Detecting stream levels...
              </div>
            ) : (
              availableQualities.map((opt) => {
                const isSelected = selectedQualityIndex === opt.levelIndex;
                return (
                  <button
                    key={`${opt.value}-${opt.levelIndex}`}
                    onClick={() => {
                      onQualityChange(opt);
                      onClose();
                    }}
                    className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-xs transition-colors ${
                      isSelected
                        ? 'bg-fuchsia-500/20 text-fuchsia-400 font-bold'
                        : 'text-gray-300 hover:bg-white/10'
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      <span>{opt.label}</span>
                      {opt.levelIndex === -1 && quality.includes('(') && (
                        <span className="text-[10px] text-gray-400 font-normal">
                          {quality.replace('Auto', '').trim()}
                        </span>
                      )}
                      {opt.bitrate && opt.bitrate > 0 && opt.levelIndex !== -1 && (
                        <span className="text-[10px] text-gray-500 font-normal">
                          {Math.round(opt.bitrate / 1000)} kbps
                        </span>
                      )}
                    </div>
                    {isSelected && (
                      <Check className="w-4 h-4 text-fuchsia-400" />
                    )}
                  </button>
                );
              })
            )}
          </div>
        </div>
      )}

      {/* 4. STREAMING SERVER SUBMENU */}
      {currentView === 'server' && (
        <div className="flex flex-col">
          <button
            onClick={() => setCurrentView('main')}
            className="flex items-center gap-2 px-2 py-2 text-xs font-bold text-gray-300 hover:text-white hover:bg-white/10 rounded-lg transition-colors mb-1"
          >
            <ChevronLeft className="w-4 h-4" />
            <span>Streaming server</span>
          </button>
          <div className="h-px bg-white/10 mb-1" />
          <div className="flex flex-col max-h-60 overflow-y-auto custom-scrollbar">
            {availableServers.map((srv, idx) => (
              <button
                key={idx}
                onClick={() => {
                  onServerChange(srv.raw);
                  onClose();
                }}
                className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-xs transition-colors ${
                  selectedServer === srv.name
                    ? 'bg-fuchsia-500/20 text-fuchsia-400 font-bold'
                    : 'text-gray-300 hover:bg-white/10'
                }`}
              >
                <div className="flex flex-col items-start">
                  <span>{srv.name}</span>
                  {srv.quality && (
                    <span className="text-[10px] text-gray-400">{srv.quality}</span>
                  )}
                </div>
                {selectedServer === srv.name && <Check className="w-4 h-4 text-fuchsia-400" />}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* 5. AUDIO TRACK (SUB / DUB) SUBMENU */}
      {currentView === 'audio' && (
        <div className="flex flex-col">
          <button
            onClick={() => setCurrentView('main')}
            className="flex items-center gap-2 px-2 py-2 text-xs font-bold text-gray-300 hover:text-white hover:bg-white/10 rounded-lg transition-colors mb-1"
          >
            <ChevronLeft className="w-4 h-4" />
            <span>Audio track</span>
          </button>
          <div className="h-px bg-white/10 mb-1" />
          <div className="flex flex-col">
            {audioOptions.map((opt) => (
              <button
                key={opt.value}
                onClick={() => {
                  onAudioChange(opt.value);
                  onClose();
                }}
                className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-xs transition-colors ${
                  audioLang === opt.value
                    ? 'bg-fuchsia-500/20 text-fuchsia-400 font-bold'
                    : 'text-gray-300 hover:bg-white/10'
                }`}
              >
                <span>{opt.label}</span>
                {audioLang === opt.value && <Check className="w-4 h-4 text-fuchsia-400" />}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* 6. SUBTITLES / CC SUBMENU */}
      {currentView === 'subtitles' && onSubtitleChange && (
        <div className="flex flex-col">
          <button
            onClick={() => setCurrentView('main')}
            className="flex items-center gap-2 px-2 py-2 text-xs font-bold text-gray-300 hover:text-white hover:bg-white/10 rounded-lg transition-colors mb-1"
          >
            <ChevronLeft className="w-4 h-4" />
            <span>Subtitles / CC</span>
          </button>
          <div className="h-px bg-white/10 mb-1" />
          <div className="flex flex-col max-h-60 overflow-y-auto custom-scrollbar">
            <button
              onClick={() => {
                onSubtitleChange('Off');
                onClose();
              }}
              className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-xs transition-colors ${
                selectedSubtitle === 'Off'
                  ? 'bg-fuchsia-500/20 text-fuchsia-400 font-bold'
                  : 'text-gray-300 hover:bg-white/10'
              }`}
            >
              <span>Off</span>
              {selectedSubtitle === 'Off' && <Check className="w-4 h-4 text-fuchsia-400" />}
            </button>
            {availableSubtitles.map((sub, idx) => (
              <button
                key={idx}
                onClick={() => {
                  onSubtitleChange(sub.label);
                  onClose();
                }}
                className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg text-xs transition-colors ${
                  selectedSubtitle === sub.label
                    ? 'bg-fuchsia-500/20 text-fuchsia-400 font-bold'
                    : 'text-gray-300 hover:bg-white/10'
                }`}
              >
                <span>{sub.label}</span>
                {selectedSubtitle === sub.label && <Check className="w-4 h-4 text-fuchsia-400" />}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
