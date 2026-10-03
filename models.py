
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.session import Base

class User(Base):
    __tablename__="users"
    id: Mapped[int]=mapped_column(primary_key=True)
    name: Mapped[str]=mapped_column(String(120))
    email: Mapped[str]=mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str]=mapped_column(String(255))
    mfa_secret: Mapped[str|None]=mapped_column(String(64), nullable=True)
    mfa_enabled: Mapped[bool]=mapped_column(Boolean, default=False)
    created_at: Mapped[datetime]=mapped_column(DateTime, default=datetime.utcnow)

class Account(Base):
    __tablename__="accounts"
    id: Mapped[int]=mapped_column(primary_key=True)
    user_id: Mapped[int]=mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str]=mapped_column(String(120))
    kind: Mapped[str]=mapped_column(String(20), default="bank") # bank/cash/card
    balance: Mapped[Decimal]=mapped_column(Numeric(14,2), default=0)
    credit_limit: Mapped[Decimal|None]=mapped_column(Numeric(14,2), nullable=True)
    created_at: Mapped[datetime]=mapped_column(DateTime, default=datetime.utcnow)

class Card(Base):
    __tablename__="cards"
    id: Mapped[int]=mapped_column(primary_key=True)
    user_id: Mapped[int]=mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    account_id: Mapped[int|None]=mapped_column(ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True)
    name: Mapped[str]=mapped_column(String(120))
    brand: Mapped[str|None]=mapped_column(String(40), nullable=True)
    last4: Mapped[str|None]=mapped_column(String(4), nullable=True)
    credit_limit: Mapped[Decimal]=mapped_column(Numeric(14,2), default=0)
    closing_day: Mapped[int]=mapped_column()
    due_day: Mapped[int]=mapped_column()
    active: Mapped[bool]=mapped_column(Boolean, default=True)
    created_at: Mapped[datetime]=mapped_column(DateTime, default=datetime.utcnow)

class Invoice(Base):
    __tablename__="invoices"
    id: Mapped[int]=mapped_column(primary_key=True)
    user_id: Mapped[int]=mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    card_id: Mapped[int]=mapped_column(ForeignKey("cards.id", ondelete="CASCADE"), index=True)
    reference_month: Mapped[date]=mapped_column(Date)
    closing_date: Mapped[date]=mapped_column(Date)
    due_date: Mapped[date]=mapped_column(Date)
    status: Mapped[str]=mapped_column(String(20), default="open") # open/closed/paid/overdue
    total: Mapped[Decimal]=mapped_column(Numeric(14,2), default=0)
    paid_amount: Mapped[Decimal]=mapped_column(Numeric(14,2), default=0)
    paid_at: Mapped[date|None]=mapped_column(Date, nullable=True)
    __table_args__=(UniqueConstraint("card_id","reference_month",name="uq_invoice_card_month"),)

class Transaction(Base):
    __tablename__="transactions"
    id: Mapped[int]=mapped_column(primary_key=True)
    user_id: Mapped[int]=mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    account_id: Mapped[int|None]=mapped_column(ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True)
    card_id: Mapped[int|None]=mapped_column(ForeignKey("cards.id", ondelete="SET NULL"), nullable=True)
    invoice_id: Mapped[int|None]=mapped_column(ForeignKey("invoices.id", ondelete="SET NULL"), nullable=True)
    recurring_id: Mapped[int|None]=mapped_column(ForeignKey("recurrings.id", ondelete="SET NULL"), nullable=True)
    installment_plan_id: Mapped[int|None]=mapped_column(ForeignKey("installment_plans.id", ondelete="SET NULL"), nullable=True)
    transfer_id: Mapped[int|None]=mapped_column(ForeignKey("transfers.id", ondelete="SET NULL"), nullable=True)
    description: Mapped[str]=mapped_column(String(255))
    category: Mapped[str]=mapped_column(String(100), default="Outros")
    type: Mapped[str]=mapped_column(String(20)) # income/expense
    amount: Mapped[Decimal]=mapped_column(Numeric(14,2))
    occurred_at: Mapped[date]=mapped_column(Date)
    status: Mapped[str]=mapped_column(String(20), default="posted")
    created_at: Mapped[datetime]=mapped_column(DateTime, default=datetime.utcnow)
    __table_args__=(Index("ix_tx_user_date","user_id","occurred_at"),)

