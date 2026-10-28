import React, { useState, useEffect } from 'react';
import {
  HelpCircle,
  CheckCircle2,
  Eye,
  ShieldAlert,
  FileText,
  Building,
  Scale,
  Info,
  ArrowRight,
  BookOpen,
} from 'lucide-react';
import { useI18n } from '../i18n';
import { api } from '../services/api';
import { Breadcrumbs } from '../components/common/Breadcrumbs';

export const HelpPage: React.FC = () => {
  const { t } = useI18n();
  const [appTypesConfig, setAppTypesConfig] = useState<Record<string, any>>({});
  const [docTypesConfig, setDocTypesConfig] = useState<Record<string, any>>({});
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    api
      .getConfig()
      .then((cfg) => {
        if (cfg) {
          if (cfg.application_types) setAppTypesConfig(cfg.application_types);
          if (cfg.document_types) setDocTypesConfig(cfg.document_types);
        }
      })
      .catch(() => {
        // Fallback default config
        setAppTypesConfig({
          new_institute: {
            name: 'New Technical Institution',
            required_documents: ['fire_safety_certificate', 'land_document', 'trust_registration'],
            description: 'Establishment of a new engineering, management or polytechnic institution.',
          },
          extension_of_approval: {
            name: 'Extension of Approval (EoA)',
            required_documents: ['fire_safety_certificate', 'building_plan'],
            description: 'Annual continuation of approval for existing institutions.',
          },
          increase_intake: {
            name: 'Increase in Intake / Additional Course',
            required_documents: ['fire_safety_certificate', 'land_document', 'building_plan'],
            description: 'Application to increase approved intake capacity.',
          },
        });
      })
      .finally(() => setIsLoading(false));
  }, []);

  return (
    <div className="max-w-content mx-auto p-4 sm:p-6 space-y-6">
      {/* Breadcrumbs */}
      <Breadcrumbs items={[{ label: 'Institution Portal', to: '/institution/applications' }, { label: 'Help & Handbook' }]} />

      {/* Header */}
      <div className="pb-4 border-b border-stoneBorder">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-stone-100 border border-stoneBorder text-primary font-mono text-xs font-semibold mb-2">
          <BookOpen className="w-3.5 h-3.5 text-primary" />
          AICTE APPROVAL PROCESS HANDBOOK GUIDELINES
        </div>
        <h1 className="text-2xl sm:text-3xl font-extrabold text-primary font-sans">
          Validation System Help & Standards
        </h1>
        <p className="text-xs text-stone-600 mt-1 max-w-2xl">
          Complete guide explaining algorithmic document scrutiny labels, mandatory filing requirements for
          each application type, and compliance best practices.
        </p>
      </div>

      {/* Important Statutory Disclaimer Banner */}
      <div className="p-4 rounded-xl bg-amber-50 border border-amber-200 text-xs text-amber-950 flex items-start gap-3 shadow-sm">
        <Scale className="w-5 h-5 text-accent flex-shrink-0 mt-0.5" />
        <div className="space-y-1">
          <h4 className="font-bold text-amber-900 text-sm">
            Statutory Decision Authority
          </h4>
          <p className="leading-relaxed">
            <strong>Results are system-assisted. The officer makes the final decision.</strong> All OCR
            extractions, rule outputs, consistency matching scores, and label assignments are illustrative
            decision-support aids designed to streamline compliance scrutiny. Under AICTE regulations, designated
            Scrutiny and Re-Scrutiny Officers retain full authority over all application decisions.
          </p>
        </div>
      </div>

      {/* SECTION 1: WHAT THE 4 LABELS MEAN IN SIMPLE WORDS */}
      <div className="bg-surface rounded-xl border border-stoneBorder p-6 shadow-sm space-y-5">
        <div>
          <h2 className="text-lg font-bold text-primary font-sans flex items-center gap-2">
            <Info className="w-5 h-5 text-primary" />
            <span>Understanding the Four Scrutiny Labels</span>
          </h2>
          <p className="text-xs text-stone-600 mt-0.5">
            Every uploaded document and application dossier is evaluated across deterministic rules, OCR confidence,
            cross-document continuity, and image authenticity.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Label 1: Verified */}
          <div className="p-4 rounded-lg border border-status-verified-border bg-status-verified-bg/40 space-y-2">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-5 h-5 text-status-verified flex-shrink-0" />
              <h3 className="text-sm font-bold text-status-verified-text">
                Verified (Green)
              </h3>
            </div>
            <p className="text-xs text-stone-700 leading-relaxed">
              <strong>In Simple Words:</strong> All requirements met and authentic.
            </p>
            <p className="text-xs text-stone-600 leading-relaxed">
              The document passed all mandatory approval norms with high OCR confidence, valid signatures or official
              seals, matching registry entries, and no contradictions with other certificates.
            </p>
          </div>

          {/* Label 2: Needs Verification */}
          <div className="p-4 rounded-lg border border-status-needsVerification-border bg-status-needsVerification-bg/40 space-y-2">
            <div className="flex items-center gap-2">
              <Eye className="w-5 h-5 text-status-needsVerification flex-shrink-0" />
              <h3 className="text-sm font-bold text-status-needsVerification-text">
                Needs Verification (Amber)
              </h3>
            </div>
            <p className="text-xs text-stone-700 leading-relaxed">
              <strong>In Simple Words:</strong> Human officer review is needed; not rejected.
            </p>
            <p className="text-xs text-stone-600 leading-relaxed">
              A document scan has minor low OCR clarity, unreadable QR code, fold marks, or missing optional
              parameters. The scrutiny officer will manually verify this item. You do not need to panic.
            </p>
          </div>

          {/* Label 3: Inconsistent */}
          <div className="p-4 rounded-lg border border-status-inconsistent-border bg-status-inconsistent-bg/40 space-y-2">
            <div className="flex items-center gap-2">
              <svg
                className="w-5 h-5 text-status-inconsistent flex-shrink-0"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.2"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                <line x1="5" y1="9" x2="19" y2="9" />
                <line x1="5" y1="15" x2="19" y2="15" />
                <line x1="19" y1="5" x2="5" y2="19" />
              </svg>
              <h3 className="text-sm font-bold text-status-inconsistent-text">
                Inconsistent (Red)
              </h3>
            </div>
            <p className="text-xs text-stone-700 leading-relaxed">
              <strong>In Simple Words:</strong> Two submitted documents contradict each other.
            </p>
            <p className="text-xs text-stone-600 leading-relaxed">
              Information in two submitted records disagrees (for example, the registered land owner does not match
              the sponsoring trust name, or registration dates conflict chronologically). Remediation requires uploading
              a corrected legal deed.
            </p>
          </div>

          {/* Label 4: Possible Tampering */}
          <div className="p-4 rounded-lg border border-status-tampering-border bg-status-tampering-bg/40 space-y-2">
            <div className="flex items-center gap-2">
              <ShieldAlert className="w-5 h-5 text-status-tampering flex-shrink-0" />
              <h3 className="text-sm font-bold text-status-tampering-text">
                Possible Tampering (Deep Magenta)
              </h3>
            </div>
            <p className="text-xs text-stone-700 leading-relaxed">
              <strong>In Simple Words:</strong> Digital image forensics flagged inconsistencies.
            </p>
            <p className="text-xs text-stone-600 leading-relaxed">
              This document could not be verified and shows inconsistencies. Please provide a genuine, unaltered copy
              directly from the issuing statutory authority.
            </p>
          </div>
        </div>
      </div>

      {/* SECTION 2: REQUIRED DOCUMENTS PER APPLICATION TYPE (READ FROM CONFIG) */}
      <div className="bg-surface rounded-xl border border-stoneBorder p-6 shadow-sm space-y-5">
        <div>
          <h2 className="text-lg font-bold text-primary font-sans flex items-center gap-2">
            <FileText className="w-5 h-5 text-primary" />
            <span>Required Documents by Application Type</span>
          </h2>
          <p className="text-xs text-stone-600 mt-0.5">
            Synchronized directly with the AICTE Approval Process Handbook configuration rules.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {Object.entries(appTypesConfig).map(([typeKey, typeData]: [string, any]) => {
            const reqDocs: string[] = typeData.required_documents || [
              'fire_safety_certificate',
              'land_document',
              'trust_registration',
            ];
            const typeTitle =
              typeof typeData === 'object' && typeData.name
                ? typeData.name
                : typeKey.replace(/_/g, ' ').toUpperCase();

            return (
              <div
                key={typeKey}
                className="p-4 rounded-lg border border-stoneBorder bg-stone-50 flex flex-col justify-between space-y-3"
              >
                <div>
                  <span className="font-mono text-[10px] uppercase font-bold text-primary px-2 py-0.5 bg-stone-200 rounded">
                    {typeKey}
                  </span>
                  <h3 className="text-sm font-bold text-stone-900 mt-2">{typeTitle}</h3>
                  <p className="text-xs text-stone-500 mt-1">
                    {typeData.description || 'Statutory approval category under Chapter 1 of Handbook.'}
                  </p>
                </div>

                <div className="pt-2 border-t border-stoneBorder space-y-2">
                  <span className="text-[11px] font-bold text-stone-700 block uppercase tracking-wider">
                    Mandatory Checklist:
                  </span>
                  <ul className="space-y-1.5 text-xs text-stone-700">
                    {reqDocs.map((doc) => (
                      <li key={doc} className="flex items-center gap-2">
                        <CheckCircle2 className="w-3.5 h-3.5 text-status-verified flex-shrink-0" />
                        <span className="capitalize">{doc.replace(/_/g, ' ')}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* SECTION 3: SCAN QUALITY AND FILING TIPS */}
      <div className="bg-surface rounded-xl border border-stoneBorder p-6 shadow-sm space-y-4">
        <h2 className="text-lg font-bold text-primary font-sans flex items-center gap-2">
          <Building className="w-5 h-5 text-primary" />
          <span>Filing Tips for Quick Scrutiny Clearance</span>
        </h2>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs text-stone-700">
          <div className="p-3 bg-stone-50 rounded border border-stoneBorder space-y-1">
            <span className="font-bold text-stone-900 block">1. 300 DPI Flatbed Scans</span>
            <p className="text-stone-600">
              Avoid phone photos with oblique angles or shadows. Use flatbed PDF or PNG scans at 300 DPI for high OCR accuracy.
            </p>
          </div>
          <div className="p-3 bg-stone-50 rounded border border-stoneBorder space-y-1">
            <span className="font-bold text-stone-900 block">2. Visible QR Codes</span>
            <p className="text-stone-600">
              Ensure government QR codes on Land Deeds and Fire Certificates are crisp, uncropped, and free of physical fold lines.
            </p>
          </div>
          <div className="p-3 bg-stone-50 rounded border border-stoneBorder space-y-1">
            <span className="font-bold text-stone-900 block">3. Consistent Legal Names</span>
            <p className="text-stone-600">
              The sponsoring Trust / Society name must match exactly across the Trust Registration Certificate and Land Title Deed.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

