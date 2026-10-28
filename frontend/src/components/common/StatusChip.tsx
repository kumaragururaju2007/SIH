import React, { useState } from 'react';
import { CheckCircle2, Eye, ShieldAlert, AlertOctagon, HelpCircle, FileEdit, Send, Clock, AlertTriangle } from 'lucide-react';
import { ResultLabel } from '../../types';

interface StatusChipProps {
  label?: ResultLabel | string | null;
  reason?: string;
  className?: string;
  size?: 'sm' | 'md';
}

export const StatusChip: React.FC<StatusChipProps> = ({
  label,
  reason,
  className = '',
  size = 'md',
}) => {
  const [showTooltip, setShowTooltip] = useState(false);
  const normalized = (label || 'needs_verification').toLowerCase().trim();

  let config = {
    text: 'Needs Verification',
    bg: 'bg-status-needsVerification-bg',
    border: 'border-status-needsVerification-border',
    textCol: 'text-status-needsVerification-text',
    icon: <Eye className={size === 'sm' ? 'w-3.5 h-3.5' : 'w-4 h-4'} strokeWidth={2} />,
    defaultReason: 'Requires human verification due to low confidence, scanning noise, or missing parameters.',
  };

  if (normalized === 'verified') {
    config = {
      text: 'Verified',
      bg: 'bg-status-verified-bg',
      border: 'border-status-verified-border',
      textCol: 'text-status-verified-text',
      icon: <CheckCircle2 className={size === 'sm' ? 'w-3.5 h-3.5' : 'w-4 h-4'} strokeWidth={2} />,
      defaultReason: 'Passed all deterministic checks, OCR thresholds, and official database cross-references.',
    };
  } else if (normalized === 'inconsistent') {
    config = {
      text: 'Inconsistent',
      bg: 'bg-status-inconsistent-bg',
      border: 'border-status-inconsistent-border',
      textCol: 'text-status-inconsistent-text',
      // Accessible Not-Equal Icon
      icon: (
        <svg
          className={size === 'sm' ? 'w-3.5 h-3.5' : 'w-4 h-4'}
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2.2"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <line x1="5" y1="9" x2="19" y2="9" />
          <line x1="5" y1="15" x2="19" y2="15" />
          <line x1="19" y1="5" x2="5" y2="19" />
        </svg>
      ),
      defaultReason: 'Cross-document conflict identified between independent certificates or records.',
    };
  } else if (normalized === 'possible_tampering' || normalized === 'tampered') {
    config = {
      text: 'Possible Tampering',
      bg: 'bg-status-tampering-bg',
      border: 'border-status-tampering-border',
      textCol: 'text-status-tampering-text',
      icon: <ShieldAlert className={size === 'sm' ? 'w-3.5 h-3.5' : 'w-4 h-4'} strokeWidth={2} />,
      defaultReason: 'This document could not be verified and shows inconsistencies. Please provide a genuine copy from the issuing authority.',
    };
  } else if (normalized === 'draft') {
    config = {
      text: 'Draft',
      bg: 'bg-stone-100',
      border: 'border-stoneBorder',
      textCol: 'text-stone-700',
      icon: <FileEdit className={size === 'sm' ? 'w-3.5 h-3.5' : 'w-4 h-4'} strokeWidth={2} />,
      defaultReason: 'Application is currently in draft mode and has not yet been submitted.',
    };
  } else if (normalized === 'submitted') {
    config = {
      text: 'Submitted',
      bg: 'bg-blue-50',
      border: 'border-blue-200',
      textCol: 'text-blue-700',
      icon: <Send className={size === 'sm' ? 'w-3.5 h-3.5' : 'w-4 h-4'} strokeWidth={2} />,
      defaultReason: 'Application submitted officially and pending officer review.',
    };
  } else if (normalized === 'in_review' || normalized === 'in review' || normalized === 'under_review') {
    config = {
      text: 'In Review',
      bg: 'bg-amber-50',
      border: 'border-amber-200',
      textCol: 'text-amber-800',
      icon: <Clock className={size === 'sm' ? 'w-3.5 h-3.5' : 'w-4 h-4'} strokeWidth={2} />,
      defaultReason: 'Application is currently under review by AICTE Scrutiny Officers.',
    };
  } else if (normalized === 'approved') {
    config = {
      text: 'Approved',
      bg: 'bg-status-verified-bg',
      border: 'border-status-verified-border',
      textCol: 'text-status-verified-text',
      icon: <CheckCircle2 className={size === 'sm' ? 'w-3.5 h-3.5' : 'w-4 h-4'} strokeWidth={2} />,
      defaultReason: 'Application officially approved by scrutiny officer.',
    };
  } else if (normalized === 'rejected') {
    config = {
      text: 'Rejected',
      bg: 'bg-status-inconsistent-bg',
      border: 'border-status-inconsistent-border',
      textCol: 'text-status-inconsistent-text',
      icon: <AlertOctagon className={size === 'sm' ? 'w-3.5 h-3.5' : 'w-4 h-4'} strokeWidth={2} />,
      defaultReason: 'Application rejected following official scrutiny review.',
    };
  } else if (normalized === 'deficiency_sent' || normalized === 'deficiency' || normalized === 'deficiency sent') {
    config = {
      text: 'Deficiency Sent',
      bg: 'bg-status-needsVerification-bg',
      border: 'border-status-needsVerification-border',
      textCol: 'text-status-needsVerification-text',
      icon: <AlertTriangle className={size === 'sm' ? 'w-3.5 h-3.5' : 'w-4 h-4'} strokeWidth={2} />,
      defaultReason: 'Deficiency report issued to applicant institution for remediation.',
    };
  }

  const tooltipText = reason || config.defaultReason;

  return (
    <div
      className="relative inline-flex items-center"
      onMouseEnter={() => setShowTooltip(true)}
      onMouseLeave={() => setShowTooltip(false)}
      onFocus={() => setShowTooltip(true)}
      onBlur={() => setShowTooltip(false)}
      tabIndex={0}
      aria-label={`${config.text}: ${tooltipText}`}
    >
      <span
        className={`inline-flex items-center gap-1.5 font-medium rounded-md border transition-colors ${
          size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-2.5 py-1 text-xs'
        } ${config.bg} ${config.border} ${config.textCol} ${className}`}
      >
        <span className="flex-shrink-0" aria-hidden="true">
          {config.icon}
        </span>
        <span className="truncate">{config.text}</span>
      </span>

      {showTooltip && (
        <div
          role="tooltip"
          className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1.5 z-40 w-64 p-2 bg-primary text-white text-xs rounded shadow-overlay pointer-events-none"
        >
          <div className="font-semibold mb-0.5">{config.text}</div>
          <div className="text-stone-200">{tooltipText}</div>
          <div className="absolute top-full left-1/2 -translate-x-1/2 border-4 border-transparent border-t-primary" />
        </div>
      )}
    </div>
  );
};
