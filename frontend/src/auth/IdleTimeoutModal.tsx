import React, { useEffect, useRef } from 'react';
import { useAuth } from './AuthContext';
import { Clock, LogOut, CheckCircle2 } from 'lucide-react';

export const IdleTimeoutModal: React.FC = () => {
  const { showIdlePrompt, idleSecondsLeft, stayLoggedIn, logout } = useAuth();
  const stayBtnRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (showIdlePrompt) {
      stayBtnRef.current?.focus();
    }
  }, [showIdlePrompt]);

  if (!showIdlePrompt) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="idle-title"
      aria-describedby="idle-desc"
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-ink/60 backdrop-blur-sm animate-fade-in"
    >
      <div className="bg-surface rounded-card border border-stoneBorder p-6 max-w-md w-full shadow-modal">
        <div className="flex items-center gap-3 mb-4 text-accent">
          <Clock className="w-6 h-6 animate-pulse" aria-hidden="true" />
          <h2 id="idle-title" className="text-lg font-bold text-ink">
            Still there?
          </h2>
        </div>

        <p id="idle-desc" className="text-sm text-ink-secondary mb-4 leading-relaxed">
          For your security on official government portals, your session will automatically expire due to inactivity in{' '}
          <strong className="text-ink font-mono-val tabular-nums text-base">{idleSecondsLeft} seconds</strong>.
        </p>

        <div className="flex items-center justify-end gap-3 pt-3 border-t border-stoneBorder">
          <button
            type="button"
            onClick={() => logout('user_choice')}
            className="px-4 py-2 text-sm font-medium text-ink-secondary hover:text-ink hover:bg-warmBg rounded-input transition-colors flex items-center gap-1.5"
          >
            <LogOut className="w-4 h-4" />
            Sign out now
          </button>
          <button
            ref={stayBtnRef}
            type="button"
            onClick={stayLoggedIn}
            className="px-5 py-2 text-sm font-bold bg-primary hover:bg-primary-hover text-white rounded-input transition-colors flex items-center gap-1.5"
          >
            <CheckCircle2 className="w-4 h-4" />
            Stay signed in
          </button>
        </div>
      </div>
    </div>
  );
};

