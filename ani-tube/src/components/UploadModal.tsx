import React, { useState } from 'react';
import { X, Upload, Film, Check, Sparkles } from 'lucide-react';
import { Video } from '../types';
import { CATEGORIES } from '../data/mockData';

interface UploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onAddVideo: (video: Video) => void;
  onShowToast: (message: string) => void;
}

export const UploadModal: React.FC<UploadModalProps> = ({
  isOpen,
  onClose,
  onAddVideo,
  onShowToast
}) => {
  if (!isOpen) return null;

  const [title, setTitle] = useState('');
  const [channel, setChannel] = useState('Studio Trigger');
  const [category, setCategory] = useState('Action');
  const [ep, setEp] = useState<string>('1');
  const [tag, setTag] = useState('SUB');
  const [description, setDescription] = useState('');
  const [thumbnailUrl, setThumbnailUrl] = useState(
    'https://images.unsplash.com/photo-1578632767115-351597cf2477?w=800&q=80'
  );
  const [videoUrl, setVideoUrl] = useState(
    'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/TearsOfSteel.mp4'
  );

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) {
      onShowToast('Please provide a title!');
      return;
    }

    const newVideo: Video = {
      id: Date.now(),
      title: title.trim(),
      channel: channel.trim() || 'Community Creator',
      channelAvatar: `https://api.dicebear.com/7.x/avataaars/svg?seed=${encodeURIComponent(channel)}`,
      subscribers: '12K',
      views: '1',
      viewsCount: 1,
      time: 'Just now',
      duration: '24:00',
      ep: ep ? parseInt(ep) : null,
      tags: [tag, '1080p'],
      thumbnail: thumbnailUrl,
      videoUrl: videoUrl,
      category: category,
      description: description.trim() || 'Uploaded to AniTube by creator.',
      likes: 1,
      dislikes: 0,
      isLiked: false,
      isDisliked: false,
      isSubscribed: false,
      isSaved: false,
      comments: []
    };

    onAddVideo(newVideo);
    onShowToast(`"${newVideo.title}" published successfully!`);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="relative w-full max-w-xl bg-[#141414] border border-white/10 rounded-3xl p-6 sm:p-8 shadow-2xl overflow-y-auto max-h-[90vh] custom-scrollbar">
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-white/10">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-fuchsia-500/20 text-fuchsia-400 flex items-center justify-center">
              <Upload className="w-4 h-4" />
            </div>
            <h2 className="text-xl font-bold text-white">Upload Anime / AMV</h2>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-gray-400 hover:text-white rounded-full hover:bg-white/10 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="mt-6 space-y-4">
          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-gray-400 mb-1.5">
              Video Title *
            </label>
            <input
              type="text"
              required
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Solo Leveling - Episode 12 AMV [4K 60FPS]"
              className="w-full bg-[#1e1e1e] border border-white/10 focus:border-fuchsia-500 rounded-xl px-4 py-2.5 text-sm text-white outline-none transition-colors"
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-gray-400 mb-1.5">
                Studio / Channel Name
              </label>
              <input
                type="text"
                value={channel}
                onChange={(e) => setChannel(e.target.value)}
                placeholder="e.g. Studio Trigger, MAPPA, etc."
                className="w-full bg-[#1e1e1e] border border-white/10 focus:border-fuchsia-500 rounded-xl px-4 py-2.5 text-sm text-white outline-none transition-colors"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-gray-400 mb-1.5">
                Category
              </label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="w-full bg-[#1e1e1e] border border-white/10 focus:border-fuchsia-500 rounded-xl px-4 py-2.5 text-sm text-white outline-none transition-colors"
              >
                {CATEGORIES.filter(c => c !== 'All').map(c => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-gray-400 mb-1.5">
                Episode #
              </label>
              <input
                type="number"
                value={ep}
                onChange={(e) => setEp(e.target.value)}
                placeholder="1"
                className="w-full bg-[#1e1e1e] border border-white/10 focus:border-fuchsia-500 rounded-xl px-4 py-2.5 text-sm text-white outline-none transition-colors"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-gray-400 mb-1.5">
                Audio Tag
              </label>
              <select
                value={tag}
                onChange={(e) => setTag(e.target.value)}
                className="w-full bg-[#1e1e1e] border border-white/10 focus:border-fuchsia-500 rounded-xl px-4 py-2.5 text-sm text-white outline-none transition-colors"
              >
                <option value="SUB">SUB (Japanese + Subs)</option>
                <option value="DUB">DUB (English)</option>
                <option value="RAW">RAW (No Subtitles)</option>
                <option value="AMV">AMV / Music</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-gray-400 mb-1.5">
              Thumbnail Image URL
            </label>
            <input
              type="url"
              value={thumbnailUrl}
              onChange={(e) => setThumbnailUrl(e.target.value)}
              className="w-full bg-[#1e1e1e] border border-white/10 focus:border-fuchsia-500 rounded-xl px-4 py-2.5 text-sm text-white outline-none transition-colors"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-gray-400 mb-1.5">
              Playable Video Stream URL (MP4)
            </label>
            <input
              type="url"
              value={videoUrl}
              onChange={(e) => setVideoUrl(e.target.value)}
              className="w-full bg-[#1e1e1e] border border-white/10 focus:border-fuchsia-500 rounded-xl px-4 py-2.5 text-sm text-white outline-none transition-colors"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-gray-400 mb-1.5">
              Synopsis / Description
            </label>
            <textarea
              rows={3}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Tell fans what happens in this episode or anime cut..."
              className="w-full bg-[#1e1e1e] border border-white/10 focus:border-fuchsia-500 rounded-xl px-4 py-2.5 text-sm text-white outline-none transition-colors"
            />
          </div>

          <div className="pt-4 flex justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              className="px-5 py-2.5 text-sm font-semibold text-gray-400 hover:text-white"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-6 py-2.5 bg-gradient-to-r from-fuchsia-500 to-cyan-500 hover:opacity-90 text-white rounded-full text-sm font-bold shadow-lg transition-transform active:scale-95 flex items-center gap-2"
            >
              <Check className="w-4 h-4" /> Publish Now
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
