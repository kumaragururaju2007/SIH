import React from 'react';
import { Calendar, User, Shield, CheckCircle, AlertTriangle, FileText } from 'lucide-react';
import { AuditLogItem, InstitutionHistory } from '../../types';

interface TimelineProps {
  auditLogs?: AuditLogItem[];
  history?: InstitutionHistory[];
  mode?: 'audit' | 'history';
  className?: string;
}

export const Timeline: React.FC<TimelineProps> = ({
  auditLogs = [],
  history = [],
  mode = 'audit',
  className = '',
}) => {
  const formatDate = (dateStr: string) => {
    try {
      const d = new Date(dateStr);
      const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
      const day = d.getDate();
      const month = months[d.getMonth()];
      const year = d.getFullYear();
      const hours = String(d.getHours()).padStart(2, '0');
      const mins = String(d.getMinutes()).padStart(2, '0');
      return `${day} ${month} ${year} ${hours}:${mins}`;
    } catch {
      return dateStr;
    }
  };

  if (mode === 'history') {
    return (
      <div className={`space-y-4 ${className}`}>
        {history.length === 0 ? (
          <p className="text-xs text-stone-500 italic p-3 bg-stone-50 rounded">
            No past inspection history recorded. New institution applicant.
          </p>
        ) : (
          <div className="relative pl-6 space-y-6 before:absolute before:left-2.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-stoneBorder">
            {history.map((h) => (
              <div key={h.id} className="relative flex flex-col gap-1 text-xs">
                {/* Timeline node */}
                <div
                  className={`absolute -left-6 top-0.5 w-5 h-5 rounded-full border-2 border-surface flex items-center justify-center ${
                    h.outcome.toLowerCase() === 'approved'
                      ? 'bg-status-verified text-white'
                      : 'bg-status-inconsistent text-white'
                  }`}
                  aria-hidden="true"
                >
                  <Calendar className="w-2.5 h-2.5" />
                </div>

                <div className="flex items-center justify-between font-semibold">
                  <span className="font-mono text-stone-900 text-sm">{h.year} AICTE Approval Cycle</span>
                  <span
                    className={`px-2 py-0.5 rounded text-[11px] uppercase font-bold tracking-wider ${
                      h.outcome.toLowerCase() === 'approved'
                        ? 'bg-status-verified-bg text-status-verified-text'
                        : 'bg-status-inconsistent-bg text-status-inconsistent-text'
                    }`}
                  >
                    {h.outcome}
                  </span>
                </div>

                <div className="flex items-center gap-4 text-stone-600 mt-1">
                  <span>Deficiencies Noted: <strong className="font-mono">{h.deficiency_count}</strong></span>
                  <span>Scrutiny Risk Flags: <strong className="font-mono">{h.flags_count}</strong></span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    );
  }

  // Audit Logs mode
  return (
    <div className={`space-y-3 ${className}`}>
      {auditLogs.length === 0 ? (
        <p className="text-xs text-stone-500 italic p-3 bg-stone-50 rounded">
          No audit entries recorded yet.
        </p>
      ) : (
        <div className="relative pl-6 space-y-4 before:absolute before:left-2.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-stoneBorder">
          {auditLogs.map((log) => (
            <div key={log.id} className="relative flex flex-col gap-1 text-xs">
              {/* Timeline marker */}
              <div
                className="absolute -left-6 top-1 w-5 h-5 rounded-full border-2 border-surface bg-primary text-white flex items-center justify-center"
                aria-hidden="true"
              >
                <Shield className="w-2.5 h-2.5" />
              </div>

              <div className="flex flex-wrap items-center justify-between gap-1">
                <span className="font-semibold text-stone-900 font-mono">
                  {log.action.replace(/_/g, ' ').toUpperCase()}
                </span>
                <span
                  className="font-mono text-[11px] text-stone-500 cursor-help"
                  title={`ISO Timestamp: ${log.timestamp}`}
                >
                  {formatDate(log.timestamp)}
                </span>
              </div>

              <div className="flex items-center gap-2 text-stone-600">
                <span className="inline-flex items-center gap-1 font-medium bg-stone-100 px-1.5 py-0.5 rounded text-[11px]">
                  <User className="w-3 h-3 text-stone-500" />
                  {log.actor}
                </span>
                <span className="font-mono text-stone-400 text-[11px]">
                  Target: {log.entity}
                </span>
              </div>

              {log.details && Object.keys(log.details).length > 0 && (
                <div className="p-2 mt-1 rounded bg-stone-50 border border-stoneBorder text-[11px] font-mono text-stone-700">
                  {Object.entries(log.details).map(([k, v]) => (
                    <div key={k} className="truncate">
                      <span className="text-stone-400">{k}:</span>{' '}
                      <span>{typeof v === 'object' ? JSON.stringify(v) : String(v)}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
