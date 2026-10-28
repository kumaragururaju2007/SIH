import React, { useEffect } from 'react';
import { X, Printer, CheckCircle2, ShieldCheck, Download, Building, FileText } from 'lucide-react';
import { ApplicationItem } from '../../types';

interface SubmissionReceiptModalProps {
  isOpen: boolean;
  onClose: () => void;
  application: ApplicationItem;
}

export const SubmissionReceiptModal: React.FC<SubmissionReceiptModalProps> = ({
  isOpen,
  onClose,
  application,
}) => {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const docs = application.documents || [];
  const submissionDateFormatted = application.submission_date
    ? new Date(application.submission_date).toLocaleString()
    : new Date().toLocaleString();

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-[1px]"
      role="dialog"
      aria-modal="true"
      aria-label="Official Submission Receipt"
    >
      <div className="w-full max-w-2xl bg-surface rounded-xl border border-stoneBorder shadow-modal overflow-hidden flex flex-col max-h-[90vh]">
        {/* Receipt Header (not printed) */}
        <div className="flex items-center justify-between p-4 border-b border-stoneBorder bg-stone-50 print:hidden">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-5 h-5 text-primary" />
            <h3 className="text-sm font-bold text-stone-900 font-sans">
              Official AICTE Submission Receipt
            </h3>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => window.print()}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-bold bg-primary hover:bg-primary-hover text-white transition-colors"
            >
              <Printer className="w-3.5 h-3.5" />
              <span>Print Receipt</span>
            </button>
            <button
              onClick={onClose}
              className="p-1.5 rounded text-stone-400 hover:text-stone-700"
              aria-label="Close receipt"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Printable Receipt Body */}
        <div className="p-6 overflow-y-auto space-y-6 text-xs text-stone-800 print:p-8">
          {/* Official Letterhead */}
          <div className="border-b-2 border-primary pb-4 text-center space-y-1">
            <h2 className="text-base font-extrabold text-primary uppercase tracking-wide">
              All India Council for Technical Education
            </h2>
            <p className="text-stone-600 text-[11px]">
              Approval Process Workstation • Statutory Submission Acknowledgment
            </p>
            <div className="inline-block mt-2 px-3 py-0.5 rounded bg-green-50 border border-green-200 text-green-900 font-mono text-[11px] font-bold">
              RECEIPT NO: AICTE-ACK-{application.id}-{new Date().getFullYear()}
            </div>
          </div>

          {/* Dossier Metadata Grid */}
          <div className="grid grid-cols-2 gap-4 bg-stone-50 p-4 rounded-lg border border-stoneBorder">
            <div>
              <span className="text-[10px] text-stone-500 uppercase font-semibold block">Applicant Institution</span>
              <span className="font-bold text-stone-900 text-sm">
                {application.institution_name || 'Registered Technical Institution'}
              </span>
            </div>
            <div>
              <span className="text-[10px] text-stone-500 uppercase font-semibold block">Application ID</span>
              <span className="font-mono font-bold text-primary text-sm">#{application.id}</span>
            </div>
            <div>
              <span className="text-[10px] text-stone-500 uppercase font-semibold block">Application Type</span>
              <span className="capitalize font-semibold text-stone-800">
                {application.application_type.replace(/_/g, ' ')}
              </span>
            </div>
            <div>
              <span className="text-[10px] text-stone-500 uppercase font-semibold block">Timestamp of Submission</span>
              <span className="font-mono text-stone-700">{submissionDateFormatted}</span>
            </div>
          </div>

          {/* Document Verification Digest Table */}
          <div className="space-y-2">
            <h4 className="font-bold text-primary uppercase tracking-wider text-[11px]">
              Uploaded Statutory Deeds & Digital Hashes ({docs.length} Documents)
            </h4>
            <div className="border border-stoneBorder rounded-lg overflow-hidden">
              <table className="w-full text-left border-collapse">
                <thead className="bg-stone-100 text-[10px] uppercase text-stone-600 border-b border-stoneBorder">
                  <tr>
                    <th className="p-2 font-semibold">#</th>
                    <th className="p-2 font-semibold">Document Type</th>
                    <th className="p-2 font-semibold">Language</th>
                    <th className="p-2 font-semibold">SHA-256 Checksum</th>
                    <th className="p-2 font-semibold">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-stoneBorder font-mono text-[11px]">
                  {docs.map((d, idx) => (
                    <tr key={d.id} className="hover:bg-stone-50/50">
                      <td className="p-2 text-stone-400 font-sans">{idx + 1}</td>
                      <td className="p-2 font-sans font-medium capitalize text-stone-900">
                        {(d.doc_type || 'Supporting Document').replace(/_/g, ' ')}
                      </td>
                      <td className="p-2 uppercase text-stone-600">{d.language || 'EN'}</td>
                      <td className="p-2 text-[10px] text-stone-600 truncate max-w-[180px]" title={d.sha256}>
                        {d.sha256 ? `${d.sha256.substring(0, 16)}...` : 'Pending'}
                      </td>
                      <td className="p-2 font-sans">
                        <span className="inline-flex items-center gap-1 text-[10px] font-semibold text-status-verified-text">
                          <CheckCircle2 className="w-3 h-3 text-status-verified" />
                          <span>Filed</span>
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Legal Certification Note */}
          <div className="p-3 bg-stone-100 rounded text-[11px] text-stone-600 border border-stoneBorder space-y-1">
            <span className="font-bold text-stone-900 block">Digital Verification Notice:</span>
            <p>
              This acknowledgment confirms receipt of the institutional application dossier for scrutiny under the
              AICTE Approval Process Handbook. System-assisted scrutiny will proceed and findings will be reviewed by
              appointed Scrutiny Officers.
            </p>
          </div>
        </div>

        {/* Modal Footer */}
        <div className="p-3 border-t border-stoneBorder bg-stone-50 flex justify-end gap-2 print:hidden">
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded border border-stoneBorder bg-surface text-stone-700 text-xs font-semibold hover:bg-stone-100"
          >
            Close
          </button>
          <button
            onClick={() => window.print()}
            className="inline-flex items-center gap-1.5 px-4 py-1.5 rounded bg-primary text-white text-xs font-bold hover:bg-primary-hover shadow-sm"
          >
            <Printer className="w-3.5 h-3.5" />
            <span>Print / Save PDF</span>
          </button>
        </div>
      </div>
    </div>
  );
};

