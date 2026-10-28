import React from 'react';
import { Link } from 'react-router-dom';
import { FileQuestion, ArrowLeft } from 'lucide-react';

export const NotFoundPage: React.FC = () => {
  return (
    <div className="min-h-[60vh] flex items-center justify-center p-6">
      <div className="bg-surface rounded-card border border-stoneBorder p-8 max-w-md w-full text-center shadow-subtle">
        <div className="w-12 h-12 bg-warmBg text-ink-secondary rounded-full flex items-center justify-center mx-auto mb-3">
          <FileQuestion className="w-6 h-6" />
        </div>
        <h1 className="text-xl font-bold text-ink mb-1">Page Not Found</h1>
        <p className="text-xs text-ink-secondary mb-5">
          The requested regulatory filing route or document dossier does not exist.
        </p>
        <Link
          to="/"
          className="inline-flex items-center gap-2 px-4 py-2 bg-primary hover:bg-primary-hover text-white text-xs font-semibold rounded-input transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Return to Dashboard</span>
        </Link>
      </div>
    </div>
  );
};

