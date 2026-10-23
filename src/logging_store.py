from __future__ import annotations
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import create_engine, String, Float, Text, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from .config import DATABASE_URL, ROOT

PIPELINE_VERSION = "1.0.0"


class Base(DeclarativeBase):
    pass


class DecisionRecord(Base):
    __tablename__ = "decisions"

    decision_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ticket_id: Mapped[str] = mapped_column(String(160), index=True, nullable=False)
    channel: Mapped[str] = mapped_column(String(40), nullable=False)
    customer_tier: Mapped[str] = mapped_column(String(40), nullable=False, default="unknown")
    customer_region: Mapped[str] = mapped_column(String(80), nullable=False, default="unknown")
    intent: Mapped[str] = mapped_column(String(80), nullable=False)
    urgency: Mapped[str] = mapped_column(String(30), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    action_taken: Mapped[str] = mapped_column(String(40), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    sources_used: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    guardrails: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    pipeline_version: Mapped[str] = mapped_column(String(40), nullable=False, default=PIPELINE_VERSION)
    prompt_version: Mapped[str] = mapped_column(String(40), nullable=False, default="support-v1.0")
    latency_ms: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    error_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    # Non-fluent language handling: store original and normalised body for audit.
    original_body: Mapped[str | None] = mapped_column(Text, nullable=True)
    normalised_body: Mapped[str | None] = mapped_column(Text, nullable=True)


class DecisionLogger:
    def __init__(self, database_url: str = DATABASE_URL):
        if database_url.startswith("sqlite:///"):
            raw_path = database_url.replace("sqlite:///", "", 1)
            if not raw_path.startswith("/"):
                (ROOT / raw_path).parent.mkdir(parents=True, exist_ok=True)
            else:
                Path(raw_path).parent.mkdir(parents=True, exist_ok=True)
        self.engine = create_engine(
            database_url,
            future=True,
            connect_args={"check_same_thread": False} if database_url.startswith("sqlite") else {},
        )
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine, expire_on_commit=False)

    def log(self, result: dict, latency_ms: float) -> None:
        now = datetime.now(timezone.utc)
        ticket = result.get("_ticket_meta", {})
        record = DecisionRecord(
            decision_id=f"{result.get('ticket_id', 'unknown')}:{now.timestamp():.6f}",
            created_at=now,
            ticket_id=str(result.get("ticket_id", "unknown")),
            channel=str(result.get("channel", "unknown")),
            customer_tier=str(ticket.get("customer_tier", "unknown")),
            customer_region=str(ticket.get("customer_region", "unknown")),
            intent=str(result.get("intent", "unclear_request")),
            urgency=str(result.get("urgency", "medium")),
            confidence=float(result.get("confidence", 0.0)),
            action_taken=str(result.get("decision", "escalate")),
            reason=str(result.get("decision_reason", "unspecified")),
            sources_used=json.dumps(
                [
                    {k: source.get(k) for k in ("doc_id", "passage_id", "title", "score")}
                    for source in result.get("sources", [])
                ],
                ensure_ascii=False,
            ),
            guardrails=json.dumps(result.get("guardrail", {}), ensure_ascii=False),
            pipeline_version=PIPELINE_VERSION,
            prompt_version="support-v1.0",
            latency_ms=float(latency_ms),
            error_type=result.get("error_type"),
            original_body=ticket.get("original_body"),
            normalised_body=ticket.get("normalised_body"),
        )
        with self.Session() as session:
            session.add(record)
            session.commit()
