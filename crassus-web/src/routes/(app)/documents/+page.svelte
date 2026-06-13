<script lang="ts">
	import { browser } from '$app/environment';
	import { api } from '$lib/api/client';

	// ── Types ────────────────────────────────────────────────────────────────

	type Property = {
		id: number;
		name: string;
		address: string;
		property_type: string;
	};

	type Document = {
		id: number;
		display_name: string;
		mime_type: string;
		file_size_bytes: number;
		document_category: string;
		related_entity_type: string;
		related_entity_id: number;
		created_at: string;
	};

	type Invoice = {
		id: number;
		invoice_number: string;
		invoice_type: string;
		invoice_status: string;
		billing_period_start: string;
		billing_period_end: string;
		issue_date: string;
		gross_amount: string;
		pdf_s3_key: string | null;
		unit_number: string | null;
	};

	const CATEGORIES: Record<string, string> = {
		lease_agreement:       'Lease Agreement',
		lease_renewal:         'Lease Renewal',
		lease_termination:     'Lease Termination',
		lease_correspondence:  'Lease Correspondence',
		property_tax_assessment: 'Property Tax Assessment',
		insurance_policy:      'Insurance Policy',
		invoice:               'Invoice',
		expense_invoice:       'Expense Invoice',
		expense_sow:           'Expense SoW',
	};

	const CATEGORY_COLORS: Record<string, string> = {
		lease_agreement:         'text-indigo-400 bg-indigo-500/10',
		lease_renewal:           'text-violet-400 bg-violet-500/10',
		lease_termination:       'text-red-400 bg-red-500/10',
		lease_correspondence:    'text-sky-400 bg-sky-500/10',
		property_tax_assessment: 'text-orange-400 bg-orange-500/10',
		insurance_policy:        'text-emerald-400 bg-emerald-500/10',
		invoice:                 'text-indigo-400 bg-indigo-500/10',
		expense_invoice:         'text-amber-400 bg-amber-500/10',
		expense_sow:             'text-rose-400 bg-rose-500/10',
	};

	// ── State ─────────────────────────────────────────────────────────────────

	type Expense = {
		id: number;
		expense_category: string;
		vendor_name: string;
		description: string;
		expense_date: string;
		net_amount: string;
		gross_amount: string;
	};

	const EXPENSE_CATEGORIES: Record<string, string> = {
		maintenance_repairs:  'Maintenance & Repairs',
		insurance:            'Insurance',
		property_tax:         'Property Tax',
		utilities:            'Utilities',
		legal_professional:   'Legal & Professional',
		management_fees:      'Management Fees',
		cleaning_landscaping: 'Cleaning & Landscaping',
		security:             'Security',
		capital_improvement:  'Capital Improvement',
		mortgage_interest:    'Mortgage Interest',
		other:                'Other',
	};

	let activeTab: 'property' | 'invoices' | 'expenses' | 'vat_reports' = $state('property');

	// VAT reports archive
	type VATDoc = {
		id: number;
		display_name: string;
		mime_type: string;
		file_size_bytes: number;
		document_category: string;
		created_at: string;
	};
	let vatDocs: VATDoc[] = $state([]);
	let vatDocsLoading = $state(false);

	function loadVATDocs() {
		vatDocsLoading = true;
		// org_id is used as entity_id for vat_report docs — fetch all for this org
		api.get<VATDoc[]>('/documents?related_entity_type=vat_report')
			.then((d) => { vatDocs = d.sort((a, b) => b.created_at.localeCompare(a.created_at)); })
			.finally(() => { vatDocsLoading = false; });
	}

	// Property docs
	let properties: Property[] = $state([]);
	let selectedProperty: Property | null = $state(null);
	let showPropertyPicker = $state(false);
	let documents: Document[] = $state([]);
	let docsLoading = $state(false);

	// Upload modal
	let showUpload = $state(false);
	let uploadFile: File | null = $state(null);
	let uploadDisplayName = $state('');
	let uploadCategory: string = $state('lease_agreement');
	let uploadError = $state('');
	let uploading = $state(false);
	let dragOver = $state(false);

	// Invoice archive
	let selectedInvoiceProperty: Property | null = $state(null);
	let showInvoicePropertyPicker = $state(false);
	let archivedInvoices: { invoice: Invoice; doc: Document }[] = $state([]);
	let invoicesLoading = $state(false);

	// Expense archive
	let selectedExpenseProperty: Property | null = $state(null);
	let showExpensePropertyPicker = $state(false);
	let expenseArchiveItems: { expense: Expense; docs: Document[] }[] = $state([]);
	let expensesLoading = $state(false);

	// ── Data loading ──────────────────────────────────────────────────────────

	function loadProperties() {
		api.get<Property[]>('/properties').then((p) => { properties = p; });
	}

	function loadDocuments(propertyId: number) {
		docsLoading = true;
		api
			.get<Document[]>(`/documents?related_entity_type=property&related_entity_id=${propertyId}`)
			.then((d) => { documents = d; })
			.finally(() => { docsLoading = false; });
	}

	async function loadArchivedInvoices(propertyId: number) {
		invoicesLoading = true;
		try {
			// Fetch all invoices for the property + all invoice Documents for this org
			const [invoices, invoiceDocs] = await Promise.all([
				api.get<Invoice[]>(`/invoices?property_id=${propertyId}`),
				api.get<Document[]>('/documents?related_entity_type=invoice'),
			]);
			// Build a map: invoice_id → Document record
			const docByInvoiceId = new Map(invoiceDocs.map((d) => [d.related_entity_id, d]));
			// Only show invoices that have an associated Document (i.e. PDF was sent and stored)
			archivedInvoices = invoices
				.filter((inv) => docByInvoiceId.has(inv.id))
				.map((inv) => ({ invoice: inv, doc: docByInvoiceId.get(inv.id)! }))
				.sort((a, b) => a.invoice.invoice_number.localeCompare(b.invoice.invoice_number));
		} finally {
			invoicesLoading = false;
		}
	}

	if (browser) {
		loadProperties();
	}

	function selectProperty(p: Property) {
		selectedProperty = p;
		showPropertyPicker = false;
		loadDocuments(p.id);
	}

	function selectInvoiceProperty(p: Property) {
		selectedInvoiceProperty = p;
		showInvoicePropertyPicker = false;
		loadArchivedInvoices(p.id);
	}

	async function loadExpenseArchive(propertyId: number) {
		expensesLoading = true;
		try {
			const expenses = await api.get<Expense[]>(`/expenses?property_id=${propertyId}`);
			const items = await Promise.all(
				expenses.map(async (exp) => {
					const docs = await api.get<Document[]>(
						`/documents?related_entity_type=expense&related_entity_id=${exp.id}`,
					);
					return { expense: exp, docs };
				}),
			);
			expenseArchiveItems = items.sort(
				(a, b) => new Date(b.expense.expense_date).getTime() - new Date(a.expense.expense_date).getTime(),
			);
		} finally {
			expensesLoading = false;
		}
	}

	function selectExpenseProperty(p: Property) {
		selectedExpenseProperty = p;
		showExpensePropertyPicker = false;
		loadExpenseArchive(p.id);
	}

	// ── Upload ────────────────────────────────────────────────────────────────

	const ACCEPTED = '.pdf,.png,.jpg,.jpeg,.heic,.heif';
	const ACCEPTED_MIME = new Set([
		'application/pdf',
		'image/png',
		'image/jpeg',
		'image/heic',
		'image/heif',
	]);

	function openUpload() {
		uploadFile = null;
		uploadDisplayName = '';
		uploadCategory = 'lease_agreement';
		uploadError = '';
		showUpload = true;
	}

	function handleFileChange(e: Event) {
		const input = e.target as HTMLInputElement;
		setFile(input.files?.[0] ?? null);
	}

	function handleDrop(e: DragEvent) {
		e.preventDefault();
		dragOver = false;
		setFile(e.dataTransfer?.files[0] ?? null);
	}

	function setFile(f: File | null) {
		if (!f) return;
		if (!ACCEPTED_MIME.has(f.type)) {
			uploadError = 'Unsupported format. Use PDF, PNG, JPEG or HEIC.';
			return;
		}
		uploadFile = f;
		if (!uploadDisplayName) uploadDisplayName = f.name.replace(/\.[^.]+$/, '');
		uploadError = '';
	}

	async function handleUpload() {
		if (!uploadFile || !selectedProperty) return;
		if (!uploadDisplayName.trim()) { uploadError = 'Please enter a document name.'; return; }
		uploading = true;
		uploadError = '';
		try {
			const form = new FormData();
			form.append('file', uploadFile);
			form.append('display_name', uploadDisplayName.trim());
			form.append('related_entity_type', 'property');
			form.append('related_entity_id', String(selectedProperty.id));
			form.append('document_category', uploadCategory);

			const token = localStorage.getItem('token');
			const base = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';
			const res = await fetch(`${base}/documents/upload`, {
				method: 'POST',
				headers: { Authorization: `Bearer ${token}` },
				body: form,
			});
			if (!res.ok) {
				const err = await res.json().catch(() => ({}));
				throw new Error(err.detail ?? 'Upload failed.');
			}
			showUpload = false;
			loadDocuments(selectedProperty.id);
		} catch (err: unknown) {
			uploadError = err instanceof Error ? err.message : 'Upload failed.';
		} finally {
			uploading = false;
		}
	}

	// ── Bulk export ───────────────────────────────────────────────────────────

	let exporting = $state(false);
	let exportError = $state('');

	async function handleExport() {
		exporting = true; exportError = '';
		try {
			const token = (await import('$lib/api/client')).getToken();
			const res = await fetch(`${import.meta.env.VITE_API_BASE_URL}/settings/export`, {
				headers: token ? { Authorization: `Bearer ${token}` } : {},
			});
			if (!res.ok) throw new Error('Export failed. Please try again.');
			const blob = await res.blob();
			const url = URL.createObjectURL(blob);
			const a = document.createElement('a');
			a.href = url;
			const today = new Date().toISOString().slice(0, 10);
			a.download = `crassus-export-${today}.zip`;
			a.click();
			URL.revokeObjectURL(url);
		} catch (err: unknown) {
			exportError = err instanceof Error ? err.message : 'Export failed.';
		} finally {
			exporting = false;
		}
	}

	// ── Download ──────────────────────────────────────────────────────────────

	async function handleDownload(doc: Document) {
		const { url } = await api.get<{ url: string }>(`/documents/${doc.id}/download`);
		window.open(url, '_blank');
	}

	async function handleInvoiceDocDownload(doc: Document) {
		const { url } = await api.get<{ url: string }>(`/documents/${doc.id}/download`);
		window.open(url, '_blank');
	}

	// ── Delete ────────────────────────────────────────────────────────────────

	async function handleDelete(doc: Document) {
		if (!confirm(`Delete "${doc.display_name}"? This cannot be undone.`)) return;
		try {
			await api.delete(`/documents/${doc.id}`);
			if (selectedProperty) loadDocuments(selectedProperty.id);
		} catch (err: unknown) {
			alert(err instanceof Error ? err.message : 'Delete failed.');
		}
	}

	// ── Helpers ───────────────────────────────────────────────────────────────

	function formatBytes(b: number): string {
		if (b < 1024) return `${b} B`;
		if (b < 1024 * 1024) return `${(b / 1024).toFixed(1)} KB`;
		return `${(b / (1024 * 1024)).toFixed(1)} MB`;
	}

	function formatDate(iso: string): string {
		return new Date(iso).toLocaleDateString('en-GB', {
			day: '2-digit',
			month: 'short',
			year: 'numeric',
		});
	}

	function mimeIcon(mime: string): string {
		if (mime === 'application/pdf') return '📄';
		if (mime.startsWith('image/')) return '🖼';
		return '📁';
	}
