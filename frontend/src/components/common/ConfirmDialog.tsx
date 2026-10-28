import React, { useEffect, useRef } from 'react';
import { X, AlertTriangle, CheckCircle2, ShieldAlert } from 'lucide-react';

interface ConfirmDialogProps {
  isOpen: boolean;
  title: string;
  message: string;
  confirmLabel?: string;
  cancelLabel?: string;
  variant?: 'primary' | 'danger' | 'accent';
  onConfirm: () => void;
  onCancel: () => void;
  isLoading?: boolean;
  children?: React.ReactNode;
}

export const ConfirmDialog: React.FC<ConfirmDialogProps> = ({
  isOpen,
  title,
  message,
  confirmLabel = 'Confirm',
  cancelLabel = 'Cancel',
  variant = 'primary',
  onConfirm,
  onCancel,
  isLoading = false,
  children,
}) => {
  const dialogRef = useRef<HTMLDivElement>(null);
  const confirmBtnRef = useRef<HTMLButtonElement>(null);

  // Focus trap & Escape listener
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        onCancel();
      }

      if (e.key === 'Tab' && dialogRef.current) {
        const focusable = dialogRef.current.querySelectorAll<HTMLElement>(
          'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        );
        if (focusable.length === 0) return;

        const first = focusable[0];
        const last = focusable[focusable.length - 1];

        if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        } else if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        }
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    // Focus the primary action button on open
    setTimeout(() => confirmBtnRef.current?.focus(), 50);

    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onCancel]);

  if (!isOpen) return null;

  const btnVariants = {
    primary: 'bg-primary hover:bg-primary-hover text-white',
    danger: 'bg-status-inconsistent hover:bg-red-800 text-white',
    accent: 'bg-accent hover:bg-accent-hover text-white',
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-[2px] transition-opacity"
      role="dialog"
      aria-modal="true"
      aria-labelledby="dialog-title"
    >
      <div
        ref={dialogRef}
        className="w-full max-w-lg bg-surface rounded-xl border border-stoneBorder shadow-modal overflow-hidden animate-in fade-in zoom-in-95 duration-150"
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-stoneBorder bg-stone-50">
          <div className="flex items-center gap-2">
            {variant === 'danger' ? (
              <AlertTriangle className="w-5 h-5 text-status-inconsistent" />
            ) : variant === 'accent' ? (
              <ShieldAlert className="w-5 h-5 text-accent" />
            ) : (
              <CheckCircle2 className="w-5 h-5 text-primary" />
            )}
            <h3 id="dialog-title" className="text-base font-bold text-stone-900 font-sans">
              {title}
            </h3>
          </div>
          <button
            onClick={onCancel}
            disabled={isLoading}
            className="p-1 rounded text-stone-400 hover:text-stone-700 focus-visible:ring-1"
            aria-label="Close dialog"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content Body */}
        <div className="p-5 text-xs text-stone-700 space-y-3">
          <p className="leading-relaxed text-sm text-stone-800">{message}</p>
          {children}
        </div>

        {/* Action Buttons */}
        <div className="flex items-center justify-end gap-2 p-4 border-t border-stoneBorder bg-stone-50">
          <button
            type="button"
            onClick={onCancel}
            disabled={isLoading}
            className="px-4 py-2 rounded-md border border-stoneBorder bg-surface text-stone-700 text-xs font-semibold hover:bg-stone-100 transition-colors focus-visible:ring-1"
          >
            {cancelLabel}
          </button>
          <button
            ref={confirmBtnRef}
            type="button"
            onClick={onConfirm}
            disabled={isLoading}
            className={`px-4 py-2 rounded-md text-xs font-semibold shadow-sm transition-colors focus-visible:ring-1 ${btnVariants[variant]}`}
          >
            {isLoading ? 'Processing...' : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
};
