from datetime import date, datetime
from decimal import Decimal
from typing import List, Literal, Optional
from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# Auth & Tenancy
# ---------------------------------------------------------------------------

UserRole = Literal["owner", "editor", "viewer"]
InviteRole = Literal["editor", "viewer"]


class RegisterRequest(BaseModel):
    org_name: str
    email: EmailStr
    password: str = Field(min_length=8)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    mobile: bool = False


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class InviteRequest(BaseModel):
    email: EmailStr
    role: InviteRole


class AcceptInviteRequest(BaseModel):
    token: str
    password: str = Field(min_length=8)


class InviteResponse(BaseModel):
    invite_token: str
    invited_email: EmailStr
    role: InviteRole


class UserRead(BaseModel):
    id: int
    org_id: int
    org_name: str
    email: EmailStr
    role: UserRole
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

InvoiceNumberingScheme = Literal["sequential", "property_ref"]


InvoiceLanguage = Literal["en", "nl"]


class SettingsCreate(BaseModel):
    company_name: str
    company_vat_number: Optional[str] = None
    company_address: str
    billing_email_sender: EmailStr
    default_vat_rate: Decimal = Field(default=Decimal("21.00"), decimal_places=2)
    currency: str = Field(default="EUR", max_length=3)
    reporting_preference: Literal["monthly", "quarterly"] = "quarterly"
    bank_account: Optional[str] = None
    lease_termination_notice_days: int = Field(default=365, ge=1, le=730)
    invoice_numbering_scheme: InvoiceNumberingScheme = "sequential"
    vat_consultant_email: Optional[EmailStr] = None
    invoice_language: InvoiceLanguage = "en"


class SettingsUpdate(BaseModel):
    company_name: Optional[str] = None
    company_vat_number: Optional[str] = None
    company_address: Optional[str] = None
    billing_email_sender: Optional[EmailStr] = None
    default_vat_rate: Optional[Decimal] = None
    currency: Optional[str] = Field(default=None, max_length=3)
    reporting_preference: Optional[Literal["monthly", "quarterly"]] = None
    bank_account: Optional[str] = None
    lease_termination_notice_days: Optional[int] = Field(default=None, ge=1, le=730)
    invoice_numbering_scheme: Optional[InvoiceNumberingScheme] = None
    vat_consultant_email: Optional[EmailStr] = None
    invoice_language: Optional[InvoiceLanguage] = None


class SettingsRead(BaseModel):
    """Read schema — all fields are optional to handle partially-created rows
    (e.g. created by a logo upload before the form has been filled in)."""
    id: int
    company_name: str = ""
    company_vat_number: Optional[str] = None
    company_address: str = ""
    billing_email_sender: Optional[str] = None   # plain str — may be empty
    default_vat_rate: Decimal = Decimal("21.00")
    currency: str = "EUR"
    reporting_preference: Literal["monthly", "quarterly"] = "quarterly"
    bank_account: Optional[str] = None
    lease_termination_notice_days: int = 365
    invoice_numbering_scheme: InvoiceNumberingScheme = "sequential"
    vat_consultant_email: Optional[str] = None   # plain str — may be empty
    invoice_language: InvoiceLanguage = "en"
    logo_s3_key: Optional[str] = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Property
# ---------------------------------------------------------------------------

PropertyType = Literal["residential", "commercial", "industrial"]


class PropertyCreate(BaseModel):
    name: str
    property_reference: Optional[str] = None
    address: str
    property_type: PropertyType
    is_vat_exempt: bool = False
    insurance_policy_number: Optional[str] = None
    insurance_provider: Optional[str] = None
    insurance_renewal_date: Optional[date] = None
    insurance_annual_premium: Optional[Decimal] = None
    asset_value: Optional[Decimal] = None
    maintenance_annual_budget: Decimal = Decimal("0.00")


class PropertyUpdate(BaseModel):
    name: Optional[str] = None
    property_reference: Optional[str] = None
    address: Optional[str] = None
    property_type: Optional[PropertyType] = None
    is_vat_exempt: Optional[bool] = None
    insurance_policy_number: Optional[str] = None
    insurance_provider: Optional[str] = None
    insurance_renewal_date: Optional[date] = None
    insurance_annual_premium: Optional[Decimal] = None
    asset_value: Optional[Decimal] = None
    maintenance_annual_budget: Optional[Decimal] = None


class PropertyRead(PropertyCreate):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Unit
# ---------------------------------------------------------------------------

class UnitCreate(BaseModel):
    property_id: int
    unit_number: str
    floor_level: Optional[int] = None
    square_meters: Optional[Decimal] = None


class UnitUpdate(BaseModel):
    unit_number: Optional[str] = None
    floor_level: Optional[int] = None
    square_meters: Optional[Decimal] = None


class UnitRead(UnitCreate):
    id: int

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Lessee
# ---------------------------------------------------------------------------

