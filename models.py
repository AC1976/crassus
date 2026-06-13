import uuid
from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from database import Base


# ---------------------------------------------------------------------------
# Auth & Tenancy
# ---------------------------------------------------------------------------

class Organisation(Base):
    __tablename__ = "organisations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    # SaaS admin fields
    subscription_status = Column(String, nullable=False, default="trial", server_default="trial")
    # trial | active | churned | exempt
    admin_notes = Column(Text, nullable=True)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    org_id = Column(Integer, ForeignKey("organisations.id", ondelete="RESTRICT"), nullable=False)
    email = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, nullable=False)  # owner / editor / viewer
    is_active = Column(Boolean, nullable=False, default=True)
    is_admin = Column(Boolean, nullable=False, default=False, server_default="0")
    created_at = Column(DateTime, nullable=False, server_default=func.now())


class Invitation(Base):
    __tablename__ = "invitations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    org_id = Column(Integer, ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False)
    invited_email = Column(String, nullable=False)
    role = Column(String, nullable=False)  # editor / viewer
    token = Column(String, unique=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    accepted_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())


# ---------------------------------------------------------------------------
# Configuration & Base Data
# ---------------------------------------------------------------------------

class Settings(Base):
    __tablename__ = "settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    org_id = Column(Integer, ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False, unique=True)
    company_name = Column(String, nullable=False)
    company_vat_number = Column(String, nullable=True)
    company_address = Column(Text, nullable=False)
    billing_email_sender = Column(String, nullable=True)
    default_vat_rate = Column(Numeric(5, 2), nullable=False, default=21.00)
    currency = Column(String(3), nullable=False, default="EUR")
    reporting_preference = Column(String, nullable=False, default="quarterly")
    bank_account = Column(String, nullable=True)
    logo_s3_key = Column(String, nullable=True)
    lease_termination_notice_days = Column(Integer, nullable=False, default=365)
    invoice_numbering_scheme = Column(String, nullable=False, default="sequential")
    vat_consultant_email = Column(String, nullable=True)
    invoice_language = Column(String(2), nullable=False, default="en", server_default="en")


