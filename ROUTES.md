# Crassus — Backend Route Reference

All routes are prefixed with `/v1`. Auth uses Bearer JWT tokens unless noted as public.

**Role hierarchy:** `owner` > `editor` > `viewer`
- Read endpoints: any authenticated user
- Write/create/update: `owner` or `editor`
- Delete and sensitive operations: `owner` only
- Admin endpoints: platform admins only (`is_admin` flag or `ADMIN_EMAILS` config)

---

## Auth `/v1/auth`

### `POST /auth/register` — public
Creates a new organisation and its first user (role: `owner`).
- Checks for duplicate email globally.
- Creates an `Organisation` row, then the `User` row scoped to it.
- Returns a JWT access token immediately (no email verification).

### `POST /auth/login` — public
Validates email + password. Checks `is_active`. Returns a JWT.

### `POST /auth/forgot-password` — public
Sends a password-reset email via Resend. Always returns 204 regardless of whether the email exists (prevents user enumeration). The reset link embeds a short-lived JWT (60 min, type `password_reset`).

### `POST /auth/reset-password` — public
Validates the reset token (type, expiry, signature). Sets a new hashed password. Rejects passwords under 8 characters.

### `GET /auth/me` — authenticated
Returns the current user's profile plus their organisation name.

### `POST /auth/invite` — owner only
Invites a new team member by email. Checks for duplicate active users and pending unexpired invites. Creates an `Invitation` row with a 72-hour expiry token. Sends an invite email via Resend with an accept link (`APP_BASE_URL/accept-invite?token=...`).

### `POST /auth/accept-invite` — public
Validates the invite token (not expired, not yet accepted). Creates a new `User` scoped to the inviting org with the role assigned in the invite. Marks the invite as accepted. Returns a JWT.

### `GET /auth/team` — authenticated
Lists all users in the caller's organisation.

### `PATCH /auth/team/{user_id}/role` — owner only
Changes a team member's role to `editor` or `viewer`. Cannot change the owner's role or your own role.

### `DELETE /auth/team/{user_id}` — owner only
Removes a team member. Cannot remove the owner or yourself.

### `GET /auth/invitations` — owner only
Lists all pending (not accepted, not expired) invitations for the org.

### `DELETE /auth/invitations/{invite_id}` — owner only
Cancels (deletes) a pending invitation.

---

## Dashboard `/v1/dashboard`

### `GET /dashboard` — authenticated
Single endpoint returning a comprehensive dashboard payload. Triggers `_mark_overdue` to flip pending invoices past their due date to overdue before computing stats. Returns:

- **stats** — pending invoice count, overdue count, total outstanding balance, occupancy rate (active agreements / total leasable slots).
- **billing_forecast** — net + VAT + gross forecast for the next calendar month, based on active agreements that overlap the first day of next month.
- **ytd_collection** — year-to-date gross invoiced vs. collected, and a collection rate %.
- **lease_expiries** — all agreements whose `valid_time_end` falls within the next 365 days, with days-to-expiry and notification deadline (based on `lease_termination_notice_days` from Settings).
- **payment_performance** — for each currently active agreement: the last 24 standard invoices in chronological order, each with payment details and a `days_delta` (negative = paid early, positive = paid late, null = unpaid).
- **open_expenses** — count and gross total of unpaid expenses; subset of those that are also past their `payment_due_date`.
- **indexations** — active agreements with an `indexation_date` set, showing next upcoming anniversary, days until it, and current rent. Suppressed for 335 days after `indexation_last_applied` to avoid re-showing immediately after applying.

---

## Properties `/v1/properties`

### `GET /properties` — authenticated
Lists all properties for the org.

### `GET /properties/{property_id}` — authenticated
Returns a single property (404 if not found or wrong org).

### `POST /properties` — owner/editor
Creates a new property.

### `PATCH /properties/{property_id}` — owner/editor
Partial update of a property (only fields provided are changed).

### `DELETE /properties/{property_id}` — owner only
Deletes a property.

---

## Units `/v1/units`

### `GET /units?property_id=` — authenticated
Lists units for the org. Optional `property_id` filter.

### `GET /units/{unit_id}` — authenticated
Returns a single unit.

### `POST /units` — owner/editor
Creates a unit. Validates that the parent `property_id` belongs to the org, and if `unit_id` is provided on the agreement, that it belongs to the property.

