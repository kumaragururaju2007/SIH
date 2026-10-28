import React from 'react';
import { Loader2, CheckCircle2, Shield } from 'lucide-react';
import { ValidationStageProgress } from '../../services/api';

interface ValidationProgressModalProps {
  isOpen: boolean;
  progress?: ValidationStageProgress | null;
}

export const ValidationProgressModal: React.FC<ValidationProgressModalProps> = ({
  isOpen,
  progress,
}) => {
  if (!isOpen) return null;

  const stages = [
    'Multilingual OCR & Script Extraction (eng+hin)',
    'Document Type Classification',
    'Deterministic Approval Norms & Clauses',
    'Cross-Document Consistency & Name Matching',
    'Forensics (ELA, Copy-Move, QR, Mock Registry)',
    'Composite Risk Scoring & Audit Logging',
  ];

  const currentIndex = progress?.stageIndex ?? 0;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-primary/40 backdrop-blur-[2px]"
      role="dialog"
      aria-modal="true"
      aria-label="Validation Pipeline Processing"
    >
      <div className="w-full max-w-md bg-surface rounded-xl border border-stoneBorder shadow-modal p-6 space-y-5 animate-in fade-in zoom-in-95">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-stone-100 flex items-center justify-center text-primary flex-shrink-0">
            <Shield className="w-5 h-5 text-primary" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-stone-900 font-sans">
              Executing Document Validation Engine
            </h3>
            <p className="text-xs text-stone-500">
              Deterministic processing across 6 scrutiny stages
            </p>
          </div>
        </div>

        {/* Stages list */}
        <div className="space-y-2.5">
          {stages.map((st, idx) => {
            const isDone = idx < currentIndex;
            const isCurrent = idx === currentIndex;

            return (
              <div
                key={idx}
                className={`flex items-center gap-2.5 p-2 rounded text-xs transition-colors ${
                  isCurrent
                    ? 'bg-amber-50 text-stone-900 font-semibold border border-amber-200'
                    : isDone
                    ? 'text-status-verified-text'
                    : 'text-stone-400'
                }`}
              >
                {isDone ? (
                  <CheckCircle2 className="w-4 h-4 text-status-verified flex-shrink-0" />
                ) : isCurrent ? (
                  <Loader2 className="w-4 h-4 text-accent animate-spin flex-shrink-0" />
                ) : (
                  <div className="w-4 h-4 rounded-full border border-stone-300 flex-shrink-0" />
                )}
                <span className="truncate">{st}</span>
              </div>
            );
          })}
        </div>

        {/* Global Progress Bar */}
        <div className="w-full h-2 bg-stone-100 rounded-full overflow-hidden">
          <div
            className="h-full bg-accent transition-all duration-300"
            style={{ width: `${Math.min(100, ((currentIndex + 1) / stages.length) * 100)}%` }}
          />
        </div>
      </div>
    </div>
  );
};