class LesseeCreate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company_legal_name: Optional[str] = None
    company_vat_id: Optional[str] = None
    email: EmailStr
    phone: Optional[str] = None
    billing_address: str
    bank_account: Optional[str] = None

    @model_validator(mode="after")
    def require_name_or_company(self) -> "LesseeCreate":
        has_person = self.first_name or self.last_name
        has_company = self.company_legal_name
        if not has_person and not has_company:
            raise ValueError("Provide at least a personal name or a company legal name.")
        return self


class LesseeUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    company_legal_name: Optional[str] = None
    company_vat_id: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None
    billing_address: Optional[str] = None
    bank_account: Optional[str] = None


class LesseeRead(LesseeCreate):
    id: int
    lessee_uuid: str

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Rental Agreement
# ---------------------------------------------------------------------------

PaymentInterval = Literal["monthly", "quarterly", "annually"]


class RentalAgreementCreate(BaseModel):
    property_id: int
    unit_id: Optional[int] = None
    lessee_uuid: str
    base_rent_amount: Decimal
    vat_rate_applied: Decimal = Decimal("0.00")
    service_charges: Decimal = Decimal("0.00")
    payment_interval: PaymentInterval = "monthly"
    deposit_amount: Decimal = Decimal("0.00")
    valid_time_start: datetime
    valid_time_end: datetime
    indexation_date: Optional[date] = None

    @model_validator(mode="after")
    def end_after_start(self) -> "RentalAgreementCreate":
        if self.valid_time_end <= self.valid_time_start:
            raise ValueError("valid_time_end must be after valid_time_start.")
        return self


class RentalAgreementUpdate(BaseModel):
    base_rent_amount: Optional[Decimal] = None
    vat_rate_applied: Optional[Decimal] = None
    service_charges: Optional[Decimal] = None
    payment_interval: Optional[PaymentInterval] = None
    deposit_amount: Optional[Decimal] = None
    valid_time_start: Optional[datetime] = None
    valid_time_end: Optional[datetime] = None
    indexation_date: Optional[date] = None


class RentalAgreementRead(RentalAgreementCreate):
    id: int
    agreement_uuid: str

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Invoice
# ---------------------------------------------------------------------------

InvoiceType = Literal["standard", "credit_note"]
InvoiceStatus = Literal["draft", "pending", "paid", "overdue", "credited"]
EmailDeliveryStatus = Literal["unsent", "sent", "delivered", "opened", "bounced"]


class InvoiceCreate(BaseModel):
    invoice_number: str
    agreement_uuid: str
    parent_invoice_id: Optional[int] = None
    invoice_type: InvoiceType = "standard"
    billing_period_start: date
    billing_period_end: date
    issue_date: date
    due_date: date
    net_amount: Decimal
    vat_amount: Decimal
    gross_amount: Decimal
    invoice_status: InvoiceStatus = "draft"

    @model_validator(mode="after")
    def gross_equals_net_plus_vat(self) -> "InvoiceCreate":
        # Round to 2dp before comparing to absorb float→Decimal drift
        net = self.net_amount.quantize(Decimal("0.01"))
        vat = self.vat_amount.quantize(Decimal("0.01"))
        gross = self.gross_amount.quantize(Decimal("0.01"))
        if abs(gross - (net + vat)) > Decimal("0.02"):
            raise ValueError("gross_amount must equal net_amount + vat_amount.")
        # Normalise stored values
        self.net_amount = net
        self.vat_amount = vat
        self.gross_amount = net + vat
        return self


class InvoiceUpdate(BaseModel):
    invoice_status: Optional[InvoiceStatus] = None
    due_date: Optional[date] = None
    resend_email_id: Optional[str] = None
    email_delivery_status: Optional[EmailDeliveryStatus] = None
    email_last_checked_at: Optional[datetime] = None


class InvoiceRead(InvoiceCreate):
    id: int
    resend_email_id: Optional[str] = None
    email_delivery_status: EmailDeliveryStatus
    email_last_checked_at: Optional[datetime] = None
    pdf_s3_key: Optional[str] = None
    pdf_s3_bucket: Optional[str] = None
    created_at: datetime
    unit_number: Optional[str] = None   # enriched server-side; not a DB column

    model_config = {"from_attributes": True}


class SendInvoiceRequest(BaseModel):
    pdf_base64: str
    filename: str
    is_reminder: bool = False


# ---------------------------------------------------------------------------
# Batch billing
# ---------------------------------------------------------------------------

class BatchPreviewRequest(BaseModel):
    reference_date: Optional[date] = None  # defaults to today server-side


class BatchPreviewRow(BaseModel):
    agreement_uuid: str
    unit_label: str
    lessee_name: str
    billing_period_start: date
    billing_period_end: date
    due_date: date
    net_amount: Decimal
    vat_amount: Decimal
    gross_amount: Decimal
    suggested_invoice_number: str
    already_invoiced: bool = False

    model_config = {"from_attributes": True}


