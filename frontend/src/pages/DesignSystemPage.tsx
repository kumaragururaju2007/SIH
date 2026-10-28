import React, { useState } from 'react';
import { StatusChip } from '../components/common/StatusChip';
import { RiskMeter } from '../components/common/RiskMeter';
import { FieldValue } from '../components/common/FieldValue';
import { SideBySideCompare } from '../components/common/SideBySideCompare';
import { EvidenceExpander } from '../components/common/EvidenceExpander';
import { DocumentViewer } from '../components/common/DocumentViewer';
import { IssueCard } from '../components/common/IssueCard';
import { BeforeAfterPanel } from '../components/common/BeforeAfterPanel';
import { Timeline } from '../components/common/Timeline';
import { DataTable, Column } from '../components/common/DataTable';
import { Stepper } from '../components/common/Stepper';
import { FileDropzone } from '../components/common/FileDropzone';
import { ConfirmDialog } from '../components/common/ConfirmDialog';
import { EmptyState } from '../components/common/EmptyState';
import { ErrorState } from '../components/common/ErrorState';
import { Breadcrumbs } from '../components/common/Breadcrumbs';
import { ConsistencyComparison, DraftComparisonResponse } from '../types';

export const DesignSystemPage: React.FC = () => {
  const [dialogVariant, setDialogVariant] = useState<'primary' | 'accent' | 'danger' | null>(null);

  // Mock data for Design Showcase
  const sampleComparison: ConsistencyComparison = {
    rule_id: 'XDOC-OWNER-TRUST',
    description: 'Land owner name must match sponsoring trust entity',
    status: 'conflict',
    severity: 'high',
    score: 64.2,
    message: "Land owner 'Ramesh Chand' does not match sponsoring trust 'Apex Educational Society' or its trustees.",
    clause: 'Approval Process Handbook Regulation 2.1 (Title Continuity)',
    left: {
      doc_type: 'land_document',
      field: 'owner_name',
      original: 'Ramesh Chand',
      normalized: 'ramesh chand',
    },
    right: {
      doc_type: 'trust_registration',
      field: 'trust_name',
      original: 'Apex Educational Society',
      normalized: 'apex education society',
    },
    evidence: {
      steps: ['Devanagari Transliteration', 'Legal Suffix Removal', 'Phonetic Collapse'],
      diff_tokens: ['ramesh', 'chand', 'apex'],
    },
  };

  const sampleDraftComparison: DraftComparisonResponse = {
    parent_application_id: 101,
    draft_application_id: 102,
    summary_sentence: '3 failures before, 1 remaining',
    counts: {
      resolved: 2,
      remaining: 1,
      new: 0,
      total_before: 3,
      total_remaining: 1,
    },
    resolved_issues: [
      {
        id: 'RULE-LAND-01',
        category: 'rule_failure',
        title: 'Land Area Below Norm',
        status: 'resolved',
        before_message: 'Area 6,500 sq.m was below 10,000 sq.m norm.',
        after_message: 'Supplementary deed uploaded (12,000 sq.m total).',
        clause: 'Handbook Norm 2.1',
        severity: 'high',
      },
      {
        id: 'RULE-FIRE-01',
        category: 'rule_failure',
        title: 'Expired Fire Clearance',
        status: 'resolved',
        before_message: 'Fire NOC expired 2026-01-15.',
        after_message: 'Renewed Municipal Fire Certificate verified.',
        clause: 'Handbook Norm 1.4',
        severity: 'medium',
      },
    ],
    remaining_issues: [
      {
        id: 'XDOC-TRUST-01',
        category: 'consistency',
        title: 'Owner Trust Mismatch',
        status: 'remaining',
        before_message: "Land owner 'Ramesh Chand' differs from registered trust.",
        after_message: 'Title conveyance deed pending registration.',
        clause: 'Handbook Norm 2.3',
        severity: 'high',
      },
    ],
    new_issues: [],
    label_changes: [
      { doc_type: 'land_document', before_label: 'inconsistent', after_label: 'verified' },
      { doc_type: 'fire_safety_certificate', before_label: 'needs_verification', after_label: 'verified' },
    ],
    risk_changes: {
      before_score: 72,
      after_score: 24,
      score_delta: -48,
    },
  };

  const sampleTableData = [
    { id: 1, name: 'Apex Institute of Technology', state: 'Maharashtra', status: 'verified', score: 18 },
    { id: 2, name: 'Horizon College of Engineering', state: 'Karnataka', status: 'inconsistent', score: 68 },
    { id: 3, name: 'National Polytechnic College', state: 'Tamil Nadu', status: 'needs_verification', score: 38 },
  ];

  const sampleTableCols: Column<any>[] = [
    { key: 'id', header: 'ID', sortable: true, className: 'w-16 font-mono text-stone-500' },
    { key: 'name', header: 'Institution Name', sortable: true, className: 'font-bold' },
    { key: 'state', header: 'State', sortable: true },
    {
      key: 'status',
      header: 'Status Label',
      render: (item) => <StatusChip label={item.status} size="sm" />,
    },
    {
      key: 'score',
      header: 'Risk Score',
      render: (item) => <RiskMeter score={item.score} size="sm" />,
    },
  ];

  return (
    <div className="max-w-content mx-auto p-4 sm:p-8 space-y-12">
      <Breadcrumbs items={[{ label: 'Design System Documentation' }]} />

      {/* Header */}
      <div className="border-b border-stoneBorder pb-6">
        <h1 className="text-3xl font-extrabold text-primary font-sans">
          DocValidate Design System & Component Library
        </h1>
        <p className="text-sm text-stone-600 mt-2 max-w-3xl leading-relaxed">
          Calm, trustworthy government-tech aesthetic. Light theme only, warm off-white surface (<code className="font-mono bg-stone-100 px-1 py-0.5 rounded text-xs">#F7F6F2</code>),
          deep ink blue primary (<code className="font-mono bg-stone-100 px-1 py-0.5 rounded text-xs">#1E3A5F</code>), muted saffron accent (<code className="font-mono bg-stone-100 px-1 py-0.5 rounded text-xs">#C77700</code>),
          and WCAG AA compliant status tokens with pairing icons.
        </p>
      </div>

      {/* 1. STATUS CHIPS */}
      <section className="space-y-4">
        <h2 className="text-lg font-bold text-stone-900 border-b border-stoneBorder pb-2">
          1. StatusChip (States & Sizes)
        </h2>
        <div className="p-5 bg-surface rounded-xl border border-stoneBorder shadow-sm space-y-4">
          <p className="text-xs text-stone-500">
            Colors are always paired with an icon and text label (never color alone). Light tint backgrounds with dark text exceed WCAG AA contrast.
          </p>
          <div className="flex flex-wrap items-center gap-4">
            <StatusChip label="verified" />
            <StatusChip label="needs_verification" />
            <StatusChip label="inconsistent" />
            <StatusChip label="possible_tampering" />
            <StatusChip label="approved" />
            <StatusChip label="rejected" />
          </div>

          <div className="flex flex-wrap items-center gap-3 pt-2">
            <span className="text-xs font-semibold text-stone-500 mr-2">Small Size (sm):</span>
            <StatusChip label="verified" size="sm" />
            <StatusChip label="needs_verification" size="sm" />
            <StatusChip label="inconsistent" size="sm" />
            <StatusChip label="possible_tampering" size="sm" />
          </div>
        </div>
      </section>

      {/* 2. RISK METER */}
      <section className="space-y-4">
        <h2 className="text-lg font-bold text-stone-900 border-b border-stoneBorder pb-2">
          2. RiskMeter (Horizontal bands with number and word)
        </h2>
        <div className="p-5 bg-surface rounded-xl border border-stoneBorder shadow-sm grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="space-y-2">
            <span className="text-xs font-bold text-stone-700">Low Risk Band (0 - 30)</span>
            <RiskMeter score={18} band="low" />
            <RiskMeter score={18} band="low" size="sm" />
          </div>

          <div className="space-y-2">
            <span className="text-xs font-bold text-stone-700">Medium Risk Band (31 - 60)</span>
            <RiskMeter score={45} band="medium" />
            <RiskMeter score={45} band="medium" size="sm" />
          </div>

          <div className="space-y-2">
            <span className="text-xs font-bold text-stone-700">High Risk Band (61 - 100)</span>
            <RiskMeter score={84} band="high" />
            <RiskMeter score={84} band="high" size="sm" />
          </div>
        </div>
      </section>

      {/* 3. FIELD VALUES & TYPOGRAPHY */}
      <section className="space-y-4">
        <h2 className="text-lg font-bold text-stone-900 border-b border-stoneBorder pb-2">
          3. FieldValue (OCR Confidence, Hindi Shaping & Verification Markers)
        </h2>
        <div className="p-5 bg-surface rounded-xl border border-stoneBorder shadow-sm grid grid-cols-1 md:grid-cols-3 gap-4">
          <FieldValue
            label="owner_name"
            originalValue="Apex Technical Education Trust"
            normalizedValue="apex technical education trust"
            confidence={0.96}
          />
          <FieldValue
            label="area_sqm"
            originalValue="12000 SQM"
            normalizedValue="12000"
            confidence={0.62}
            needsVerification={true}
          />
          <FieldValue
            label="hindi_deed_title"
            originalValue="श्री साईं शिक्षा समिति"
            normalizedValue="sri sai shiksha samiti"
            confidence={0.89}
            isHindi={true}
          />
        </div>
      </section>

      {/* 4. SIDE BY SIDE COMPARE */}
      <section className="space-y-4">
        <h2 className="text-lg font-bold text-stone-900 border-b border-stoneBorder pb-2">
          4. SideBySideCompare (Token Differences Highlighted with Underline + Bold)
        </h2>
        <div className="space-y-2">
          <p className="text-xs text-stone-500">
            Tokens that differ between columns are highlighted using underline + bold font formatting (accessible without color alone).
          </p>
          <SideBySideCompare comparison={sampleComparison} />
        </div>
      </section>

      {/* 5. EVIDENCE EXPANDER */}
      <section className="space-y-4">
        <h2 className="text-lg font-bold text-stone-900 border-b border-stoneBorder pb-2">
          5. EvidenceExpander ("How this was decided")
        </h2>
        <EvidenceExpander
          ruleId="LAND-AREA-MIN"
          clause="AICTE Approval Process Handbook Clause 2.1 (Urban Norm: 10,000 sq.m)"
          valuesUsed={{ area_sqm: 12500, min_required: 10000, margin: '+2500 sq.m' }}
          version="1.0.0"
          rawPayload={{ rule_id: 'LAND-AREA-MIN', evaluated: true, status: 'passed' }}
          defaultOpen={true}
        />
      </section>

      {/* 6. BEFORE AND AFTER PANEL */}
      <section className="space-y-4">
        <h2 className="text-lg font-bold text-stone-900 border-b border-stoneBorder pb-2">
          6. BeforeAfterPanel (Resubmission Differential)
        </h2>
        <BeforeAfterPanel comparison={sampleDraftComparison} />
      </section>

      {/* 7. ISSUE CARDS */}
      <section className="space-y-4">
        <h2 className="text-lg font-bold text-stone-900 border-b border-stoneBorder pb-2">
          7. IssueCard (Plain Language Compliance Findings)
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <IssueCard
            id="FIRE-EXPIRY"
            title="Fire Safety Clearance Expired"
            message="Certificate valid until 2026-02-01. Inspection rules require statutory clearance valid throughout the approval academic year."
            severity="high"
            docType="fire_safety_certificate"
            actionRequired="Upload renewed Fire NOC issued by municipal fire department."
            clause="Approval Process Handbook Clause 1.4"
          />
          <IssueCard
            id="LAND-DEED-BOUNDARIES"
            title="Cadastral Survey Number Discrepancy"
            message="Survey number 142/B listed in deed; tax assessment receipt cites 142/B-1."
            severity="medium"
            docType="land_document"
            actionRequired="Provide municipal revenue mutation register extract."
            clause="Handbook Regulation 2.4"
          />
        </div>
      </section>

      {/* 8. DATA TABLE */}
      <section className="space-y-4">
        <h2 className="text-lg font-bold text-stone-900 border-b border-stoneBorder pb-2">
          8. DataTable (Sortable, 44px Row Height, Keyboard Accessible)
        </h2>
        <DataTable
          data={sampleTableData}
          columns={sampleTableCols}
          keyExtractor={(item) => item.id}
          onRowClick={(item) => alert(`Selected row: ${item.name}`)}
        />
      </section>

      {/* 9. STEPPER & DROPZONE */}
      <section className="space-y-4">
        <h2 className="text-lg font-bold text-stone-900 border-b border-stoneBorder pb-2">
          9. Stepper & FileDropzone
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-start">
          <div className="p-4 bg-surface rounded-xl border border-stoneBorder shadow-sm">
            <span className="text-xs font-bold text-stone-700 block mb-3 uppercase tracking-wide">
              Institution 5-Step Process
            </span>
            <Stepper
              steps={[
                { id: 1, label: '1. Documents', description: 'Upload mandatory deeds' },
                { id: 2, label: '2. Pre-Check', description: 'Safe self-scrutiny' },
                { id: 3, label: '3. Submit', description: 'Official dossier submission' },
                { id: 4, label: '4. Deficiency Report', description: 'Officer findings' },
                { id: 5, label: '5. Fix & Recheck', description: 'Draft resubmission' },
              ]}
              activeStep={2}
            />
          </div>

          <div className="p-4 bg-surface rounded-xl border border-stoneBorder shadow-sm space-y-3">
            <span className="text-xs font-bold text-stone-700 block uppercase tracking-wide">
              Drag-and-Drop Ingestion Dropzone
            </span>
            <FileDropzone
              onFileSelect={(file) => alert(`File selected: ${file.name}`)}
              detectedType="land_document"
              detectedLang="en"
              confidence={0.92}
            />
          </div>
        </div>
      </section>

      {/* 10. CONFIRM DIALOG TRIGGER BUTTONS */}
      <section className="space-y-4">
        <h2 className="text-lg font-bold text-stone-900 border-b border-stoneBorder pb-2">
          10. ConfirmDialog (Variants with Focus Trap & Escape Handling)
        </h2>
        <div className="flex flex-wrap items-center gap-3">
          <button
            onClick={() => setDialogVariant('primary')}
            className="px-4 py-2 rounded-md bg-primary text-white text-xs font-bold"
          >
            Open Primary Dialog (Approval)
          </button>
          <button
            onClick={() => setDialogVariant('accent')}
            className="px-4 py-2 rounded-md bg-accent text-white text-xs font-bold"
          >
            Open Accent Dialog (Override)
          </button>
          <button
            onClick={() => setDialogVariant('danger')}
            className="px-4 py-2 rounded-md bg-status-inconsistent text-white text-xs font-bold"
          >
            Open Danger Dialog (Rejection)
          </button>
        </div>

        <ConfirmDialog
          isOpen={dialogVariant !== null}
          title={
            dialogVariant === 'danger'
              ? 'Reject Approval Application'
              : dialogVariant === 'accent'
              ? 'Override Document Result'
              : 'Approve Official Application'
          }
          message="This is a demonstration of the accessible modal dialog with focus trap, tab navigation loop, and Escape key listener."
          variant={dialogVariant || 'primary'}
          confirmLabel="Confirm Action"
          onConfirm={() => setDialogVariant(null)}
          onCancel={() => setDialogVariant(null)}
        />
      </section>

      {/* 11. EMPTY AND ERROR STATES */}
      <section className="space-y-4">
        <h2 className="text-lg font-bold text-stone-900 border-b border-stoneBorder pb-2">
          11. EmptyState & ErrorState
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <EmptyState
            title="No Documents Uploaded"
            description="Please upload required fire safety, land title, and trust registration deeds."
            action={
              <button className="px-3 py-1.5 rounded bg-primary text-white text-xs font-semibold">
                Upload Deed
              </button>
            }
          />
          <ErrorState
            title="Validation Service Timeout"
            message="Could not reach http://localhost:8000. Verify the FastAPI backend is running."
            onRetry={() => alert('Retrying...')}
          />
        </div>
      </section>
    </div>
  );
};
