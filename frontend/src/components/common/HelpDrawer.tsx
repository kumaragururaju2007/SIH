import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { X, CheckCircle2, Eye, ShieldAlert, BookOpen, ExternalLink, Scale, FileText } from 'lucide-react';
import { useI18n } from '../../i18n';
import { api } from '../../services/api';

interface HelpDrawerProps {
  isOpen: boolean;
  onClose: () => void;
}

export const HelpDrawer: React.FC<HelpDrawerProps> = ({ isOpen, onClose }) => {
  const { t } = useI18n();
  const [appTypes, setAppTypes] = useState<Record<string, any>>({});

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  useEffect(() => {
    if (isOpen) {
      api
        .getConfig()
        .then((cfg) => {
          if (cfg && cfg.application_types) {
            setAppTypes(cfg.application_types);
          }
        })
        .catch(() => {
          setAppTypes({
            new_institute: {
              name: 'New Technical Institution',
              required_documents: ['fire_safety_certificate', 'land_document', 'trust_registration'],
            },
            extension_of_approval: {
              name: 'Extension of Approval',
              required_documents: ['fire_safety_certificate', 'building_plan'],
            },
          });
        });
    }
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex justify-end bg-black/30 backdrop-blur-[1px] transition-opacity"
      role="dialog"
      aria-modal="true"
      aria-label="Result Labels Help Guide"
    >
      <div className="w-full max-w-md bg-surface h-full shadow-modal border-l border-stoneBorder flex flex-col animate-in slide-in-from-right duration-150">
        {/* Drawer Header */}
        <div className="flex items-center justify-between p-4 border-b border-stoneBorder bg-stone-50">
          <div className="flex items-center gap-2">
            <BookOpen className="w-5 h-5 text-primary" />
            <h3 className="text-sm font-bold text-stone-900 font-sans">
              {t('help.drawerTitle', 'Understanding Validation Labels')}
            </h3>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded text-stone-400 hover:text-stone-700 focus-visible:ring-1"
            aria-label="Close help drawer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Drawer Content */}
        <div className="p-5 overflow-y-auto space-y-5 text-xs text-stone-700 flex-1">
          {/* Statutory Note */}
          <div className="p-3 bg-amber-50 rounded-lg border border-amber-200 text-amber-950 flex items-start gap-2">
            <Scale className="w-4 h-4 text-accent flex-shrink-0 mt-0.5" />
            <div>
              <span className="font-bold block text-amber-900 mb-0.5">Decision Authority:</span>
              Results are system-assisted. The officer makes the final decision.
            </div>
          </div>

          {/* Verified */}
          <div className="p-3.5 rounded-lg border border-status-verified-border bg-status-verified-bg/40 space-y-1.5">
            <div className="flex items-center gap-2 text-status-verified-text font-bold text-sm">
              <CheckCircle2 className="w-4 h-4 text-status-verified" />
              <span>{t('labels.verified', 'Verified')}</span>
            </div>
            <p className="leading-relaxed text-stone-700">
              {t(
                'help.verifiedDesc',
                'All deterministic approval checks passed with high OCR confidence, matching metadata, valid cross-document linkages, and authentic government registry records.'
              )}
            </p>
          </div>

          {/* Needs Verification */}
          <div className="p-3.5 rounded-lg border border-status-needsVerification-border bg-status-needsVerification-bg/40 space-y-1.5">
            <div className="flex items-center gap-2 text-status-needsVerification-text font-bold text-sm">
              <Eye className="w-4 h-4 text-status-needsVerification" />
              <span>{t('labels.needs_verification', 'Needs Verification')}</span>
            </div>
            <p className="leading-relaxed text-stone-700">
              {t(
                'help.needsVerificationDesc',
                'A document has minor low OCR confidence, unreadable QR code, scan blur/noise, or missing fields that require human officer review. This is NOT a rejection.'
              )}
            </p>
          </div>

          {/* Inconsistent */}
          <div className="p-3.5 rounded-lg border border-status-inconsistent-border bg-status-inconsistent-bg/40 space-y-1.5">
            <div className="flex items-center gap-2 text-status-inconsistent-text font-bold text-sm">
              <svg
                className="w-4 h-4 text-status-inconsistent"
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
              <span>{t('labels.inconsistent', 'Inconsistent')}</span>
            </div>
            <p className="leading-relaxed text-stone-700">
              {t(
                'help.inconsistentDesc',
                'Information between two submitted documents conflicts (e.g. land ownership name differs from sponsoring trust entity name, or registration dates appear in reverse chronological order).'
              )}
            </p>
          </div>

          {/* Possible Tampering */}
          <div className="p-3.5 rounded-lg border border-status-tampering-border bg-status-tampering-bg/40 space-y-1.5">
            <div className="flex items-center gap-2 text-status-tampering-text font-bold text-sm">
              <ShieldAlert className="w-4 h-4 text-status-tampering" />
              <span>{t('labels.possible_tampering', 'Possible Tampering')}</span>
            </div>
            <p className="leading-relaxed text-stone-700">
              This document could not be verified and shows inconsistencies. Please provide a genuine copy from the issuing authority.
            </p>
          </div>

          {/* Required Documents by Application Type */}
          <div className="pt-2 border-t border-stoneBorder space-y-2.5">
            <div className="flex items-center gap-1.5 font-bold text-primary text-xs uppercase tracking-wider">
              <FileText className="w-4 h-4" />
              <span>Required Documents by Category</span>
            </div>
            <div className="space-y-2">
              {Object.entries(appTypes).map(([typeKey, typeData]: [string, any]) => {
                const reqDocs: string[] = typeData.required_documents || [];
                const typeTitle =
                  typeof typeData === 'object' && typeData.name
                    ? typeData.name
                    : typeKey.replace(/_/g, ' ').toUpperCase();

                return (
                  <div key={typeKey} className="p-2.5 bg-stone-50 rounded border border-stoneBorder">
                    <span className="font-semibold text-stone-900 block text-xs mb-1">
                      {typeTitle}
                    </span>
                    <div className="flex flex-wrap gap-1">
                      {reqDocs.map((d) => (
                        <span
                          key={d}
                          className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-surface border border-stoneBorder text-stone-700"
                        >
                          {d.replace(/_/g, ' ')}
                        </span>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Link to Dedicated Help Page */}
          <div className="pt-2 border-t border-stoneBorder flex justify-end">
            <Link
              to="/help"
              onClick={onClose}
              className="inline-flex items-center gap-1.5 text-xs font-bold text-primary hover:underline"
            >
              <span>View Full Handbook & Guidelines</span>
              <ExternalLink className="w-3.5 h-3.5" />
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
};