class BatchGenerateItem(BaseModel):
    agreement_uuid: str
    invoice_number: str
    billing_period_start: date
    billing_period_end: date
    issue_date: date
    due_date: date
    net_amount: Decimal
    vat_amount: Decimal
    gross_amount: Decimal


class BatchGenerateRequest(BaseModel):
    items: List[BatchGenerateItem]


class BatchSendRequest(BaseModel):
    invoice_ids: List[int]


class BatchSendResult(BaseModel):
    invoice_id: int
    invoice_number: str
    success: bool
    error: Optional[str] = None


class NextPeriodResponse(BaseModel):
    billing_period_start: date
    billing_period_end: date
    due_date: date
    net_amount: Decimal
    vat_amount: Decimal
    gross_amount: Decimal
    suggested_invoice_number: str


class ApplyIndexRequest(BaseModel):
    index_numerator: Optional[Decimal] = None
    index_denominator: Optional[Decimal] = None
    index_percentage: Optional[Decimal] = None
    effective_date: date
    send_notification: bool = True

    @model_validator(mode="after")
    def validate_index_input(self) -> "ApplyIndexRequest":
        has_quotient = self.index_numerator is not None and self.index_denominator is not None
        has_percentage = self.index_percentage is not None
        if not has_quotient and not has_percentage:
            raise ValueError("Provide either (index_numerator + index_denominator) or index_percentage.")
        if has_quotient and has_percentage:
            raise ValueError("Provide either quotient or percentage, not both.")
        if has_quotient and (self.index_denominator is None or self.index_denominator == 0):
            raise ValueError("index_denominator cannot be zero.")
        return self


class RecordPaymentRequest(BaseModel):
    payment_date: date
    amount_received: Decimal
    payment_method: Literal["bank_transfer", "stripe", "direct_debit", "cash", "other"]
    transaction_reference: Optional[str] = None
    notes: Optional[str] = None


# ---------------------------------------------------------------------------
# Payment
# ---------------------------------------------------------------------------

PaymentMethod = Literal["bank_transfer", "stripe", "direct_debit", "cash", "other"]


class PaymentCreate(BaseModel):
    invoice_id: int
    payment_date: datetime
    amount_received: Decimal
    payment_method: PaymentMethod
    transaction_reference: Optional[str] = None
    notes: Optional[str] = None


class PaymentRead(PaymentCreate):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Expense
# ---------------------------------------------------------------------------

ExpenseCategory = Literal[
    "maintenance_repairs",
    "insurance",
    "property_tax",
    "utilities",
    "legal_professional",
    "management_fees",
    "cleaning_landscaping",
    "security",
    "capital_improvement",
    "mortgage_interest",
    "other",
]


class ExpenseCreate(BaseModel):
    property_id: int
    vendor_name: str
    invoice_reference: Optional[str] = None
    expense_category: ExpenseCategory
    expense_date: date
    net_amount: Decimal
    vat_amount: Decimal
    gross_amount: Decimal
    description: str
    payment_due_date: Optional[date] = None

    @model_validator(mode="after")
    def gross_equals_net_plus_vat(self) -> "ExpenseCreate":
        expected = self.net_amount + self.vat_amount
        if abs(self.gross_amount - expected) > Decimal("0.01"):
            raise ValueError("gross_amount must equal net_amount + vat_amount.")
        return self


class ExpenseUpdate(BaseModel):
    vendor_name: Optional[str] = None
    invoice_reference: Optional[str] = None
    expense_category: Optional[ExpenseCategory] = None
    expense_date: Optional[date] = None
    net_amount: Optional[Decimal] = None
    vat_amount: Optional[Decimal] = None
    gross_amount: Optional[Decimal] = None
    description: Optional[str] = None
    payment_due_date: Optional[date] = None


class ExpenseRead(ExpenseCreate):
    id: int
    is_paid: bool = False
    paid_date: Optional[date] = None
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Document
# ---------------------------------------------------------------------------

DocumentEntityType = Literal["property", "agreement", "invoice", "expense", "vat_report"]
DocumentCategory = Literal[
    "lease_agreement",
    "lease_renewal",
    "lease_termination",
    "lease_correspondence",
    "property_tax_assessment",
    "insurance_policy",
    "invoice",
    "expense_invoice",
    "expense_sow",
    "vat_report",
    "other",
]


class DocumentCreate(BaseModel):
    display_name: str
    s3_bucket: str
    s3_key: str
    file_size_bytes: int
    mime_type: str
    related_entity_type: DocumentEntityType
    related_entity_id: int
    document_category: DocumentCategory = "other"
    uploaded_by_user_id: Optional[int] = None


class DocumentRead(DocumentCreate):
    id: int
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentDownloadResponse(BaseModel):
    url: str
    expires_in: int
