import React from 'react';
import { Sparkles, CheckCircle } from 'lucide-react';

interface ToastProps {
  message: string | null;
}

export const Toast: React.FC<ToastProps> = ({ message }) => {
  if (!message) return null;

  return (
    <div className="fixed bottom-6 right-6 z-50 animate-in fade-in slide-in-from-bottom-5 duration-300">
      <div className="flex items-center gap-2.5 px-4 py-3 bg-[#181818]/95 backdrop-blur-xl border border-fuchsia-500/40 text-white text-sm font-semibold rounded-2xl shadow-[0_10px_30px_rgba(0,0,0,0.8)]">
        <div className="w-6 h-6 rounded-full bg-fuchsia-500/20 text-fuchsia-400 flex items-center justify-center">
          <CheckCircle className="w-4 h-4" />
        </div>
        <span>{message}</span>
      </div>
    </div>
  );
};
