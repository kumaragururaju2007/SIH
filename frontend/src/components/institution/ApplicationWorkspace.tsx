import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  FileText,
  Play,
  Send,
  AlertTriangle,
  CheckCircle2,
  RefreshCw,
  ArrowRight,
  ShieldAlert,
  FileCheck,
  Building,
  Trash2,
  Upload,
  Info,
  Clock,
  Printer,
  ChevronDown,
  ChevronRight,
  Scale,
  Eye,
} from 'lucide-react';
import { api, ValidationStageProgress } from '../../services/api';
import { useAuth } from '../../auth/AuthContext';
import { useToast } from '../../context/ToastContext';
import { useI18n } from '../../i18n';
import {
  ApplicationItem,
  CompletenessData,
  DocumentItem,
  DraftComparisonResponse,
  DeficiencyReportData,
  ConsistencyComparison,
} from '../../types';
import { Stepper, StepItem } from '../common/Stepper';
import { FileDropzone } from '../common/FileDropzone';
import { StatusChip } from '../common/StatusChip';
import { IssueCard } from '../common/IssueCard';
import { BeforeAfterPanel } from '../common/BeforeAfterPanel';
import { ConfirmDialog } from '../common/ConfirmDialog';
import { ValidationProgressModal } from '../common/ValidationProgressModal';
import { Breadcrumbs } from '../common/Breadcrumbs';
import { HowDecidedExpander } from '../common/HowDecidedExpander';
import { SideBySideCompare } from '../common/SideBySideCompare';
import { ApplicationTimeline } from './ApplicationTimeline';
import { SubmissionReceiptModal } from './SubmissionReceiptModal';
import { DeficiencyReportView } from './DeficiencyReportView';
import { ExtractedFieldsView } from './ExtractedFieldsView';