### `PATCH /units/{unit_id}` — owner/editor
Partial update of a unit.

### `DELETE /units/{unit_id}` — owner only
Deletes a unit.

---

## Lessees `/v1/lessees`

### `GET /lessees` — authenticated
Lists all lessees for the org.

### `GET /lessees/{lessee_id}` — authenticated
Returns a single lessee.

### `POST /lessees` — owner/editor
Creates a lessee. A lessee can be a natural person (first/last name) or a company (`company_legal_name`).

### `PATCH /lessees/{lessee_id}` — owner/editor
Partial update of a lessee.

### `DELETE /lessees/{lessee_id}` — owner only
Deletes a lessee.

---

## Rental Agreements `/v1/rental-agreements`

### `GET /rental-agreements` — authenticated
Lists all rental agreements for the org.

### `GET /rental-agreements/{agreement_id}` — authenticated
Returns a single agreement.

### `POST /rental-agreements` — owner/editor
Creates a rental agreement. Validates:
- `property_id` belongs to the org.
- If `unit_id` is provided, it belongs to the org and to the given property.
- `lessee_uuid` belongs to the org.
Assigns a new `agreement_uuid` (UUID4).

### `PATCH /rental-agreements/{agreement_id}` — owner/editor
Partial update of an agreement.

### `DELETE /rental-agreements/{agreement_id}` — owner only
Deletes an agreement.

### `POST /rental-agreements/{agreement_uuid}/apply-index` — owner/editor
Applies a rent indexation to an agreement. Accepts either:
- `index_numerator` + `index_denominator` (e.g. new index / old index), or
- `index_percentage` (e.g. 2.5 for 2.5%).

Computes the new `base_rent_amount`, saves it, and records `indexation_last_applied = effective_date` (used by the dashboard to suppress the indexation reminder for ~335 days). Optionally sends an i18n-formatted notification email to the lessee via Resend. Email errors are caught and logged without failing the request.

---

## Invoices `/v1/invoices`

### `GET /invoices?invoice_status=&property_id=` — authenticated
Lists invoices for the org, ordered by issue date descending. Triggers `_mark_overdue` on every call. Optional filters:
- `invoice_status` — pending, overdue, paid, credited.
- `property_id` — joins through RentalAgreement → Unit → Property (handles both unit-level and property-level agreements).
Enriches each invoice with `unit_number` via agreement → unit lookup.

### `GET /invoices/{invoice_id}` — authenticated
Returns a single invoice.

### `POST /invoices` — owner/editor
Creates a single invoice manually. Validates:
- `agreement_uuid` belongs to the org.
- If `parent_invoice_id` is set, it must be a `standard` invoice (for credit notes only).
- `invoice_number` must be unique within the org.

### `PATCH /invoices/{invoice_id}` — owner/editor
Partial update of an invoice.

### `GET /invoices/check-period?agreement_uuid=&billing_period_start=&billing_period_end=` — authenticated
Checks whether a standard invoice already exists for the given agreement and exact billing period. Used by the manual invoice modal to warn when the user enters dates that overlap a previously issued invoice. Returns `already_invoiced` (bool), and if true, also `invoice_id` and `invoice_number`.

### `POST /invoices/batch-preview` — owner/editor
Previews the set of invoices to generate for a selected billing month. The frontend sends `reference_date` = last day of the selected month (e.g., `2026-07-31` for July 2026).

Logic per active agreement:
1. Walks forward from `valid_time_start` period by period until finding the billing period whose `period_end >= reference_date`. This is the **target period** for the selected month.
2. Queries the DB directly: does a standard invoice already exist for this agreement with exactly this `billing_period_start` and `billing_period_end`?
3. If yes → `already_invoiced = true`. If no → ready to generate.

Also pre-allocates invoice numbers in-memory (without committing) so the preview shows correct, non-colliding numbers. For `property_ref` scheme, derives numbers from the property reference field; falls back to the in-memory sequential counter for any property that has no `property_reference` set — ensuring no two preview rows share the same number.

Returns a `BatchPreviewRow` per active agreement including amounts, labels, target period, suggested invoice number, and `already_invoiced` flag.

### `POST /invoices/batch-generate` — owner/editor
Accepts a list of items from the batch-preview confirmation. For each item:
- Verifies the agreement belongs to the org.
- Skips if an invoice with the same `invoice_number` already exists (deduplication guard).
- Creates the invoice row and flushes (without committing between rows).
Commits all rows at once at the end.

