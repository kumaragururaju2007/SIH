export type UserRole = 'institution' | 'officer';

export interface DemoUser {
  role: UserRole;
  institutionId?: number;
  institutionName?: string;
  officerName?: string;
}

export type ResultLabel = 'verified' | 'needs_verification' | 'inconsistent' | 'possible_tampering';
export type RiskBand = 'low' | 'medium' | 'high';

export interface InstitutionHistory {
  id: number;
  institution_id: number;
  year: number;
  outcome: string;
  flags_count: number;
  deficiency_count: number;
  created_at: string;
}

export interface Institution {
  id: number;
  name: string;
  state: string;
  trust_name: string;
  created_at: string;
  history?: InstitutionHistory[];
}

export interface ExtractedField {
  id?: number;
  document_id?: number;
  name?: string;
  field_name?: string;
  value_original?: string;
  raw_value?: string;
  value_normalized?: string;
  normalized_value?: string;
  confidence: number;
  needs_verification: boolean;
  page_number?: number;
}

export interface DocumentReason {
  check_type?: string;
  rule_id?: string;
  message: string;
  severity?: string;
  doc_type?: string;
}

export interface RuleResultItem {
  id: number;
  rule_id: string;
  document_id?: number | null;
  description?: string;
  status: 'passed' | 'failed' | 'not_evaluable';
  passed: boolean;
  severity: 'low' | 'medium' | 'high';
  message: string;
  clause?: string;
  version?: string;
  evidence?: Record<string, any>;
}

export interface AuthCheckItem {
  id?: number;
  document_id?: number;
  check_type: 'duplicate' | 'metadata' | 'tampering' | 'qr' | 'registry';
  result: string;
  probability?: number | null;
  evidence?: Record<string, any>;
  message?: string;
}

export interface DocumentItem {
  id: number;
  application_id: number;
  doc_type?: string;
  file_path: string;
  sha256?: string;
  phash?: string;
  language?: string;
  ocr_language?: string;
  ocr_confidence?: number;
  mean_ocr_confidence?: number;
  ocr_text?: string;
  qr_text?: string;
  label?: ResultLabel;
  system_label?: ResultLabel;
  override_label?: ResultLabel;
  override_reason?: string;
  override_by?: string;
  reasons?: DocumentReason[];
  extracted_fields?: ExtractedField[];
  rule_results?: RuleResultItem[];
  authentication?: AuthCheckItem[];
  created_at?: string;
}

export interface RiskFactor {
  factor: string;
  points: number;
  description: string;
}

export interface ApplicationItem {
  id: number;
  institution_id: number;
  institution_name?: string;
  institution_state?: string;
  application_type: string;
  status: string;
  parent_application_id?: number | null;
  submission_date?: string | null;
  risk_score?: number | null;
  risk_band?: RiskBand | null;
  risk_factors?: {
    score: number;
    band: RiskBand;
    top_factors: RiskFactor[];
    disclaimer: string;
  } | null;
  label?: ResultLabel | null;
  reasons?: any;
  created_at: string;
  documents?: DocumentItem[];
}

export interface QueueItem {
  application_id: number;
  rank?: number;
  institution_id: number;
  institution_name: string;
  institution_state: string;
  application_type: string;
  status: string;
  submission_date?: string | null;
  label?: ResultLabel | null;
  risk_score?: number | null;
  risk_band?: RiskBand | null;
  top_factors?: RiskFactor[];
  issue_counts?: {
    total: number;
    rule_failures: number;
    consistency_conflicts: number;
    possible_tampering: number;
    needs_verification: number;
  };
  is_resubmission: boolean;
  parent_application_id?: number | null;
  created_at?: string;
}

export interface CompletenessData {
  application_id: number;
  application_type: string;
  is_complete: boolean;
  required: string[];
  present: string[];
  missing: string[];
  unrecognized: string[];
  duplicates_of_type: string[];
  missing_findings?: Array<{
    rule_id: string;
    description: string;
    missing_doc_type: string;
    severity: string;
    clause: string;
  }>;
}

export interface ConsistencySide {
  doc_type?: string;
  field?: string;
  document_id?: number | null;
  original?: string;
  normalized?: string;
}

export interface ConsistencyComparison {
  rule_id: string;
  description?: string;
  kind?: string;
  relation?: string;
  status: 'match' | 'partial' | 'conflict' | 'not_evaluable';
  severity: 'low' | 'medium' | 'high';
  score: number;
  message: string;
  clause?: string;
  version?: string;
  left: ConsistencySide;
  right: ConsistencySide;
  explanation?: string;
  evidence?: Record<string, any>;
}

export interface DocumentForensics {
  document_id: number;
  doc_type?: string;
  annotated_image_path?: string;
  heatmap_image_path?: string;
  tampering_score?: number | null;
  status: string;
  regions?: Array<Record<string, any>>;
  evidence?: Record<string, any>;
}

export interface AuditLogItem {
  id: number;
  timestamp: string;
  actor: string;
  action: string;
  entity: string;
  details?: Record<string, any>;
}

export interface DeficiencyReportItem {
  id?: string;
  item_id?: string;
  title?: string;
  what_failed?: string;
  why?: string;
  what_to_resubmit?: string;
  clause: string;
  severity: 'low' | 'medium' | 'high';
  description?: string;
  actual_values?: Record<string, any>;
  action_required?: string;
  system_provided?: boolean;
}

export interface DeficiencyReportData {
  id?: number;
  application_id: number;
  status: 'draft' | 'approved' | 'sent';
  content: {
    items: DeficiencyReportItem[];
    summary_text?: string;
    statutory_notice?: string;
  };
  approved_by?: string | null;
  created_at?: string;
}

export interface ComparisonItem {
  id: string;
  category: string;
  title: string;
  status: 'resolved' | 'remaining' | 'new';
  before_message?: string;
  after_message?: string;
  clause?: string;
  doc_type?: string;
  severity: string;
}

export interface LabelChange {
  doc_type: string;
  document_id?: number;
  before_label: ResultLabel;
  after_label: ResultLabel;
}

export interface DraftComparisonResponse {
  parent_application_id: number;
  draft_application_id: number;
  summary_sentence: string;
  counts: {
    resolved: number;
    remaining: number;
    new: number;
    total_before: number;
    total_remaining: number;
  };
  resolved_issues: ComparisonItem[];
  remaining_issues: ComparisonItem[];
  new_issues: ComparisonItem[];
  label_changes: LabelChange[];
  risk_changes?: {
    before_score?: number;
    after_score?: number;
    before_band?: RiskBand;
    after_band?: RiskBand;
    score_delta?: number;
  };
}

export interface OfficerApplicationDetailResponse {
  application: ApplicationItem;
  institution: Institution;
  history_timeline: InstitutionHistory[];
  documents: DocumentItem[];
  completeness: CompletenessData;
  rule_results: RuleResultItem[];
  consistency: ConsistencyComparison[];
  consistency_summary: {
    match: number;
    partial: number;
    conflict: number;
    not_evaluable: number;
    total: number;
  };
  authentication: {
    application_id: number;
    summary: Record<string, number>;
    total_checks: number;
  };
  forensics: DocumentForensics[];
  risk_breakdown: {
    score?: number;
    band?: RiskBand;
    top_factors?: RiskFactor[];
    disclaimer?: string;
    rule_failure_points?: number;
    consistency_points?: number;
    tampering_points?: number;
    history_points?: number;
  };
  deficiency_report?: DeficiencyReportData | null;
  audit_logs: AuditLogItem[];
}
