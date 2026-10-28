import React from 'react';
import { AlertCircle, AlertTriangle, Info, FileWarning } from 'lucide-react';
import { EvidenceExpander } from './EvidenceExpander';

interface IssueCardProps {
  id: string;
  title: string;
  message: string;
  severity?: 'low' | 'medium' | 'high' | string;
  clause?: string;
  docType?: string;
  actionRequired?: string;
  valuesUsed?: Record<string, any>;
  version?: string;
  rawPayload?: any;
  className?: string;
}

export const IssueCard: React.FC<IssueCardProps> = ({
  id,
  title,
  message,
  severity = 'high',
  clause,
  docType,
  actionRequired,
  valuesUsed,
  version = '1.0.0',
  rawPayload,
  className = '',
}) => {
  const sev = severity.toLowerCase();

  const sevConfig = {
    high: {
      badgeBg: 'bg-status-inconsistent-bg',
      badgeBorder: 'border-status-inconsistent-border',
      badgeText: 'text-status-inconsistent-text',
      icon: <AlertCircle className="w-4 h-4 text-status-inconsistent flex-shrink-0" />,
      label: 'High Severity',
    },
    medium: {
      badgeBg: 'bg-status-needsVerification-bg',
      badgeBorder: 'border-status-needsVerification-border',
      badgeText: 'text-status-needsVerification-text',
      icon: <AlertTriangle className="w-4 h-4 text-status-needsVerification flex-shrink-0" />,
      label: 'Medium Severity',
    },
    low: {
      badgeBg: 'bg-stone-100',
      badgeBorder: 'border-stone-300',
      badgeText: 'text-stone-700',
      icon: <Info className="w-4 h-4 text-stone-500 flex-shrink-0" />,
      label: 'Minor Advisory',
    },
  }[sev] || {
    badgeBg: 'bg-stone-100',
    badgeBorder: 'border-stone-300',
    badgeText: 'text-stone-700',
    icon: <Info className="w-4 h-4 text-stone-500 flex-shrink-0" />,
    label: 'Advisory',
  };

  return (
    <div className={`p-4 rounded-lg border border-stoneBorder bg-surface shadow-sm flex flex-col gap-3 ${className}`}>
      {/* Top Strip */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          {sevConfig.icon}
          <h4 className="text-sm font-semibold text-stone-900">{title}</h4>
        </div>
        <div className="flex items-center gap-2">
          {docType && (
            <span className="text-xs font-mono px-2 py-0.5 rounded bg-stone-100 text-stone-700 border border-stoneBorder">
              {docType.replace(/_/g, ' ')}
            </span>
          )}
          <span
            className={`inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded border ${sevConfig.badgeBg} ${sevConfig.badgeBorder} ${sevConfig.badgeText}`}
          >
            {sevConfig.label}
          </span>
        </div>
      </div>

      {/* Main explanation message */}
      <p className="text-xs text-stone-700 leading-relaxed font-sans">{message}</p>

      {/* Action required if specified */}
      {actionRequired && (
        <div className="p-2.5 rounded bg-amber-50 border border-amber-200 text-xs text-amber-900 flex items-start gap-2">
          <span className="font-semibold uppercase tracking-wider text-[11px] text-amber-800">
            Action:
          </span>
          <span className="flex-1">{actionRequired}</span>
        </div>
      )}

      {/* Embedded EvidenceExpander */}
      <EvidenceExpander
        ruleId={id}
        clause={clause}
        valuesUsed={valuesUsed}
        version={version}
        rawPayload={rawPayload}
      />
    </div>
  );
};
