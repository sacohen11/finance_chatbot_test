from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Contractor(Base):
    __tablename__ = "contractors"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    org_unit: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(50))
    address: Mapped[str | None] = mapped_column(Text())
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    contracts: Mapped[list[Contract]] = relationship(back_populates="contractor")


class Contract(Base):
    __tablename__ = "contracts"
    __table_args__ = (Index("ix_contracts_contract_number", "contract_number"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    contract_number: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    contractor_id: Mapped[int] = mapped_column(
        ForeignKey("contractors.id", ondelete="RESTRICT"), nullable=False
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    budget_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    contractor: Mapped[Contractor] = relationship(back_populates="contracts")
    monthly_reports: Mapped[list[ContractMonthlyReport]] = relationship(
        back_populates="contract", cascade="all, delete-orphan"
    )


class ContractMonthlyReport(Base):
    __tablename__ = "contract_monthly_reports"
    __table_args__ = (
        UniqueConstraint("contract_id", "report_month", name="uq_contract_monthly_report"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    contract_id: Mapped[int] = mapped_column(
        ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False
    )
    report_month: Mapped[date] = mapped_column(Date, nullable=False)
    planned_spend: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    actual_spend: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    hours_planned: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    hours_actual: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text())
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    contract: Mapped[Contract] = relationship(back_populates="monthly_reports")


class Analyst(Base):
    __tablename__ = "analysts"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    chat_sessions: Mapped[list[ChatSession]] = relationship(back_populates="analyst")
    recommended_prompts: Mapped[list[RecommendedPrompt]] = relationship(
        back_populates="analyst", cascade="all, delete-orphan"
    )


class ChatSession(Base):
    __tablename__ = "chat_sessions"
    __table_args__ = (Index("ix_chat_sessions_analyst_id", "analyst_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    analyst_id: Mapped[int] = mapped_column(
        ForeignKey("analysts.id", ondelete="CASCADE"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_active_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    analyst: Mapped[Analyst] = relationship(back_populates="chat_sessions")
    chat_messages: Mapped[list[ChatMessage]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    __table_args__ = (Index("ix_chat_messages_session_id", "session_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(
        ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(50), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    session: Mapped[ChatSession] = relationship(back_populates="chat_messages")


class RecommendedPrompt(Base):
    __tablename__ = "recommended_prompts"

    id: Mapped[int] = mapped_column(primary_key=True)
    analyst_id: Mapped[int] = mapped_column(
        ForeignKey("analysts.id", ondelete="CASCADE"), nullable=False
    )
    prompt_text: Mapped[str] = mapped_column(Text, nullable=False)
    score: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    analyst: Mapped[Analyst] = relationship(back_populates="recommended_prompts")