class Recurring(Base):
    __tablename__="recurrings"
    id: Mapped[int]=mapped_column(primary_key=True)
    user_id: Mapped[int]=mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    account_id: Mapped[int|None]=mapped_column(ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True)
    card_id: Mapped[int|None]=mapped_column(ForeignKey("cards.id", ondelete="SET NULL"), nullable=True)
    description: Mapped[str]=mapped_column(String(255))
    category: Mapped[str]=mapped_column(String(100), default="Recorrente")
    amount: Mapped[Decimal]=mapped_column(Numeric(14,2))
    type: Mapped[str]=mapped_column(String(20)) # income/expense
    frequency: Mapped[str]=mapped_column(String(20)) # monthly/weekly/yearly
    next_date: Mapped[date]=mapped_column(Date)
    active: Mapped[bool]=mapped_column(Boolean, default=True)

class InstallmentPlan(Base):
    __tablename__="installment_plans"
    id: Mapped[int]=mapped_column(primary_key=True)
    user_id: Mapped[int]=mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    card_id: Mapped[int|None]=mapped_column(ForeignKey("cards.id", ondelete="SET NULL"), nullable=True)
    account_id: Mapped[int|None]=mapped_column(ForeignKey("accounts.id", ondelete="SET NULL"), nullable=True)
    description: Mapped[str]=mapped_column(String(255))
    category: Mapped[str]=mapped_column(String(100), default="Parcelado")
    total_amount: Mapped[Decimal]=mapped_column(Numeric(14,2))
    installment_amount: Mapped[Decimal]=mapped_column(Numeric(14,2))
    total_count: Mapped[int]=mapped_column()
    paid_count: Mapped[int]=mapped_column(default=0)
    first_due_date: Mapped[date]=mapped_column(Date)
    status: Mapped[str]=mapped_column(String(20), default="active")
    created_at: Mapped[datetime]=mapped_column(DateTime, default=datetime.utcnow)

class Installment(Base):
    __tablename__="installments"
    id: Mapped[int]=mapped_column(primary_key=True)
    plan_id: Mapped[int]=mapped_column(ForeignKey("installment_plans.id", ondelete="CASCADE"), index=True)
    invoice_id: Mapped[int|None]=mapped_column(ForeignKey("invoices.id", ondelete="SET NULL"), nullable=True)
    number: Mapped[int]=mapped_column()
    amount: Mapped[Decimal]=mapped_column(Numeric(14,2))
    due_date: Mapped[date]=mapped_column(Date)
    status: Mapped[str]=mapped_column(String(20), default="pending") # pending/paid
    paid_at: Mapped[date|None]=mapped_column(Date, nullable=True)
    __table_args__=(UniqueConstraint("plan_id","number",name="uq_installment_number"),)

class Transfer(Base):
    __tablename__="transfers"
    id: Mapped[int]=mapped_column(primary_key=True)
    user_id: Mapped[int]=mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    from_account_id: Mapped[int]=mapped_column(ForeignKey("accounts.id", ondelete="RESTRICT"))
    to_account_id: Mapped[int]=mapped_column(ForeignKey("accounts.id", ondelete="RESTRICT"))
    amount: Mapped[Decimal]=mapped_column(Numeric(14,2))
    transfer_date: Mapped[date]=mapped_column(Date)
    description: Mapped[str]=mapped_column(String(255), default="Transferência")
    created_at: Mapped[datetime]=mapped_column(DateTime, default=datetime.utcnow)

