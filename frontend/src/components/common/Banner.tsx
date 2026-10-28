import React from 'react';
import { ShieldAlert } from 'lucide-react';
import { useI18n } from '../../i18n';

export const Banner: React.FC = () => {
  const { t } = useI18n();

  return (
    <div
      role="note"
      aria-label="Prototype synthetic data disclaimer banner"
      className="banner-proto bg-stone-100 border-b border-stoneBorder px-4 py-1.5 text-xs text-stone-700 flex items-center justify-center gap-2 select-none"
    >
      <ShieldAlert className="w-3.5 h-3.5 text-accent flex-shrink-0" />
      <span className="font-semibold text-primary uppercase text-[11px] tracking-wider">
        Prototype Notice:
      </span>
      <span className="truncate">
        {t(
          'app.banner',
          'Prototype using synthetic data. Scores and thresholds are illustrative; officers make all decisions.'
        )}
      </span>
    </div>
  );
};