### `POST /invoices/{invoice_id}/credit` — owner/editor
Issues a credit note against a standard invoice. Only works on `pending` or `overdue` invoices. Creates a new `Invoice` with `invoice_type = credit_note`, negated amounts, `parent_invoice_id` set, and sets the original invoice's status to `credited`.

### `POST /invoices/{invoice_id}/pay` — owner/editor
Records a payment against a pending or overdue invoice. Creates a `Payment` row and sets the invoice status to `paid`.

### `GET /invoices/{invoice_id}/preview` — authenticated
Renders the invoice or credit note HTML using the Jinja2 template, with full context (lessee, property, org settings, logo as base64 data URL, i18n). Returns the HTML as a JSON string for client-side PDF generation.

### `GET /invoices/{invoice_id}/download` — authenticated
Returns a pre-signed S3 URL (15-min TTL) for the stored invoice PDF. 404 if no PDF has been uploaded yet (i.e., the invoice has not been sent).

### `POST /invoices/{invoice_id}/send` — owner/editor
Sends the invoice by email via Resend. Accepts a base64-encoded PDF and filename. Workflow:
1. Decodes and uploads the PDF to S3 under `invoices/{org_id}/{filename}`.
2. Builds a rich HTML + plain-text email (i18n, due date callout, amount table, bank details block).
3. Sends to lessee (or `DEV_EMAIL` in dev mode). CCs `billing_email_sender` in production.
4. Stores the `pdf_s3_key`, `resend_email_id`, and sets `email_delivery_status = sent` on the invoice.
5. Upserts a `Document` record so the PDF appears in the Documents archive.
Also supports `is_reminder = true` for overdue reminders, which changes the subject line and intro copy.

---

## Payments `/v1/payments`

### `GET /payments?invoice_id=` — authenticated
Lists payments for the org. Optional `invoice_id` filter.

### `GET /payments/{payment_id}` — authenticated
Returns a single payment.

### `POST /payments` — owner/editor
Records a payment. Validates that the linked invoice belongs to the org and is in `pending` or `overdue` status.

### `DELETE /payments/{payment_id}` — owner only
Deletes a payment record.

---

## Expenses `/v1/expenses`

### `GET /expenses?property_id=` — authenticated
Lists expenses for the org. Optional `property_id` filter.

### `GET /expenses/{expense_id}` — authenticated
Returns a single expense.

### `POST /expenses` — owner/editor
Creates an expense. Validates that `property_id` belongs to the org.

### `PATCH /expenses/{expense_id}` — owner/editor
Partial update of an expense.

### `POST /expenses/{expense_id}/pay` — owner/editor
Marks an expense as paid. Sets `is_paid = true` and `paid_date = today`.

### `DELETE /expenses/{expense_id}` — owner only
Deletes an expense.

---

## Documents `/v1/documents`

### `GET /documents?related_entity_type=&related_entity_id=` — authenticated
Lists documents for the org, ordered by `created_at` descending. Optional filters by entity type and ID (e.g., `related_entity_type=invoice&related_entity_id=42`).

### `GET /documents/{document_id}` — authenticated
Returns a single document record (metadata only, no file content).

### `POST /documents/upload` — owner/editor
Uploads a file to S3 and creates a `Document` record. Validates:
- MIME type must be PDF, PNG, JPEG, or HEIC.
- File size ≤ 25 MB.
S3 key: `orgs/{org_id}/documents/{entity_type}/{entity_id}/{uuid}.{ext}`. Accepts `multipart/form-data` with `file`, `display_name`, `related_entity_type`, `related_entity_id`, and optional `document_category`.

### `GET /documents/{document_id}/download` — authenticated
Returns a pre-signed S3 download URL (15-min TTL).

### `DELETE /documents/{document_id}` — owner only
Deletes the S3 object (tolerates missing objects) and the DB record.

---

## VAT Report `/v1/vat-report`

### `GET /vat-report?period_start=&period_end=` — authenticated
Builds a VAT report for the given date range. Uses `issue_date` as the tax-point for invoices (not billing period). Returns:
- All standard and credit_note invoices whose `issue_date` falls in the range (excluding draft/void).
- All expenses whose `expense_date` falls in the range.
- Per-line lessee name and unit label (resolved via agreement → unit → property).
- Totals: invoice net, invoice VAT, expense net, expense VAT, and net VAT due (invoice VAT − expense VAT reclaimable).

