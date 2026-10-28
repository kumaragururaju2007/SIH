from datetime import datetime
from typing import Optional, Any, List
from pydantic import BaseModel, ConfigDict, Field


# ---------------- Institution Schemas ----------------
class InstitutionBase(BaseModel):
    name: str
    state: str
    trust_name: str


class InstitutionCreate(InstitutionBase):
    pass


class InstitutionHistoryResponse(BaseModel):
    id: int
    institution_id: int
    year: int
    outcome: str
    flags_count: int
    deficiency_count: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InstitutionResponse(InstitutionBase):
    id: int
    created_at: datetime
    history: List[InstitutionHistoryResponse] = []

    model_config = ConfigDict(from_attributes=True)


# ---------------- Application Schemas ----------------
class ApplicationCreate(BaseModel):
    institution_id: int
    application_type: str = Field(default="new_institute")
    parent_application_id: Optional[int] = None


class ApplicationResponse(BaseModel):
    id: int
    institution_id: int
    application_type: str
    submission_date: Optional[Any] = None
    status: str
    parent_application_id: Optional[int] = None
    risk_score: Optional[float] = None
    risk_band: Optional[str] = None
    risk_factors: Optional[Any] = None
    label: Optional[str] = None
    reasons: Optional[Any] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------- Document Schemas ----------------
class DocumentResponse(BaseModel):
    id: int
    application_id: int
    doc_type: Optional[str] = None
    file_path: str
    sha256: str
    phash: Optional[str] = None
    language: Optional[str] = None
    ocr_text: Optional[str] = None
    ocr_confidence: Optional[float] = None
    qr_text: Optional[str] = None
    label: Optional[str] = None
    system_label: Optional[str] = None
    override_label: Optional[str] = None
    override_reason: Optional[str] = None
    override_by: Optional[str] = None
    reasons: Optional[Any] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ---------------- ExtractedField Schemas ----------------
class ExtractedFieldResponse(BaseModel):
    id: int
    document_id: int
    name: str
    value_original: Optional[str] = None
    value_normalized: Optional[str] = None
    confidence: float
    needs_verification: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentDetailResponse(DocumentResponse):
    extracted_fields: List[ExtractedFieldResponse] = []


# ---------------- AuditLog Schemas ----------------
class AuditLogResponse(BaseModel):
    id: int
    timestamp: datetime
    actor: str
    action: str
    entity: str
    details: Optional[Any] = None

    model_config = ConfigDict(from_attributes=True)


# ---------------- Health Schema ----------------
class HealthResponse(BaseModel):
    status: str


# ---------------- Synthetic Manifest Schemas ----------------
class DocumentManifest(BaseModel):
    doc_type: str
    file_path_png: str
    file_path_pdf: str
    fields: dict[str, Any]
    language: str = "en"
    has_qr: bool = True
    tampered: bool = False
    tampered_bbox: Optional[List[int]] = None
    sha256: str
    metadata: Optional[dict[str, Any]] = None


class ApplicationManifest(BaseModel):
    app_id: str
    institution_name: str
    institution_id: Optional[int] = None
    application_type: str = "new_institution"
    submission_date: str
    min_area_sqm: float
    scenario: str
    expected_labels: dict[str, str]
    expected_issues: List[str] = []
    documents: List[DocumentManifest]


class SyntheticManifest(BaseModel):
    generated_at: str
    seed: int
    min_area_sqm_norm: float
    applications: List[ApplicationManifest]


# ---------------- Rule, Completeness & Validation Schemas ----------------
class RuleOutcome(BaseModel):
    rule_id: str
    document_id: Optional[int] = None
    document_type: Optional[str] = None
    status: str  # passed | failed | not_evaluable
    passed: bool
    severity: str  # low | medium | high
    message: str
    clause: Optional[str] = None
    evidence: Optional[dict[str, Any]] = None


class RuleResultResponse(BaseModel):
    id: int
    application_id: int
    document_id: Optional[int] = None
    rule_id: str
    status: str
    passed: bool
    severity: str
    message: str
    clause: Optional[str] = None
    evidence: Optional[Any] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CompletenessResponse(BaseModel):
    application_id: int
    application_type: str
    is_complete: bool
    required: List[str]
    present: List[str]
    missing: List[str]
    unrecognized: List[int] = []
    duplicates_of_type: List[str] = []
    missing_findings: List[RuleOutcome] = []


class ValidationResponse(BaseModel):
    application_id: int
    status: str
    is_valid: bool
    completeness: CompletenessResponse
    summary: dict[str, int]
    findings: List[RuleOutcome]
    consistency: List["ConsistencyComparison"] = []
    consistency_summary: dict[str, int] = {}
    authentication: Optional[dict[str, Any]] = None
    label: Optional[str] = None
    risk_score: Optional[float] = None
    risk_band: Optional[str] = None
    risk_breakdown: Optional[dict[str, Any]] = None


class AuthResultResponse(BaseModel):
    id: int
    document_id: int
    check_type: str
    result: str
    probability: Optional[float] = None
    evidence: Optional[Any] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentAuthenticationResponse(BaseModel):
    document_id: int
    doc_type: Optional[str] = None
    checks: List[AuthResultResponse] = []


