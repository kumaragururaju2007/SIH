import React from 'react';
import { useI18n } from '../../i18n';

export const Banner: React.FC = () => {
  const { t } = useI18n();

  return (
    <div
      role="region"
      aria-label="Prototype Notice"
      className="banner-container bg-primary text-white text-xs py-1.5 px-4 text-center font-medium border-b border-primary-hover flex items-center justify-center gap-2 select-none"
    >
      <span className="w-2 h-2 rounded-full bg-accent animate-pulse" aria-hidden="true" />
      <span>{t('app.banner', 'Prototype using synthetic data. Scores and thresholds are illustrative; officers make all decisions.')}</span>
    </div>
  );
};