class Property(Base):
    __tablename__ = "properties"

    id = Column(Integer, primary_key=True, autoincrement=True)
    org_id = Column(Integer, ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    property_reference = Column(String, nullable=True)  # short code for invoice numbering, e.g. "M2"
    address = Column(Text, nullable=False)
    property_type = Column(String, nullable=False)
    is_vat_exempt = Column(Boolean, nullable=False, default=False)
    insurance_policy_number = Column(String, nullable=True)
    insurance_provider = Column(String, nullable=True)
    insurance_renewal_date = Column(Date, nullable=True)
    insurance_annual_premium = Column(Numeric(12, 2), nullable=True)
    asset_value = Column(Numeric(14, 2), nullable=True)
    maintenance_annual_budget = Column(Numeric(12, 2), nullable=False, default=0.00)
    created_at = Column(DateTime, nullable=False, server_default=func.now())


class Unit(Base):
    __tablename__ = "units"

    id = Column(Integer, primary_key=True, autoincrement=True)
    org_id = Column(Integer, ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False)
    property_id = Column(Integer, ForeignKey("properties.id", ondelete="CASCADE"), nullable=False)
    unit_number = Column(String, nullable=False)
    floor_level = Column(Integer, nullable=True)
    square_meters = Column(Numeric(8, 2), nullable=True)


class Lessee(Base):
    __tablename__ = "lessees"

    id = Column(Integer, primary_key=True, autoincrement=True)
    org_id = Column(Integer, ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False)
    lessee_uuid = Column(String, nullable=False, default=lambda: str(uuid.uuid4()))
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    company_legal_name = Column(String, nullable=True)
    company_vat_id = Column(String, nullable=True)
    email = Column(String, nullable=False)
    phone = Column(String, nullable=True)
    billing_address = Column(Text, nullable=False)
    bank_account = Column(String, nullable=True)


# ---------------------------------------------------------------------------
# Contracts & Agreements
# ---------------------------------------------------------------------------

class RentalAgreement(Base):
    __tablename__ = "rental_agreements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    org_id = Column(Integer, ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False)
    agreement_uuid = Column(String, nullable=False, default=lambda: str(uuid.uuid4()))
    property_id = Column(Integer, ForeignKey("properties.id", ondelete="RESTRICT"), nullable=True)
    unit_id = Column(Integer, ForeignKey("units.id", ondelete="RESTRICT"), nullable=True)
    lessee_uuid = Column(String, nullable=False)
    base_rent_amount = Column(Numeric(12, 2), nullable=False)
    vat_rate_applied = Column(Numeric(5, 2), nullable=False, default=0.00)
    service_charges = Column(Numeric(12, 2), nullable=False, default=0.00)
    payment_interval = Column(String, nullable=False, default="monthly")
    deposit_amount = Column(Numeric(12, 2), nullable=False, default=0.00)
    valid_time_start = Column(DateTime, nullable=False)
    valid_time_end = Column(DateTime, nullable=False)
    # Annual indexation: day/month on which rent is indexed each year (year part ignored)
    indexation_date = Column(Date, nullable=True)
    # Date on which the rent was last indexed (used to hide already-applied rows on dashboard)
    indexation_last_applied = Column(Date, nullable=True)


# ---------------------------------------------------------------------------
# Financials & Invoicing
# ---------------------------------------------------------------------------

class Invoice(Base):
    __tablename__ = "invoices"
    __table_args__ = (UniqueConstraint("org_id", "invoice_number", name="uq_invoice_number_per_org"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    org_id = Column(Integer, ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False)
    invoice_number = Column(String, nullable=False)
    agreement_uuid = Column(String, nullable=False)  # logical FK to rental_agreements.agreement_uuid
    parent_invoice_id = Column(Integer, ForeignKey("invoices.id", ondelete="RESTRICT"), nullable=True)
    invoice_type = Column(String, nullable=False, default="standard")
    billing_period_start = Column(Date, nullable=False)
    billing_period_end = Column(Date, nullable=False)
    issue_date = Column(Date, nullable=False)
    due_date = Column(Date, nullable=False)
    net_amount = Column(Numeric(12, 2), nullable=False)
    vat_amount = Column(Numeric(12, 2), nullable=False)
    gross_amount = Column(Numeric(12, 2), nullable=False)
    invoice_status = Column(String, nullable=False, default="draft")
    resend_email_id = Column(String, nullable=True)
    email_delivery_status = Column(String, nullable=False, default="unsent")
    email_last_checked_at = Column(DateTime, nullable=True)
    pdf_s3_key = Column(String, nullable=True)
    pdf_s3_bucket = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())


class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    org_id = Column(Integer, ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False)
    invoice_id = Column(Integer, ForeignKey("invoices.id", ondelete="RESTRICT"), nullable=False)
    payment_date = Column(DateTime, nullable=False)
    amount_received = Column(Numeric(12, 2), nullable=False)
    payment_method = Column(String, nullable=False)
    transaction_reference = Column(String, unique=True, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())


# ---------------------------------------------------------------------------
# Operations & Reporting
# ---------------------------------------------------------------------------

class Expense(Base):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    org_id = Column(Integer, ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False)
    property_id = Column(Integer, ForeignKey("properties.id", ondelete="RESTRICT"), nullable=False)
    vendor_name = Column(String, nullable=False)
    invoice_reference = Column(String, nullable=True)
    expense_category = Column(String, nullable=False)
    expense_date = Column(Date, nullable=False)
    net_amount = Column(Numeric(12, 2), nullable=False)
    vat_amount = Column(Numeric(12, 2), nullable=False)
    gross_amount = Column(Numeric(12, 2), nullable=False)
    description = Column(Text, nullable=False)
    payment_due_date = Column(Date, nullable=True)
    is_paid = Column(Boolean, nullable=False, default=False, server_default="0")
    paid_date = Column(Date, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())


# ---------------------------------------------------------------------------
# Storage
# ---------------------------------------------------------------------------

class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    org_id = Column(Integer, ForeignKey("organisations.id", ondelete="CASCADE"), nullable=False)
    display_name = Column(String, nullable=False)
    s3_bucket = Column(String, nullable=False)
    s3_key = Column(String, unique=True, nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    mime_type = Column(String, nullable=False)
    related_entity_type = Column(String, nullable=False)
    related_entity_id = Column(Integer, nullable=False)
    document_category = Column(String, nullable=False, server_default="other")
    uploaded_by_user_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
