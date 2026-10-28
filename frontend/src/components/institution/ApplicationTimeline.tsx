import React from 'react';
import { CheckCircle2, Clock, FileText, Send, AlertTriangle, RefreshCw } from 'lucide-react';
import { ApplicationItem } from '../../types';

interface ApplicationTimelineProps {
  application: ApplicationItem;
  className?: string;
}

export const ApplicationTimeline: React.FC<ApplicationTimelineProps> = ({
  application,
  className = '',
}) => {
  const status = application.status.toLowerCase();
  const isDraft = status === 'draft';
  const isSubmitted = status === 'submitted';
  const isInReview = status === 'in_review';
  const isDeficiency = status === 'deficiency_sent';
  const isApproved = status === 'approved';
  const isRejected = status === 'rejected';
  const isResubmission = !!application.parent_application_id;

  const events = [
    {
      id: 'created',
      title: isResubmission ? `Draft Resubmission Created` : 'Application Initialized',
      date: application.created_at
        ? new Date(application.created_at).toLocaleDateString(undefined, {
            month: 'short',
            day: 'numeric',
            year: 'numeric',
          })
        : 'Initial',
      description: isResubmission
        ? `Remediation draft initialized from #${application.parent_application_id}.`
        : 'Dossier created by applicant institution.',
      completed: true,
      icon: <FileText className="w-3.5 h-3.5" />,
    },
    {
      id: 'submitted',
      title: 'Official Submission',
      date: application.submission_date
        ? new Date(application.submission_date).toLocaleDateString(undefined, {
            month: 'short',
            day: 'numeric',
            year: 'numeric',
          })
        : isDraft
        ? 'Pending'
        : 'Submitted',
      description: isDraft
        ? 'Application is in draft status awaiting final submission.'
        : 'Submitted to AICTE Scrutiny Officers.',
      completed: !isDraft,
      icon: <Send className="w-3.5 h-3.5" />,
    },
    {
      id: 'review',
      title: 'Officer Scrutiny & Review',
      date: isDeficiency || isApproved || isRejected ? 'Completed' : !isDraft ? 'In Progress' : 'Pending',
      description:
        isDeficiency || isApproved || isRejected
          ? 'Scrutiny officer completed evaluation of records.'
          : !isDraft
          ? 'Application queued for verification.'
          : 'Pending official submission.',
      completed: isDeficiency || isApproved || isRejected,
      icon: <Clock className="w-3.5 h-3.5" />,
    },
    {
      id: 'outcome',
      title: isApproved
        ? 'Approval Granted'
        : isRejected
        ? 'Application Rejected'
        : isDeficiency
        ? 'Deficiency Report Sent'
        : 'Final Scrutiny Decision',
      date: isApproved || isRejected || isDeficiency ? 'Issued' : 'Pending',
      description: isApproved
        ? 'AICTE Approval Order issued.'
        : isRejected
        ? 'Application rejected by officer.'
        : isDeficiency
        ? 'Deficiency report issued. Fixes may be submitted via draft.'
        : 'Formal decision pending officer review.',
      completed: isApproved || isRejected || isDeficiency,
      isWarning: isDeficiency,
      isError: isRejected,
      icon: isApproved ? (
        <CheckCircle2 className="w-3.5 h-3.5 text-status-verified" />
      ) : isDeficiency ? (
        <AlertTriangle className="w-3.5 h-3.5 text-status-needsVerification" />
      ) : (
        <CheckCircle2 className="w-3.5 h-3.5" />
      ),
    },
  ];

  return (
    <div className={`p-4 bg-surface rounded-xl border border-stoneBorder ${className}`}>
      <h3 className="text-xs font-bold text-primary uppercase tracking-wider mb-3">
        Application Progress Timeline
      </h3>

      <div className="relative pl-6 space-y-4 before:absolute before:left-2.5 before:top-2 before:bottom-2 before:w-0.5 before:bg-stone-200">
        {events.map((evt) => (
          <div key={evt.id} className="relative">
            {/* Timeline Dot */}
            <div
              className={`absolute -left-6 top-0.5 w-5 h-5 rounded-full border flex items-center justify-center text-xs ${
                evt.completed
                  ? evt.isWarning
                    ? 'bg-status-needsVerification-bg border-status-needsVerification-border text-status-needsVerification-text'
                    : evt.isError
                    ? 'bg-status-inconsistent-bg border-status-inconsistent-border text-status-inconsistent-text'
                    : 'bg-primary text-white border-primary'
                  : 'bg-stone-100 border-stone-300 text-stone-400'
              }`}
            >
              {evt.icon}
            </div>

            <div className="text-xs">
              <div className="flex items-center justify-between gap-2">
                <span className={`font-semibold ${evt.completed ? 'text-stone-900' : 'text-stone-500'}`}>
                  {evt.title}
                </span>
                <span className="font-mono text-[11px] text-stone-600">{evt.date}</span>
              </div>
              <p className="text-[11px] text-stone-600 mt-0.5 leading-relaxed">{evt.description}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