</script>

<!-- ── Page header ──────────────────────────────────────────────────────── -->
<div class="mb-8 flex items-center justify-between">
	<div>
		<h2 class="text-2xl font-semibold text-white">Documents</h2>
		<p class="mt-1 text-sm text-white/40">Property files and invoice archive</p>
	</div>
	<div class="flex flex-col items-end gap-1">
		<button
			onclick={handleExport}
			disabled={exporting}
			class="rounded-xl border border-white/10 bg-[#1a1a1a] px-5 py-2.5 text-sm font-medium text-white hover:bg-white/10 disabled:opacity-40 transition-colors"
		>{exporting ? 'Preparing…' : 'Export all data'}</button>
		{#if exportError}
			<p class="text-xs text-red-400">{exportError}</p>
		{/if}
	</div>
</div>

<!-- ── Tabs ─────────────────────────────────────────────────────────────── -->
<div class="mb-6 flex gap-1 rounded-xl border border-white/[0.07] bg-[#111111] p-1 w-fit">
	<button
		onclick={() => (activeTab = 'property')}
		class="rounded-lg px-5 py-2 text-sm font-medium transition-colors {activeTab === 'property'
			? 'bg-white/10 text-white'
			: 'text-white/40 hover:text-white/70'}"
	>Property Documents</button>
	<button
		onclick={() => (activeTab = 'invoices')}
		class="rounded-lg px-5 py-2 text-sm font-medium transition-colors {activeTab === 'invoices'
			? 'bg-white/10 text-white'
			: 'text-white/40 hover:text-white/70'}"
	>Invoice Archive</button>
	<button
		onclick={() => (activeTab = 'expenses')}
		class="rounded-lg px-5 py-2 text-sm font-medium transition-colors {activeTab === 'expenses'
			? 'bg-white/10 text-white'
			: 'text-white/40 hover:text-white/70'}"
	>Expense Archive</button>
	<button
		onclick={() => { activeTab = 'vat_reports'; loadVATDocs(); }}
		class="rounded-lg px-5 py-2 text-sm font-medium transition-colors {activeTab === 'vat_reports'
			? 'bg-white/10 text-white'
			: 'text-white/40 hover:text-white/70'}"
	>VAT Reports</button>
