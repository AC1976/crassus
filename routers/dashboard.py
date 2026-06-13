from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import extract, func
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from models import Expense, Invoice, Lessee, Payment, Property, RentalAgreement, Settings, Unit, User
from routers.invoices import _mark_overdue

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class StatCards(BaseModel):
    invoices_pending: int
    invoices_overdue: int
    outstanding_balance: Decimal
    occupancy_rate: float          # 0–100 %


class BillingCycleForecast(BaseModel):
    net_amount: Decimal
    vat_amount: Decimal
    gross_amount: Decimal
    invoice_count: int


class YtdCollection(BaseModel):
    invoiced_gross: Decimal
    collected: Decimal
    collection_rate: float         # 0–100 %


class LeaseExpiryRow(BaseModel):
    agreement_uuid: str
    property_name: str
    unit_number: str
    lessee_name: str
    lease_end: date
    days_to_expiry: int
    notification_deadline: date
    days_to_notification: int      # negative = already missed


class PaymentPerformancePoint(BaseModel):
    invoice_number: str
    billing_period_start: date
    billing_period_end: date
    due_date: date
    gross_amount: Decimal
    # Payment details — None if unpaid
    paid_date: Optional[date]
    days_delta: Optional[int]           # negative = early, positive = late, None = unpaid
    payment_method: Optional[str]
    amount_received: Optional[Decimal]
    transaction_reference: Optional[str]
    notes: Optional[str]


class PropertyPerformance(BaseModel):
    property_id: int
    property_name: str
    unit_number: str
    lessee_name: str
    agreement_uuid: str
    points: List[PaymentPerformancePoint]


class OpenExpenseStats(BaseModel):
    open_count: int
    open_total: Decimal          # gross sum of unpaid expenses
    overdue_count: int           # unpaid and past payment_due_date
    overdue_total: Decimal


class IndexationRow(BaseModel):
    agreement_uuid: str
    property_name: str
    unit_number: str
    lessee_name: str
    indexation_date: date        # the stored month/day anchor
    next_indexation: date        # next upcoming anniversary
    days_until: int              # 0 = today, negative = already passed this year
    base_rent_amount: Decimal
    currency: str


class DashboardResponse(BaseModel):
    stats: StatCards
    billing_forecast: BillingCycleForecast
    ytd_collection: YtdCollection
    lease_expiries: List[LeaseExpiryRow]       # agreements expiring within 365 days
    payment_performance: List[PropertyPerformance]
    open_expenses: OpenExpenseStats
    indexations: List[IndexationRow]           # active leases with an indexation date


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _lessee_display(l: Lessee) -> str:
    if l.company_legal_name:
        return l.company_legal_name
    return " ".join(filter(None, [l.first_name, l.last_name])) or l.email


def _next_indexation(anchor: date, today: date) -> date:
    """Return the next occurrence of the anchor's month/day on or after today."""
    candidate = anchor.replace(year=today.year)
    if candidate < today:
        # Handle Feb 29 anchors in non-leap years gracefully
        try:
            candidate = anchor.replace(year=today.year + 1)
        except ValueError:
            candidate = date(today.year + 1, anchor.month, 28)
    return candidate


