import React from 'react';
import { AlertCircle, CheckCircle2 } from 'lucide-react';

interface FieldValueProps {
  label: string;
  originalValue?: string | number | null;
  normalizedValue?: string | number | null;
  confidence?: number | null;
  needsVerification?: boolean;
  isHindi?: boolean;
  className?: string;
}

export const FieldValue: React.FC<FieldValueProps> = ({
  label,
  originalValue,
  normalizedValue,
  confidence,
  needsVerification = false,
  isHindi = false,
  className = '',
}) => {
  const confPercent = confidence !== null && confidence !== undefined ? Math.round(confidence * 100) : null;
  const isLowConf = confPercent !== null && confPercent < 70;
  const requiresVerification = needsVerification || isLowConf;

  return (
    <div className={`p-3 bg-surface rounded-lg border border-stoneBorder ${className}`}>
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-xs font-semibold text-primary uppercase tracking-wide">
          {label.replace(/_/g, ' ')}
        </span>
        <div className="flex items-center gap-2">
          {confPercent !== null && (
            <div
              className="flex items-center gap-1 text-xs text-stone-500 font-mono"
              title={`OCR confidence: ${confPercent}%`}
            >
              <span
                className={`w-2 h-2 rounded-full ${
                  confPercent >= 85
                    ? 'bg-status-verified'
                    : confPercent >= 70
                    ? 'bg-status-needsVerification'
                    : 'bg-status-inconsistent'
                }`}
                aria-hidden="true"
              />
              <span className="tabular-nums">{confPercent}%</span>
            </div>
          )}
          {requiresVerification && (
            <span
              className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[11px] font-medium bg-status-needsVerification-bg text-status-needsVerification-text border border-status-needsVerification-border"
              title="Field flagged for human verification"
            >
              <AlertCircle className="w-3 h-3 flex-shrink-0" />
              Check
            </span>
          )}
        </div>
      </div>

      {/* Normalized Value */}
      <div className="flex flex-col gap-1">
        <div className="flex items-baseline gap-2">
          <span className="text-xs text-stone-500 font-medium">Standardized:</span>
          <span
            className={`text-sm font-semibold text-stone-900 font-mono select-all ${
              isHindi ? 'lang-hi' : ''
            }`}
          >
            {normalizedValue !== null && normalizedValue !== undefined && String(normalizedValue).trim() !== ''
              ? String(normalizedValue)
              : originalValue !== null && originalValue !== undefined && String(originalValue).trim() !== ''
              ? String(originalValue)
              : '—'}
          </span>
        </div>

        {/* Original Raw Value (if distinct from normalized) */}
        {originalValue !== null &&
          originalValue !== undefined &&
          String(originalValue) !== String(normalizedValue) && (
            <div className="flex items-baseline gap-2 text-xs text-stone-500">
              <span>OCR Read:</span>
              <span className={`font-mono italic text-stone-600 ${isHindi ? 'lang-hi' : ''}`}>
                "{String(originalValue)}"
              </span>
            </div>
          )}
      </div>
    </div>
  );
};