class AuthenticationSectionResponse(BaseModel):
    application_id: int
    summary: dict[str, int] = {}
    documents: List[DocumentAuthenticationResponse] = []


class DocumentForensicsResponse(BaseModel):
    document_id: int
    doc_type: Optional[str] = None
    annotated_image_path: Optional[str] = None
    heatmap_image_path: Optional[str] = None
    tampering_score: Optional[float] = None
    status: str
    regions: List[dict[str, Any]] = []
    evidence: Optional[dict[str, Any]] = None


class DocumentWithResultsResponse(DocumentDetailResponse):
    rule_results: List[RuleResultResponse] = []
    authentication: List[AuthResultResponse] = []


class ConsistencyComparisonSide(BaseModel):
    doc_type: Optional[str] = None
    field: Optional[str] = None
    document_id: Optional[int] = None
    original: Optional[str] = None
    normalized: Optional[str] = None


class ConsistencyComparison(BaseModel):
    rule_id: str
    description: Optional[str] = None
    kind: str
    relation: str
    status: str  # match | partial | conflict | not_evaluable
    severity: str  # high | medium | low
    score: float
    message: str
    clause: Optional[str] = None
    left: ConsistencyComparisonSide
    right: ConsistencyComparisonSide
    explanation: Optional[str] = None
    evidence: Optional[dict[str, Any]] = None


class ConsistencyResultResponse(BaseModel):
    id: int
    application_id: int
    rule_id: str
    field: str
    doc_a_id: Optional[int] = None
    doc_b_id: Optional[int] = None
    value_a: Optional[str] = None
    value_b: Optional[str] = None
    score: float
    outcome: str
    status: str
    severity: str
    relation: str
    message: str
    clause: Optional[str] = None
    evidence: Optional[Any] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConsistencySectionResponse(BaseModel):
    application_id: int
    summary: dict[str, int]
    comparisons: List[ConsistencyComparison]


class ResultsResponse(BaseModel):
    application_id: int
    application_type: str
    completeness: CompletenessResponse
    documents: List[DocumentWithResultsResponse]
    all_rule_results: List[RuleResultResponse]
    summary: dict[str, int]
    consistency: List[ConsistencyComparison] = []
    consistency_summary: dict[str, int] = {}
    authentication: Optional[dict[str, Any]] = None


class ConfigResponse(BaseModel):
    document_types: List[str]
    application_types: dict[str, Any]
    rules_count: int
    rules_by_type: dict[str, List[dict[str, Any]]]
    consistency_rules_count: int = 0
    consistency_rules: List[dict[str, Any]] = []


# ---------------- Officer & Queue Schemas ----------------
class OfficerQueueItem(BaseModel):
    id: int
    institution_id: int
    institution_name: str
    institution_state: str
    application_type: str
    status: str
    submission_date: Optional[Any] = None
    label: Optional[str] = None
    risk_score: Optional[float] = None
    risk_band: Optional[str] = None
    top_factors: List[dict[str, Any]] = []
    issue_counts: dict[str, int] = {}
    is_resubmission: bool = False
    parent_application_id: Optional[int] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OverrideRequest(BaseModel):
    document_id: int
    new_label: str
    reason: str = Field(..., min_length=10)


class DecisionRequest(BaseModel):
    decision: str  # approve | reject | send_deficiency
    comments: Optional[str] = None


class OfficerApplicationDetail(BaseModel):
    application: ApplicationResponse
    institution: InstitutionResponse
    history_timeline: List[InstitutionHistoryResponse] = []
    documents: List[DocumentWithResultsResponse] = []
    completeness: CompletenessResponse
    rule_results: List[RuleResultResponse] = []
    consistency: List[ConsistencyComparison] = []
    consistency_summary: dict[str, int] = {}
    authentication: Optional[dict[str, Any]] = None
    forensics: List[DocumentForensicsResponse] = []
    risk_breakdown: Optional[dict[str, Any]] = None
    deficiency_report: Optional[dict[str, Any]] = None
    audit_logs: List[AuditLogResponse] = []


# ---------------- Deficiency Report Schemas ----------------
class DeficiencyReportResponse(BaseModel):
    id: int
    application_id: int
    status: str
    approved_by: Optional[str] = None
    content: dict[str, Any]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DeficiencyReportUpdateRequest(BaseModel):
    items: Optional[List[dict[str, Any]]] = None
    summary: Optional[str] = None
    content: Optional[dict[str, Any]] = None


# ---------------- Fix & Recheck Comparison Schemas ----------------
class ComparisonItem(BaseModel):
    id: str
    category: str
    title: str
    status: str  # resolved | remaining | new
    before_message: Optional[str] = None
    after_message: Optional[str] = None
    clause: Optional[str] = None
    doc_type: Optional[str] = None
    severity: str = "medium"


class DraftComparisonResponse(BaseModel):
    draft_id: int
    parent_id: int
    summary_sentence: str
    before_failures_count: int
    remaining_failures_count: int
    resolved_count: int
    new_count: int
    resolved_issues: List[ComparisonItem] = []
    remaining_issues: List[ComparisonItem] = []
    new_issues: List[ComparisonItem] = []
    overall: dict[str, Any]



