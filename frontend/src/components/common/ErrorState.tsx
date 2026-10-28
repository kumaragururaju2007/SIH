import React from 'react';
import { AlertCircle, RefreshCw } from 'lucide-react';

interface ErrorStateProps {
  title?: string;
  message?: string;
  onRetry?: () => void;
  className?: string;
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  title = 'Something went wrong',
  message = 'An error occurred while communicating with the validation server.',
  onRetry,
  className = '',
}) => {
  return (
    <div
      role="alert"
      className={`flex flex-col items-center justify-center p-8 text-center rounded-lg border border-status-inconsistent-border bg-status-inconsistent-bg/30 ${className}`}
    >
      <div className="w-12 h-12 rounded-full bg-status-inconsistent-bg flex items-center justify-center text-status-inconsistent mb-3">
        <AlertCircle className="w-6 h-6" />
      </div>
      <h3 className="text-sm font-semibold text-status-inconsistent-text mb-1">{title}</h3>
      <p className="text-xs text-stone-600 max-w-md mb-4">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-semibold bg-surface border border-stoneBorder hover:bg-stone-50 text-stone-700 shadow-sm transition-colors focus-visible:ring-1"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>Retry Connection</span>
        </button>
      )}
    </div>
  );
};
