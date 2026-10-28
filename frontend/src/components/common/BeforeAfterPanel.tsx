import React from 'react';
import { CheckCircle2, AlertTriangle, AlertCircle, ArrowRight, TrendingDown, TrendingUp } from 'lucide-react';
import { DraftComparisonResponse } from '../../types';
import { StatusChip } from './StatusChip';
import { useAuth } from '../../auth/AuthContext';

interface BeforeAfterPanelProps {
  comparison: DraftComparisonResponse;
  className?: string;
}

export const BeforeAfterPanel: React.FC<BeforeAfterPanelProps> = ({ comparison, className = '' }) => {
  const { user } = useAuth();
  const isOfficer = user?.role === 'officer';

  const { counts, resolved_issues, remaining_issues, new_issues, label_changes, risk_changes } = comparison;

  return (
    <div className={`flex flex-col gap-5 p-5 bg-surface rounded-card border border-stoneBorder shadow-subtle ${className}`}>
      {/* Big Headline Sentence */}
      <div className="flex flex-wrap items-center justify-between gap-3 pb-4 border-b border-stoneBorder">
        <div>
          <span className="text-xs uppercase tracking-wider font-semibold text-primary">
            Resubmission Differential Analysis
          </span>
          <h3 className="text-xl sm:text-2xl font-bold text-ink mt-1 font-sans">
            {comparison.summary_sentence ||
              `${counts.total_before} failures before, ${counts.total_remaining} remaining`}
          </h3>
        </div>

        {/* Risk Score Delta - Shown ONLY to Officers on officer routes */}
        {isOfficer && typeof window !== 'undefined' && window.location.pathname.startsWith('/officer') && risk_changes && risk_changes.before_score !== undefined && (
          <div className="p-3 bg-surface-subtle rounded-input border border-stoneBorder flex items-center gap-4">
            <div>
              <span className="text-[11px] uppercase tracking-wider font-semibold text-ink-secondary block">
                Officer Risk Index Change
              </span>
              <div className="flex items-center gap-2 mt-0.5 font-mono">
                <span className="text-sm line-through text-ink-muted">
                  {risk_changes.before_score}
                </span>
                <ArrowRight className="w-3.5 h-3.5 text-ink-secondary" />
                <span className="text-lg font-bold text-primary">
                  {risk_changes.after_score}
                </span>
                <span className="text-xs text-ink-muted">/ 100</span>
              </div>
            </div>

            {risk_changes.score_delta !== undefined && (
              <div
                className={`flex items-center gap-1 text-xs font-semibold px-2 py-1 rounded ${
                  risk_changes.score_delta <= 0
                    ? 'bg-status-verified-bg text-status-verified-text border border-status-verified/30'
                    : 'bg-status-inconsistent-bg text-status-inconsistent-text border border-status-inconsistent/30'
                }`}
              >
                {risk_changes.score_delta <= 0 ? (
                  <>
                    <TrendingDown className="w-4 h-4 text-status-verified" />
                    <span>{Math.abs(risk_changes.score_delta)} pts decrease</span>
                  </>
                ) : (
                  <>
                    <TrendingUp className="w-4 h-4 text-status-inconsistent" />
                    <span>+{risk_changes.score_delta} pts increase</span>
                  </>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Per-Document Label Evolution Transitions */}
      {label_changes && label_changes.length > 0 && (
        <div className="p-3.5 bg-surface-subtle rounded-card border border-stoneBorder">
          <span className="text-xs font-bold uppercase tracking-wider text-ink block mb-2.5">
            Document Label Transitions
          </span>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2.5">
            {label_changes.map((change, idx) => (
              <div
                key={idx}
                className="flex items-center justify-between p-2.5 bg-surface rounded-input border border-stoneBorder text-xs"
              >
                <span className="font-semibold text-ink capitalize truncate max-w-[120px]">
                  {change.doc_type ? change.doc_type.replace(/_/g, ' ') : `Document #${change.document_id || ''}`}
                </span>
                <div className="flex items-center gap-1.5 flex-shrink-0">
                  <StatusChip label={change.before_label} size="sm" />
                  <ArrowRight className="w-3 h-3 text-ink-muted" />
                  <StatusChip label={change.after_label} size="sm" />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 3 Differential Analysis Columns: Resolved, Remaining, New */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Column 1: Resolved Issues (Green) */}
        <div className="flex flex-col rounded-card border border-status-verified/40 bg-surface overflow-hidden">
          <div className="p-3 bg-status-verified-bg border-b border-status-verified/30 flex items-center justify-between">
            <div className="flex items-center gap-1.5 text-status-verified-text font-bold text-xs uppercase tracking-wide">
              <CheckCircle2 className="w-4 h-4" />
              <span>Resolved</span>
            </div>
            <span className="px-2 py-0.5 rounded-full text-xs font-bold bg-white text-status-verified-text border border-status-verified/40">
              {counts.resolved}
            </span>
          </div>

          <div className="p-3 flex-1 flex flex-col gap-2 max-h-80 overflow-y-auto">
            {resolved_issues && resolved_issues.length > 0 ? (
              resolved_issues.map((issue, idx) => (
                <div
                  key={idx}
                  className="p-2.5 rounded-input bg-status-verified-bg/40 border border-status-verified/30 text-xs flex flex-col gap-1"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-[11px] font-bold text-status-verified-text">
                      {issue.id}
                    </span>
                    <span className="capitalize text-[10px] text-ink-muted">
                      {issue.doc_type ? issue.doc_type.replace(/_/g, ' ') : ''}
                    </span>
                  </div>
                  <p className="text-ink font-medium leading-relaxed">{issue.after_message || issue.before_message || issue.title}</p>
                </div>
              ))
            ) : (
              <p className="text-xs text-ink-muted italic p-2 text-center my-auto">
                No issues marked resolved yet
              </p>
            )}
          </div>
        </div>

        {/* Column 2: Remaining Issues (Amber) */}
        <div className="flex flex-col rounded-card border border-status-needsVerification/40 bg-surface overflow-hidden">
          <div className="p-3 bg-status-needsVerification-bg border-b border-status-needsVerification/30 flex items-center justify-between">
            <div className="flex items-center gap-1.5 text-status-needsVerification-text font-bold text-xs uppercase tracking-wide">
              <AlertTriangle className="w-4 h-4" />
              <span>Remaining</span>
            </div>
            <span className="px-2 py-0.5 rounded-full text-xs font-bold bg-white text-status-needsVerification-text border border-status-needsVerification/40">
              {counts.remaining}
            </span>
          </div>

          <div className="p-3 flex-1 flex flex-col gap-2 max-h-80 overflow-y-auto">
            {remaining_issues && remaining_issues.length > 0 ? (
              remaining_issues.map((issue, idx) => (
                <div
                  key={idx}
                  className="p-2.5 rounded-input bg-status-needsVerification-bg/40 border border-status-needsVerification/30 text-xs flex flex-col gap-1"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-[11px] font-bold text-status-needsVerification-text">
                      {issue.id}
                    </span>
                    <span className="capitalize text-[10px] text-ink-muted">
                      {issue.doc_type ? issue.doc_type.replace(/_/g, ' ') : ''}
                    </span>
                  </div>
                  <p className="text-ink font-medium leading-relaxed">{issue.after_message || issue.before_message || issue.title}</p>
                </div>
              ))
            ) : (
              <p className="text-xs text-status-verified-text font-medium p-2 text-center my-auto">
                All previous issues resolved!
              </p>
            )}
          </div>
        </div>

        {/* Column 3: New Issues (Red) */}
        <div className="flex flex-col rounded-card border border-status-inconsistent/40 bg-surface overflow-hidden">
          <div className="p-3 bg-status-inconsistent-bg border-b border-status-inconsistent/30 flex items-center justify-between">
            <div className="flex items-center gap-1.5 text-status-inconsistent-text font-bold text-xs uppercase tracking-wide">
              <AlertCircle className="w-4 h-4" />
              <span>New Defects</span>
            </div>
            <span className="px-2 py-0.5 rounded-full text-xs font-bold bg-white text-status-inconsistent-text border border-status-inconsistent/40">
              {counts.new}
            </span>
          </div>

          <div className="p-3 flex-1 flex flex-col gap-2 max-h-80 overflow-y-auto">
            {new_issues && new_issues.length > 0 ? (
              new_issues.map((issue, idx) => (
                <div
                  key={idx}
                  className="p-2.5 rounded-input bg-status-inconsistent-bg/40 border border-status-inconsistent/30 text-xs flex flex-col gap-1"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-mono text-[11px] font-bold text-status-inconsistent-text">
                      {issue.id}
                    </span>
                    <span className="capitalize text-[10px] text-ink-muted">
                      {issue.doc_type ? issue.doc_type.replace(/_/g, ' ') : ''}
                    </span>
                  </div>
                  <p className="text-ink font-medium leading-relaxed">{issue.after_message || issue.before_message || issue.title}</p>
                </div>
              ))
            ) : (
              <p className="text-xs text-ink-muted italic p-2 text-center my-auto">
                No new defects introduced
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
