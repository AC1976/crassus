"""
Invoice / email translation strings.

Usage:
    from i18n import get_translations
    t = get_translations(lang)   # lang = "en" | "nl"
    t["invoice_heading"]         # -> "INVOICE" or "FACTUUR"
"""

from typing import Literal

InvoiceLang = Literal["en", "nl"]

_TRANSLATIONS: dict[str, dict[str, str]] = {
    "en": {
        # ── PDF: header meta labels ──────────────────────────────────────────
        "invoice_heading":          "INVOICE",
        "credit_note_heading":      "CREDIT NOTE",
        "invoice_no_label":         "Invoice No.",
        "issue_date_label":         "Issue Date",
        "due_date_label":           "Due Date",
        # ── PDF: company block ───────────────────────────────────────────────
        "vat_company_label":        "VAT:",
        # ── PDF: bill-to block ───────────────────────────────────────────────
        "bill_to_label":            "Bill To",
        "vat_reg_label":            "VAT Reg. No:",
        # ── PDF: line-items table ────────────────────────────────────────────
        "col_description":          "Description",
        "col_period":               "Rental Period",
        "col_net":                  "Net",
        "col_vat":                  "VAT",
        "col_total":                "Total",
        "rental_label":             "Rental",
        "period_to":                "to",
        # ── PDF: totals block ────────────────────────────────────────────────
        "net_total_label":          "Net Total",
        "vat_label":                "VAT",
        "total_due_label":          "Total Due",
        "total_credit_label":       "Total Credit",
        # ── PDF: payment footer (invoice) ────────────────────────────────────
        "payment_please_transfer":  "Please transfer",
        "payment_by":               "by",
        "bank_account_label":       "Bank account:",
        "payment_reference_label":  "Always quote reference:",
        # ── PDF: credit-note footer ──────────────────────────────────────────
        "credit_amount_prefix":     "The amount of",
        "credit_amount_suffix":     "will be credited to your bank account.",
        "credits_invoice_prefix":   "This credits the original invoice with reference",
        # ── Email: subjects ──────────────────────────────────────────────────
        "email_subject_invoice":    "Invoice Rent {period} for {property} from {company}",
        "email_subject_reminder":   "Payment Reminder: Rent {period} for {property} from {company}",
        # ── Email: body ──────────────────────────────────────────────────────
        "email_greeting":           "Dear {name},",
        "email_intro_invoice":      (
            "Please find attached your invoice for the rental period "
            "<strong>{start} – {end}</strong>. "
            "A summary is included below for your reference."
        ),
        "email_intro_reminder":     (
            "We hope this note finds you well. We wanted to gently follow up on invoice "
            "<strong>{number}</strong>, which was due on <strong>{date}</strong> and remains "
            "outstanding. Please find the invoice attached once more for your convenience."
        ),
        "email_due_label":          "Payment due",
        "email_overdue_label":      "Payment overdue",
        # ── Email: summary table labels ──────────────────────────────────────
        "email_invoice_no":         "Invoice no.",
        "email_period":             "Period",
        "email_description":        "Description",
        "email_net":                "Net",
        "email_vat_prefix":         "VAT",
        "email_total_due":          "Total due",
        # ── Email: payment block ─────────────────────────────────────────────
        "email_payment_details":    "Payment details",
        "email_bank_account":       "Bank account:",
        "email_reference":          "Reference:",
        # ── Email: closing ───────────────────────────────────────────────────
        "email_closing":            (
            "If you have any questions about this invoice, please don’t hesitate to "
            "reply to this email. We appreciate your prompt payment."
        ),
        "email_kind_regards":       "Kind regards,",
        # ── Plain-text fallback labels ───────────────────────────────────────
        "plain_invoice_no":         "Invoice no.:",
        "plain_period":             "Period:     ",
        "plain_net":                "Net:        ",
        "plain_vat_prefix":         "VAT",
        "plain_total_due":          "Total due:  ",
        "plain_due_date":           "Due date:   ",
        "plain_bank":               "Bank account:",
        "plain_reference":          "Reference:",
        # ── Indexation notification email ────────────────────────────────────
        "idx_subject":              "Notice of Rent Indexation — {property}",
        "idx_intro":                (
            "We hereby inform you that the rent for your rental at "
            "<strong>{property}</strong> has been indexed with effect from "
            "<strong>{effective_date}</strong>."
        ),
        "idx_index_applied":        "Index applied",
        "idx_old_rent":             "Previous rent (excl. VAT)",
        "idx_new_rent":             "New rent (excl. VAT)",
        "idx_effective_date":       "Effective from",
        "idx_closing":              (
            "If you have any questions about this rent adjustment, "
            "please don't hesitate to reply to this email."
        ),
        "plain_idx_intro":          "Notice of rent indexation for {property}.",
        "plain_idx_index":          "Index applied:          {index}",
        "plain_idx_old_rent":       "Previous rent (ex VAT): {old_rent}",
        "plain_idx_new_rent":       "New rent (ex VAT):      {new_rent}",
        "plain_idx_effective":      "Effective from:         {date}",
        # ── VAT report email ─────────────────────────────────────────────────
        "vat_email_salutation":     "Dear Sir / Madam,",
        "vat_email_intro":          (
            "Please find attached the VAT report for <strong>{company}</strong> "
            "(VAT ID: <strong>{vat_id}</strong>) covering the period "
            "<strong>{period_start}</strong> to <strong>{period_end}</strong>."
        ),
        "vat_email_request":        (
            "We kindly request you to file the VAT return on the basis of the figures "
            "below. The full detail is provided in the attached Excel report."
        ),
        "vat_email_col_position":   "VAT Position",
        "vat_email_col_amount":     "Amount",
        "vat_email_row_inv_net":    "Invoice revenue (net)",
        "vat_email_row_inv_vat":    "VAT collected on invoices",
        "vat_email_row_exp_net":    "Deductible expenses (net)",
        "vat_email_row_exp_vat":    "VAT reclaimable on expenses",
        "vat_email_row_vat_due":    "Net VAT due / (refundable)",
        "vat_email_closing":        (
            "Please do not hesitate to reply to this email if you have any questions."
        ),
    },

    "nl": {
        # ── PDF: header meta labels ──────────────────────────────────────────
        "invoice_heading":          "FACTUUR",
        "credit_note_heading":      "CREDITNOTA",
        "invoice_no_label":         "Factuurnummer",
        "issue_date_label":         "Factuurdatum",
        "due_date_label":           "Vervaldatum",
        # ── PDF: company block ───────────────────────────────────────────────
        "vat_company_label":        "BTW:",
        # ── PDF: bill-to block ───────────────────────────────────────────────
        "bill_to_label":            "Factuuradres",
        "vat_reg_label":            "BTW-nummer:",
        # ── PDF: line-items table ────────────────────────────────────────────
        "col_description":          "Omschrijving",
        "col_period":               "Huurperiode",
        "col_net":                  "Netto",
        "col_vat":                  "BTW",
        "col_total":                "Totaal",
        "rental_label":             "Huur",
        "period_to":                "t/m",
        # ── PDF: totals block ────────────────────────────────────────────────
        "net_total_label":          "Netto totaal",
        "vat_label":                "BTW",
        "total_due_label":          "Totaal te betalen",
        "total_credit_label":       "Totaal credit",
        # ── PDF: payment footer (invoice) ────────────────────────────────────
        "payment_please_transfer":  "Gelieve",
        "payment_by":               "te betalen vóór",
        "bank_account_label":       "Rekeningnummer:",
        "payment_reference_label":  "Vermeld altijd betalingsreferentie:",
        # ── PDF: credit-note footer ──────────────────────────────────────────
        "credit_amount_prefix":     "Het bedrag van",
        "credit_amount_suffix":     "wordt gecrediteerd op uw rekening.",
        "credits_invoice_prefix":   "Dit crediteert de originele factuur met referentie",
        # ── Email: subjects ──────────────────────────────────────────────────
        "email_subject_invoice":    "Factuur Huur {period} voor {property} van {company}",
        "email_subject_reminder":   "Betalingsherinnering: Huur {period} voor {property} van {company}",
        # ── Email: body ──────────────────────────────────────────────────────
        "email_greeting":           "Beste {name},",
        "email_intro_invoice":      (
            "Bijgevoegd vindt u uw factuur voor de huurperiode "
            "<strong>{start} – {end}</strong>. "
            "Hieronder vindt u een overzicht ter referentie."
        ),
        "email_intro_reminder":     (
            "Wij hopen dat u dit bericht in goede gezondheid ontvangt. Wij herinneren u vriendelijk "
            "aan factuur <strong>{number}</strong> die op <strong>{date}</strong> betaald "
            "had moeten worden maar nog openstaat. Bijgevoegd vindt u de factuur nogmaals "
            "voor uw gemak."
        ),
        "email_due_label":          "Betaaldatum",
        "email_overdue_label":      "Betaling achterstallig",
        # ── Email: summary table labels ──────────────────────────────────────
        "email_invoice_no":         "Factuurnummer",
        "email_period":             "Periode",
        "email_description":        "Omschrijving",
        "email_net":                "Netto",
        "email_vat_prefix":         "BTW",
        "email_total_due":          "Totaal te betalen",
        # ── Email: payment block ─────────────────────────────────────────────
        "email_payment_details":    "Betalingsgegevens",
        "email_bank_account":       "Rekeningnummer:",
        "email_reference":          "Referentie:",
        # ── Email: closing ───────────────────────────────────────────────────
        "email_closing":            (
            "Heeft u vragen over deze factuur, aarzel dan niet om op dit e-mailadres te "
            "regeren. Wij waarderen uw snelle betaling."
        ),
        "email_kind_regards":       "Met vriendelijke groet,",
        # ── Plain-text fallback labels ───────────────────────────────────────
        "plain_invoice_no":         "Factuurnummer:",
        "plain_period":             "Periode:    ",
        "plain_net":                "Netto:      ",
        "plain_vat_prefix":         "BTW",
        "plain_total_due":          "Totaal:     ",
        "plain_due_date":           "Vervaldatum:",
        "plain_bank":               "Rekeningnummer:",
        "plain_reference":          "Referentie:",
        # ── Indexation notification email ────────────────────────────────────
        "idx_subject":              "Kennisgeving huurindexatie — {property}",
        "idx_intro":                (
            "Hierbij informeren wij u dat de huurprijs voor uw huurobject "
            "<strong>{property}</strong> met ingang van "
            "<strong>{effective_date}</strong> is geïndexeerd."
        ),
        "idx_index_applied":        "Toegepaste index",
        "idx_old_rent":             "Vorige huurprijs (excl. BTW)",
        "idx_new_rent":             "Nieuwe huurprijs (excl. BTW)",
        "idx_effective_date":       "Ingangsdatum",
        "idx_closing":              (
            "Heeft u vragen over deze huurindexatie, "
            "aarzel dan niet om op dit e-mailadres te antwoorden."
        ),
        "plain_idx_intro":          "Kennisgeving huurindexatie voor {property}.",
        "plain_idx_index":          "Toegepaste index:           {index}",
        "plain_idx_old_rent":       "Vorige huurprijs (ex BTW):  {old_rent}",
        "plain_idx_new_rent":       "Nieuwe huurprijs (ex BTW):  {new_rent}",
        "plain_idx_effective":      "Ingangsdatum:               {date}",
        # ── VAT report email ─────────────────────────────────────────────────
        "vat_email_salutation":     "Geachte heer / mevrouw,",
        "vat_email_intro":          (
            "Hierbij ontvangt u het btw-rapport van <strong>{company}</strong> "
            "(btw-nummer: <strong>{vat_id}</strong>) over de periode "
            "<strong>{period_start}</strong> tot en met <strong>{period_end}</strong>."
        ),
        "vat_email_request":        (
            "Wij verzoeken u vriendelijk de btw-aangifte in te dienen op basis van de "
            "onderstaande cijfers. De volledige specificatie vindt u in het bijgevoegde "
            "Excel-rapport."
        ),
        "vat_email_col_position":   "Btw-positie",
        "vat_email_col_amount":     "Bedrag",
        "vat_email_row_inv_net":    "Factuuropbrengst (netto)",
        "vat_email_row_inv_vat":    "Btw geheven op facturen",
        "vat_email_row_exp_net":    "Aftrekbare kosten (netto)",
        "vat_email_row_exp_vat":    "Terugvorderbare btw op kosten",
        "vat_email_row_vat_due":    "Netto btw verschuldigd / (terug te vorderen)",
        "vat_email_closing":        (
            "Voor vragen kunt u altijd reageren op dit e-mailbericht."
        ),
    },
}


def get_translations(lang: str) -> dict[str, str]:
    """Return the translation dict for *lang*, falling back to English."""
    return _TRANSLATIONS.get(lang, _TRANSLATIONS["en"])