def _next_period_end(start: date, interval: str) -> date:
    """Return the last day of the billing period that starts on `start`."""
    import calendar
    if interval == "monthly":
        if start.month == 12:
            end = date(start.year + 1, 1, 1) - timedelta(days=1)
        else:
            end = date(start.year, start.month + 1, 1) - timedelta(days=1)
    elif interval == "quarterly":
        month = start.month + 3
        year = start.year + (month - 1) // 12
        month = (month - 1) % 12 + 1
        end = date(year, month, 1) - timedelta(days=1)
    else:  # annually
        end = date(start.year + 1, start.month, start.day) - timedelta(days=1)
    return end


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.get("", response_model=DashboardResponse)
def get_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> DashboardResponse:
    org_id = current_user.org_id
    today = date.today()

    # Auto-flip pending invoices past their due date to overdue
    _mark_overdue(db, org_id)

    # Org settings (for notice days)
    org_settings = db.query(Settings).filter(Settings.org_id == org_id).first()
    notice_days = org_settings.lease_termination_notice_days if org_settings else 365

    # ── Stat cards ────────────────────────────────────────────────────────────

    pending_count = (
        db.query(func.count(Invoice.id))
        .filter(Invoice.org_id == org_id, Invoice.invoice_status == "pending")
        .scalar() or 0
    )
    overdue_count = (
        db.query(func.count(Invoice.id))
        .filter(Invoice.org_id == org_id, Invoice.invoice_status == "overdue")
        .scalar() or 0
    )
    outstanding_balance = (
        db.query(func.coalesce(func.sum(Invoice.gross_amount), 0))
        .filter(Invoice.org_id == org_id, Invoice.invoice_status.in_(["pending", "overdue"]))
        .scalar() or Decimal("0")
    )

    # Occupancy: active agreements / (units + unit-less properties)
    # A property with no units counts as 1 leasable slot.
    total_units = (
        db.query(func.count(Unit.id))
        .join(Property, Property.id == Unit.property_id)
        .filter(Property.org_id == org_id)
        .scalar() or 0
    )
    props_without_units = (
        db.query(func.count(Property.id))
        .filter(
            Property.org_id == org_id,
            ~db.query(Unit.id).filter(Unit.property_id == Property.id).exists(),
        )
        .scalar() or 0
    )
    total_leasable = total_units + props_without_units or 1
    now_dt = datetime.combine(today, datetime.min.time())
    occupied_units = (
        db.query(func.count(RentalAgreement.id))
        .filter(
            RentalAgreement.org_id == org_id,
            RentalAgreement.valid_time_start <= now_dt,
            RentalAgreement.valid_time_end >= now_dt,
        )
        .scalar() or 0
    )
    occupancy_rate = round((occupied_units / total_leasable * 100), 1)

    stats = StatCards(
        invoices_pending=pending_count,
        invoices_overdue=overdue_count,
        outstanding_balance=Decimal(str(outstanding_balance)),
        occupancy_rate=occupancy_rate,
    )

    # ── Billing cycle forecast (next calendar month) ──────────────────────────

    if today.month == 12:
        next_month_start = date(today.year + 1, 1, 1)
    else:
        next_month_start = date(today.year, today.month + 1, 1)

    active_agreements = (
        db.query(RentalAgreement)
        .filter(
            RentalAgreement.org_id == org_id,
            RentalAgreement.valid_time_start <= datetime.combine(next_month_start, datetime.min.time()),
            RentalAgreement.valid_time_end >= datetime.combine(next_month_start, datetime.min.time()),
        )
        .all()
    )

    forecast_net = Decimal("0")
    forecast_vat = Decimal("0")
    for ag in active_agreements:
        net = Decimal(str(ag.base_rent_amount)) + Decimal(str(ag.service_charges))
        vat = (net * Decimal(str(ag.vat_rate_applied)) / 100).quantize(Decimal("0.01"))
        forecast_net += net
        forecast_vat += vat

    billing_forecast = BillingCycleForecast(
        net_amount=forecast_net,
        vat_amount=forecast_vat,
        gross_amount=forecast_net + forecast_vat,
        invoice_count=len(active_agreements),
    )

    # ── YTD collection ────────────────────────────────────────────────────────

    ytd_invoiced = (
        db.query(func.coalesce(func.sum(Invoice.gross_amount), 0))
        .filter(
            Invoice.org_id == org_id,
            Invoice.invoice_type == "standard",
            extract("year", Invoice.issue_date) == today.year,
        )
        .scalar() or Decimal("0")
    )
    ytd_collected = (
        db.query(func.coalesce(func.sum(Payment.amount_received), 0))
        .filter(
            Payment.org_id == org_id,
            extract("year", Payment.payment_date) == today.year,
        )
        .scalar() or Decimal("0")
    )
    ytd_invoiced_d = Decimal(str(ytd_invoiced))
    ytd_collected_d = Decimal(str(ytd_collected))
    collection_rate = round(
        float(ytd_collected_d / ytd_invoiced_d * 100) if ytd_invoiced_d else 0.0, 1
    )

    ytd_collection = YtdCollection(
        invoiced_gross=ytd_invoiced_d,
        collected=ytd_collected_d,
        collection_rate=collection_rate,
    )

    # ── Lease expiries (within next 365 days) ─────────────────────────────────

    window_end = today + timedelta(days=365)
    window_end_dt = datetime.combine(window_end, datetime.min.time())
    today_dt = datetime.combine(today, datetime.min.time())

    expiring = (
        db.query(RentalAgreement)
        .filter(
            RentalAgreement.org_id == org_id,
            RentalAgreement.valid_time_end >= today_dt,
            RentalAgreement.valid_time_end <= window_end_dt,
        )
        .order_by(RentalAgreement.valid_time_end)
        .all()
    )

    lease_expiries: List[LeaseExpiryRow] = []
    for ag in expiring:
        unit = db.query(Unit).filter(Unit.id == ag.unit_id).first() if ag.unit_id else None
        prop_id = unit.property_id if unit else ag.property_id
        prop = db.query(Property).filter(Property.id == prop_id).first() if prop_id else None
        lessee = db.query(Lessee).filter(Lessee.lessee_uuid == ag.lessee_uuid).first()
        if not prop or not lessee:
            continue
        lease_end = ag.valid_time_end.date()
        notification_deadline = lease_end - timedelta(days=notice_days)
        lease_expiries.append(LeaseExpiryRow(
            agreement_uuid=ag.agreement_uuid,
            property_name=prop.name,
            unit_number=unit.unit_number if unit else "—",
            lessee_name=_lessee_display(lessee),
            lease_end=lease_end,
            days_to_expiry=(lease_end - today).days,
            notification_deadline=notification_deadline,
            days_to_notification=(notification_deadline - today).days,
        ))

    # ── Payment performance (last 12 paid invoices per active agreement) ──────

    payment_performance: List[PropertyPerformance] = []

    for ag in (
        db.query(RentalAgreement)
        .filter(
            RentalAgreement.org_id == org_id,
            RentalAgreement.valid_time_start <= now_dt,
            RentalAgreement.valid_time_end >= now_dt,
        )
        .all()
    ):
        unit = db.query(Unit).filter(Unit.id == ag.unit_id).first() if ag.unit_id else None
        prop_id = unit.property_id if unit else ag.property_id
        prop = db.query(Property).filter(Property.id == prop_id).first() if prop_id else None
        lessee = db.query(Lessee).filter(Lessee.lessee_uuid == ag.lessee_uuid).first()
        if not prop or not lessee:
            continue

        invoices = (
            db.query(Invoice)
            .filter(
                Invoice.org_id == org_id,
                Invoice.agreement_uuid == ag.agreement_uuid,
                Invoice.invoice_type == "standard",
            )
            .order_by(Invoice.billing_period_start.desc())
            .limit(24)
            .all()
        )

        points: List[PaymentPerformancePoint] = []
        for inv in reversed(invoices):  # restore chronological order for the chart
            payment = (
                db.query(Payment)
                .filter(Payment.invoice_id == inv.id)
                .order_by(Payment.payment_date)
                .first()
            )
            paid_date = payment.payment_date.date() if payment else None
            days_delta = (paid_date - inv.due_date).days if paid_date else None
            points.append(PaymentPerformancePoint(
                invoice_number=inv.invoice_number,
                billing_period_start=inv.billing_period_start,
                billing_period_end=inv.billing_period_end,
                due_date=inv.due_date,
                gross_amount=inv.gross_amount,
                paid_date=paid_date,
                days_delta=days_delta,
                payment_method=payment.payment_method if payment else None,
                amount_received=payment.amount_received if payment else None,
                transaction_reference=payment.transaction_reference if payment else None,
                notes=payment.notes if payment else None,
            ))

        if points:
            payment_performance.append(PropertyPerformance(
                property_id=prop.id,
                property_name=prop.name,
                unit_number=unit.unit_number if unit else "—",
                lessee_name=_lessee_display(lessee),
                agreement_uuid=ag.agreement_uuid,
                points=points,
            ))

    # ── Open expenses ─────────────────────────────────────────────────────────

    open_expense_rows = (
        db.query(Expense)
        .filter(Expense.org_id == org_id, Expense.is_paid == False)  # noqa: E712
        .all()
    )
    open_count = len(open_expense_rows)
    open_total = sum((Decimal(str(e.gross_amount)) for e in open_expense_rows), Decimal("0"))
    overdue_rows = [
        e for e in open_expense_rows
        if e.payment_due_date is not None and e.payment_due_date < today
    ]
    overdue_count = len(overdue_rows)
    overdue_total = sum((Decimal(str(e.gross_amount)) for e in overdue_rows), Decimal("0"))

    open_expenses = OpenExpenseStats(
        open_count=open_count,
        open_total=open_total,
        overdue_count=overdue_count,
        overdue_total=overdue_total,
    )

    # ── Indexation schedule ───────────────────────────────────────────────────

    active_for_indexation = (
        db.query(RentalAgreement)
        .filter(
            RentalAgreement.org_id == org_id,
            RentalAgreement.valid_time_start <= now_dt,
            RentalAgreement.valid_time_end >= now_dt,
            RentalAgreement.indexation_date.isnot(None),
        )
        .all()
    )

    indexations: List[IndexationRow] = []
    for ag in active_for_indexation:
        unit = db.query(Unit).filter(Unit.id == ag.unit_id).first() if ag.unit_id else None
        prop_id = unit.property_id if unit else ag.property_id
        prop = db.query(Property).filter(Property.id == prop_id).first() if prop_id else None
        lessee = db.query(Lessee).filter(Lessee.lessee_uuid == ag.lessee_uuid).first()
        if not prop or not lessee:
            continue
        next_idx = _next_indexation(ag.indexation_date, today)
        # Skip if the index was already applied within the last ~335 days
        # relative to the next upcoming date — avoids re-showing right after applying
        if ag.indexation_last_applied and next_idx <= ag.indexation_last_applied + timedelta(days=335):
            continue
        indexations.append(IndexationRow(
            agreement_uuid=ag.agreement_uuid,
            property_name=prop.name,
            unit_number=unit.unit_number if unit else "—",
            lessee_name=_lessee_display(lessee),
            indexation_date=ag.indexation_date,
            next_indexation=next_idx,
            days_until=(next_idx - today).days,
            base_rent_amount=Decimal(str(ag.base_rent_amount)),
            currency=org_settings.currency if org_settings else "EUR",
        ))

    indexations.sort(key=lambda r: r.days_until)

    return DashboardResponse(
        stats=stats,
        billing_forecast=billing_forecast,
        ytd_collection=ytd_collection,
        lease_expiries=lease_expiries,
        payment_performance=payment_performance,
        open_expenses=open_expenses,
        indexations=indexations,
    )