### `POST /vat-report/export` — authenticated
Builds the VAT report and exports it as a formatted Excel workbook (`.xlsx`) with three sheets: VAT Summary, Invoices, Expenses. Uploads to S3. Optionally creates a `Document` record (`document_category = vat_report`). Returns a pre-signed download URL (15-min TTL) and the document ID.

### `POST /vat-report/send` — authenticated
Builds the report, generates the Excel file, and emails it to `vat_consultant_email` from Settings. Requires `vat_consultant_email` to be configured. Email includes an i18n-formatted summary table. Attachment is base64-encoded and sent via Resend.

---

## Settings `/v1/settings`

### `GET /settings` — authenticated
Returns the org's settings. 404 if not yet configured.

### `POST /settings` — owner only
Creates the settings record (one per org). 409 if already exists.

### `PATCH /settings` — owner only
Partial update of settings. Key fields include: `company_name`, `company_address`, `company_vat_number`, `billing_email_sender`, `bank_account`, `currency`, `invoice_language`, `invoice_numbering_scheme` (`sequential` or `property_ref`), `vat_consultant_email`, `lease_termination_notice_days`, `logo_s3_key`.

### `POST /settings/logo` — owner only
Uploads a logo (PNG, JPEG, or SVG, ≤ no explicit size limit here). Uploads to S3 first; if that succeeds, creates or updates the settings row with `logo_s3_key`. S3 key: `logos/{org_id}/logo.{ext}`.

### `DELETE /settings/logo` — owner only
Deletes the logo from S3 and clears `logo_s3_key` on the settings row.

### `GET /settings/export` — owner only
Streams a ZIP archive of all org data. Contains:
- `data/*.json` — one JSON file per entity type (properties, units, lessees, agreements, invoices, expenses, payments, documents).
- `documents/{category}/{filename}` — all S3 document files, fetched individually (missing files are skipped silently).

### `DELETE /settings/account` — owner only
Permanently deletes the entire organisation and all its data. Process:
1. Deletes all S3 objects under `orgs/{org_id}/`, `invoices/{org_id}/`, `logos/{org_id}/`.
2. Deletes all `User` rows for the org (FK constraint requires this before org deletion).
3. Deletes the `Organisation` row — cascades to all related tables.

---

## Admin `/v1/admin`

Access restricted to users with `is_admin = true` or whose email is in `ADMIN_EMAILS` config.

### `GET /admin/me` — authenticated
Returns `{ is_admin: true/false }` for the current user. Lightweight check used by the frontend to show/hide the admin panel.

### `GET /admin/orgs` — admin only
Lists all organisations with enriched metadata: owner email, property count, active user count, trial end date, days remaining, subscription status, and a suggested plan tier (Starter ≤ 3 properties, Growth ≤ 10, Portfolio > 10).

### `PATCH /admin/orgs/{org_id}` — admin only
Updates an org's `subscription_status` (`trial`, `active`, `churned`, `exempt`) and/or `admin_notes`.

### `POST /admin/orgs/{org_id}/contact` — admin only
Sends a freeform email to the org owner via Resend. Accepts `subject` and `body`. In dev mode, sends to `DEV_EMAIL`.

---

## Invoice numbering schemes

Controlled by `Settings.invoice_numbering_scheme`:

- **`sequential`** (default) — `INV-{year}-{0001}`. Sequence is per-year, derived by scanning existing invoice numbers for the current year.
- **`property_ref`** — `{property_reference}/{year}/{month:02d}`. Falls back to sequential if the property has no `property_reference` set. Credit notes append `/CR` to the parent invoice number.

---

## Key shared behaviours

- **Org isolation** — every query filters by `org_id` derived from the JWT. No cross-org data leakage is possible via the API.
- **`_mark_overdue`** — called on invoice list and dashboard reads. Bulk-updates all `pending` invoices past their `due_date` to `overdue` in a single query.
- **Billing period computation** — `_period_end(start, interval)` always returns the last calendar day of the period (monthly = last day of same month, quarterly = last day of 3rd month from start, annually = day before same date next year).
- **DEV_EMAIL** — when set, all outgoing emails are redirected to this address regardless of the intended recipient.
