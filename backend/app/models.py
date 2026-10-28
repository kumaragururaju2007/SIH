from datetime import datetime, timezone, date
from typing import Optional, Any
from sqlalchemy import (
    Integer,
    String,
    Float,
    Boolean,
    Text,
    DateTime,
    Date,
    ForeignKey,
    JSON,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Institution(Base):
    __tablename__ = "institutions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    state: Mapped[str] = mapped_column(String(100), nullable=False)
    trust_name: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), default=lambda: datetime.now(timezone.utc)
    )

    history: Mapped[list["InstitutionHistory"]] = relationship(
        "InstitutionHistory", back_populates="institution", cascade="all, delete-orphan"
    )
    applications: Mapped[list["Application"]] = relationship(
        "Application", back_populates="institution", cascade="all, delete-orphan"
    )


class InstitutionHistory(Base):
    __tablename__ = "institution_histories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    institution_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    outcome: Mapped[str] = mapped_column(String(50), nullable=False)
    flags_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    deficiency_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), default=lambda: datetime.now(timezone.utc)
    )

    institution: Mapped["Institution"] = relationship("Institution", back_populates="history")


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    institution_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("institutions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    application_type: Mapped[str] = mapped_column(String(100), nullable=False)
    submission_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    # status options: draft, submitted, in_review, deficiency_sent, approved, rejected
    status: Mapped[str] = mapped_column(String(50), default="draft", nullable=False)
    parent_application_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("applications.id", ondelete="SET NULL"), nullable=True
    )
    risk_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    risk_band: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    risk_factors: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    label: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    reasons: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), default=lambda: datetime.now(timezone.utc)
    )

    institution: Mapped["Institution"] = relationship("Institution", back_populates="applications")
    parent_application: Mapped[Optional["Application"]] = relationship(
        "Application", remote_side=[id], backref="child_applications"
    )
    documents: Mapped[list["Document"]] = relationship(
        "Document", back_populates="application", cascade="all, delete-orphan"
    )
    rule_results: Mapped[list["RuleResult"]] = relationship(
        "RuleResult", back_populates="application", cascade="all, delete-orphan"
    )
    consistency_results: Mapped[list["ConsistencyResult"]] = relationship(
        "ConsistencyResult", back_populates="application", cascade="all, delete-orphan"
    )
    deficiency_reports: Mapped[list["DeficiencyReport"]] = relationship(
        "DeficiencyReport", back_populates="application", cascade="all, delete-orphan"
    )
    reviews: Mapped[list["Review"]] = relationship(
        "Review", back_populates="application", cascade="all, delete-orphan"
    )


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    application_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True
    )
    doc_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    phash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    language: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    ocr_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ocr_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    qr_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    label: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    system_label: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    override_label: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    override_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    override_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    reasons: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), default=lambda: datetime.now(timezone.utc)
    )

    application: Mapped["Application"] = relationship("Application", back_populates="documents")
    extracted_fields: Mapped[list["ExtractedField"]] = relationship(
        "ExtractedField", back_populates="document", cascade="all, delete-orphan"
    )
    auth_results: Mapped[list["AuthResult"]] = relationship(
        "AuthResult", back_populates="document", cascade="all, delete-orphan"
    )


class ExtractedField(Base):
    __tablename__ = "extracted_fields"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    value_original: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    value_normalized: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    needs_verification: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), default=lambda: datetime.now(timezone.utc)
    )

    document: Mapped["Document"] = relationship("Document", back_populates="extracted_fields")


class AuthResult(Base):
    __tablename__ = "auth_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    check_type: Mapped[str] = mapped_column(String(100), nullable=False)
    result: Mapped[str] = mapped_column(String(50), nullable=False)
    probability: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    evidence: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), default=lambda: datetime.now(timezone.utc)
    )

    document: Mapped["Document"] = relationship("Document", back_populates="auth_results")


class RuleResult(Base):
    __tablename__ = "rule_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    application_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True
    )
    document_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("documents.id", ondelete="SET NULL"), nullable=True, index=True
    )
    rule_id: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="passed", nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    severity: Mapped[str] = mapped_column(String(50), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    clause: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    evidence: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), default=lambda: datetime.now(timezone.utc)
    )

    application: Mapped["Application"] = relationship("Application", back_populates="rule_results")
    document: Mapped[Optional["Document"]] = relationship("Document")


class ConsistencyResult(Base):
    __tablename__ = "consistency_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    application_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True
    )
    rule_id: Mapped[str] = mapped_column(String(100), default="", nullable=False)
    field: Mapped[str] = mapped_column(String(100), nullable=False)
    doc_a_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )
    doc_b_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("documents.id", ondelete="SET NULL"), nullable=True
    )
    value_a: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    value_b: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    # outcome: match, partial, conflict (for compatibility)
    outcome: Mapped[str] = mapped_column(String(50), default="match", nullable=False)
    # status: match, partial, conflict, not_evaluable
    status: Mapped[str] = mapped_column(String(50), default="match", nullable=False)
    severity: Mapped[str] = mapped_column(String(50), default="high", nullable=False)
    relation: Mapped[str] = mapped_column(String(50), default="equals", nullable=False)
    message: Mapped[str] = mapped_column(Text, default="", nullable=False)
    clause: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    evidence: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), default=lambda: datetime.now(timezone.utc)
    )

    application: Mapped["Application"] = relationship("Application", back_populates="consistency_results")
    doc_a: Mapped[Optional["Document"]] = relationship("Document", foreign_keys=[doc_a_id])
    doc_b: Mapped[Optional["Document"]] = relationship("Document", foreign_keys=[doc_b_id])


class DeficiencyReport(Base):
    __tablename__ = "deficiency_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    application_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # status: draft, approved, sent
    status: Mapped[str] = mapped_column(String(50), default="draft", nullable=False)
    content: Mapped[Any] = mapped_column(JSON, nullable=False)
    approved_by: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), default=lambda: datetime.now(timezone.utc)
    )

    application: Mapped["Application"] = relationship("Application", back_populates="deficiency_reports")


class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    application_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True
    )
    officer_name: Mapped[str] = mapped_column(String(100), nullable=False)
    decision: Mapped[str] = mapped_column(String(50), nullable=False)
    comments: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), default=lambda: datetime.now(timezone.utc)
    )

    application: Mapped["Application"] = relationship("Application", back_populates="reviews")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    actor: Mapped[str] = mapped_column(String(100), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    entity: Mapped[str] = mapped_column(String(100), nullable=False)
    details: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
