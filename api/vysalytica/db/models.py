"""
Database models for Vysalytica audit system
"""

from sqlalchemy import Column, Integer, String, Float, Text, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from api.vysalytica.db import Base


class AuditRun(Base):
    """
    Represents a complete audit run for a website.
    Stores overall scores and metadata.
    """

    __tablename__ = "audit_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    url = Column(String(512), nullable=False, index=True)
    domain = Column(String(255), nullable=False, index=True)
    packs = Column(JSON, nullable=False)  # ["base", "ecomm", "docs"]
    overall_score = Column(Float, nullable=False)
    category_scores = Column(JSON, nullable=False)  # {"Crawlability": 85.5, ...}
    page_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, index=True, nullable=False)

    # Relationship to findings
    findings = relationship(
        "Finding",
        back_populates="audit_run",
        cascade="all, delete-orphan",
        lazy="joined",
    )

    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "url": self.url,
            "domain": self.domain,
            "packs": self.packs,
            "overall_score": self.overall_score,
            "category_scores": self.category_scores,
            "page_count": self.page_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "findings": [f.to_dict() for f in self.findings] if self.findings else [],
        }


class Finding(Base):
    """
    Represents a single rule evaluation finding.
    Linked to an audit run.
    """

    __tablename__ = "findings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    audit_run_id = Column(
        Integer, ForeignKey("audit_runs.id"), nullable=False, index=True
    )
    rule_id = Column(String(64), nullable=False, index=True)
    rule_title = Column(String(255), nullable=False)
    category = Column(String(64), nullable=False, index=True)
    status = Column(String(16), nullable=False)  # "pass", "fail", "partial"
    confidence = Column(Float, nullable=True)
    evidence = Column(JSON, nullable=True)  # List of evidence dicts
    why = Column(Text, nullable=True)
    fix = Column(Text, nullable=True)
    fix_snippet = Column(Text, nullable=True)  # LLM-generated fix code
    acceptance_test = Column(Text, nullable=True)  # LLM-generated pytest test

    # Relationship to audit run
    audit_run = relationship("AuditRun", back_populates="findings")

    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "audit_run_id": self.audit_run_id,
            "rule_id": self.rule_id,
            "rule_title": self.rule_title,
            "category": self.category,
            "status": self.status,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "why": self.why,
            "fix": self.fix,
            "fix_snippet": self.fix_snippet,
            "acceptance_test": self.acceptance_test,
        }


class RuleDefinition(Base):
    """
    Stores static rule metadata for audit packs.
    """

    __tablename__ = "rule_definitions"

    id = Column(String(64), primary_key=True)
    title = Column(String(255), nullable=False)
    category = Column(String(128), nullable=False, index=True)
    pack = Column(String(64), nullable=False, index=True)
    description = Column(Text, nullable=True)
    why = Column(Text, nullable=True)
    fix = Column(Text, nullable=True)
    confidence = Column(Float, nullable=False, default=0.5)
    acceptance_criteria = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "title": self.title,
            "category": self.category,
            "pack": self.pack,
            "description": self.description,
            "why": self.why,
            "fix": self.fix,
            "confidence": self.confidence,
            "acceptance_criteria": self.acceptance_criteria,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class CitationSnapshot(Base):
    """
    Stores AI citation tracking results.
    Records whether a brand was cited by ChatGPT/Claude for a given query.
    """

    __tablename__ = "citation_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    brand = Column(String(255), nullable=False, index=True)
    intent = Column(String(512), nullable=False)
    assistant = Column(String(64), nullable=False, index=True)  # "ChatGPT" or "Claude"
    cited = Column(
        Integer, nullable=False
    )  # 1 if cited, 0 if not (Boolean stored as int)
    response_text = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True, nullable=False)

    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "brand": self.brand,
            "intent": self.intent,
            "assistant": self.assistant,
            "cited": bool(self.cited),
            "response_text": self.response_text,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class APIKey(Base):
    """
    Stores API keys for public API access.
    Includes basic quota tracking.
    """

    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, autoincrement=True)
    key = Column(String(64), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=True)  # Optional name/description
    quota_per_hour = Column(Integer, nullable=False, default=10)  # Rate limit
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_used_at = Column(DateTime, nullable=True)
    is_active = Column(Integer, nullable=False, default=1)  # Boolean stored as int

    def to_dict(self):
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "key": self.key,
            "name": self.name,
            "quota_per_hour": self.quota_per_hour,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_used_at": (
                self.last_used_at.isoformat() if self.last_used_at else None
            ),
            "is_active": bool(self.is_active),
        }


