import React, { useState } from 'react';
import {
  FileText,
  Printer,
  Download,
  Globe,
  AlertTriangle,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  Building,
} from 'lucide-react';
import { DeficiencyReportData } from '../../types';
import { useI18n } from '../../i18n';

interface DeficiencyReportViewProps {
  report: DeficiencyReportData;
  onCreateDraftAndFix: () => void;
  isCreatingDraft: boolean;
  institutionName?: string;
  applicationId: number;
}

export const DeficiencyReportView: React.FC<DeficiencyReportViewProps> = ({
  report,
  onCreateDraftAndFix,
  isCreatingDraft,
  institutionName,
  applicationId,
}) => {
  const { language, setLanguage, t } = useI18n();
  const [reportLang, setReportLang] = useState<'en' | 'hi'>((language as 'en' | 'hi') || 'en');

  const content = report.content || {};
  const items: any[] = content.items || [];
  const summaryText = content.summary_text || `${items.length} items require remediation`;

  const handlePrint = () => {
    window.print();
  };

  const toggleLanguage = () => {
    const nextLang = reportLang === 'en' ? 'hi' : 'en';
    setReportLang(nextLang);
    setLanguage(nextLang);
  };

  return (
    <div className="bg-surface rounded-xl border border-stoneBorder shadow-sm overflow-hidden space-y-6 p-6">
      {/* Top Action Bar (Print / Language / CTA) */}
      <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-stoneBorder print:hidden">
        <div>
          <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-status-needsVerification-bg border border-status-needsVerification-border text-status-needsVerification-text text-xs font-semibold mb-1">
            <AlertTriangle className="w-3.5 h-3.5" />
            <span>OFFICIAL SCRUTINY DEFICIENCY REPORT</span>
          </div>
          <h2 className="text-xl sm:text-2xl font-bold text-primary font-sans">
            {reportLang === 'hi' ? 'आधिकारिक संवीक्षा कमी रिपोर्ट' : 'Official Deficiency & Scrutiny Report'}
          </h2>
          <p className="text-xs text-stone-600 mt-0.5">
            Issued for Application #{applicationId} • {institutionName}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {/* Language Toggle */}
          <button
            onClick={toggleLanguage}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md border border-stoneBorder bg-surface hover:bg-stone-50 text-xs font-semibold text-stone-700 transition-colors focus-visible:ring-1"
            title="Switch Language / भाषा बदलें"
          >
            <Globe className="w-3.5 h-3.5 text-stone-500" />
            <span>{reportLang === 'en' ? 'हिन्दी में देखें' : 'View in English'}</span>
          </button>

          {/* Print Button */}
          <button
            onClick={handlePrint}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md border border-stoneBorder bg-surface hover:bg-stone-50 text-xs font-semibold text-stone-700 transition-colors focus-visible:ring-1"
            title="Print Official Report"
          >
            <Printer className="w-3.5 h-3.5 text-stone-500" />
            <span>Print</span>
          </button>

          {/* Download PDF Button */}
          <button
            onClick={handlePrint}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md border border-stoneBorder bg-surface hover:bg-stone-50 text-xs font-semibold text-stone-700 transition-colors focus-visible:ring-1"
            title="Download PDF"
          >
            <Download className="w-3.5 h-3.5 text-stone-500" />
            <span>Download PDF</span>
          </button>

          {/* Primary Accent CTA: Create Draft & Fix */}
          <button
            onClick={onCreateDraftAndFix}
            disabled={isCreatingDraft}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-md bg-accent hover:bg-accent-hover text-stone-950 text-xs font-bold shadow-sm transition-colors focus-visible:ring-2"
          >
            <RefreshCw className={`w-4 h-4 ${isCreatingDraft ? 'animate-spin' : ''} text-stone-950`} />
            <span>Create Draft & Fix</span>
          </button>
        </div>
      </div>

      {/* Official Summary Card */}
      <div className="p-4 rounded-lg bg-stone-50 border border-stoneBorder flex flex-wrap items-center justify-between gap-4 text-xs">
        <div>
          <span className="text-[10px] uppercase font-bold text-stone-500 block">
            {reportLang === 'hi' ? 'रिपोर्ट स्थिति' : 'Report Status'}
          </span>
          <span className="font-bold text-primary text-sm uppercase">
            {report.status || 'Deficiency Issued'}
          </span>
        </div>

        <div>
          <span className="text-[10px] uppercase font-bold text-stone-500 block">
            {reportLang === 'hi' ? 'कुल चिह्नित कमियां' : 'Total Findings'}
          </span>
          <span className="font-mono font-bold text-sm text-stone-900">
            {items.length} {items.length === 1 ? 'item' : 'items'}
          </span>
        </div>

        <div>
          <span className="text-[10px] uppercase font-bold text-stone-500 block">
            {reportLang === 'hi' ? 'स्वीकृत अधिकारी' : 'Authorizing Officer'}
          </span>
          <span className="font-semibold text-stone-800">
            {report.approved_by || 'Dr. S. K. Verma (Scrutiny Officer)'}
          </span>
        </div>

        <div>
          <span className="text-[10px] uppercase font-bold text-stone-500 block">
            {reportLang === 'hi' ? 'जारी करने की तिथि' : 'Date of Issue'}
          </span>
          <span className="font-mono text-stone-700">
            {report.created_at ? new Date(report.created_at).toLocaleDateString() : 'Current Scrutiny Cycle'}
          </span>
        </div>
      </div>

      {/* Numbered Deficiency Items List */}
      <div className="space-y-4">
        <h3 className="text-xs font-bold text-stone-800 uppercase tracking-wide">
          {reportLang === 'hi' ? 'क्रमबद्ध कमियां एवं सुधार निर्देश' : 'Numbered Remediation Items'}
        </h3>

        {items.length === 0 ? (
          <div className="p-6 text-center bg-stone-50 rounded-lg border border-stoneBorder text-xs text-stone-600">
            <CheckCircle2 className="w-8 h-8 text-status-verified mx-auto mb-2" />
            <p className="font-semibold text-stone-900">
              {reportLang === 'hi' ? 'कोई कमी नहीं पाई गई।' : 'No deficiencies found. All documents verified.'}
            </p>
          </div>
        ) : (
          items.map((item: any, idx: number) => {
            const sev = (item.severity || 'high').toLowerCase();
            const sevConfig: Record<string, { badge: string; label: string }> = {
              high: {
                badge: 'bg-status-inconsistent-bg text-status-inconsistent-text border-status-inconsistent-border',
                label: reportLang === 'hi' ? 'उच्च गंभीरता' : 'High Severity',
              },
              medium: {
                badge: 'bg-status-needsVerification-bg text-status-needsVerification-text border-status-needsVerification-border',
                label: reportLang === 'hi' ? 'मध्यम गंभीरता' : 'Medium Severity',
              },
              low: {
                badge: 'bg-stone-100 text-stone-700 border-stone-300',
                label: reportLang === 'hi' ? 'सामान्य परामर्श' : 'Minor Advisory',
              },
            };
            const currentSev = sevConfig[sev] || {
              badge: 'bg-stone-100 text-stone-700 border-stone-300',
              label: 'Advisory',
            };

            return (
              <div
                key={item.item_id || idx}
                className="p-5 rounded-xl border border-stoneBorder bg-surface shadow-sm space-y-3.5 text-xs"
              >
                {/* Item Number + Title + Severity Chip */}
                <div className="flex flex-wrap items-center justify-between gap-2 border-b border-stoneBorder pb-2.5">
                  <div className="flex items-center gap-2">
                    <span className="font-mono font-bold text-primary text-sm bg-stone-100 px-2 py-0.5 rounded border border-stoneBorder">
                      #{idx + 1}
                    </span>
                    <h4 className="text-sm font-bold text-stone-900">
                      {item.title || item.item_id || `Deficiency ${idx + 1}`}
                    </h4>
                  </div>
                  <span
                    className={`inline-flex items-center gap-1 font-mono text-[11px] font-bold px-2 py-0.5 rounded border ${currentSev.badge}`}
                  >
                    {currentSev.label}
                  </span>
                </div>

                {/* Structured Fields: What Failed, Why, Clause, What to Resubmit */}
                <div className="space-y-2.5 text-stone-700">
                  {/* What Failed */}
                  <div>
                    <span className="font-semibold text-stone-900 block mb-0.5">
                      {reportLang === 'hi' ? 'क्या विफल हुआ (What Failed):' : 'What Failed:'}
                    </span>
                    <p className="text-stone-700 bg-stone-50 p-2.5 rounded border border-stone-200">
                      {item.what_failed || item.message || 'Deficiency detected during evaluation.'}
                    </p>
                  </div>

                  {/* Why */}
                  <div>
                    <span className="font-semibold text-stone-900 block mb-0.5">
                      {reportLang === 'hi' ? 'विफलता का कारण (Why):' : 'Reason / Findings:'}
                    </span>
                    <p className="text-stone-700 bg-stone-50 p-2.5 rounded border border-stone-200 font-mono text-[11px]">
                      {item.why || 'Conflict identified between submitted legal certificates.'}
                    </p>
                  </div>

                  {/* Clause */}
                  <div>
                    <span className="font-semibold text-stone-900 block mb-0.5">
                      {reportLang === 'hi' ? 'हैंडबुक खंड (Regulatory Clause):' : 'Handbook Regulatory Clause:'}
                    </span>
                    <p className="text-stone-600 font-mono text-[11px]">
                      {item.clause || 'AICTE Approval Process Handbook — Mandatory Legal Documents'}
                    </p>
                  </div>

                  {/* What to Resubmit */}
                  <div className="p-3 rounded-lg bg-amber-50 border border-amber-200 text-amber-950 space-y-1">
                    <span className="font-bold text-amber-900 uppercase tracking-wider text-[11px] block">
                      {reportLang === 'hi' ? 'क्या पुनः प्रस्तुत करें (What to Resubmit):' : 'What to Resubmit:'}
                    </span>
                    <p className="leading-relaxed">
                      {item.what_to_resubmit ||
                        'Please upload a genuine, valid copy from the issuing authority into your draft copy.'}
                    </p>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>

      {/* Footer CTA */}
      <div className="pt-4 border-t border-stoneBorder flex flex-wrap items-center justify-between gap-3 print:hidden">
        <p className="text-xs text-stone-500">
          Clicking "Create Draft and Fix" generates an isolated workspace copy. Your original submitted dossier remains completely untouched.
        </p>

        <button
          onClick={onCreateDraftAndFix}
          disabled={isCreatingDraft}
          className="inline-flex items-center gap-2 px-6 py-3 rounded-md bg-accent hover:bg-accent-hover text-stone-950 text-xs font-bold shadow-sm transition-colors focus-visible:ring-2"
        >
          <RefreshCw className={`w-4 h-4 ${isCreatingDraft ? 'animate-spin' : ''} text-stone-950`} />
          <span>Create Draft & Fix</span>
        </button>
      </div>
    </div>
  );
};