class Budget(Base):
    __tablename__="budgets"
    id: Mapped[int]=mapped_column(primary_key=True)
    user_id: Mapped[int]=mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    category: Mapped[str]=mapped_column(String(100))
    month: Mapped[date]=mapped_column(Date)
    limit_amount: Mapped[Decimal]=mapped_column(Numeric(14,2))
    alert_percent: Mapped[int]=mapped_column(default=80)
    __table_args__=(UniqueConstraint("user_id","category","month",name="uq_budget_user_cat_month"),)

class Alert(Base):
    __tablename__="alerts"
    id: Mapped[int]=mapped_column(primary_key=True)
    user_id: Mapped[int]=mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str]=mapped_column(String(40))
    title: Mapped[str]=mapped_column(String(160))
    message: Mapped[str]=mapped_column(Text)
    severity: Mapped[str]=mapped_column(String(20), default="info")
    read: Mapped[bool]=mapped_column(Boolean, default=False)
    created_at: Mapped[datetime]=mapped_column(DateTime, default=datetime.utcnow)

class Goal(Base):
    __tablename__="goals"
    id: Mapped[int]=mapped_column(primary_key=True)
    user_id: Mapped[int]=mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str]=mapped_column(String(120))
    target_amount: Mapped[Decimal]=mapped_column(Numeric(14,2))
    current_amount: Mapped[Decimal]=mapped_column(Numeric(14,2), default=0)
    target_date: Mapped[date|None]=mapped_column(Date, nullable=True)

class Debt(Base):
    __tablename__="debts"
    id: Mapped[int]=mapped_column(primary_key=True)
    user_id: Mapped[int]=mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    creditor: Mapped[str]=mapped_column(String(160))
    balance: Mapped[Decimal]=mapped_column(Numeric(14,2))
    monthly_payment: Mapped[Decimal]=mapped_column(Numeric(14,2))
    interest_rate: Mapped[Decimal]=mapped_column(Numeric(8,4), default=0)

class AuditLog(Base):
    __tablename__="audit_logs"
    id: Mapped[int]=mapped_column(primary_key=True)
    user_id: Mapped[int|None]=mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action: Mapped[str]=mapped_column(String(100), index=True)
    detail: Mapped[str|None]=mapped_column(Text, nullable=True)
    ip_address: Mapped[str|None]=mapped_column(String(64), nullable=True)
    user_agent: Mapped[str|None]=mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime]=mapped_column(DateTime, default=datetime.utcnow, index=True)

class Session(Base):
    __tablename__="sessions"
    id: Mapped[int]=mapped_column(primary_key=True)
    user_id: Mapped[int]=mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    token_hash: Mapped[str]=mapped_column(String(128), unique=True, index=True)
    created_at: Mapped[datetime]=mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[datetime]=mapped_column(DateTime, index=True)
    last_used_at: Mapped[datetime]=mapped_column(DateTime, default=datetime.utcnow)
    revoked_at: Mapped[datetime|None]=mapped_column(DateTime, nullable=True, index=True)
    ip_address: Mapped[str|None]=mapped_column(String(64), nullable=True)
    user_agent: Mapped[str|None]=mapped_column(String(512), nullable=True)

class Consent(Base):
    __tablename__="consents"
    id: Mapped[int]=mapped_column(primary_key=True)
    user_id: Mapped[int]=mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    purpose: Mapped[str]=mapped_column(String(100), index=True)
    granted: Mapped[bool]=mapped_column(Boolean, default=False)
    version: Mapped[str]=mapped_column(String(32), default="1.0")
    granted_at: Mapped[datetime|None]=mapped_column(DateTime, nullable=True)
    revoked_at: Mapped[datetime|None]=mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime]=mapped_column(DateTime, default=datetime.utcnow)
    __table_args__=(Index("ix_consent_user_purpose","user_id","purpose"),)
