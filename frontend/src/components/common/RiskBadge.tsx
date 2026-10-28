import React from 'react';
import { ShieldCheck, ShieldAlert, AlertTriangle } from 'lucide-react';
import { RiskBand } from '../../types';

interface RiskBadgeProps {
  score?: number | null;
  band?: RiskBand | string | null;
  size?: 'sm' | 'md' | 'lg';
  showScore?: boolean;
}

export const RiskBadge: React.FC<RiskBadgeProps> = ({ score, band, size = 'md', showScore = true }) => {
  const normBand = (band || 'low').toLowerCase();

  let config = {
    label: 'Low Risk',
    icon: ShieldCheck,
    bg: 'bg-emerald-50 text-emerald-800 border-emerald-300',
    barColor: 'bg-emerald-500',
  };

  if (normBand === 'medium') {
    config = {
      label: 'Medium Risk',
      icon: AlertTriangle,
      bg: 'bg-amber-50 text-amber-800 border-amber-300',
      barColor: 'bg-amber-500',
    };
  } else if (normBand === 'high') {
    config = {
      label: 'High Risk',
      icon: ShieldAlert,
      bg: 'bg-rose-50 text-rose-800 border-rose-300',
      barColor: 'bg-rose-600',
    };
  }

  const Icon = config.icon;
  const roundedScore = score !== undefined && score !== null ? Math.round(score) : null;

  const sizeClasses = {
    sm: 'text-xs px-2 py-0.5 gap-1',
    md: 'text-xs md:text-sm px-2.5 py-1 gap-1.5 font-medium',
    lg: 'text-sm px-3.5 py-1.5 gap-2 font-semibold',
  }[size];

  return (
    <span className={`inline-flex items-center rounded-md border ${config.bg} ${sizeClasses} shadow-2xs`}>
      <Icon className="w-4 h-4 flex-shrink-0" />
      <span>{config.label}</span>
      {showScore && roundedScore !== null && (
        <span className="font-mono font-bold bg-white/70 px-1.5 py-0.2 rounded border border-black/10">
          {roundedScore}/100
        </span>
      )}
    </span>
  );
};
