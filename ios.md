# Crassus iOS Companion App — Technical Specification

## Overview

A SwiftUI companion app for the Crassus property management platform. The app targets existing registered users only — no sign-up flow. It covers four features:

1. Mark pending invoices as paid
2. Send reminders for overdue invoices
3. Generate a new batch of invoices for a selected period
4. Scan a vendor invoice with the camera, extract fields, and post an expense

---

## Base URL

All requests go to the same backend as the web app:

```
https://<production-host>/v1
```

The base URL should be stored as a build-time constant (e.g. in `Config.swift`), with a debug override for local development (`http://localhost:8000/v1`).

---

## Authentication

### Login

**No sign-up.** The user must already have an account on the Crassus web platform.

**Endpoint**

```
POST /auth/login
Content-Type: application/json
```

**Request body**

```json
{
  "email": "user@example.com",
  "password": "••••••••",
  "mobile": true
}
```

The `mobile: true` flag issues a **120-day token** instead of the default 24-hour web token.

**Response**

```json
{
  "access_token": "<jwt>",
  "token_type": "bearer"
}
```

**Error responses**

| Status | Meaning |
|--------|---------|
| 401 | Wrong email or password |
| 403 | Account inactive |

### Token storage

Store the token in the iOS **Keychain** (not UserDefaults). Use a dedicated service key, e.g. `"crassus.accessToken"`.

### Authenticated requests

Every subsequent request must include:

```
Authorization: Bearer <token>
```

### Session expiry

If any request returns `401 Unauthorized`, clear the Keychain token and redirect the user to the login screen.

### Logout

Delete the token from the Keychain. No backend call required.

---

## Feature 1 — Mark Pending Invoice as Paid

### Step 1: Fetch invoices

```
GET /invoices
Authorization: Bearer <token>
```

**Response** — array of `Invoice` objects (see data models below). Filter client-side for `invoice_status == "pending"`.

### Step 2: Record payment

```
POST /invoices/{id}/pay
Authorization: Bearer <token>
Content-Type: application/json
```

**Request body**

