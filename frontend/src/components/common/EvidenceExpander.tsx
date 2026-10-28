import React, { useState } from 'react';
import { ChevronDown, ChevronUp, Code2, ShieldAlert, FileText, CheckCircle2 } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

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
  const { currentUser } = useAuth();
  const isOfficer = currentUser.role === 'officer';

  const id = ruleId || checkId || 'SPEC-001';
  const clauseRef = clause || 'AICTE Approval Process Handbook Clause 1.4';

  return (
    <div className={`border border-stoneBorder rounded-lg bg-surface overflow-hidden ${className}`}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between p-3 text-left hover:bg-stone-50 transition-colors focus-visible:ring-1"
        aria-expanded={isOpen}
      >
        <div className="flex items-center gap-2">
          <span className="font-mono text-xs font-bold text-primary px-2 py-0.5 bg-stone-100 rounded border border-stoneBorder">
            {id}
          </span>
          <span className="text-xs font-semibold text-stone-700">How this was decided</span>
        </div>
        <div className="flex items-center gap-2 text-stone-500 text-xs">
          <span className="hidden sm:inline font-mono text-[11px]">v{version}</span>
          {isOpen ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </div>
      </button>

      {isOpen && (
        <div className="p-3.5 border-t border-stoneBorder bg-stone-50/50 space-y-3 text-xs">
          {/* Statutory Handbook Clause Reference */}
          <div className="flex items-start gap-2 text-stone-700">
            <FileText className="w-4 h-4 text-primary flex-shrink-0 mt-0.5" />
            <div>
              <span className="font-semibold text-stone-800">Regulatory Norm Reference:</span>
              <p className="font-mono text-[11px] text-stone-600 mt-0.5">{clauseRef}</p>
            </div>
          </div>

          {/* Evaluated Values */}
          {valuesUsed && Object.keys(valuesUsed).length > 0 && (
            <div>
              <span className="font-semibold text-stone-800 block mb-1">Evaluated Field Values:</span>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {Object.entries(valuesUsed).map(([key, val]) => (
                  <div key={key} className="p-2 bg-surface rounded border border-stoneBorder flex justify-between">
                    <span className="text-stone-500 font-mono text-[11px]">{key}:</span>
                    <span className="font-mono font-semibold text-stone-900 text-[11px]">
                      {typeof val === 'object' ? JSON.stringify(val) : String(val)}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Officer-only Raw JSON Toggle */}
          {isOfficer && rawPayload && (
            <div className="pt-2 border-t border-stoneBorder">
              <button
                onClick={() => setShowRaw(!showRaw)}
                className="inline-flex items-center gap-1.5 text-xs text-primary font-semibold hover:text-primary-hover p-1 rounded focus-visible:ring-1"
                aria-expanded={showRaw}
              >
                <Code2 className="w-3.5 h-3.5" />
                <span>{showRaw ? 'Hide Raw Audit JSON' : 'View Raw Audit JSON (Officer Mode)'}</span>
              </button>

              {showRaw && (
                <pre className="mt-2 p-2.5 bg-primary text-stone-100 font-mono text-[11px] rounded overflow-x-auto max-h-48 border border-stone-800 select-all">
                  {JSON.stringify(rawPayload, null, 2)}
                </pre>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
