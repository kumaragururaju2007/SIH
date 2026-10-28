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

  // Determine band if not explicitly provided
  let computedBand: 'low' | 'medium' | 'high' = 'low';
  if (band) {
    const b = band.toLowerCase();
    if (b.includes('high')) computedBand = 'high';
    else if (b.includes('med')) computedBand = 'medium';
    else computedBand = 'low';
  } else if (numericScore >= 60) {
    computedBand = 'high';
  } else if (numericScore >= 30) {
    computedBand = 'medium';
  }

  const bandConfigs = {
    low: {
      label: 'Low',
      textCol: 'text-status-verified-text',
      activeBg: 'bg-status-verified',
      lightBg: 'bg-status-verified-bg',
    },
    medium: {
      label: 'Medium',
      textCol: 'text-status-needsVerification-text',
      activeBg: 'bg-status-needsVerification',
      lightBg: 'bg-status-needsVerification-bg',
    },
    high: {
      label: 'High',
      textCol: 'text-status-inconsistent-text',
      activeBg: 'bg-status-inconsistent',
      lightBg: 'bg-status-inconsistent-bg',
    },
  };

  const activeConfig = bandConfigs[computedBand];

  return (
    <div
      role="meter"
      aria-valuenow={numericScore}
      aria-valuemin={0}
      aria-valuemax={100}
      aria-label={`Risk score: ${numericScore} out of 100, ${activeConfig.label} risk band`}
      className={`inline-flex flex-col gap-1 ${className}`}
    >
      <div className="flex items-center justify-between text-xs font-semibold gap-3">
        <span className="font-mono-val tabular-nums text-ink text-xs font-bold">
          {numericScore}<span className="text-[10px] text-ink-muted">/100</span>
        </span>
        {showLabel && (
          <span className={`text-[11px] font-bold uppercase tracking-wider ${activeConfig.textCol}`}>
            {activeConfig.label} Risk
          </span>
        )}
      </div>

      {/* Segmented Horizontal Meter: Low, Medium, High */}
      <div className="flex items-center gap-1 w-full min-w-[100px] h-2">
        {/* Segment 1: Low (0 - 30) */}
        <div
          className={`flex-1 h-full rounded-full transition-colors ${
            computedBand === 'low' || computedBand === 'medium' || computedBand === 'high'
              ? computedBand === 'low'
                ? 'bg-status-verified ring-1 ring-status-verified'
                : 'bg-status-verified/40'
              : 'bg-stoneBorder'
          }`}
          title="Low Risk Segment (0-30)"
        />

        {/* Segment 2: Medium (31 - 60) */}
        <div
          className={`flex-1 h-full rounded-full transition-colors ${
            computedBand === 'medium' || computedBand === 'high'
              ? computedBand === 'medium'
                ? 'bg-status-needsVerification ring-1 ring-status-needsVerification'
                : 'bg-status-needsVerification/40'
              : 'bg-stoneBorder'
          }`}
          title="Medium Risk Segment (31-60)"
        />

        {/* Segment 3: High (61 - 100) */}
        <div
          className={`flex-1 h-full rounded-full transition-colors ${
            computedBand === 'high'
              ? 'bg-status-inconsistent ring-1 ring-status-inconsistent'
              : 'bg-stoneBorder'
          }`}
          title="High Risk Segment (61-100)"
        />
      </div>
    </div>
  );
};