```json
{
  "payment_date": "2026-06-16",
  "amount_received": "1250.00",
  "payment_method": "bank_transfer",
  "transaction_reference": "TXN-123456",
  "notes": "Optional free text"
}
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `payment_date` | `date` (ISO 8601) | Yes | |
| `amount_received` | `decimal string` | Yes | |
| `payment_method` | enum | Yes | `bank_transfer`, `stripe`, `direct_debit`, `cash`, `other` |
| `transaction_reference` | string | No | |
| `notes` | string | No | |

**Response** — updated `Invoice` object with `invoice_status: "paid"`.

**Error responses**

| Status | Meaning |
|--------|---------|
| 404 | Invoice not found |
| 422 | Invoice is not pending or overdue |

---

## Feature 2 — Send Reminder for Overdue Invoice

Filter the `/invoices` response for `invoice_status == "overdue"`. The reminder is a single API call — no PDF generation required. The backend composes and sends the full reminder email (with invoice details and bank payment information) entirely server-side.

```
POST /invoices/{id}/send-reminder
Authorization: Bearer <token>
```

No request body required.

**Response** — updated `Invoice` object with `email_delivery_status: "sent"`.

**Error responses**

| Status | Meaning |
|--------|---------|
| 404 | Invoice not found |
| 422 | Invoice is not overdue |

---

## Feature 3 — Generate a Batch of Invoices

This is a two-step flow: preview first, then confirm.

### Step 1: Preview the batch

```
POST /invoices/batch-preview
Authorization: Bearer <token>
Content-Type: application/json
```

**Request body**

```json
{
  "reference_date": "2026-06-01"
}
```

`reference_date` is optional; it defaults to today on the server. The server uses it to determine the billing period for all active agreements.

**Response** — array of `BatchPreviewRow`:

```json
[
  {
    "agreement_uuid": "abc-123",
    "unit_label": "Apt 4B",
    "lessee_name": "Jane Smith",
    "billing_period_start": "2026-06-01",
    "billing_period_end": "2026-06-30",
    "due_date": "2026-07-01",
    "net_amount": "1136.36",
    "vat_amount": "113.64",
    "gross_amount": "1250.00",
    "suggested_invoice_number": "INV-2026-0043",
    "already_invoiced": false
  }
]
```

Rows where `already_invoiced: true` should be shown as disabled / greyed out in the UI. The user should be able to deselect individual rows before confirming.

### Step 2: Confirm and generate

```
POST /invoices/batch-generate
Authorization: Bearer <token>
Content-Type: application/json
```

**Request body** — pass back only the rows the user confirmed (omit `already_invoiced` rows):

```json
{
  "items": [
    {
      "agreement_uuid": "abc-123",
      "invoice_number": "INV-2026-0043",
      "billing_period_start": "2026-06-01",
      "billing_period_end": "2026-06-30",
      "issue_date": "2026-06-16",
      "due_date": "2026-07-01",
      "net_amount": "1136.36",
      "vat_amount": "113.64",
      "gross_amount": "1250.00"
    }
  ]
}
```

**Response** — array of created `Invoice` objects (HTTP 201).

**Error responses**

| Status | Meaning |
|--------|---------|
| 422 | Validation error (e.g. gross ≠ net + VAT) |
| 409 | Duplicate invoice number |

---

## Feature 4 — Scan Vendor Invoice → Post Expense

### Step 1: Scan

Use `VNDocumentCameraViewController` (VisionKit) to present the system document scanner. The result is one or more `UIImage` pages.

### Step 2: Extract fields

Use Apple's **Vision framework** (`VNRecognizeTextRequest`) to perform on-device OCR on the scanned image. This runs fully offline with no API key or per-call cost.

```swift
let request = VNRecognizeTextRequest { request, error in
    let observations = request.results as? [VNRecognizedTextObservation] ?? []
    let lines = observations.compactMap { $0.topCandidates(1).first?.string }
    // pass lines to field extraction heuristics
}
request.recognitionLevel = .accurate
request.usesLanguageCorrection = true
try VNImageRequestHandler(cgImage: cgImage).perform([request])
```

Write lightweight heuristics over the returned text lines to extract:
- **vendor_name** — typically the first prominent text block at the top
- **invoice_reference** — lines matching patterns like `INV-`, `Ref:`, `Factuurnummer`
- **expense_date** — lines matching date formats (`dd/mm/yyyy`, `dd-mm-yyyy`, `Month dd, yyyy`)
- **gross_amount** — line labelled `Total`, `Totaal`, `Amount due` etc., largest currency value
- **vat_amount** — line labelled `VAT`, `BTW`, `TVA`
- **net_amount** — derived as `gross - vat` if not explicitly found

### Step 3: User review

Present the extracted fields in an editable form so the user can correct any mistakes before submitting. Also require the user to select:

- **Property** — fetched from `GET /properties` (see data models)
- **Category** — one of the enum values listed below

### Step 4: Post the expense

```
POST /expenses
Authorization: Bearer <token>
Content-Type: application/json
```

**Request body**

```json
{
  "property_id": 1,
  "vendor_name": "Acme Plumbing",
  "invoice_reference": "INV-2024-987",
  "expense_category": "maintenance_repairs",
  "expense_date": "2026-06-15",
  "net_amount": "500.00",
  "vat_amount": "105.00",
  "gross_amount": "605.00",
  "description": "Emergency pipe repair, unit 3A",
  "payment_due_date": "2026-07-15"
}
```

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `property_id` | int | Yes | From `GET /properties` |
| `vendor_name` | string | Yes | |
| `invoice_reference` | string | No | |
| `expense_category` | enum | Yes | See values below |
| `expense_date` | date | Yes | |
| `net_amount` | decimal string | Yes | |
| `vat_amount` | decimal string | Yes | |
| `gross_amount` | decimal string | Yes | Must equal net + vat |
| `description` | string | Yes | |
| `payment_due_date` | date | No | |

**Expense category values**

```
maintenance_repairs
insurance
property_tax
utilities
legal_professional
management_fees
cleaning_landscaping
security
capital_improvement
mortgage_interest
other
```

**Response** — created `ExpenseRead` object (HTTP 201).

**Error responses**

| Status | Meaning |
|--------|---------|
| 404 | Property not found |
| 422 | gross_amount ≠ net_amount + vat_amount, or missing required fields |

---

## Supporting Endpoint — List Properties

Required for the expense property picker (Feature 4).

```
GET /properties
Authorization: Bearer <token>
```

**Response** — array of `Property` objects:

```json
[
  {
    "id": 1,
    "name": "Riverside Apartments",
    "address_line1": "12 River Street",
    "address_line2": null,
    "city": "Amsterdam",
    "postal_code": "1011 AB",
    "country": "NL"
  }
]
```

---

## Data Models

### Invoice

```json
{
  "id": 42,
  "invoice_number": "INV-2026-0042",
  "agreement_uuid": "abc-123",
  "invoice_type": "standard",
  "billing_period_start": "2026-06-01",
  "billing_period_end": "2026-06-30",
  "issue_date": "2026-06-01",
  "due_date": "2026-07-01",
  "net_amount": "1136.36",
  "vat_amount": "113.64",
  "gross_amount": "1250.00",
  "invoice_status": "pending",
  "email_delivery_status": "delivered",
  "resend_email_id": "re_abc123",
  "pdf_s3_key": "orgs/1/invoices/42.pdf",
  "unit_number": "4B",
  "created_at": "2026-06-01T08:00:00Z"
}
```

**`invoice_status` values:** `draft`, `pending`, `paid`, `overdue`, `credited`

**`email_delivery_status` values:** `unsent`, `sent`, `delivered`, `opened`, `bounced`

**`invoice_type` values:** `standard`, `credit_note`

### Expense

```json
{
  "id": 7,
  "property_id": 1,
  "vendor_name": "Acme Plumbing",
  "invoice_reference": "INV-2024-987",
  "expense_category": "maintenance_repairs",
  "expense_date": "2026-06-15",
  "net_amount": "500.00",
  "vat_amount": "105.00",
  "gross_amount": "605.00",
  "description": "Emergency pipe repair, unit 3A",
  "payment_due_date": "2026-07-15",
  "is_paid": false,
  "paid_date": null,
  "created_at": "2026-06-15T10:30:00Z"
}
```

### BatchPreviewRow

```json
{
  "agreement_uuid": "abc-123",
  "unit_label": "Apt 4B",
  "lessee_name": "Jane Smith",
  "billing_period_start": "2026-06-01",
  "billing_period_end": "2026-06-30",
  "due_date": "2026-07-01",
  "net_amount": "1136.36",
  "vat_amount": "113.64",
  "gross_amount": "1250.00",
  "suggested_invoice_number": "INV-2026-0043",
  "already_invoiced": false
}
```

---

## Required iOS Permissions

| Permission | Usage |
|------------|-------|
| `NSCameraUsageDescription` | Document scanning for expense invoices |
| Keychain access | Token storage (no additional entitlement needed for app's own Keychain) |

No location, contacts, or photo library access required.

---

## Roles & Authorisation

The JWT encodes the user's role. The backend enforces it server-side, but the app should reflect it in the UI:

| Role | Can mark paid | Can send reminder | Can batch generate | Can post expense |
|------|--------------|-------------------|--------------------|-----------------|
| `owner` | Yes | Yes | Yes | Yes |
| `editor` | Yes | Yes | Yes | Yes |
| `viewer` | No | No | No | No |

For a `viewer` role, disable or hide all write actions. The JWT payload can be decoded client-side (it is a standard Base64-encoded JSON structure — no signature verification needed client-side) to read the `role` field.

---

## Suggested App Structure

```
CrassusApp/
├── Config.swift                  # Base URL, Keychain key constants
├── Network/
│   ├── APIClient.swift           # URLSession wrapper, injects Bearer token
│   └── Models/                   # Codable structs matching data models above
│       ├── Invoice.swift
│       ├── Expense.swift
│       ├── Property.swift
│       └── BatchPreview.swift
├── Auth/
│   ├── KeychainService.swift
│   ├── AuthViewModel.swift
│   └── LoginView.swift
├── Invoices/
│   ├── InvoiceListView.swift     # Pending + overdue tabs
│   ├── MarkPaidView.swift
│   └── ReminderView.swift
├── Batch/
│   ├── BatchPreviewView.swift
│   └── BatchConfirmView.swift
└── Expenses/
    ├── ScanView.swift            # VNDocumentCameraViewController wrapper
    ├── ExpenseReviewView.swift   # Editable extracted fields
    └── ExpenseViewModel.swift    # Claude API call + POST /expenses
```

---

## Open Questions for Review

1. **Batch invoice send** — after generating a batch, should the app immediately offer to send all invoices by email, or is that a separate action taken later in the web app?
