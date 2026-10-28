import React from 'react';
import { RiskBand } from '../../types';

interface RiskMeterProps {
  score?: number | null;
  band?: RiskBand | string | null;
  size?: 'sm' | 'md' | 'lg';
  showLabel?: boolean;
  className?: string;
}

export const RiskMeter: React.FC<RiskMeterProps> = ({
  score = 0,
  band,
  size = 'md',
  showLabel = true,
  className = '',
}) => {
  const numericScore = score !== null && score !== undefined ? Math.round(score) : 0;
  
  // Determine band if not provided
  let computedBand: RiskBand = 'low';
  if (band) {
    computedBand = band.toLowerCase() as RiskBand;
  } else if (numericScore > 60) {
    computedBand = 'high';
  } else if (numericScore > 30) {
    computedBand = 'medium';
  }

  const bandConfigs: Record<RiskBand, { label: string; textCol: string; barCol: string; bgCol: string }> = {
    low: {
      label: 'Low Risk',
      textCol: 'text-risk-low-text',
      barCol: 'bg-risk-low',
      bgCol: 'bg-risk-low-bg',
    },
    medium: {
      label: 'Medium Risk',
      textCol: 'text-risk-medium-text',
      barCol: 'bg-risk-medium',
      bgCol: 'bg-risk-medium-bg',
    },
    high: {
      label: 'High Risk',
      textCol: 'text-risk-high-text',
      barCol: 'bg-risk-high',
      bgCol: 'bg-risk-high-bg',
    },
  };

  const current = bandConfigs[computedBand] || bandConfigs.low;

  if (size === 'sm') {
    return (
      <div className={`inline-flex items-center gap-2 ${className}`}>
        <div className="w-16 h-2 bg-stone-200 rounded-full overflow-hidden flex-shrink-0" aria-hidden="true">
          <div
            className={`h-full rounded-full transition-all duration-300 ${current.barCol}`}
            style={{ width: `${Math.min(100, Math.max(4, numericScore))}%` }}
          />
        </div>
        <span className={`text-xs font-mono font-semibold tabular-nums ${current.textCol}`}>
          {numericScore}
        </span>
        {showLabel && (
          <span className={`text-xs font-medium uppercase tracking-wider ${current.textCol}`}>
            {current.label.split(' ')[0]}
          </span>
        )}
      </div>
    );
  }

  return (
    <div className={`flex flex-col gap-1.5 ${className}`}>
      {showLabel && (
        <div className="flex items-center justify-between text-xs font-medium">
          <span className={`uppercase tracking-wider font-semibold ${current.textCol}`}>
            {current.label}
          </span>
          <span className="font-mono text-stone-600 font-semibold tabular-nums">
            {numericScore} / 100
          </span>
        </div>
      )}
      <div
        className="w-full h-2.5 bg-stone-200 rounded-full overflow-hidden"
        role="progressbar"
        aria-valuenow={numericScore}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={`Risk score: ${numericScore} out of 100, ${current.label}`}
      >
        <div
          className={`h-full rounded-full transition-all duration-300 ${current.barCol}`}
          style={{ width: `${Math.min(100, Math.max(3, numericScore))}%` }}
        />
      </div>
    </div>
  );
};
