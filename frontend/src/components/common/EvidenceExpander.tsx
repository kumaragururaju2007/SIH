import React, { useState } from 'react';
import { ChevronDown, ChevronUp, Code2, FileText } from 'lucide-react';
import { useAuth } from '../../auth/AuthContext';

interface EvidenceExpanderProps {
  ruleId?: string;
  checkId?: string;
  clause?: string;
  valuesUsed?: Record<string, any>;
  version?: string;
  rawPayload?: any;
  defaultOpen?: boolean;
  className?: string;
}

export const EvidenceExpander: React.FC<EvidenceExpanderProps> = ({
  ruleId,
  checkId,
  clause,
  valuesUsed,
  version = '1.0.0',
  rawPayload,
  defaultOpen = false,
  className = '',
}) => {
  const [isOpen, setIsOpen] = useState(defaultOpen);
  const [showRaw, setShowRaw] = useState(false);
  const { user } = useAuth();
  const isOfficerOrAdmin = user?.role === 'officer' || user?.role === 'admin';

  const id = ruleId || checkId || 'SPEC-001';
  const clauseRef = clause || 'AICTE Approval Process Handbook Clause 1.4';

  return (
    <div className={`border border-stoneBorder rounded-card bg-surface overflow-hidden ${className}`}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between p-3 text-left hover:bg-warmBg transition-colors"
        aria-expanded={isOpen}
      >
        <div className="flex items-center gap-2">
          <span className="font-mono text-xs font-bold text-primary px-2 py-0.5 bg-warmBg rounded border border-stoneBorder">
            {id}
          </span>
          <span className="text-xs font-semibold text-ink">How this was decided</span>
        </div>
        <div className="flex items-center gap-2 text-ink-muted text-xs">
          <span className="hidden sm:inline font-mono text-[11px]">v{version}</span>
          {isOpen ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </div>
      </button>

      {isOpen && (
        <div className="p-3.5 border-t border-stoneBorder bg-surface-subtle space-y-3 text-xs">
          {/* Statutory Handbook Clause Reference */}
          <div className="flex items-start gap-2 text-ink">
            <FileText className="w-4 h-4 text-primary flex-shrink-0 mt-0.5" />
            <div>
              <span className="font-semibold text-ink">Regulatory Norm Reference:</span>
              <p className="font-mono text-[11px] text-ink-secondary mt-0.5">{clauseRef}</p>
            </div>
          </div>

          {/* Evaluated Parameters */}
          {valuesUsed && Object.keys(valuesUsed).length > 0 && (
            <div>
              <span className="font-semibold text-ink block mb-1.5">Evaluated Parameter Values:</span>
              <div className="bg-surface border border-stoneBorder rounded-input p-2.5 font-mono text-[11px] space-y-1">
                {Object.entries(valuesUsed).map(([k, v]) => (
                  <div key={k} className="flex flex-wrap items-baseline justify-between gap-2 border-b border-stoneBorder/40 pb-1 last:border-0 last:pb-0">
                    <span className="text-ink-secondary font-medium">{k}:</span>
                    <span className="font-bold text-ink">{typeof v === 'object' ? JSON.stringify(v) : String(v)}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Officer-only Raw JSON Toggle */}
          {isOfficerOrAdmin && (
            <div className="pt-2 border-t border-stoneBorder">
              <button
                type="button"
                onClick={() => setShowRaw(!showRaw)}
                className="text-[11px] font-medium text-primary hover:text-primary-hover flex items-center gap-1.5"
              >
                <Code2 className="w-3.5 h-3.5" />
                <span>{showRaw ? 'Hide raw inspector JSON' : 'View raw inspector JSON (officer only)'}</span>
              </button>

              {showRaw && (
                <div className="mt-2 p-2.5 bg-ink text-primary-tint rounded-input font-mono text-[11px] overflow-x-auto max-h-48">
                  <pre>{JSON.stringify(rawPayload || { rule_id: id, values: valuesUsed, clause: clauseRef }, null, 2)}</pre>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