class ReferralCode(Base):
    """
    Simple referral codes for partner attribution.
    """

    __tablename__ = "referral_codes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(64), unique=True, nullable=False, index=True)
    partner_name = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    attributions = relationship(
        "ReferralAttribution",
        back_populates="referral_code",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class ReferralAttribution(Base):
    """
    Attribution events when a user visits with a referral code.
    """

    __tablename__ = "referral_attributions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    referral_code_id = Column(Integer, ForeignKey("referral_codes.id"), index=True)
    cookie_id = Column(String(64), nullable=True, index=True)
    user_agent = Column(Text, nullable=True)
    ip_address = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    referral_code = relationship("ReferralCode", back_populates="attributions")


# =====================
# New Tables (Answer Graph & Playbooks)
# =====================


class AnswerGraph(Base):
    """
    Snapshot of an answer graph build for a domain and intents.
    Stores graph payload for quick retrieval and reporting.
    """

    __tablename__ = "answer_graphs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    domain = Column(String(255), nullable=False, index=True)
    intents = Column(JSON, nullable=False, default=list)
    packs = Column(JSON, nullable=False, default=list)
    nodes = Column(JSON, nullable=False, default=list)
    edges = Column(JSON, nullable=False, default=list)
    gaps = Column(JSON, nullable=False, default=list)
    priority_score = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow, index=True, nullable=False)

    def to_dict(self):
        return {
            "id": self.id,
            "domain": self.domain,
            "intents": self.intents,
            "packs": self.packs,
            "nodes": self.nodes,
            "edges": self.edges,
            "gaps": self.gaps,
            "priority_score": self.priority_score,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Playbook(Base):
    """
    Structured visibility playbook for a specific intent.
    Stores normalized fields and a full JSON blob for portability.
    """

    __tablename__ = "playbooks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    domain = Column(String(255), nullable=False, index=True)
    intent = Column(String(512), nullable=False, index=True)
    target_assistant = Column(String(64), nullable=True)
    playbook_json = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow, index=True, nullable=False)

    fixes = relationship(
        "PlaybookFix",
        back_populates="playbook",
        cascade="all, delete-orphan",
        lazy="joined",
    )

    def to_dict(self):
        return {
            "id": self.id,
            "domain": self.domain,
            "intent": self.intent,
            "target_assistant": self.target_assistant,
            "playbook": self.playbook_json,
            "fixes": [f.to_dict() for f in self.fixes] if self.fixes else [],
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class PlaybookFix(Base):
    """
    Individual fix item associated with a playbook.
    Useful for reporting and future workflow.
    """

    __tablename__ = "playbook_fixes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    playbook_id = Column(
        Integer, ForeignKey("playbooks.id"), index=True, nullable=False
    )
    fix_id = Column(String(128), nullable=False)
    title = Column(String(255), nullable=False)
    language = Column(String(32), nullable=True)
    snippet = Column(Text, nullable=True)
    why = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True, nullable=False)

    playbook = relationship("Playbook", back_populates="fixes")

    def to_dict(self):
        return {
            "id": self.id,
            "playbook_id": self.playbook_id,
            "fix_id": self.fix_id,
            "title": self.title,
            "language": self.language,
            "snippet": self.snippet,
            "why": self.why,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