</div>

<!-- ══════════════════════════════════════════════════════════════════════ -->
<!-- TAB: PROPERTY DOCUMENTS                                               -->
<!-- ══════════════════════════════════════════════════════════════════════ -->
{#if activeTab === 'property'}

	{#if !selectedProperty}
		<div class="rounded-2xl border border-white/[0.07] bg-[#111111] p-12 text-center">
			<div class="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-white/5 text-2xl">🏢</div>
			<p class="mb-1 text-sm font-medium text-white">Select a property</p>
			<p class="mb-6 text-sm text-white/30">Choose a property to view and manage its documents.</p>
			<button
				onclick={() => (showPropertyPicker = true)}
				class="rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-indigo-500 transition-colors"
			>Select Property</button>
		</div>
	{:else}
		<!-- Property selected header -->
		<div class="mb-5 flex items-center justify-between">
			<div class="flex items-center gap-3">
				<button
					onclick={() => { selectedProperty = null; documents = []; }}
					class="text-sm text-white/40 hover:text-white transition-colors"
				>← All Properties</button>
				<span class="text-white/20">/</span>
				<div>
					<span class="text-sm font-semibold text-white">{selectedProperty.name}</span>
					<span class="ml-2 text-xs text-white/30">{selectedProperty.address}</span>
				</div>
			</div>
			<div class="flex items-center gap-3">
				<button
					onclick={() => (showPropertyPicker = true)}
					class="rounded-xl border border-white/10 px-4 py-2 text-sm text-white/50 hover:text-white transition-colors"
				>Switch Property</button>
				<button
					onclick={openUpload}
					class="rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-500 transition-colors"
				>+ Upload Document</button>
			</div>
		</div>

		{#if docsLoading}
			<div class="rounded-2xl border border-white/[0.07] bg-[#111111] p-10 text-center">
				<p class="text-sm text-white/30">Loading…</p>
			</div>
		{:else if documents.length === 0}
			<div class="rounded-2xl border border-white/[0.07] bg-[#111111] p-10 text-center">
				<p class="text-sm text-white/30">No documents yet for this property. Upload the first one.</p>
			</div>
		{:else}
			<div class="overflow-hidden rounded-2xl border border-white/[0.07] bg-[#111111]">
				<table class="w-full text-sm">
					<thead>
						<tr class="border-b border-white/[0.07]">
							<th class="px-5 py-3.5 text-left text-xs font-medium uppercase tracking-wider text-white/30">Document</th>
							<th class="px-5 py-3.5 text-left text-xs font-medium uppercase tracking-wider text-white/30">Category</th>
							<th class="px-5 py-3.5 text-left text-xs font-medium uppercase tracking-wider text-white/30">Size</th>
							<th class="px-5 py-3.5 text-left text-xs font-medium uppercase tracking-wider text-white/30">Uploaded</th>
							<th class="px-5 py-3.5"></th>
						</tr>
					</thead>
					<tbody>
						{#each documents as doc}
							<tr class="border-b border-white/[0.04] hover:bg-white/[0.02] transition-colors">
								<td class="px-5 py-4">
									<div class="flex items-center gap-3">
										<span class="text-lg">{mimeIcon(doc.mime_type)}</span>
										<span class="font-medium text-white">{doc.display_name}</span>
									</div>
								</td>
								<td class="px-5 py-4">
									<span class="rounded-md px-2 py-1 text-xs {CATEGORY_COLORS[doc.document_category] ?? CATEGORY_COLORS.other}">
										{CATEGORIES[doc.document_category] ?? doc.document_category}
									</span>
								</td>
								<td class="px-5 py-4 text-white/50">{formatBytes(doc.file_size_bytes)}</td>
								<td class="px-5 py-4 text-white/50">{formatDate(doc.created_at)}</td>
								<td class="px-5 py-4 text-right whitespace-nowrap">
									<button
										onclick={() => handleDownload(doc)}
										class="mr-4 text-xs text-indigo-400 hover:text-indigo-300 transition-colors"
									>↓ Download</button>
									<button
										onclick={() => handleDelete(doc)}
										class="text-xs text-red-400/60 hover:text-red-400 transition-colors"
									>Delete</button>
								</td>
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		{/if}
	{/if}

{/if}

<!-- ══════════════════════════════════════════════════════════════════════ -->
<!-- TAB: INVOICE ARCHIVE                                                  -->
<!-- ══════════════════════════════════════════════════════════════════════ -->
{#if activeTab === 'invoices'}

	{#if !selectedInvoiceProperty}
		<div class="rounded-2xl border border-white/[0.07] bg-[#111111] p-12 text-center">
			<div class="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-white/5 text-2xl">🗂</div>
			<p class="mb-1 text-sm font-medium text-white">Select a property</p>
			<p class="mb-6 text-sm text-white/30">Choose a property to view its invoice archive.</p>
			<button
				onclick={() => (showInvoicePropertyPicker = true)}
				class="rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-indigo-500 transition-colors"
			>Select Property</button>
		</div>
	{:else}
		<!-- Property selected header -->
		<div class="mb-5 flex items-center justify-between">
			<div class="flex items-center gap-3">
				<button
					onclick={() => { selectedInvoiceProperty = null; archivedInvoices = []; }}
					class="text-sm text-white/40 hover:text-white transition-colors"
				>← All Properties</button>
				<span class="text-white/20">/</span>
				<div>
					<span class="text-sm font-semibold text-white">{selectedInvoiceProperty.name}</span>
					<span class="ml-2 text-xs text-white/30">{selectedInvoiceProperty.address}</span>
				</div>
			</div>
			<button
				onclick={() => (showInvoicePropertyPicker = true)}
				class="rounded-xl border border-white/10 px-4 py-2 text-sm text-white/50 hover:text-white transition-colors"
			>Switch Property</button>
		</div>

	{#if invoicesLoading}
		<div class="rounded-2xl border border-white/[0.07] bg-[#111111] p-10 text-center">
			<p class="text-sm text-white/30">Loading…</p>
		</div>
	{:else if archivedInvoices.length === 0}
		<div class="rounded-2xl border border-white/[0.07] bg-[#111111] p-10 text-center">
			<div class="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-white/5 text-2xl">🗂</div>
			<p class="mb-1 text-sm font-medium text-white">No invoices in archive for this property</p>
			<p class="text-sm text-white/30">Invoices appear here once they have been sent to the lessee and their PDF is stored.</p>
		</div>
	{:else}
		<div class="overflow-hidden rounded-2xl border border-white/[0.07] bg-[#111111]">
			<table class="w-full text-sm">
				<thead>
					<tr class="border-b border-white/[0.07]">
						<th class="px-5 py-3.5 text-left text-xs font-medium uppercase tracking-wider text-white/30">Invoice No.</th>
						<th class="px-5 py-3.5 text-left text-xs font-medium uppercase tracking-wider text-white/30">Unit</th>
						<th class="px-5 py-3.5 text-left text-xs font-medium uppercase tracking-wider text-white/30">Type</th>
						<th class="px-5 py-3.5 text-left text-xs font-medium uppercase tracking-wider text-white/30">Period</th>
						<th class="px-5 py-3.5 text-left text-xs font-medium uppercase tracking-wider text-white/30">Issue Date</th>
						<th class="px-5 py-3.5 text-right text-xs font-medium uppercase tracking-wider text-white/30">Amount</th>
						<th class="px-5 py-3.5 text-left text-xs font-medium uppercase tracking-wider text-white/30">Status</th>
						<th class="px-5 py-3.5"></th>
					</tr>
				</thead>
				<tbody>
					{#each archivedInvoices as { invoice: inv, doc }}
						<tr class="border-b border-white/[0.04] hover:bg-white/[0.02] transition-colors">
							<td class="px-5 py-4 font-mono text-sm text-white">{inv.invoice_number}</td>
							<td class="px-5 py-4 text-white/60">{inv.unit_number ?? '—'}</td>
							<td class="px-5 py-4">
								{#if inv.invoice_type === 'credit_note'}
									<span class="rounded-md bg-red-500/10 px-2 py-1 text-xs text-red-400">Credit</span>
								{:else}
									<span class="rounded-md bg-white/5 px-2 py-1 text-xs text-white/40">Invoice</span>
								{/if}
							</td>
							<td class="px-5 py-4 text-white/60">
								{formatDate(inv.billing_period_start)} – {formatDate(inv.billing_period_end)}
							</td>
							<td class="px-5 py-4 text-white/60">{formatDate(inv.issue_date)}</td>
							<td class="px-5 py-4 text-right font-medium text-white">{inv.gross_amount}</td>
							<td class="px-5 py-4">
								{#if inv.invoice_status === 'paid'}
									<span class="rounded-md bg-emerald-500/10 px-2 py-1 text-xs text-emerald-400">Paid</span>
								{:else if inv.invoice_status === 'credited'}
									<span class="rounded-md bg-orange-500/10 px-2 py-1 text-xs text-orange-400">Credited</span>
								{:else if inv.invoice_status === 'overdue'}
									<span class="rounded-md bg-red-500/10 px-2 py-1 text-xs text-red-400">Overdue</span>
								{:else}
									<span class="rounded-md bg-sky-500/10 px-2 py-1 text-xs text-sky-400">Sent</span>
								{/if}
							</td>
							<td class="px-5 py-4 text-right">
								<button
									onclick={() => handleInvoiceDocDownload(doc)}
									class="text-xs text-indigo-400 hover:text-indigo-300 transition-colors"
								>↓ PDF</button>
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	{/if}
	{/if}<!-- /selectedInvoiceProperty -->

{/if}

<!-- ══════════════════════════════════════════════════════════════════════ -->
<!-- MODAL: Property Picker                                                -->
<!-- ══════════════════════════════════════════════════════════════════════ -->
{#if showPropertyPicker}
	<div
		class="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4"
		role="dialog"
		aria-modal="true"
	>
		<div class="w-full max-w-md rounded-2xl border border-white/[0.08] bg-[#111111] shadow-2xl">
			<div class="flex items-center justify-between border-b border-white/[0.07] px-6 py-4">
				<h3 class="text-base font-semibold text-white">Select Property</h3>
				<button
					onclick={() => (showPropertyPicker = false)}
					class="text-white/30 hover:text-white transition-colors text-xl leading-none"
				>×</button>
			</div>

			{#if properties.length === 0}
				<div class="px-6 py-10 text-center">
					<p class="text-sm text-white/30">No properties found. Add properties first.</p>
				</div>
			{:else}
				<div class="max-h-96 divide-y divide-white/[0.05] overflow-y-auto">
					{#each properties as p}
						<button
							onclick={() => selectProperty(p)}
							class="flex w-full items-start gap-4 px-6 py-4 text-left transition-colors hover:bg-white/[0.04] {selectedProperty?.id === p.id ? 'bg-indigo-600/10' : ''}"
						>
							<div class="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-xl bg-white/5 text-base">🏢</div>
							<div class="min-w-0">
								<p class="text-sm font-semibold text-white">{p.name}</p>
								<p class="truncate text-xs text-white/40">{p.address}</p>
							</div>
							{#if selectedProperty?.id === p.id}
								<span class="ml-auto text-sm text-indigo-400">✓</span>
							{/if}
						</button>
					{/each}
				</div>
			{/if}
		</div>
	</div>
{/if}

<!-- ══════════════════════════════════════════════════════════════════════ -->
<!-- TAB: EXPENSE ARCHIVE                                                  -->
<!-- ══════════════════════════════════════════════════════════════════════ -->
{#if activeTab === 'expenses'}

	{#if !selectedExpenseProperty}
		<div class="rounded-2xl border border-white/[0.07] bg-[#111111] p-12 text-center">
			<div class="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-white/5 text-2xl">🧾</div>
			<p class="mb-1 text-sm font-medium text-white">Select a property</p>
			<p class="mb-6 text-sm text-white/30">Choose a property to view its expense receipts.</p>
			<button
				onclick={() => (showExpensePropertyPicker = true)}
				class="rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-indigo-500 transition-colors"
			>Select Property</button>
		</div>
	{:else}
		<div class="mb-5 flex items-center justify-between">
			<div class="flex items-center gap-3">
				<button
					onclick={() => { selectedExpenseProperty = null; expenseArchiveItems = []; }}
					class="text-sm text-white/40 hover:text-white transition-colors"
				>← All Properties</button>
				<span class="text-white/20">/</span>
				<span class="text-sm font-semibold text-white">{selectedExpenseProperty.name}</span>
				<span class="ml-1 text-xs text-white/30">{selectedExpenseProperty.address}</span>
			</div>
			<button
				onclick={() => (showExpensePropertyPicker = true)}
				class="rounded-xl border border-white/10 px-4 py-2 text-sm text-white/50 hover:text-white transition-colors"
			>Switch Property</button>
		</div>

		{#if expensesLoading}
			<div class="rounded-2xl border border-white/[0.07] bg-[#111111] p-10 text-center">
				<p class="text-sm text-white/30">Loading…</p>
			</div>
		{:else if expenseArchiveItems.length === 0}
			<div class="rounded-2xl border border-white/[0.07] bg-[#111111] p-10 text-center">
				<p class="text-sm text-white/30">No expenses recorded for this property yet.</p>
			</div>
		{:else}
			<div class="space-y-2">
				{#each expenseArchiveItems as item}
					<div class="rounded-2xl border border-white/[0.07] bg-[#111111] px-5 py-4">
						<div class="flex items-start justify-between gap-4">
							<div class="flex items-start gap-4 min-w-0">
								<div class="flex-shrink-0 mt-0.5">
									<span class="rounded-md px-2 py-1 text-xs {
										item.expense.expense_category === 'maintenance_repairs' ? 'text-amber-400 bg-amber-500/10' :
										item.expense.expense_category === 'insurance' ? 'text-emerald-400 bg-emerald-500/10' :
										item.expense.expense_category === 'property_tax' ? 'text-orange-400 bg-orange-500/10' :
										item.expense.expense_category === 'utilities' ? 'text-sky-400 bg-sky-500/10' :
										item.expense.expense_category === 'legal_professional' ? 'text-violet-400 bg-violet-500/10' :
										'text-white/40 bg-white/5'
									}">
										{EXPENSE_CATEGORIES[item.expense.expense_category] ?? item.expense.expense_category}
									</span>
								</div>
								<div class="min-w-0">
									<p class="text-sm font-semibold text-white">{item.expense.vendor_name}</p>
									<p class="text-xs text-white/50 mt-0.5">{item.expense.description}</p>
								</div>
							</div>
							<div class="flex-shrink-0 text-right">
								<p class="text-sm font-semibold text-white">{Number(item.expense.gross_amount).toLocaleString('en-GB', {minimumFractionDigits:2, maximumFractionDigits:2})}</p>
								<p class="text-xs text-white/30 mt-0.5">{formatDate(item.expense.expense_date)}</p>
							</div>
						</div>

						{#if item.docs.length > 0}
							<div class="mt-3 flex flex-wrap gap-2 border-t border-white/[0.05] pt-3">
								{#each item.docs as doc}
									<button
										onclick={async () => { const { url } = await api.get<{ url: string }>(`/documents/${doc.id}/download`); window.open(url, '_blank'); }}
										class="flex items-center gap-1.5 rounded-lg border border-white/10 bg-white/[0.03] px-3 py-1.5 text-xs text-white/60 hover:border-white/20 hover:text-white transition-colors"
									>
										<span>{mimeIcon(doc.mime_type)}</span>
										<span>{doc.display_name}</span>
										<span class="text-white/25">↓</span>
									</button>
								{/each}
							</div>
						{:else}
							<p class="mt-3 border-t border-white/[0.05] pt-3 text-xs text-white/20">No receipt uploaded</p>
						{/if}
					</div>
				{/each}
			</div>
		{/if}
	{/if}

{/if}

<!-- ══════════════════════════════════════════════════════════════════════ -->
<!-- TAB: VAT REPORTS                                                      -->
<!-- ══════════════════════════════════════════════════════════════════════ -->
{#if activeTab === 'vat_reports'}

	<div class="mb-5 flex items-center justify-between">
		<p class="text-sm text-white/40">Exported VAT report Excel files, auto-saved here when you export from the VAT Report page.</p>
		<a href="/vat" class="rounded-xl border border-indigo-500/30 bg-indigo-500/10 px-4 py-2 text-sm font-medium text-indigo-400 hover:bg-indigo-500/20 transition-colors">
			→ Go to VAT Report
		</a>
	</div>

	{#if vatDocsLoading}
		<div class="py-12 text-center text-sm text-white/30">Loading…</div>
	{:else if vatDocs.length === 0}
		<div class="rounded-2xl border border-white/[0.07] bg-[#111111] p-12 text-center">
			<div class="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-white/5 text-2xl">📊</div>
			<p class="text-sm text-white/40">No VAT reports exported yet.</p>
			<p class="mt-1 text-xs text-white/20">Generate and export a report from the VAT Report page to see it here.</p>
		</div>
	{:else}
		<div class="overflow-hidden rounded-2xl border border-white/[0.07] bg-[#111111]">
			<table class="w-full text-sm">
				<thead><tr class="border-b border-white/[0.07]">
					<th class="px-5 py-3.5 text-left text-xs font-medium uppercase tracking-wider text-white/30">File</th>
					<th class="px-5 py-3.5 text-left text-xs font-medium uppercase tracking-wider text-white/30">Size</th>
					<th class="px-5 py-3.5 text-left text-xs font-medium uppercase tracking-wider text-white/30">Exported</th>
					<th class="px-5 py-3.5"></th>
				</tr></thead>
				<tbody>
					{#each vatDocs as doc}
					<tr class="border-b border-white/[0.04] hover:bg-white/[0.02] transition-colors">
						<td class="px-5 py-4">
							<div class="flex items-center gap-3">
								<span class="text-lg">📊</span>
								<div>
									<p class="text-sm font-medium text-white">{doc.display_name}</p>
									<p class="text-xs text-white/30 mt-0.5">Excel Spreadsheet</p>
								</div>
							</div>
						</td>
						<td class="px-5 py-4 text-xs text-white/40">{formatBytes(doc.file_size_bytes)}</td>
						<td class="px-5 py-4 text-xs text-white/40">{formatDate(doc.created_at)}</td>
						<td class="px-5 py-4 text-right">
							<button
								onclick={() => handleDownload(doc as Document)}
								class="text-xs text-indigo-400 hover:text-indigo-300 transition-colors"
							>Download</button>
						</td>
					</tr>
					{/each}
				</tbody>
			</table>
		</div>
	{/if}

{/if}

<!-- ══════════════════════════════════════════════════════════════════════ -->
<!-- MODAL: Invoice Property Picker                                        -->
<!-- ══════════════════════════════════════════════════════════════════════ -->
{#if showInvoicePropertyPicker}
	<div
		class="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4"
		role="dialog"
		aria-modal="true"
	>
		<div class="w-full max-w-md rounded-2xl border border-white/[0.08] bg-[#111111] shadow-2xl">
			<div class="flex items-center justify-between border-b border-white/[0.07] px-6 py-4">
				<h3 class="text-base font-semibold text-white">Select Property</h3>
				<button
					onclick={() => (showInvoicePropertyPicker = false)}
					class="text-white/30 hover:text-white transition-colors text-xl leading-none"
				>×</button>
			</div>

			{#if properties.length === 0}
				<div class="px-6 py-10 text-center">
					<p class="text-sm text-white/30">No properties found. Add properties first.</p>
				</div>
			{:else}
				<div class="max-h-96 divide-y divide-white/[0.05] overflow-y-auto">
					{#each properties as p}
						<button
							onclick={() => selectInvoiceProperty(p)}
							class="flex w-full items-start gap-4 px-6 py-4 text-left transition-colors hover:bg-white/[0.04] {selectedInvoiceProperty?.id === p.id ? 'bg-indigo-600/10' : ''}"
						>
							<div class="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-xl bg-white/5 text-base">🏢</div>
							<div class="min-w-0">
								<p class="text-sm font-semibold text-white">{p.name}</p>
								<p class="truncate text-xs text-white/40">{p.address}</p>
							</div>
							{#if selectedInvoiceProperty?.id === p.id}
								<span class="ml-auto text-sm text-indigo-400">✓</span>
							{/if}
						</button>
					{/each}
				</div>
			{/if}
		</div>
	</div>
{/if}

<!-- ══════════════════════════════════════════════════════════════════════ -->
<!-- MODAL: Expense Property Picker                                        -->
<!-- ══════════════════════════════════════════════════════════════════════ -->
{#if showExpensePropertyPicker}
	<div
		class="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4"
		role="dialog" aria-modal="true"
	>
		<div class="w-full max-w-md rounded-2xl border border-white/[0.08] bg-[#111111] shadow-2xl">
			<div class="flex items-center justify-between border-b border-white/[0.07] px-6 py-4">
				<h3 class="text-base font-semibold text-white">Select Property</h3>
				<button onclick={() => (showExpensePropertyPicker = false)} class="text-xl leading-none text-white/30 hover:text-white transition-colors">×</button>
			</div>
			{#if properties.length === 0}
				<div class="px-6 py-10 text-center">
					<p class="text-sm text-white/30">No properties found.</p>
				</div>
			{:else}
				<div class="max-h-96 divide-y divide-white/[0.05] overflow-y-auto">
					{#each properties as p}
						<button
							onclick={() => selectExpenseProperty(p)}
							class="flex w-full items-start gap-4 px-6 py-4 text-left transition-colors hover:bg-white/[0.04] {selectedExpenseProperty?.id === p.id ? 'bg-indigo-600/10' : ''}"
						>
							<div class="flex h-9 w-9 flex-shrink-0 items-center justify-center rounded-xl bg-white/5 text-base">🏢</div>
							<div class="min-w-0">
								<p class="text-sm font-semibold text-white">{p.name}</p>
								<p class="truncate text-xs text-white/40">{p.address}</p>
							</div>
							{#if selectedExpenseProperty?.id === p.id}
								<span class="ml-auto text-sm text-indigo-400">✓</span>
							{/if}
						</button>
					{/each}
				</div>
			{/if}
		</div>
	</div>
{/if}

<!-- ══════════════════════════════════════════════════════════════════════ -->
<!-- MODAL: Upload Document                                                -->
<!-- ══════════════════════════════════════════════════════════════════════ -->
{#if showUpload}
	<div
		class="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4"
		role="dialog"
		aria-modal="true"
	>
		<div class="w-full max-w-lg rounded-2xl border border-white/[0.08] bg-[#111111] shadow-2xl">
			<div class="flex items-center justify-between border-b border-white/[0.07] px-6 py-4">
				<div>
					<h3 class="text-base font-semibold text-white">Upload Document</h3>
					<p class="text-xs text-white/30">{selectedProperty?.name}</p>
				</div>
				<button
					onclick={() => (showUpload = false)}
					class="text-white/30 hover:text-white transition-colors text-xl leading-none"
				>×</button>
			</div>

			<div class="space-y-5 px-6 py-5">
				<!-- Drop zone -->
				<!-- svelte-ignore a11y_interactive_supports_focus -->
				<div
					role="button"
					tabindex="0"
					class="relative flex flex-col items-center justify-center rounded-xl border-2 border-dashed py-10 transition-colors cursor-pointer
						{dragOver
							? 'border-indigo-500 bg-indigo-500/5'
							: uploadFile
							? 'border-emerald-500/40 bg-emerald-500/5'
							: 'border-white/10 hover:border-white/20'}"
					ondragover={(e) => { e.preventDefault(); dragOver = true; }}
					ondragleave={() => (dragOver = false)}
					ondrop={handleDrop}
					onclick={() => (document.getElementById('doc-file-input') as HTMLInputElement)?.click()}
					onkeydown={(e) => { if (e.key === 'Enter') (document.getElementById('doc-file-input') as HTMLInputElement)?.click(); }}
				>
					<input
						id="doc-file-input"
						type="file"
						accept={ACCEPTED}
						class="hidden"
						onchange={handleFileChange}
					/>
					{#if uploadFile}
						<span class="mb-2 text-3xl">{mimeIcon(uploadFile.type)}</span>
						<p class="text-sm font-medium text-white">{uploadFile.name}</p>
						<p class="mt-1 text-xs text-white/40">{formatBytes(uploadFile.size)} · click to change</p>
					{:else}
						<span class="mb-2 text-3xl text-white/20">☁</span>
						<p class="text-sm text-white/50">Drop a file here or <span class="text-indigo-400">browse</span></p>
						<p class="mt-1 text-xs text-white/25">PDF, PNG, JPEG, HEIC · max 25 MB</p>
					{/if}
				</div>

				<!-- Document name -->
				<div>
					<label class="mb-1.5 block text-xs font-medium uppercase tracking-wider text-white/40" for="doc-name">
						Document Name *
					</label>
					<input
						id="doc-name"
						type="text"
						bind:value={uploadDisplayName}
						placeholder="e.g. Lease Agreement Jan 2026"
						class="w-full rounded-xl border border-white/10 bg-[#1a1a1a] px-4 py-3 text-sm text-white placeholder-white/20 focus:border-indigo-500/50 focus:outline-none focus:ring-1 focus:ring-indigo-500/50 transition"
					/>
				</div>

				<!-- Category -->
				<div>
					<label class="mb-1.5 block text-xs font-medium uppercase tracking-wider text-white/40" for="doc-cat">
						Category
					</label>
					<select
						id="doc-cat"
						bind:value={uploadCategory}
						class="w-full rounded-xl border border-white/10 bg-[#1a1a1a] px-4 py-3 text-sm text-white focus:border-indigo-500/50 focus:outline-none focus:ring-1 focus:ring-indigo-500/50 transition"
					>
						{#each Object.entries(CATEGORIES) as [val, label]}
							<option value={val}>{label}</option>
						{/each}
					</select>
				</div>

				{#if uploadError}
					<div class="rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3">
						<p class="text-sm text-red-400">{uploadError}</p>
					</div>
				{/if}
			</div>

			<div class="flex justify-end gap-3 border-t border-white/[0.07] px-6 py-4">
				<button
					onclick={() => (showUpload = false)}
					class="rounded-xl border border-white/10 px-5 py-2.5 text-sm text-white/50 hover:text-white transition-colors"
				>Cancel</button>
				<button
					onclick={handleUpload}
					disabled={!uploadFile || uploading}
					class="rounded-xl bg-indigo-600 px-6 py-2.5 text-sm font-semibold text-white hover:bg-indigo-500 disabled:opacity-40 transition-colors"
				>
					{uploading ? 'Uploading…' : 'Upload'}
				</button>
			</div>
		</div>
	</div>
{/if}
