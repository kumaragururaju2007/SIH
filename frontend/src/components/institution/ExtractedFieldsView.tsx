import React from 'react';
import { ExtractedField } from '../../types';
import { AlertCircle, CheckCircle2, ShieldCheck, FileText } from 'lucide-react';

interface ExtractedFieldsViewProps {
  fields: ExtractedField[];
  docTitle?: string;
  className?: string;
}

export const ExtractedFieldsView: React.FC<ExtractedFieldsViewProps> = ({
  fields,
  docTitle,
  className = '',
}) => {
  if (!fields || fields.length === 0) {
    return (
      <div className={`p-4 bg-stone-50 rounded-lg border border-stoneBorder text-center text-xs text-stone-500 ${className}`}>
        No extracted fields available for this document.
      </div>
    );
  }

  return (
    <div className={`space-y-3 ${className}`}>
      {docTitle && (
        <div className="flex items-center gap-2 text-xs font-bold text-primary uppercase tracking-wider">
          <FileText className="w-3.5 h-3.5" />
          <span>Extracted Document Attributes ({fields.length} Fields)</span>
        </div>
      )}

      <div className="border border-stoneBorder rounded-lg overflow-hidden bg-surface shadow-sm">
        <table className="w-full text-left border-collapse text-xs">
          <thead className="bg-stone-100 text-stone-700 font-semibold border-b border-stoneBorder text-[11px] uppercase tracking-wider">
            <tr>
              <th className="p-3">Attribute Name</th>
              <th className="p-3">Extracted Original Value</th>
              <th className="p-3">Standardized / Normalized Value</th>
              <th className="p-3 text-center">OCR Confidence</th>
              <th className="p-3 text-right">Verification Status</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-stoneBorder font-mono">
            {fields.map((field, idx) => {
              const name = field.name || field.field_name || `field_${idx + 1}`;
              const orig = field.value_original ?? field.raw_value ?? '—';
              const norm = field.value_normalized ?? field.normalized_value ?? orig;
              const conf = field.confidence !== undefined ? Math.round(field.confidence * 100) : 85;
              const isLowConf = conf < 70;
              const needsVerify = field.needs_verification || isLowConf;

              return (
                <tr key={idx} className="hover:bg-stone-50/60 transition-colors">
                  <td className="p-3 font-sans font-medium text-stone-900 capitalize">
                    {name.replace(/_/g, ' ')}
                  </td>
                  <td className="p-3 text-stone-600 break-words max-w-[200px]">
                    <span className="bg-stone-100 px-1.5 py-0.5 rounded text-[11px] border border-stone-200">
                      {orig}
                    </span>
                  </td>
                  <td className="p-3 text-stone-900 font-semibold break-words max-w-[220px]">
                    <span className="bg-stone-50 px-1.5 py-0.5 rounded text-[11px] border border-stoneBorder">
                      {norm}
                    </span>
                  </td>
                  <td className="p-3 text-center">
                    <span
                      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-bold ${
                        conf >= 80
                          ? 'bg-status-verified-bg text-status-verified-text'
                          : conf >= 65
                          ? 'bg-status-needsVerification-bg text-status-needsVerification-text'
                          : 'bg-status-inconsistent-bg text-status-inconsistent-text'
                      }`}
                    >
                      {conf}%
                    </span>
                  </td>
                  <td className="p-3 text-right font-sans">
                    {needsVerify ? (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold bg-status-needsVerification-bg text-status-needsVerification-text border border-status-needsVerification-border">
                        <AlertCircle className="w-3 h-3 flex-shrink-0" />
                        <span>Needs verification</span>
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[10px] font-bold bg-status-verified-bg text-status-verified-text border border-status-verified-border">
                        <CheckCircle2 className="w-3 h-3 flex-shrink-0" />
                        <span>Standard verified</span>
                      </span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-between text-[11px] text-stone-500 pt-1">
        <span>Read-only: Institutional applicants cannot modify OCR-extracted values directly.</span>
        <span>Standardized against AICTE approval ontologies</span>
      </div>
    </div>
  );
};

