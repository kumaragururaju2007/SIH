import React from 'react';
import { CheckCircle2, AlertTriangle, AlertCircle, ArrowRight, TrendingDown, TrendingUp } from 'lucide-react';
import { DraftComparisonResponse } from '../../types';
import { StatusChip } from './StatusChip';
import { useAuth } from '../../context/AuthContext';

interface BeforeAfterPanelProps {
  comparison: DraftComparisonResponse;
  className?: string;
}

export const BeforeAfterPanel: React.FC<BeforeAfterPanelProps> = ({ comparison, className = '' }) => {
  const { currentUser } = useAuth();
  const isOfficer = currentUser.role === 'officer';

  const { counts, resolved_issues, remaining_issues, new_issues, label_changes, risk_changes } = comparison;

  return (
    <div className={`flex flex-col gap-5 p-5 bg-surface rounded-xl border border-stoneBorder shadow-sm ${className}`}>
      {/* Big Headline Sentence */}
      <div className="flex flex-wrap items-center justify-between gap-3 pb-4 border-b border-stoneBorder">
        <div>
          <span className="text-xs uppercase tracking-wider font-semibold text-primary">
            Resubmission Differential Analysis
          </span>
          <h3 className="text-xl sm:text-2xl font-bold text-stone-900 mt-1 font-sans">
            {comparison.summary_sentence ||
              `${counts.total_before} failures before, ${counts.total_remaining} remaining`}
          </h3>
        </div>

        {/* Risk Score Delta - Shown ONLY to Officers on officer workstation */}
        {isOfficer && typeof window !== 'undefined' && window.location.pathname.startsWith('/officer') && risk_changes && risk_changes.before_score !== undefined && (
          <div className="p-3 bg-stone-50 rounded-lg border border-stoneBorder flex items-center gap-4">
            <div>
              <span className="text-[11px] uppercase tracking-wider font-semibold text-stone-600 block">
                Officer Risk Index Change
              </span>
              <div className="flex items-center gap-2 mt-0.5 font-mono">
                <span className="text-sm line-through text-stone-600">
                  {risk_changes.before_score}
                </span>
                <ArrowRight className="w-3.5 h-3.5 text-stone-600" />
                <span className="text-lg font-bold text-primary">
                  {risk_changes.after_score}
                </span>
                <span className="text-xs text-stone-600">/ 100</span>
              </div>
            </div>

            {risk_changes.score_delta !== undefined && (
              <div
                className={`flex items-center gap-1 text-xs font-semibold px-2 py-1 rounded ${
                  risk_changes.score_delta <= 0
                    ? 'bg-status-verified-bg text-status-verified-text border border-status-verified-border'
                    : 'bg-status-inconsistent-bg text-status-inconsistent-text border border-status-inconsistent-border'
                }`}
              >
                {risk_changes.score_delta <= 0 ? (
                  <>
                    <TrendingDown className="w-4 h-4" />
                    <span>{Math.abs(risk_changes.score_delta)} pts safer</span>
                  </>
                ) : (
                  <>
                    <TrendingUp className="w-4 h-4" />
                    <span>+{risk_changes.score_delta} pts risk</span>
                  </>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Per-Document Label Transitions */}
      {label_changes && label_changes.length > 0 && (
        <div className="space-y-2">
          <h4 className="text-xs font-semibold text-stone-700 uppercase tracking-wide">
            Document Label Evolution
          </h4>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5">
            {label_changes.map((lc, idx) => (
              <div
                key={idx}
                className="p-3 rounded-lg bg-stone-50 border border-stoneBorder flex items-center justify-between gap-2"
              >
                <span className="text-xs font-medium text-stone-800 capitalize">
                  {lc.doc_type.replace(/_/g, ' ')}
                </span>
                <div className="flex items-center gap-1.5 flex-shrink-0">
                  <StatusChip label={lc.before_label} size="sm" />
                  <ArrowRight className="w-3.5 h-3.5 text-stone-400" />
                  <StatusChip label={lc.after_label} size="sm" />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Three Columns: Resolved, Remaining, New */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
        {/* Resolved Column */}
        <div className="flex flex-col rounded-lg border border-status-verified-border bg-status-verified-bg/30 p-3.5">
          <div className="flex items-center justify-between pb-2.5 border-b border-status-verified-border mb-3">
            <div className="flex items-center gap-1.5 font-semibold text-status-verified-text text-xs uppercase tracking-wide">
              <CheckCircle2 className="w-4 h-4 text-status-verified" />
              <span>Resolved</span>
            </div>
            <span className="px-2 py-0.5 rounded-full text-xs font-bold font-mono bg-status-verified text-white">
              {counts.resolved}
            </span>
          </div>

          <div className="space-y-2 flex-1">
            {resolved_issues.length === 0 ? (
              <p className="text-xs text-stone-500 italic py-2">No resolved items recorded</p>
            ) : (
              resolved_issues.map((item) => (
                <div key={item.id} className="p-2.5 bg-surface rounded border border-stoneBorder text-xs space-y-1">
                  <div className="font-semibold text-stone-900">{item.title}</div>
                  <div className="text-[11px] text-stone-500 line-through">{item.before_message}</div>
                  <div className="text-[11px] font-medium text-status-verified-text flex items-center gap-1">
                    <CheckCircle2 className="w-3 h-3 text-status-verified" />
                    <span>Fixed in resubmission</span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Remaining Column */}
        <div className="flex flex-col rounded-lg border border-status-needsVerification-border bg-status-needsVerification-bg/30 p-3.5">
          <div className="flex items-center justify-between pb-2.5 border-b border-status-needsVerification-border mb-3">
            <div className="flex items-center gap-1.5 font-semibold text-status-needsVerification-text text-xs uppercase tracking-wide">
              <AlertTriangle className="w-4 h-4 text-status-needsVerification" />
              <span>Remaining</span>
            </div>
            <span className="px-2 py-0.5 rounded-full text-xs font-bold font-mono bg-status-needsVerification text-white">
              {counts.remaining}
            </span>
          </div>

          <div className="space-y-2 flex-1">
            {remaining_issues.length === 0 ? (
              <p className="text-xs text-stone-500 italic py-2">All previous defects addressed!</p>
            ) : (
              remaining_issues.map((item) => (
                <div key={item.id} className="p-2.5 bg-surface rounded border border-stoneBorder text-xs space-y-1">
                  <div className="font-semibold text-stone-900">{item.title}</div>
                  <div className="text-[11px] text-status-needsVerification-text font-medium">
                    {item.after_message || item.before_message}
                  </div>
                  {item.clause && (
                    <div className="text-[10px] font-mono text-stone-600">Ref: {item.clause}</div>
                  )}
                </div>
              ))
            )}
          </div>
        </div>

        {/* New Column */}
        <div className="flex flex-col rounded-lg border border-status-inconsistent-border bg-status-inconsistent-bg/30 p-3.5">
          <div className="flex items-center justify-between pb-2.5 border-b border-status-inconsistent-border mb-3">
            <div className="flex items-center gap-1.5 font-semibold text-status-inconsistent-text text-xs uppercase tracking-wide">
              <AlertCircle className="w-4 h-4 text-status-inconsistent" />
              <span>New Defects</span>
            </div>
            <span className="px-2 py-0.5 rounded-full text-xs font-bold font-mono bg-status-inconsistent text-white">
              {counts.new}
            </span>
          </div>

          <div className="space-y-2 flex-1">
            {new_issues.length === 0 ? (
              <p className="text-xs text-stone-500 italic py-2">No new defects introduced</p>
            ) : (
              new_issues.map((item) => (
                <div key={item.id} className="p-2.5 bg-surface rounded border border-status-inconsistent-border text-xs space-y-1">
                  <div className="font-semibold text-status-inconsistent-text">{item.title}</div>
                  <div className="text-[11px] text-stone-700">{item.after_message}</div>
                </div>
              ))
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
