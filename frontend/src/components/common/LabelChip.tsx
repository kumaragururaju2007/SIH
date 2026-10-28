import React from 'react';
import { CheckCircle2, AlertCircle, AlertTriangle, ShieldAlert, HelpCircle } from 'lucide-react';
import { ResultLabel } from '../../types';

interface LabelChipProps {
  label?: ResultLabel | string | null;
  size?: 'sm' | 'md' | 'lg';
  showOriginal?: ResultLabel | string | null;
}

export const LabelChip: React.FC<LabelChipProps> = ({ label, size = 'md', showOriginal }) => {
  const normLabel = (label || '').toLowerCase();

  let config = {
    text: 'Unassigned',
    icon: HelpCircle,
    bg: 'bg-slate-100',
    textCol: 'text-slate-700',
    border: 'border-slate-300',
  };

  if (normLabel === 'verified') {
    config = {
      text: 'Verified',
      icon: CheckCircle2,
      bg: 'bg-emerald-50',
      textCol: 'text-emerald-700',
      border: 'border-emerald-200',
    };
  } else if (normLabel === 'needs_verification') {
    config = {
      text: 'Needs Verification',
      icon: AlertCircle,
      bg: 'bg-sky-50',
      textCol: 'text-sky-700',
      border: 'border-sky-200',
    };
  } else if (normLabel === 'inconsistent') {
    config = {
      text: 'Inconsistent',
      icon: AlertTriangle,
      bg: 'bg-amber-50',
      textCol: 'text-amber-700',
      border: 'border-amber-200',
    };
  } else if (normLabel === 'possible_tampering') {
    config = {
      text: 'Possible Tampering',
      icon: ShieldAlert,
      bg: 'bg-rose-50',
      textCol: 'text-rose-700',
      border: 'border-rose-200',
    };
  }

  const Icon = config.icon;
  const sizeClasses = {
    sm: 'text-xs px-2 py-0.5 gap-1',
    md: 'text-xs md:text-sm px-2.5 py-1 gap-1.5 font-medium',
    lg: 'text-sm px-3.5 py-1.5 gap-2 font-semibold',
  }[size];

  const iconSizes = {
    sm: 'w-3 h-3',
    md: 'w-4 h-4',
    lg: 'w-4.5 h-4.5',
  }[size];

  return (
    <div className="inline-flex items-center gap-1.5 flex-wrap">
      <span
        className={`inline-flex items-center rounded-full border ${config.bg} ${config.textCol} ${config.border} ${sizeClasses} shadow-xs select-none`}
        title={`Status: ${config.text}`}
      >
        <Icon className={`${iconSizes} flex-shrink-0`} aria-hidden="true" />
        <span>{config.text}</span>
      </span>

      {showOriginal && showOriginal !== label && (
        <span
          className="text-[11px] text-slate-500 bg-slate-100 border border-slate-200 rounded px-1.5 py-0.5"
          title={`Original system label: ${showOriginal}`}
        >
          (Sys: {showOriginal.replace('_', ' ')})
        </span>
      )}
    </div>
  );
};