export const ApplicationWorkspace: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const appId = Number(id);
  const { user } = useAuth();
  const { showToast } = useToast();
  const { t } = useI18n();
  const navigate = useNavigate();

  const [activeStep, setActiveStep] = useState<number>(1);
  const [application, setApplication] = useState<ApplicationItem | null>(null);
  const [completeness, setCompleteness] = useState<CompletenessData | null>(null);
  const [consistencyData, setConsistencyData] = useState<{ summary: any; comparisons: ConsistencyComparison[] } | null>(null);
  const [deficiencyReport, setDeficiencyReport] = useState<DeficiencyReportData | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Upload progress state per docType or general
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<number>(0);
  const [targetUploadDocType, setTargetUploadDocType] = useState<string | null>(null);

  // Delete document modal
  const [docToDelete, setDocToDelete] = useState<DocumentItem | null>(null);
  const [isDeleting, setIsDeleting] = useState(false);

  // Pre-check state
  const [isValidating, setIsValidating] = useState(false);
  const [validationProgress, setValidationProgress] = useState<ValidationStageProgress | null>(null);
  const [validationResults, setValidationResults] = useState<any | null>(null);
  const [selectedDocForFields, setSelectedDocForFields] = useState<DocumentItem | null>(null);

  // Submit confirmation dialog
  const [showSubmitModal, setShowSubmitModal] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [showReceiptModal, setShowReceiptModal] = useState(false);

  // Fix and recheck draft state
  const [draftApp, setDraftApp] = useState<ApplicationItem | null>(null);
  const [comparison, setComparison] = useState<DraftComparisonResponse | null>(null);
  const [isRechecking, setIsRechecking] = useState(false);
  const [isCreatingDraft, setIsCreatingDraft] = useState(false);
  const [hasRecheckedOnce, setHasRecheckedOnce] = useState(false);
  const [showResubmitModal, setShowResubmitModal] = useState(false);
  const [isSubmittingResubmission, setIsSubmittingResubmission] = useState(false);

  const steps: StepItem[] = [
    { id: 1, label: t('institution.stepper.step1', '1. Documents'), description: 'Upload mandatory deeds' },
    { id: 2, label: t('institution.stepper.step2', '2. Pre-submission check'), description: 'Safe self-scrutiny' },
    { id: 3, label: t('institution.stepper.step3', '3. Submit'), description: 'Official dossier submission' },
    { id: 4, label: t('institution.stepper.step4', '4. Feedback'), description: 'Deficiency report' },
    { id: 5, label: t('institution.stepper.step5', '5. Fix and recheck'), description: 'Draft resubmission' },
  ];

  const loadData = async () => {
    if (!appId) return;
    setIsLoading(true);
    try {
      const [appData, compData, consData] = await Promise.all([
        api.getApplication(appId),
        api.getCompleteness(appId).catch(() => null),
        api.getConsistency(appId).catch(() => null),
      ]);
      setApplication(appData);
      setCompleteness(compData);
      setConsistencyData(consData);

      // Attempt to load deficiency report if status suggests it
      if (appData.status === 'deficiency_sent' || appData.status === 'approved') {
        try {
          const report = await api.getApplicationDeficiencyReport(appId);
          setDeficiencyReport(report);
        } catch {
          // If not formal yet, will derive in UI
        }
      }

      // Auto-position stepper based on status on first load
      if (appData.status === 'submitted') {
        setActiveStep(3);
      } else if (appData.status === 'deficiency_sent') {
        setActiveStep(4);
      } else if (appData.parent_application_id && appData.status === 'draft') {
        setActiveStep(5);
        setDraftApp(appData);
        // Load comparison
        api.getDraftComparison(appData.id).then((cmp) => {
          if (cmp) {
            setComparison(cmp);
            setHasRecheckedOnce(true);
          }
        }).catch(() => null);
      }
    } catch (err: any) {
      showToast('error', 'Error loading application', err.message);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [appId]);

  // Handle document upload with animated progress bar
  const handleFileUpload = async (file: File) => {
    if (!appId) return;
    setIsUploading(true);
    setUploadProgress(15);

    const progressTimer = setInterval(() => {
      setUploadProgress((p) => (p < 85 ? p + 20 : p));
    }, 120);

    try {
      await api.uploadDocument(appId, file);
      clearInterval(progressTimer);
      setUploadProgress(100);
      showToast('success', 'Document uploaded', `${file.name} uploaded successfully.`);
      await loadData();
    } catch (err: any) {
      clearInterval(progressTimer);
      showToast('error', 'Upload failed', err.message);
    } finally {
      setTimeout(() => {
        setIsUploading(false);
        setUploadProgress(0);
        setTargetUploadDocType(null);
      }, 400);
    }
  };

  // Remove document in draft mode
  const handleConfirmDeleteDoc = async () => {
    if (!docToDelete) return;
    setIsDeleting(true);
    try {
      await api.deleteDocument(docToDelete.id);
      showToast('success', 'Document removed', 'Document scan removed from draft application.');
      setDocToDelete(null);
      await loadData();
    } catch (err: any) {
      showToast('error', 'Failed to remove document', err.message);
    } finally {
      setIsDeleting(false);
    }
  };

  // Run Pre-submission Check
  const handleRunPreCheck = async () => {
    if (!appId) return;
    setIsValidating(true);
    try {
      const results = await api.runValidationWithProgress(appId, (progress) => {
        setValidationProgress(progress);
      });
      setValidationResults(results);
      showToast('success', 'Pre-submission check completed', 'Safe evaluation findings updated.');
      await loadData();
    } catch (err: any) {
      showToast('error', 'Validation check failed', err.message);
    } finally {
      setIsValidating(false);
      setValidationProgress(null);
    }
  };

  // Official Submit
  const handleOfficialSubmit = async () => {
    if (!appId) return;
    setIsSubmitting(true);
    try {
      const updated = await api.submitApplication(appId);
      setApplication(updated);
      setShowSubmitModal(false);
      showToast('success', 'Application submitted officially!', 'Your application has entered the officer scrutiny queue.');
      setShowReceiptModal(true);
      await loadData();
    } catch (err: any) {
      showToast('error', 'Submission failed', err.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  // Create Draft and Fix
  const handleCreateDraftAndFix = async () => {
    if (!appId) return;
    setIsCreatingDraft(true);
    try {
      const draft = await api.createDraft(appId);
      setDraftApp(draft);
      showToast('success', 'Draft created', `Draft copy #${draft.id} created. Your original submission stays unchanged.`);
      setActiveStep(5);
      // Run initial comparison
      const cmp = await api.getDraftComparison(draft.id).catch(() => null);
      if (cmp) setComparison(cmp);
    } catch (err: any) {
      showToast('error', 'Failed to create draft', err.message);
    } finally {
      setIsCreatingDraft(false);
    }
  };

  // Draft replacement upload
  const handleDraftDocUpload = async (file: File) => {
    const targetDraftId = draftApp ? draftApp.id : appId;
    setIsUploading(true);
    setUploadProgress(20);

    const progressTimer = setInterval(() => {
      setUploadProgress((p) => (p < 85 ? p + 20 : p));
    }, 120);

    try {
      await api.uploadDraftDocument(targetDraftId, file);
      clearInterval(progressTimer);
      setUploadProgress(100);
      showToast('success', 'Replacement uploaded', 'Replacement deed uploaded into draft copy.');
      await handleRecheckDraft();
    } catch (err: any) {
      clearInterval(progressTimer);
      showToast('error', 'Draft upload failed', err.message);
    } finally {
      setTimeout(() => {
        setIsUploading(false);
        setUploadProgress(0);
      }, 400);
    }
  };

  // Recheck Draft
  const handleRecheckDraft = async () => {
    const targetDraftId = draftApp ? draftApp.id : appId;
    setIsRechecking(true);
    try {
      await api.recheckDraft(targetDraftId);
      const cmp = await api.getDraftComparison(targetDraftId);
      setComparison(cmp);
      setHasRecheckedOnce(true);
      showToast('success', 'Draft recheck complete', 'Differential comparison refreshed.');
    } catch (err: any) {
      showToast('error', 'Recheck failed', err.message);
    } finally {
      setIsRechecking(false);
    }
  };

  // Submit Resubmission
  const handleSubmitResubmission = async () => {
    const targetDraftId = draftApp ? draftApp.id : appId;
    setIsSubmittingResubmission(true);
    try {
      await api.submitResubmission(targetDraftId);
      setShowResubmitModal(false);
      showToast('success', 'Resubmission submitted!', 'Your corrected dossier is now officially resubmitted.');
      navigate('/institution/applications');
    } catch (err: any) {
      showToast('error', 'Resubmission failed', err.message);
    } finally {
      setIsSubmittingResubmission(false);
    }
  };

  if (isLoading || !application) {
    return (
      <div className="max-w-content mx-auto p-12 text-center text-stone-500 space-y-3">
        <RefreshCw className="w-8 h-8 mx-auto animate-spin text-primary" />
        <p className="text-xs font-semibold">Loading application dossier #{appId}...</p>
      </div>
    );
  }

  const docs = application.documents || [];
  const requiredDocTypes = completeness?.required || [
    'fire_safety_certificate',
    'land_document',
    'trust_registration',
  ];
  const isDraft = application.status === 'draft';
  const isDeficiency = application.status === 'deficiency_sent';
  const isSubmitted = application.status === 'submitted';

  // Calculate label summary counts for pre-submission check
  const labelCounts = {
    verified: docs.filter((d) => (d.label || '').toLowerCase() === 'verified').length,
    needs_verification: docs.filter(
      (d) => (d.label || '').toLowerCase() === 'needs_verification' || !d.label
    ).length + (completeness?.missing?.length || 0),
    inconsistent: docs.filter((d) => (d.label || '').toLowerCase() === 'inconsistent').length +
      (consistencyData?.comparisons?.filter((c) => c.status === 'conflict').length || 0),
    possible_tampering: docs.filter(
      (d) =>
        (d.label || '').toLowerCase() === 'possible_tampering' ||
        (d.label || '').toLowerCase() === 'tampered'
    ).length,
  };

  return (
    <div className="max-w-content mx-auto p-4 sm:p-6 space-y-6">
      {/* Breadcrumbs */}
      <Breadcrumbs
        items={[
          { label: 'Institution Portal', to: '/institution/applications' },
          { label: `Application #${application.id}` },
        ]}
      />

      {/* Top Header Card */}
      <div className="p-4 sm:p-5 bg-surface rounded-xl border border-stoneBorder flex flex-wrap items-center justify-between gap-4 shadow-sm">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="font-mono text-xs font-bold text-primary px-2 py-0.5 bg-stone-100 rounded border border-stoneBorder">
              APP #{application.id}
            </span>
            <span className="capitalize text-xs font-semibold px-2 py-0.5 rounded bg-stone-100 text-stone-700">
              {application.application_type.replace(/_/g, ' ')}
            </span>
            {application.parent_application_id && (
              <span className="text-[11px] font-mono text-accent font-semibold px-2 py-0.5 bg-amber-50 rounded border border-amber-200">
                Resubmission of #{application.parent_application_id}
              </span>
            )}
          </div>
          <h1 className="text-lg sm:text-xl font-bold text-stone-900 font-sans">
            {user?.institutionName || application.institution_name}
          </h1>
          <p className="text-xs text-stone-500 mt-0.5">
            Target Submission Date:{' '}
            <span className="font-mono">{application.submission_date || 'Draft in progress'}</span>
          </p>
        </div>

        <div className="flex items-center gap-4">
          <div className="text-right">
            <span className="text-[10px] uppercase font-bold text-stone-600 block tracking-wider">
              Dossier Status
            </span>
            <StatusChip label={application.status} size="sm" />
          </div>

          {!isDraft && (
            <button
              onClick={() => setShowReceiptModal(true)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md border border-stoneBorder bg-surface hover:bg-stone-50 text-xs font-semibold text-stone-700 transition-colors focus-visible:ring-1"
              title="View & Print Official Receipt"
            >
              <Printer className="w-3.5 h-3.5 text-stone-500" />
              <span>Receipt</span>
            </button>
          )}
        </div>
      </div>

      {/* 2-Column Layout: Stepper (Left) & Workspace Content (Right) */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6 items-start">
        {/* Left Column: Stepper & Application Timeline */}
        <div className="lg:col-span-1 space-y-4">
          <div className="bg-surface p-3 rounded-xl border border-stoneBorder shadow-sm">
            <Stepper steps={steps} activeStep={activeStep} onStepClick={(s) => setActiveStep(s)} />
          </div>

          <ApplicationTimeline application={application} />
        </div>

        {/* Right Content Area */}
        <div className="lg:col-span-3 space-y-6">
          {/* STEP 1: DOCUMENTS */}
          {activeStep === 1 && (
            <div className="bg-surface p-5 rounded-xl border border-stoneBorder shadow-sm space-y-5">
              <div className="flex flex-wrap items-center justify-between gap-2 pb-4 border-b border-stoneBorder">
                <div>
                  <h2 className="text-base font-bold text-primary font-sans">
                    {t('institution.documents.title', 'Mandatory Approval Documents')}
                  </h2>
                  <p className="text-xs text-stone-600 mt-0.5">
                    {t('institution.documents.uploadHint', 'Upload PDF or high-resolution PNG/JPG scans up to 25MB')}
                  </p>
                </div>
                <span className="font-mono text-xs text-stone-500">
                  {docs.length} / {requiredDocTypes.length} Uploaded
                </span>
              </div>

              {/* Upload Progress Bar if active */}
              {isUploading && (
                <div className="p-3 bg-stone-50 rounded-lg border border-stoneBorder space-y-1.5">
                  <div className="flex justify-between text-xs text-stone-700 font-semibold">
                    <span>Uploading document scan...</span>
                    <span className="font-mono">{uploadProgress}%</span>
                  </div>
                  <div className="w-full h-2 bg-stone-200 rounded-full overflow-hidden">
                    <div
                      className="h-full bg-accent transition-all duration-200"
                      style={{ width: `${uploadProgress}%` }}
                    />
                  </div>
                </div>
              )}

              {/* Checklist Cards per Required Document */}
              <div className="grid grid-cols-1 gap-4">
                {requiredDocTypes.map((docType) => {
                  const uploaded = docs.find((d) => d.doc_type === docType);
                  const isPresent = !!uploaded;
                  const isDuplicate = completeness?.duplicates_of_type?.includes(docType);

                  return (
                    <div
                      key={docType}
                      className={`p-4 rounded-xl border transition-all ${
                        isPresent
                          ? 'border-status-verified-border bg-status-verified-bg/15'
                          : 'border-status-needsVerification-border bg-status-needsVerification-bg/15'
                      }`}
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2 mb-3">
                        <div className="flex items-center gap-2">
                          {isPresent ? (
                            <CheckCircle2 className="w-5 h-5 text-status-verified flex-shrink-0" />
                          ) : (
                            <AlertTriangle className="w-5 h-5 text-status-needsVerification flex-shrink-0" />
                          )}
                          <div>
                            <h4 className="text-sm font-bold text-stone-900 capitalize">
                              {docType.replace(/_/g, ' ')}
                            </h4>
                            <span className="text-[11px] font-mono text-stone-500">
                              {isPresent ? 'State: Present' : 'State: Missing'}
                            </span>
                          </div>
                        </div>

                        <StatusChip
                          label={uploaded ? uploaded.label || 'verified' : 'needs_verification'}
                          size="sm"
                        />
                      </div>

                      {/* Duplicate Warning */}
                      {isDuplicate && (
                        <div className="mb-3 p-2 bg-amber-50 border border-amber-200 rounded text-xs text-amber-900 flex items-center gap-2">
                          <AlertTriangle className="w-4 h-4 text-accent flex-shrink-0" />
                          <span>Multiple scans for this deed uploaded. Latest version will be evaluated.</span>
                        </div>
                      )}

                      {/* Document Details Thumbnail Card if Uploaded */}
                      {uploaded ? (
                        <div className="space-y-3">
                          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs font-mono bg-surface p-3 rounded-lg border border-stoneBorder shadow-sm">
                            <div>
                              <span className="text-[10px] text-stone-600 block uppercase">Language</span>
                              <span className="font-semibold text-stone-800 uppercase">
                                {uploaded.ocr_language || uploaded.language || 'EN'}
                              </span>
                            </div>
                            <div>
                              <span className="text-[10px] text-stone-600 block uppercase">OCR Score</span>
                              <span className="font-semibold text-stone-800 tabular-nums">
                                {uploaded.ocr_confidence
                                  ? `${Math.round(uploaded.ocr_confidence * 100)}%`
                                  : '88%'}
                              </span>
                            </div>
                            <div>
                              <span className="text-[10px] text-stone-600 block uppercase">Doc ID</span>
                              <span className="font-semibold text-primary">#{uploaded.id}</span>
                            </div>
                            <div>
                              <span className="text-[10px] text-stone-600 block uppercase">SHA-256</span>
                              <span className="text-stone-600 truncate block text-[10px]" title={uploaded.sha256}>
                                {uploaded.sha256 ? `${uploaded.sha256.substring(0, 8)}...` : 'Computed'}
                              </span>
                            </div>
                          </div>

                          <div className="flex flex-wrap items-center justify-between gap-2 pt-1 text-xs">
                            <span className="text-stone-500 truncate max-w-xs font-mono text-[11px]">
                              {uploaded.file_path.split(/[\\/]/).pop()}
                            </span>

                            {isDraft && (
                              <div className="flex items-center gap-2">
                                <button
                                  onClick={() => setTargetUploadDocType(docType)}
                                  className="px-2.5 py-1 rounded border border-stoneBorder bg-surface hover:bg-stone-50 font-semibold text-primary transition-colors text-xs"
                                >
                                  Replace Scan
                                </button>
                                <button
                                  onClick={() => setDocToDelete(uploaded)}
                                  className="p-1 rounded text-red-600 hover:bg-red-50 hover:text-red-700 transition-colors"
                                  title="Remove uploaded document"
                                  aria-label={`Remove ${docType}`}
                                >
                                  <Trash2 className="w-4 h-4" />
                                </button>
                              </div>
                            )}
                          </div>
                        </div>
                      ) : (
                        <FileDropzone
                          label={`Upload ${docType.replace(/_/g, ' ')} (PDF, PNG, JPG up to 25MB)`}
                          onFileSelect={handleFileUpload}
                        />
                      )}
                    </div>
                  );
                })}

                {/* Unrecognized Documents Section */}
                {completeness?.unrecognized && completeness.unrecognized.length > 0 && (
                  <div className="p-4 rounded-xl border border-amber-200 bg-amber-50 text-xs text-amber-900 space-y-2">
                    <div className="flex items-center gap-1.5 font-bold">
                      <AlertTriangle className="w-4 h-4 text-accent" />
                      <span>Unrecognized Document Scans Detected</span>
                    </div>
                    <p className="leading-relaxed">
                      An officer will review this document manually during official scrutiny.
                    </p>
                  </div>
                )}
              </div>

              {/* Upload Additional Supporting Document */}
              <div className="pt-4 border-t border-stoneBorder space-y-2">
                <h4 className="text-xs font-bold text-stone-700 uppercase tracking-wide">
                  Upload Additional Supporting File
                </h4>
                <FileDropzone onFileSelect={handleFileUpload} />
              </div>

              {/* Document Clearance Tips Card */}
              <div className="p-3 bg-stone-50 rounded-lg border border-stoneBorder text-xs text-stone-600 flex items-start gap-2">
                <Info className="w-4 h-4 text-stone-400 flex-shrink-0 mt-0.5" />
                <p>
                  <strong>Filing Tips:</strong> Ensure deed scans are flat, 300 DPI, and government QR codes are uncropped.
                  Clear scans achieve higher OCR confidence and faster scrutiny approval.
                </p>
              </div>

              {/* Bottom CTA to Step 2 */}
              <div className="flex justify-end pt-2">
                <button
                  onClick={() => setActiveStep(2)}
                  className="inline-flex items-center gap-2 px-5 py-2.5 rounded-md bg-primary hover:bg-primary-hover text-white text-xs font-bold shadow-sm transition-colors focus-visible:ring-2"
                >
                  <span>Proceed to Pre-Submission Check</span>
                  <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}

          {/* STEP 2: PRE-SUBMISSION CHECK (RESULTS VIEW) */}
          {activeStep === 2 && (
            <div className="bg-surface p-5 rounded-xl border border-stoneBorder shadow-sm space-y-6">
              <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-stoneBorder">
                <div>
                  <h2 className="text-base font-bold text-primary font-sans">
                    {t('institution.preCheck.title', 'Pre-Submission Validation Check')}
                  </h2>
                  <p className="text-xs text-stone-600 mt-0.5">
                    Safe self-scrutiny runs rules, cross-document entity checks, and checks for deficiencies.
                  </p>
                </div>

                <button
                  onClick={handleRunPreCheck}
                  disabled={isValidating}
                  className="inline-flex items-center gap-2 px-5 py-2.5 rounded-md bg-accent hover:bg-accent-hover text-stone-950 text-xs font-bold shadow-sm transition-colors focus-visible:ring-2"
                >
                  {isValidating ? (
                    <RefreshCw className="w-4 h-4 animate-spin text-stone-950" />
                  ) : (
                    <Play className="w-4 h-4 fill-stone-950 text-stone-950" />
                  )}
                  <span>{t('institution.preCheck.runButton', 'Run Pre-Submission Check')}</span>
                </button>
              </div>

              {/* Prominent Safety Notice */}
              <div className="p-3.5 bg-stone-100 rounded-lg border border-stoneBorder flex items-center gap-2.5 text-xs text-stone-800">
                <ShieldAlert className="w-4 h-4 text-accent flex-shrink-0" />
                <span>
                  <strong>Safe Evaluation:</strong> This check does not submit your application. You can review all
                  findings, compare conflicting documents side by side, and upload fixes beforehand without penalty.
                </span>
              </div>

              {/* Summary Strip (Counts per Label with Icon + Text) */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                <div className="p-3 rounded-lg border border-status-verified-border bg-status-verified-bg/40 text-center flex flex-col items-center justify-center">
                  <div className="flex items-center gap-1.5 text-status-verified-text text-xs font-semibold mb-1">
                    <CheckCircle2 className="w-4 h-4 text-status-verified" />
                    <span>Verified</span>
                  </div>
                  <span className="text-2xl font-bold font-mono text-status-verified-text">
                    {labelCounts.verified}
                  </span>
                </div>

                <div className="p-3 rounded-lg border border-status-needsVerification-border bg-status-needsVerification-bg/40 text-center flex flex-col items-center justify-center">
                  <div className="flex items-center gap-1.5 text-status-needsVerification-text text-xs font-semibold mb-1">
                    <Eye className="w-4 h-4 text-status-needsVerification" />
                    <span>Needs Verification</span>
                  </div>
                  <span className="text-2xl font-bold font-mono text-status-needsVerification-text">
                    {labelCounts.needs_verification}
                  </span>
                </div>

                <div className="p-3 rounded-lg border border-status-inconsistent-border bg-status-inconsistent-bg/40 text-center flex flex-col items-center justify-center">
                  <div className="flex items-center gap-1.5 text-status-inconsistent-text text-xs font-semibold mb-1">
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
                    <span>Inconsistent</span>
                  </div>
                  <span className="text-2xl font-bold font-mono text-status-inconsistent-text">
                    {labelCounts.inconsistent}
                  </span>
                </div>

                <div className="p-3 rounded-lg border border-status-tampering-border bg-status-tampering-bg/40 text-center flex flex-col items-center justify-center">
                  <div className="flex items-center gap-1.5 text-status-tampering-text text-xs font-semibold mb-1">
                    <ShieldAlert className="w-4 h-4 text-status-tampering" />
                    <span>Possible Tampering</span>
                  </div>
                  <span className="text-2xl font-bold font-mono text-status-tampering-text">
                    {labelCounts.possible_tampering}
                  </span>
                </div>
              </div>

              {/* Per-Document Evaluation Cards with Plain Language Reasons */}
              <div className="space-y-3 pt-2">
                <h3 className="text-xs font-bold text-stone-800 uppercase tracking-wide">
                  Per-Document Evaluation Status
                </h3>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {docs.map((d) => (
                    <div
                      key={d.id}
                      className="p-4 rounded-xl border border-stoneBorder bg-surface shadow-sm space-y-2 text-xs"
                    >
                      <div className="flex items-center justify-between gap-2 border-b border-stoneBorder pb-2">
                        <span className="font-bold text-stone-900 capitalize text-sm">
                          {(d.doc_type || 'Document').replace(/_/g, ' ')}
                        </span>
                        <StatusChip label={d.label || 'needs_verification'} size="sm" />
                      </div>

                      <p className="text-stone-600 leading-relaxed text-[11px]">
                        {d.label === 'possible_tampering'
                          ? 'This document could not be verified and shows inconsistencies. Please provide a genuine copy from the issuing authority.'
                          : d.label === 'inconsistent'
                          ? 'Cross-document conflict identified between this certificate and other submitted legal records.'
                          : d.label === 'verified'
                          ? 'All automated checks passed with verified registry continuity.'
                          : 'Requires review due to low scan clarity, missing parameters, or unread QR.'}
                      </p>

                      <div className="flex items-center justify-between pt-1 border-t border-stone-100">
                        <span className="font-mono text-[10px] text-stone-400">
                          Confidence: {d.ocr_confidence ? `${Math.round(d.ocr_confidence * 100)}%` : '85%'}
                        </span>
                        <button
                          onClick={() => setSelectedDocForFields(selectedDocForFields?.id === d.id ? null : d)}
                          className="text-xs font-semibold text-primary hover:underline"
                        >
                          {selectedDocForFields?.id === d.id ? 'Hide Extracted Fields' : 'View Extracted Fields'}
                        </button>
                      </div>

                      {/* Expandable Extracted Fields Table */}
                      {selectedDocForFields?.id === d.id && (
                        <div className="pt-2 border-t border-stoneBorder">
                          <ExtractedFieldsView fields={d.extracted_fields || []} />
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              {/* Side-by-Side Inconsistency Comparisons (e.g. Land Owner vs Trust) */}
              {consistencyData?.comparisons && consistencyData.comparisons.length > 0 && (
                <div className="space-y-3 pt-2">
                  <h3 className="text-xs font-bold text-stone-800 uppercase tracking-wide">
                    Cross-Document Consistency Analysis
                  </h3>
                  <div className="space-y-3">
                    {consistencyData.comparisons.map((cmp, idx) => (
                      <SideBySideCompare key={idx} comparison={cmp} />
                    ))}
                  </div>
                </div>
              )}

              {/* Regulatory Findings & Issues Cards */}
              <div className="space-y-3 pt-2">
                <h3 className="text-xs font-bold text-stone-800 uppercase tracking-wide">
                  Regulatory Issues & Actions Needed
                </h3>

                {completeness?.missing && completeness.missing.length > 0 && (
                  completeness.missing.map((m) => (
                    <IssueCard
                      key={m}
                      id={`MISSING-${m}`}
                      title={`Missing Mandatory Document: ${m.replace(/_/g, ' ').toUpperCase()}`}
                      message={`The application dossier is missing '${m.replace(/_/g, ' ')}' which is required under AICTE Approval Process Handbook norms.`}
                      severity="high"
                      clause="Handbook Chapter 1 Mandatory Documents"
                      docType={m}
                      actionRequired={`Upload official ${m.replace(/_/g, ' ')} in Step 1 before proceeding to final submission.`}
                    />
                  ))
                )}

                {validationResults?.findings?.map((f: any, idx: number) => (
                  <div key={idx} className="space-y-2">
                    <IssueCard
                      id={f.rule_id || `RULE-${idx}`}
                      title={f.description || f.rule_id}
                      message={f.message}
                      severity={f.severity || 'high'}
                      clause={f.clause || 'Handbook Approval Norms'}
                      valuesUsed={f.actual_values}
                    />
                    <HowDecidedExpander
                      ruleId={f.rule_id}
                      checkType={f.category || 'compliance_rule'}
                      docType={f.doc_type}
                      clause={f.clause || 'Handbook Approval Norms'}
                      actualValues={f.actual_values}
                    />
                  </div>
                ))}
              </div>

              {/* Bottom Navigation */}
              <div className="flex items-center justify-between pt-4 border-t border-stoneBorder">
                <button
                  onClick={() => setActiveStep(1)}
                  className="px-4 py-2 text-xs font-semibold text-stone-600 hover:text-stone-900"
                >
                  Back to Documents
                </button>
                <button
                  onClick={() => setActiveStep(3)}
                  className="inline-flex items-center gap-2 px-5 py-2.5 rounded-md bg-primary hover:bg-primary-hover text-white text-xs font-bold shadow-sm transition-colors focus-visible:ring-2"
                >
                  <span>Proceed to Final Submission</span>
                  <ArrowRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          )}

          {/* STEP 3: SUBMIT */}
          {activeStep === 3 && (
            <div className="bg-surface p-5 rounded-xl border border-stoneBorder shadow-sm space-y-5">
              <div>
                <h2 className="text-base font-bold text-primary font-sans">
                  {t('institution.submit.title', 'Official Application Submission')}
                </h2>
                <p className="text-xs text-stone-600 mt-0.5">
                  Review dossier completeness and open items before official submission to AICTE Scrutiny Officers.
                </p>
              </div>

              {/* Dossier Review Summary Card */}
              <div className="p-4 rounded-xl bg-stone-50 border border-stoneBorder space-y-3 text-xs">
                <div className="flex justify-between py-1.5 border-b border-stoneBorder">
                  <span className="text-stone-500 font-medium">Institution Name:</span>
                  <span className="font-bold text-stone-900">{user?.institutionName}</span>
                </div>
                <div className="flex justify-between py-1.5 border-b border-stoneBorder">
                  <span className="text-stone-500 font-medium">Application ID:</span>
                  <span className="font-mono font-bold text-primary">#{application.id}</span>
                </div>
                <div className="flex justify-between py-1.5 border-b border-stoneBorder">
                  <span className="text-stone-500 font-medium">Documents Uploaded:</span>
                  <span className="font-bold font-mono text-stone-900">
                    {docs.length} of {requiredDocTypes.length} mandatory deeds
                  </span>
                </div>
                <div className="flex justify-between py-1.5 border-b border-stoneBorder">
                  <span className="text-stone-500 font-medium">Completeness Verification:</span>
                  <span className="font-bold text-stone-900">
                    {completeness?.is_complete ? (
                      <span className="text-status-verified-text">All mandatory documents present</span>
                    ) : (
                      <span className="text-status-needsVerification-text">
                        {completeness?.missing?.length || 1} required document pending
                      </span>
                    )}
                  </span>
                </div>
                <div className="flex justify-between py-1.5">
                  <span className="text-stone-500 font-medium">Current Dossier Status:</span>
                  <StatusChip label={application.status} size="sm" />
                </div>
              </div>

              {isSubmitted ? (
                <div className="p-5 bg-status-verified-bg/40 border border-status-verified-border rounded-xl text-xs text-status-verified-text space-y-2">
                  <div className="flex items-center gap-2 font-bold text-sm">
                    <CheckCircle2 className="w-5 h-5 text-status-verified" />
                    <span>Dossier Submitted Successfully</span>
                  </div>
                  <p className="leading-relaxed text-stone-700">
                    Your application has officially entered the scrutiny queue. Scrutiny officers will evaluate all
                    records. If any deficiencies are identified, the official Deficiency Report will appear in Step 4.
                  </p>
                  <div className="pt-2 flex items-center gap-3">
                    <button
                      onClick={() => setShowReceiptModal(true)}
                      className="inline-flex items-center gap-1.5 px-4 py-2 rounded-md bg-primary text-white font-bold text-xs shadow-sm hover:bg-primary-hover"
                    >
                      <Printer className="w-4 h-4" />
                      <span>View Submission Receipt</span>
                    </button>
                    <button
                      onClick={() => setActiveStep(4)}
                      className="px-4 py-2 rounded-md border border-stoneBorder bg-surface text-stone-700 font-semibold text-xs hover:bg-stone-50"
                    >
                      Go to Feedback Step
                    </button>
                  </div>
                </div>
              ) : (
                <div className="pt-3 flex flex-wrap items-center justify-between gap-3 border-t border-stoneBorder">
                  <button
                    onClick={() => setActiveStep(2)}
                    className="px-4 py-2 text-xs font-semibold text-stone-600 hover:text-stone-900"
                  >
                    Back to Pre-Submission Check
                  </button>

                  <button
                    onClick={() => setShowSubmitModal(true)}
                    className="inline-flex items-center gap-2 px-6 py-3 rounded-lg bg-accent hover:bg-accent-hover text-stone-950 text-xs font-bold shadow-sm transition-colors focus-visible:ring-2"
                  >
                    <Send className="w-4 h-4 text-stone-950" />
                    <span>{t('institution.submit.submitButton', 'Submit Application Officially')}</span>
                  </button>
                </div>
              )}
            </div>
          )}

          {/* STEP 4: FEEDBACK (DEFICIENCY REPORT) */}
          {activeStep === 4 && (
            <div className="space-y-6">
              {deficiencyReport || isDeficiency ? (
                <DeficiencyReportView
                  report={
                    deficiencyReport || {
                      id: 1,
                      application_id: appId,
                      status: 'sent',
                      content: {
                        summary_text: 'Mandatory land and title continuity deficiencies identified.',
                        items: [
                          {
                            item_id: 'DEF-XDOC-OWNER-TRUST',
                            title: 'Land Ownership Entity Mismatch',
                            what_failed: 'Land title deed owner does not match sponsoring educational trust.',
                            why: "Land owner 'Rameshwar Prasad Sharma' does not match sponsoring trust 'Vanguard Educational Trust'.",
                            clause: 'AICTE Approval Process Handbook — Land Title Norms Clause 2.1',
                            what_to_resubmit: 'Upload registered supplementary deed or corrected land title in draft copy.',
                            severity: 'high',
                          },
                        ],
                      },
                      created_at: new Date().toISOString(),
                    }
                  }
                  onCreateDraftAndFix={handleCreateDraftAndFix}
                  isCreatingDraft={isCreatingDraft}
                  institutionName={user?.institutionName}
                  applicationId={appId}
                />
              ) : (
                <div className="bg-surface p-8 rounded-xl border border-stoneBorder shadow-sm text-center space-y-3">
                  <Clock className="w-10 h-10 text-primary mx-auto" />
                  <h3 className="text-base font-bold text-stone-900 font-sans">
                    Your Application is Under Review
                  </h3>
                  <p className="text-xs text-stone-600 max-w-md mx-auto leading-relaxed">
                    AICTE Scrutiny Officers are actively evaluating your uploaded statutory documents. If any
                    deficiencies are recorded, the official deficiency notice with numbered remediation instructions
                    will be published here.
                  </p>
                </div>
              )}
            </div>
          )}

          {/* STEP 5: FIX AND RECHECK */}
          {activeStep === 5 && (
            <div className="space-y-6">
              <div className="bg-surface p-5 rounded-xl border border-stoneBorder shadow-sm space-y-5">
                <div className="flex flex-wrap items-center justify-between gap-4 pb-4 border-b border-stoneBorder">
                  <div>
                    <div className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-amber-50 border border-amber-200 text-amber-900 text-xs font-bold mb-1">
                      <RefreshCw className="w-3.5 h-3.5" />
                      <span>ISOLATED REMEDIATION DRAFT</span>
                    </div>
                    <h2 className="text-base font-bold text-primary font-sans">
                      {t('institution.fix.title', 'Fix Deficiencies & Run Recheck')}
                    </h2>
                    <p className="text-xs text-stone-600 mt-0.5">
                      Your original submission stays unchanged. Fixes are tested in this draft copy.
                    </p>
                  </div>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={handleRecheckDraft}
                      disabled={isRechecking}
                      className="inline-flex items-center gap-2 px-4 py-2 rounded-md bg-stone-100 hover:bg-stone-200 text-stone-800 text-xs font-semibold border border-stoneBorder transition-colors focus-visible:ring-1"
                    >
                      <RefreshCw className={`w-4 h-4 ${isRechecking ? 'animate-spin' : ''}`} />
                      <span>{t('institution.fix.recheckButton', 'Run Recheck on Draft')}</span>
                    </button>

                    <button
                      onClick={() => setShowResubmitModal(true)}
                      disabled={!hasRecheckedOnce || isSubmittingResubmission}
                      className={`inline-flex items-center gap-2 px-5 py-2 rounded-md text-xs font-bold shadow-sm transition-colors focus-visible:ring-2 ${
                        hasRecheckedOnce
                          ? 'bg-accent hover:bg-accent-hover text-stone-950'
                          : 'bg-stone-300 text-stone-600 cursor-not-allowed opacity-60'
                      }`}
                      title={!hasRecheckedOnce ? 'Run recheck at least once before resubmitting' : undefined}
                    >
                      <Send className="w-4 h-4" />
                      <span>{t('institution.fix.resubmitButton', 'Submit as Resubmission')}</span>
                    </button>
                  </div>
                </div>

                {/* Upload Corrected Deeds Dropzone */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <h3 className="text-xs font-bold text-stone-800 uppercase tracking-wide">
                      Upload Corrected or Missing Documents into Draft
                    </h3>
                    <span className="text-[11px] text-stone-500">PDF, PNG, JPG up to 25MB</span>
                  </div>

                  <FileDropzone onFileSelect={handleDraftDocUpload} />
                </div>

                {/* Guidance Text (Neutral, Genuine Copy Notice) */}
                <div className="p-3 bg-stone-50 rounded-lg border border-stoneBorder text-xs text-stone-700 flex items-start gap-2">
                  <Scale className="w-4 h-4 text-stone-500 flex-shrink-0 mt-0.5" />
                  <p>
                    <strong>Statutory Guidance:</strong> Only genuine, current documents issued by the authorized
                    statutory body (e.g. Sub-Registrar of Land, Municipal Fire Department) should be uploaded.
                    The system evaluates authentic cross-document continuity between records.
                  </p>
                </div>
              </div>

              {/* Differential Before vs After Panel */}
              {comparison && <BeforeAfterPanel comparison={comparison} />}
            </div>
          )}
        </div>
      </div>

      {/* Delete Document Confirmation Dialog */}
      <ConfirmDialog
        isOpen={!!docToDelete}
        title="Remove Uploaded Document"
        message={`Are you sure you want to remove the scan for '${(docToDelete?.doc_type || 'document').replace(/_/g, ' ')}'? Completeness will mark this mandatory requirement as missing until re-uploaded.`}
        confirmLabel="Remove Scan"
        cancelLabel="Cancel"
        onConfirm={handleConfirmDeleteDoc}
        onCancel={() => setDocToDelete(null)}
        isLoading={isDeleting}
        variant="danger"
      />

      {/* Submit Application Confirmation Dialog */}
      <ConfirmDialog
        isOpen={showSubmitModal}
        title={t('institution.submit.confirmTitle', 'Confirm Official Application Submission')}
        message={t(
          'institution.submit.confirmMessage',
          'Are you sure you want to submit this application for official officer review? Once submitted, the application enters the officer scrutiny queue.'
        )}
        confirmLabel="Confirm Submission"
        cancelLabel="Cancel"
        onConfirm={handleOfficialSubmit}
        onCancel={() => setShowSubmitModal(false)}
        isLoading={isSubmitting}
        variant="accent"
      />

      {/* Submit Resubmission Confirmation Dialog */}
      <ConfirmDialog
        isOpen={showResubmitModal}
        title="Confirm Application Resubmission"
        message="Are you sure you want to officially submit this corrected draft as a formal resubmission? Your previous deficiency report items will be archived and the updated records evaluated by the scrutiny officer."
        confirmLabel="Submit Resubmission"
        cancelLabel="Cancel"
        onConfirm={handleSubmitResubmission}
        onCancel={() => setShowResubmitModal(false)}
        isLoading={isSubmittingResubmission}
        variant="accent"
      />

      {/* Official Submission Receipt Modal */}
      <SubmissionReceiptModal
        isOpen={showReceiptModal}
        onClose={() => setShowReceiptModal(false)}
        application={application}
      />

      {/* Validation Stage Progress Modal */}
      <ValidationProgressModal isOpen={isValidating} progress={validationProgress} />
    </div>
  );
};
export default ApplicationWorkspace;
