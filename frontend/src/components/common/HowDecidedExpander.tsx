import React, { useState } from 'react';
import { ChevronDown, ChevronRight, HelpCircle, FileText } from 'lucide-react';

interface HowDecidedProps {
  ruleId?: string;
  checkType?: string;
  docType?: string;
  clause?: string;
  actualValues?: any;
  threshold?: any;
  explanation?: string;
  reasons?: any[];
}

export const HowDecidedExpander: React.FC<HowDecidedProps> = ({
  ruleId,
  checkType,
  docType,
  clause,
  actualValues,
  threshold,
  explanation,
  reasons,
}) => {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="mt-2 text-xs border border-slate-200 rounded-lg bg-slate-50/80 overflow-hidden">
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between px-3 py-1.5 text-left text-slate-700 hover:bg-slate-100 transition-colors font-medium cursor-pointer"
        aria-expanded={isOpen}
      >
        <div className="flex items-center gap-1.5 text-indigo-700 font-semibold">
          <HelpCircle className="w-3.5 h-3.5" />
          <span>How this was decided</span>
        </div>
        {isOpen ? <ChevronDown className="w-3.5 h-3.5 text-slate-500" /> : <ChevronRight className="w-3.5 h-3.5 text-slate-500" />}
      </button>

      {isOpen && (
        <div className="p-3 border-t border-slate-200 bg-white space-y-2 text-slate-600">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[11px]">
            {ruleId && (
              <div>
                <span className="font-semibold text-slate-700">Rule/Check ID:</span>{' '}
                <code className="bg-slate-100 text-slate-800 px-1 py-0.5 rounded font-mono">{ruleId}</code>
              </div>
            )}
            {checkType && (
              <div>
                <span className="font-semibold text-slate-700">Check Category:</span>{' '}
                <span className="capitalize">{checkType.replace('_', ' ')}</span>
              </div>
            )}
            {docType && (
              <div>
                <span className="font-semibold text-slate-700">Document Type:</span>{' '}
                <span className="capitalize">{docType.replace('_', ' ')}</span>
              </div>
            )}
            {clause && (
              <div className="col-span-full flex items-start gap-1">
                <FileText className="w-3 h-3 text-slate-500 mt-0.5 flex-shrink-0" />
                <span>
                  <span className="font-semibold text-slate-700">Regulatory Clause:</span> {clause}
                </span>
              </div>
            )}
          </div>

          {actualValues !== undefined && (
            <div className="bg-slate-50 p-2 rounded border border-slate-200">
              <span className="font-semibold text-slate-700 block mb-1">Evaluated Field Values:</span>
              <pre className="font-mono text-[11px] text-slate-800 whitespace-pre-wrap overflow-x-auto">
                {typeof actualValues === 'object' ? JSON.stringify(actualValues, null, 2) : String(actualValues)}
              </pre>
            </div>
          )}

          {threshold !== undefined && (
            <div className="bg-slate-50 p-2 rounded border border-slate-200">
              <span className="font-semibold text-slate-700 block mb-1">Configured Norm / Threshold:</span>
              <span className="font-mono text-[11px] text-slate-800">
                {typeof threshold === 'object' ? JSON.stringify(threshold) : String(threshold)}
              </span>
            </div>
          )}

          {explanation && (
            <div className="text-slate-700 italic border-l-2 border-indigo-400 pl-2 text-[11px]">
              {explanation}
            </div>
          )}

          {reasons && reasons.length > 0 && (
            <div className="space-y-1">
              <span className="font-semibold text-slate-700 block">System Evidence Records:</span>
              <ul className="list-disc list-inside space-y-0.5 text-[11px]">
                {reasons.map((r, i) => (
                  <li key={i}>{typeof r === 'object' ? r.message || JSON.stringify(r) : String(r)}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
