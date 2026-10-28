import React, { useState } from 'react';
import { StatusChip } from './StatusChip';
import { ConsistencyComparison } from '../../types';
import { ChevronDown, ChevronUp, ArrowRight, ShieldCheck, Info } from 'lucide-react';

interface SideBySideCompareProps {
  comparison: ConsistencyComparison;
  className?: string;
}

export const SideBySideCompare: React.FC<SideBySideCompareProps> = ({ comparison, className = '' }) => {
  const [showSteps, setShowSteps] = useState(false);

  const leftNorm = comparison.left.normalized || comparison.left.original || '';
  const rightNorm = comparison.right.normalized || comparison.right.original || '';

  // Differing tokens helper: underlines and bolds tokens that don't match across sides
  const highlightDifferences = (text: string, otherText: string) => {
    if (!text) return <span>—</span>;
    const tokens = text.split(/\s+/);
    const otherTokens = new Set(otherText.toLowerCase().split(/\s+/));

    return (
      <span>
        {tokens.map((token, idx) => {
          const clean = token.toLowerCase().replace(/[^\w\u0900-\u097F]/g, '');
          const isDifferent = clean.length > 0 && !otherTokens.has(clean);
          return (
            <React.Fragment key={idx}>
              {idx > 0 && ' '}
              <span
                className={
                  isDifferent
                    ? 'font-bold underline decoration-2 decoration-stone-700 bg-stone-100 px-0.5 rounded'
                    : ''
                }
              >
                {token}
              </span>
            </React.Fragment>
          );
        })}
      </span>
    );
  };

  const evidence = comparison.evidence || {};
  const steps = evidence.steps || evidence.normalization_steps || [];

  return (
    <div className={`bg-surface rounded-lg border border-stoneBorder p-4 shadow-sm ${className}`}>
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-2 pb-3 border-b border-stoneBorder">
        <div className="flex items-center gap-2">
          <span className="font-mono text-xs font-bold text-primary px-2 py-0.5 bg-stone-100 rounded border border-stoneBorder">
            {comparison.rule_id}
          </span>
          <span className="text-sm font-semibold text-stone-900">
            {comparison.description || comparison.rule_id}
          </span>
        </div>
        <div className="flex items-center gap-3">
          <div className="text-xs font-mono font-semibold text-stone-600">
            Score: <span className="text-primary tabular-nums font-bold">{comparison.score.toFixed(1)}</span>
            <span className="text-stone-400 font-normal ml-1">(Min: 85.0 / Partial: 70.0)</span>
          </div>
          <StatusChip label={comparison.status} />
        </div>
      </div>

      {/* Side by side columns */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 my-4">
        {/* Left Entity */}
        <div className="p-3.5 rounded-md bg-stone-50 border border-stoneBorder">
          <div className="flex items-center justify-between text-xs text-stone-500 font-semibold mb-2 uppercase tracking-wide">
            <span>{comparison.left.doc_type ? comparison.left.doc_type.replace(/_/g, ' ') : 'Primary Document'}</span>
            <span className="font-mono text-stone-400">
              {comparison.left.field ? comparison.left.field : 'Owner / Entity'}
            </span>
          </div>

          <div className="space-y-1.5">
            <div className="text-xs text-stone-500">
              Original Record:
              <span className="ml-1.5 font-mono text-stone-800 font-medium">
                "{comparison.left.original || '—'}"
              </span>
            </div>
            <div className="text-xs text-stone-700">
              <span className="text-stone-500">Standardized:</span>{' '}
              <span className="font-mono text-sm font-semibold text-primary">
                {highlightDifferences(leftNorm, rightNorm)}
              </span>
            </div>
          </div>
        </div>

        {/* Right Entity */}
        <div className="p-3.5 rounded-md bg-stone-50 border border-stoneBorder">
          <div className="flex items-center justify-between text-xs text-stone-500 font-semibold mb-2 uppercase tracking-wide">
            <span>{comparison.right.doc_type ? comparison.right.doc_type.replace(/_/g, ' ') : 'Target Document'}</span>
            <span className="font-mono text-stone-400">
              {comparison.right.field ? comparison.right.field : 'Trust / Institution'}
            </span>
          </div>

          <div className="space-y-1.5">
            <div className="text-xs text-stone-500">
              Original Record:
              <span className="ml-1.5 font-mono text-stone-800 font-medium">
                "{comparison.right.original || '—'}"
              </span>
            </div>
            <div className="text-xs text-stone-700">
              <span className="text-stone-500">Standardized:</span>{' '}
              <span className="font-mono text-sm font-semibold text-primary">
                {highlightDifferences(rightNorm, leftNorm)}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Plain Language Evaluation Message */}
      {comparison.message && (
        <div className="p-2.5 bg-stone-100 rounded text-xs text-stone-800 flex items-start gap-2 mb-3">
          <Info className="w-4 h-4 text-primary flex-shrink-0 mt-0.5" />
          <p className="flex-1">{comparison.message}</p>
        </div>
      )}

      {/* Audit & Transformation Steps Toggle */}
      <div className="pt-2 border-t border-stoneBorder flex items-center justify-between">
        <button
          onClick={() => setShowSteps(!showSteps)}
          className="text-xs font-semibold text-primary hover:text-primary-hover flex items-center gap-1 focus-visible:ring-1 p-1 rounded"
          aria-expanded={showSteps}
        >
          {showSteps ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          <span>{showSteps ? 'Hide Matching Audit Trail' : 'View Normalization & Matching Steps'}</span>
        </button>

        {comparison.clause && (
          <span className="text-[11px] font-mono text-stone-500">
            Ref: {comparison.clause}
          </span>
        )}
      </div>

      {showSteps && (
        <div className="mt-3 p-3 bg-stone-50 border border-stoneBorder rounded-md text-xs space-y-2">
          <div className="font-semibold text-stone-700 uppercase tracking-wide text-[11px]">
            Transformation Pipeline Steps:
          </div>
          <ol className="list-decimal list-inside space-y-1 text-stone-600 font-mono text-[11px]">
            <li>Devanagari Transliteration via ITRANS (Latin phonetic mapping)</li>
            <li>Honorific stripping (Dr., Prof., Shri, Smt., श्री, श्रीमती)</li>
            <li>Legal entity suffix normalization (Society, Trust, Foundation, Ltd, Regd)</li>
            <li>Phonetic canonicalization (shree/sri, w/v, ee/i, oo/u)</li>
            <li>RapidFuzz dual scoring: 65% token ratio + 35% Levenshtein char ratio</li>
            <li>Distinct name token guardrail (protects against Ramesh vs Suresh Kumar)</li>
          </ol>
          {evidence.diff_tokens && (
            <div className="pt-1 text-[11px] text-stone-600">
              <span className="font-semibold">Differing Token Set:</span>{' '}
              <span className="font-mono underline">{JSON.stringify(evidence.diff_tokens)}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
