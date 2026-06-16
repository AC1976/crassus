<script lang="ts">
	import { browser } from '$app/environment';
	import { onDestroy } from 'svelte';
	import { api, getToken } from '$lib/api/client';

	type Agreement = {
		id: number; agreement_uuid: string; property_id: number; unit_id: number | null; lessee_uuid: string;
		base_rent_amount: string; vat_rate_applied: string; service_charges: string;
		payment_interval: string; valid_time_start: string; valid_time_end: string;
	};
	type Property = { id: number; name: string; };
	type Unit = { id: number; property_id: number; unit_number: string; };
	type Lessee = { id: number; lessee_uuid: string; first_name: string | null; last_name: string | null; company_legal_name: string | null; email: string; };
	type Invoice = {
		id: number; invoice_number: string; agreement_uuid: string; parent_invoice_id: number | null;
		invoice_type: string; billing_period_start: string; billing_period_end: string;
		issue_date: string; due_date: string; net_amount: string; vat_amount: string;
		gross_amount: string; invoice_status: string; created_at: string;
		pdf_s3_key: string | null;
		email_delivery_status: string;
	};
	type CheckPeriodResult = {
		already_invoiced: boolean;
		invoice_id: number | null;
		invoice_number: string | null;
	};

	let agreements: Agreement[] = $state([]);
	let properties: Property[] = $state([]);
	let allUnits: Unit[] = $state([]);
	let lessees: Lessee[] = $state([]);
	let invoices: Invoice[] = $state([]);
	let statusFilter = $state('active');
	let selectedAgreement: Agreement | null = $state(null);

	// Generate invoice modal
	let showGenerateModal = $state(false);
	let generating = $state(false);
	let generateError = $state('');
	let genForm = $state<{
		invoice_number: string; issue_date: string; due_date: string;
		period_start: string; period_end: string;
		net: string; vat: string; gross: string;
	} | null>(null);
	let periodCheckResult = $state<CheckPeriodResult | null>(null);
	let periodChecking = $state(false);

	// Pay modal
	let showPayModal = $state(false);
	let payingInvoice: Invoice | null = $state(null);
	let pay_date = $state('');
	let pay_amount = $state('');
	let pay_method = $state('bank_transfer');
	let pay_reference = $state('');
	let pay_notes = $state('');
	let paying = $state(false);
	let payError = $state('');

	// Send invoice
	let sendingInvoice: Invoice | null = $state(null);
	let sendError = $state('');
	let sending = $state(false);

	// Actions dropdown
	let openActionId: number | null = $state(null);
	function toggleAction(id: number) { openActionId = openActionId === id ? null : id; }
	function closeAction() { openActionId = null; }

	// ── Batch billing ──────────────────────────────────────────────────────
	type BatchRow = {
		agreement_uuid: string;
		unit_label: string;
		lessee_name: string;
		billing_period_start: string;
		billing_period_end: string;
		due_date: string;
		net_amount: string;
		vat_amount: string;
		gross_amount: string;
		suggested_invoice_number: string;
		already_invoiced: boolean;
		// UI state
		included: boolean;
		invoice_number: string;
		net: string;
		vat: string;
		gross: string;
	};
	type CreatedInvoice = Invoice & {
		_sending?: boolean;
		_sent?: boolean;
		_sendError?: string;
		_excluded?: boolean;
		_previewing?: boolean;
	};

	let showBatchModal = $state(false);
	let batchStep: 'period' | 'review' | 'generating' | 'done' = $state('period');

	// Period picker — default to next month
	const _now = new Date();
	const _nextMonth = new Date(_now.getFullYear(), _now.getMonth() + 1, 1);
	let batchMonth = $state(_nextMonth.getMonth() + 1); // 1-12
	let batchYear = $state(_nextMonth.getFullYear());

	let batchRows: BatchRow[] = $state([]);
	let batchLoading = $state(false);
	let batchError = $state('');

	// Generating progress
	let batchGenProgress = $state(0);
	let batchGenTotal = $state(0);

	// Done step
	let batchCreated: CreatedInvoice[] = $state([]);
	let batchSendingAll = $state(false);

	const MONTHS = ['January','February','March','April','May','June','July','August','September','October','November','December'];

	function openBatchModal() {
		batchStep = 'period';
		batchError = '';
		batchRows = [];
		batchCreated = [];
		showBatchModal = true;
	}

	async function loadBatchPreview() {
		batchLoading = true;
		batchError = '';
		// reference_date = last day of selected month (period due date reference)
		const lastDay = new Date(batchYear, batchMonth, 0).getDate();
		const refDate = `${batchYear}-${String(batchMonth).padStart(2,'0')}-${String(lastDay).padStart(2,'0')}`;
		try {
			const rows = await api.post<BatchRow[]>('/invoices/batch-preview', { reference_date: refDate });
			batchRows = rows.map((r) => ({
				...r,
				included: !r.already_invoiced,
				invoice_number: r.suggested_invoice_number,
				net: String(r.net_amount),
				vat: String(r.vat_amount),
				gross: String(r.gross_amount),
			}));
			batchStep = 'review';
		} catch (err: unknown) {
			batchError = err instanceof Error ? err.message : 'Failed to load preview.';
		} finally {
			batchLoading = false;
		}
	}

	async function runBatchGenerate() {
		const selected = batchRows.filter((r) => r.included && !r.already_invoiced);
		if (selected.length === 0) return;
		batchStep = 'generating';
		batchGenTotal = selected.length;
		batchGenProgress = 0;
		batchCreated = [];
		const issueDate = new Date().toISOString().slice(0, 10);
		try {
			const items = selected.map((r) => ({
				agreement_uuid: r.agreement_uuid,
				invoice_number: r.invoice_number,
				billing_period_start: r.billing_period_start,
				billing_period_end: r.billing_period_end,
				issue_date: issueDate,
				due_date: r.due_date,
				net_amount: parseFloat(r.net).toFixed(2),
				vat_amount: parseFloat(r.vat).toFixed(2),
				gross_amount: (parseFloat(r.net) + parseFloat(r.vat)).toFixed(2),
			}));
			const created = await api.post<CreatedInvoice[]>('/invoices/batch-generate', { items });
			batchCreated = created;
			batchGenProgress = selected.length;
			batchStep = 'done';
			load(); // refresh ledger
		} catch (err: unknown) {
			batchError = err instanceof Error ? err.message : 'Batch generation failed.';
			batchStep = 'review';
		}
	}

	async function sendCreatedInvoice(inv: CreatedInvoice) {
		inv._sending = true;
		inv._sendError = undefined;
		batchCreated = [...batchCreated]; // trigger reactivity
		try {
			const { html } = await api.get<{ html: string }>(`/invoices/${inv.id}/preview`);
			const html2pdf = (await import('html2pdf.js')).default;
			const pdfBlob: Blob = await html2pdf()
				.set({
					margin: 0,
					filename: `${inv.invoice_number}.pdf`,
					image: { type: 'jpeg', quality: 0.95 },
					html2canvas: { scale: 3, useCORS: true, logging: false, backgroundColor: '#ffffff', letterRendering: true },
					jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' },
				})
				.from(html)
				.outputPdf('blob');
			const base64 = await new Promise<string>((resolve, reject) => {
				const reader = new FileReader();
				reader.onloadend = () => resolve((reader.result as string).split(',')[1]);
				reader.onerror = reject;
				reader.readAsDataURL(pdfBlob);
			});
			await api.post(`/invoices/${inv.id}/send`, { pdf_base64: base64, filename: `${inv.invoice_number}.pdf` });
			inv._sent = true;
		} catch (err: unknown) {
			inv._sendError = err instanceof Error ? err.message : 'Send failed.';
		} finally {
			inv._sending = false;
			batchCreated = [...batchCreated];
		}
	}

	async function previewCreatedInvoice(inv: CreatedInvoice) {
		inv._previewing = true;
		batchCreated = [...batchCreated];
		try {
			const { html } = await api.get<{ html: string }>(`/invoices/${inv.id}/preview`);
			const blob = new Blob([html], { type: 'text/html' });
			const url = URL.createObjectURL(blob);
			const win = window.open(url, '_blank');
			// Revoke after the tab has had time to load
			setTimeout(() => URL.revokeObjectURL(url), 10000);
			if (!win) alert('Allow pop-ups to preview invoices.');
		} catch (err: unknown) {
			alert(err instanceof Error ? err.message : 'Preview failed.');
		} finally {
			inv._previewing = false;
			batchCreated = [...batchCreated];
		}
	}

	async function sendAllCreated() {
		batchSendingAll = true;
		for (const inv of batchCreated) {
			if (!inv._sent && !inv._sending && !inv._excluded) await sendCreatedInvoice(inv);
		}
		batchSendingAll = false;
		load();
	}

	const today = new Date().toISOString().slice(0, 10);

	function unitLabel(agreement: Agreement) {
		if (agreement.unit_id) {
			const u = allUnits.find((x) => x.id === agreement.unit_id);
			const p = properties.find((x) => x.id === (u?.property_id ?? agreement.property_id));
			return u ? `${p?.name ?? ''} — ${u.unit_number}` : '—';
		}
		const p = properties.find((x) => x.id === agreement.property_id);
		return p?.name ?? '—';
	}
	function lesseeLabel(uuid: string) {
		const l = lessees.find((x) => x.lessee_uuid === uuid);
		if (!l) return uuid;
		if (l.company_legal_name) return l.company_legal_name;
		const name = [l.first_name, l.last_name].filter(Boolean).join(' ');
		return name || l.email;
	}

	function isActive(a: Agreement) {
		const now = today;
		return a.valid_time_start.slice(0, 10) <= now && a.valid_time_end.slice(0, 10) >= now;
	}

	let activeAgreements = $derived(agreements.filter(isActive));

	let filteredInvoices = $derived((() => {
		if (statusFilter === 'active') return invoices.filter((i) => ['pending', 'overdue'].includes(i.invoice_status));
		if (statusFilter === 'paid') return invoices.filter((i) => i.invoice_status === 'paid');
		if (statusFilter === 'credited') return invoices.filter((i) => i.invoice_status === 'credited' || i.invoice_type === 'credit_note');
		return invoices;
	})());

	function load() {
		api.get<Agreement[]>('/rental-agreements').then((a) => { agreements = a; });
		api.get<Property[]>('/properties').then((p) => { properties = p; });
		api.get<Unit[]>('/units').then((u) => { allUnits = u; });
		api.get<Lessee[]>('/lessees').then((l) => { lessees = l; });
		api.get<Invoice[]>('/invoices').then((i) => { invoices = i; });
	}
	let pollTimer: ReturnType<typeof setInterval> | null = null;
	if (browser) {
		load();
		// Refresh invoice list every 30s so email delivery badges stay current
		pollTimer = setInterval(() => {
			api.get<Invoice[]>('/invoices').then((i) => { invoices = i; });
		}, 30_000);
	}
	onDestroy(() => { if (pollTimer) clearInterval(pollTimer); });

	function openGenerateModal(a: Agreement) {
		selectedAgreement = a;
		generateError = '';
		periodCheckResult = null;
		const net = parseFloat(a.base_rent_amount) + parseFloat(a.service_charges);
		const vat = net * parseFloat(a.vat_rate_applied) / 100;
		genForm = {
			invoice_number: '',
			issue_date: today,
			due_date: '',
			period_start: '',
			period_end: '',
			net: net.toFixed(2),
			vat: vat.toFixed(2),
			gross: (net + vat).toFixed(2),
		};
		showGenerateModal = true;
	}

	async function checkPeriod() {
		if (!selectedAgreement || !genForm?.period_start || !genForm?.period_end) {
			periodCheckResult = null;
			return;
		}
		periodChecking = true;
		periodCheckResult = null;
		try {
			periodCheckResult = await api.get<CheckPeriodResult>(
				`/invoices/check-period?agreement_uuid=${selectedAgreement.agreement_uuid}&billing_period_start=${genForm.period_start}&billing_period_end=${genForm.period_end}`
			);
		} catch {
			periodCheckResult = null;
		} finally {
			periodChecking = false;
		}
	}

	async function previewInvoiceById(invoiceId: number) {
		try {
			const { html } = await api.get<{ html: string }>(`/invoices/${invoiceId}/preview`);
			const blob = new Blob([html], { type: 'text/html' });
			const url = URL.createObjectURL(blob);
			const win = window.open(url, '_blank');
			setTimeout(() => URL.revokeObjectURL(url), 10000);
			if (!win) alert('Allow pop-ups to preview invoices.');
		} catch (err: unknown) {
			alert(err instanceof Error ? err.message : 'Preview failed.');
		}
	}

	async function handleGenerate(e: SubmitEvent) {
		e.preventDefault();
		if (!selectedAgreement || !genForm) return;
		generating = true; generateError = '';
		try {
			const net = parseFloat(String(genForm.net)).toFixed(2);
			const vat = parseFloat(String(genForm.vat)).toFixed(2);
			const gross = (parseFloat(net) + parseFloat(vat)).toFixed(2);
			await api.post('/invoices', {
				invoice_number: genForm.invoice_number,
				agreement_uuid: selectedAgreement.agreement_uuid,
				invoice_type: 'standard',
				billing_period_start: genForm.period_start,
				billing_period_end: genForm.period_end,
				issue_date: genForm.issue_date,
				due_date: genForm.due_date,
				net_amount: net,
				vat_amount: vat,
				gross_amount: gross,
				invoice_status: 'pending',
			});
			showGenerateModal = false;
			load();
		} catch (err: unknown) {
			generateError = err instanceof Error ? err.message : 'Failed to generate invoice.';
		} finally { generating = false; }
	}

	async function handleDeleteInvoice(inv: Invoice) {
		if (!confirm(`Delete invoice ${inv.invoice_number}? This cannot be undone.`)) return;
		try {
			await api.delete(`/invoices/${inv.id}`);
			load();
		} catch (err: unknown) {
			alert(err instanceof Error ? err.message : 'Failed to delete invoice.');
		}
	}

	async function handleCredit(inv: Invoice) {
		if (!confirm(`Credit invoice ${inv.invoice_number}? This will mark the original as credited and create a credit note.`)) return;
		try {
			await api.post(`/invoices/${inv.id}/credit`, {});
			load();
		} catch (err: unknown) {
			alert(err instanceof Error ? err.message : 'Failed to credit invoice.');
		}
	}

	function openPayModal(inv: Invoice) {
		payingInvoice = inv;
		pay_date = today;
		pay_amount = inv.gross_amount;
		pay_method = 'bank_transfer';
		pay_reference = '';
		pay_notes = '';
		payError = '';
		showPayModal = true;
	}

	async function handleSend(inv: Invoice) {
		sendingInvoice = inv;
		sendError = '';
		sending = true;
		try {
			// 1. Fetch rendered HTML from backend
			const { html } = await api.get<{ html: string }>(`/invoices/${inv.id}/preview`);

			// 2. Generate PDF — pass HTML string directly; all styles are inline in the template
			//    so html2canvas captures everything without needing a <style> block.
			const html2pdf = (await import('html2pdf.js')).default;
			const pdfBlob: Blob = await html2pdf()
				.set({
					margin: 0,
					filename: `${inv.invoice_number}.pdf`,
					image: { type: 'jpeg', quality: 0.95 },
					html2canvas: { scale: 3, useCORS: true, logging: false, backgroundColor: '#ffffff', letterRendering: true },
					jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' },
				})
				.from(html)
				.outputPdf('blob');

			// 4. Convert blob to base64
			const base64 = await new Promise<string>((resolve, reject) => {
				const reader = new FileReader();
				reader.onloadend = () => resolve((reader.result as string).split(',')[1]);
				reader.onerror = reject;
				reader.readAsDataURL(pdfBlob);
			});

			// 5. Send to backend
			await api.post(`/invoices/${inv.id}/send`, {
				pdf_base64: base64,
				filename: `${inv.invoice_number}.pdf`,
				is_reminder: !!inv.pdf_s3_key,
			});

			load();
		} catch (err: unknown) {
			sendError = err instanceof Error ? err.message : 'Failed to send invoice.';
		} finally {
			sending = false;
			if (!sendError) sendingInvoice = null;
		}
	}

	async function handleDownload(inv: Invoice) {
		try {
			const token = getToken();
			const base = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/v1';
			const res = await fetch(`${base}/invoices/${inv.id}/download`, {
				headers: token ? { Authorization: `Bearer ${token}` } : {},
			});
			if (!res.ok) throw new Error(await res.text());
			const blob = await res.blob();
			const url = URL.createObjectURL(blob);
			const a = document.createElement('a');
			a.href = url;
			a.download = `${inv.invoice_number}.pdf`;
			document.body.appendChild(a);
			a.click();
			document.body.removeChild(a);
			URL.revokeObjectURL(url);
		} catch (err: unknown) {
			alert(err instanceof Error ? err.message : 'Failed to download invoice.');
		}
	}

	async function handlePay(e: SubmitEvent) {
		e.preventDefault();
		if (!payingInvoice) return;
		paying = true; payError = '';
		try {
			await api.post(`/invoices/${payingInvoice.id}/pay`, {
				payment_date: pay_date,
				amount_received: pay_amount,
				payment_method: pay_method,
				transaction_reference: pay_reference || null,
				notes: pay_notes || null,
			});
			showPayModal = false;
			load();
		} catch (err: unknown) {
			payError = err instanceof Error ? err.message : 'Failed to record payment.';
		} finally { paying = false; }
	}

	const statusBadge: Record<string, string> = {
		pending: 'bg-blue-500/10 text-blue-400',
		overdue: 'bg-red-500/10 text-red-400',
		paid: 'bg-emerald-500/10 text-emerald-400',
		credited: 'bg-white/5 text-white/40',
		draft: 'bg-white/5 text-white/40',
	};

	const inputClass = 'w-full rounded-xl border border-white/10 bg-[#1a1a1a] px-4 py-3 text-sm text-white placeholder-white/20 focus:border-indigo-500/50 focus:outline-none focus:ring-1 focus:ring-indigo-500/50 transition';
</script>

<svelte:window onclick={closeAction} />

<!-- Page header -->
<div class="mb-8 flex items-start justify-between">
	<div>
		<h2 class="text-2xl font-semibold text-white">Invoices</h2>
		<p class="mt-1 text-sm text-white/40">Generate, track, and manage invoices</p>
	</div>
	<button onclick={openBatchModal}
		class="rounded-xl bg-indigo-600 px-4 py-2.5 text-sm font-semibold text-white hover:bg-indigo-500 transition-colors">
		⚡ Run Batch Billing
	</button>
</div>

<!-- Active leases section -->
<div class="mb-8">
	<h3 class="mb-4 text-xs font-semibold uppercase tracking-wider text-white/30">Active Leases</h3>
	{#if activeAgreements.length === 0}
		<div class="rounded-2xl border border-white/[0.07] bg-[#111111] p-8 text-center">
			<p class="text-sm text-white/30">No active leases found.</p>
		</div>
	{:else}
		<div class="overflow-hidden rounded-2xl border border-white/[0.07] bg-[#111111]">
			<table class="w-full text-sm">
				<thead><tr class="border-b border-white/[0.07]">
					<th class="px-5 py-3.5 text-left text-xs font-medium uppercase tracking-wider text-white/30">Unit</th>
					<th class="px-5 py-3.5 text-left text-xs font-medium uppercase tracking-wider text-white/30">Lessee</th>
					<th class="px-5 py-3.5 text-left text-xs font-medium uppercase tracking-wider text-white/30">Rent</th>
					<th class="px-5 py-3.5 text-left text-xs font-medium uppercase tracking-wider text-white/30">Interval</th>
					<th class="px-5 py-3.5 text-left text-xs font-medium uppercase tracking-wider text-white/30">Lease End</th>
					<th class="px-5 py-3.5"></th>
				</tr></thead>
				<tbody>
					{#each activeAgreements as a}
					<tr class="border-b border-white/[0.04] hover:bg-white/[0.02] transition-colors">
						<td class="px-5 py-4 font-medium text-white">{unitLabel(a)}</td>
						<td class="px-5 py-4 text-white/60">{lesseeLabel(a.lessee_uuid)}</td>
						<td class="px-5 py-4 text-white/60">€ {Number(a.base_rent_amount).toLocaleString()}</td>
						<td class="px-5 py-4"><span class="rounded-md bg-white/5 px-2 py-1 text-xs capitalize text-white/60">{a.payment_interval}</span></td>
						<td class="px-5 py-4 text-xs text-white/40">{a.valid_time_end.slice(0,10)}</td>
						<td class="px-5 py-4 text-right">
							<button onclick={() => openGenerateModal(a)}
								class="rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-indigo-500 transition-colors">
								Generate Invoice
							</button>
						</td>
					</tr>
					{/each}
				</tbody>
			</table>
		</div>
	{/if}
</div>

<!-- Invoice ledger -->
<div>
	<div class="mb-4 flex items-center justify-between">
		<h3 class="text-xs font-semibold uppercase tracking-wider text-white/30">Invoice Ledger</h3>
		<div class="flex gap-1 rounded-xl bg-[#1a1a1a] p-1">
			{#each [['active','Pending / Overdue'],['paid','Paid'],['credited','Credited'],['all','All']] as [val, label]}
				<button onclick={() => (statusFilter = val)}
					class="rounded-lg px-3 py-1.5 text-xs font-medium transition
						{statusFilter === val ? 'bg-[#2a2a2a] text-white' : 'text-white/40 hover:text-white/70'}">
					{label}
				</button>
			{/each}
		</div>
	</div>

	{#if filteredInvoices.length === 0}
		<div class="rounded-2xl border border-white/[0.07] bg-[#111111] p-8 text-center">
			<p class="text-sm text-white/30">No invoices in this category.</p>
		</div>
	{:else}
		<div class="overflow-hidden rounded-2xl border border-white/[0.07] bg-[#111111]">
			<table class="w-full text-sm">
				<thead><tr class="border-b border-white/[0.07]">
					<th class="px-5 py-3.5 text-left text-xs font-medium uppercase tracking-wider text-white/30">Number / Lessee</th>
					<th class="px-5 py-3.5 text-left text-xs font-medium uppercase tracking-wider text-white/30">Period</th>
					<th class="px-5 py-3.5 text-left text-xs font-medium uppercase tracking-wider text-white/30">Due</th>
					<th class="px-5 py-3.5 text-right text-xs font-medium uppercase tracking-wider text-white/30">Amount</th>
					<th class="px-5 py-3.5 text-left text-xs font-medium uppercase tracking-wider text-white/30">Payment</th>
					<th class="px-5 py-3.5 text-left text-xs font-medium uppercase tracking-wider text-white/30">Email</th>
					<th class="px-5 py-3.5 text-right text-xs font-medium uppercase tracking-wider text-white/30">Actions</th>
				</tr></thead>
				<tbody>
					{#each filteredInvoices as inv}
					<tr class="border-b border-white/[0.04] hover:bg-white/[0.02] transition-colors">
						<td class="px-5 py-4">
							<p class="font-medium text-white">{inv.invoice_number}</p>
							<p class="mt-0.5 text-xs text-white/40">{lesseeLabel(agreements.find((a) => a.agreement_uuid === inv.agreement_uuid)?.lessee_uuid ?? '')}</p>
							{#if inv.invoice_type === 'credit_note'}
								<span class="mt-0.5 text-xs text-amber-400/70">Credit Note</span>
							{/if}
						</td>
						<td class="px-5 py-4 text-xs text-white/40">{inv.billing_period_start.slice(0,10)} → {inv.billing_period_end.slice(0,10)}</td>
						<td class="px-5 py-4 text-xs text-white/60">{inv.due_date.slice(0,10)}</td>
						<td class="px-5 py-4 text-right font-medium {Number(inv.gross_amount) < 0 ? 'text-red-400' : 'text-white'}">
							€ {Number(inv.gross_amount).toLocaleString('en', {minimumFractionDigits: 2})}
						</td>
						<td class="px-5 py-4">
							<span class="rounded-md px-2 py-1 text-xs capitalize {statusBadge[inv.invoice_status] ?? 'bg-white/5 text-white/40'}">
								{inv.invoice_status}
							</span>
						</td>
						<td class="px-5 py-4">
							{#if inv.email_delivery_status === 'delivered'}
								<span class="rounded-md bg-emerald-500/10 px-2 py-1 text-xs text-emerald-400">✓ Delivered</span>
							{:else if inv.email_delivery_status === 'opened'}
								<span class="rounded-md bg-indigo-500/10 px-2 py-1 text-xs text-indigo-400">👁 Opened</span>
							{:else if inv.email_delivery_status === 'bounced'}
								<span class="rounded-md bg-red-500/10 px-2 py-1 text-xs text-red-400">✕ Bounced</span>
							{:else if inv.email_delivery_status === 'sent'}
								<span class="rounded-md bg-white/5 px-2 py-1 text-xs text-white/30">Sent</span>
							{:else}
								<span class="text-xs text-white/20">—</span>
							{/if}
						</td>
						<td class="px-5 py-4 text-right">
							<div class="relative inline-block">
								<button
									onclick={() => toggleAction(inv.id)}
									class="rounded-lg border border-white/10 px-3 py-1.5 text-xs text-white/50 transition hover:border-white/20 hover:text-white/80"
								>
									Actions ▾
								</button>
								{#if openActionId === inv.id}
									<!-- svelte-ignore a11y_no_static_element_interactions -->
									<div
										class="fixed inset-0 z-40"
										onclick={closeAction}
										onkeydown={() => {}}
									></div>
									<div class="absolute right-0 top-full z-50 mt-1 w-64 overflow-hidden rounded-xl border border-white/10 bg-[#1a1a1a] shadow-2xl">
										<!-- Preview -->
										<button onclick={() => { previewInvoiceById(inv.id); closeAction(); }}
											class="flex w-full items-start gap-3 px-4 py-3 text-left transition hover:bg-white/5">
											<span class="mt-0.5 text-sm">🔍</span>
											<div>
												<p class="text-xs font-medium text-white">Preview</p>
												<p class="text-[11px] text-white/40">View the invoice in your browser.</p>
											</div>
										</button>
										{#if inv.invoice_status === 'pending' || inv.invoice_status === 'overdue'}
											<!-- Send / Reminder -->
											<button onclick={() => { handleSend(inv); closeAction(); }}
												disabled={sending && sendingInvoice?.id === inv.id}
												class="flex w-full items-start gap-3 px-4 py-3 text-left transition hover:bg-white/5 disabled:opacity-40">
												<span class="mt-0.5 text-sm">📨</span>
												<div>
													<p class="text-xs font-medium text-indigo-400">{inv.pdf_s3_key ? 'Send Reminder' : 'Send'}</p>
													<p class="text-[11px] text-white/40">{inv.pdf_s3_key ? 'Send email to remind lessee of overdue payment.' : 'Email this invoice as a PDF to the lessee.'}</p>
												</div>
											</button>
											<!-- Pay -->
											<button onclick={() => { openPayModal(inv); closeAction(); }}
												class="flex w-full items-start gap-3 px-4 py-3 text-left transition hover:bg-white/5">
												<span class="mt-0.5 text-sm">✅</span>
												<div>
													<p class="text-xs font-medium text-emerald-400">Pay</p>
													<p class="text-[11px] text-white/40">Mark invoice as paid.</p>
												</div>
											</button>
											<!-- Credit -->
											<button onclick={() => { handleCredit(inv); closeAction(); }}
												class="flex w-full items-start gap-3 px-4 py-3 text-left transition hover:bg-white/5">
												<span class="mt-0.5 text-sm">↩️</span>
												<div>
													<p class="text-xs font-medium text-amber-400">Credit</p>
													<p class="text-[11px] text-white/40">Send a credit note for the invoice.</p>
												</div>
											</button>
										{/if}
										{#if inv.pdf_s3_key}
											<!-- Download PDF -->
											<button onclick={() => { handleDownload(inv); closeAction(); }}
												class="flex w-full items-start gap-3 px-4 py-3 text-left transition hover:bg-white/5">
												<span class="mt-0.5 text-sm">⬇️</span>
												<div>
													<p class="text-xs font-medium text-white/60">Download PDF</p>
													<p class="text-[11px] text-white/40">Download the invoice PDF directly to your device.</p>
												</div>
											</button>
										{/if}
										{#if inv.invoice_status === 'pending'}
											<div class="border-t border-white/[0.07]"></div>
											<!-- Delete -->
											<button onclick={() => { handleDeleteInvoice(inv); closeAction(); }}
												class="flex w-full items-start gap-3 px-4 py-3 text-left transition hover:bg-red-500/10">
												<span class="mt-0.5 text-sm">🗑️</span>
												<div>
													<p class="text-xs font-medium text-red-400">Delete</p>
													<p class="text-[11px] text-white/40">Delete the invoice (if not sent yet).</p>
												</div>
											</button>
										{/if}
									</div>
								{/if}
							</div>
						</td>
					</tr>
					{/each}
				</tbody>
			</table>
		</div>
	{/if}
</div>

<!-- Generate Invoice Modal -->
{#if showGenerateModal}
<div class="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm">
	<div class="w-full max-w-2xl rounded-2xl border border-white/10 bg-[#111111] shadow-2xl">
		<div class="border-b border-white/[0.07] px-6 py-4">
			<h3 class="text-base font-semibold text-white">Generate Invoice</h3>
			{#if selectedAgreement}
				<p class="mt-0.5 text-sm text-white/40">{unitLabel(selectedAgreement)} · {lesseeLabel(selectedAgreement.lessee_uuid)}</p>
			{/if}
		</div>

		{#if genForm}
			<form onsubmit={handleGenerate}>
				<div class="space-y-4 p-6">
					<div class="grid grid-cols-2 gap-4">
						<div class="col-span-2">
							<label class="mb-1.5 block text-xs font-medium uppercase tracking-wider text-white/40">Invoice Number</label>
							<input type="text" bind:value={genForm.invoice_number} required placeholder="e.g. INV-2026-0001" class={inputClass} />
						</div>
						<div>
							<label class="mb-1.5 block text-xs font-medium uppercase tracking-wider text-white/40">Issue Date</label>
							<input type="date" bind:value={genForm.issue_date} required class={inputClass} />
						</div>
						<div>
							<label class="mb-1.5 block text-xs font-medium uppercase tracking-wider text-white/40">Due Date</label>
							<input type="date" bind:value={genForm.due_date} required class={inputClass} />
						</div>
						<div>
							<label class="mb-1.5 block text-xs font-medium uppercase tracking-wider text-white/40">Period Start</label>
							<input type="date" bind:value={genForm.period_start} required class={inputClass}
								onchange={checkPeriod} />
						</div>
						<div>
							<label class="mb-1.5 block text-xs font-medium uppercase tracking-wider text-white/40">Period End</label>
							<input type="date" bind:value={genForm.period_end} required class={inputClass}
								onchange={checkPeriod} />
						</div>
					</div>

					<!-- Period conflict warning -->
					{#if periodChecking}
						<p class="text-xs text-white/30">Checking period…</p>
					{:else if periodCheckResult?.already_invoiced}
						<div class="flex items-start justify-between gap-3 rounded-xl border border-amber-500/20 bg-amber-500/10 px-4 py-3">
							<p class="text-sm text-amber-400">
								This period is already covered by invoice <strong>{periodCheckResult.invoice_number}</strong>.
							</p>
							<button type="button"
								onclick={() => previewInvoiceById(periodCheckResult!.invoice_id!)}
								class="shrink-0 text-xs text-amber-400/70 hover:text-amber-300 transition-colors whitespace-nowrap">
								Preview →
							</button>
						</div>
					{/if}

					<div class="rounded-xl border border-white/[0.07] bg-[#1a1a1a] p-4">
						<div class="grid grid-cols-3 gap-4">
							<div>
								<label class="mb-1.5 block text-xs font-medium uppercase tracking-wider text-white/40">Net</label>
								<input type="number" step="0.01" bind:value={genForm.net} required class={inputClass} />
							</div>
							<div>
								<label class="mb-1.5 block text-xs font-medium uppercase tracking-wider text-white/40">VAT</label>
								<input type="number" step="0.01" bind:value={genForm.vat} required class={inputClass} />
							</div>
							<div>
								<label class="mb-1.5 block text-xs font-medium uppercase tracking-wider text-white/40">Gross</label>
								<input type="number" step="0.01" bind:value={genForm.gross} required class={inputClass} />
							</div>
						</div>
					</div>

					{#if generateError}
						<div class="rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3">
							<p class="text-sm text-red-400">{generateError}</p>
						</div>
					{/if}
				</div>

				<div class="flex justify-end gap-3 border-t border-white/[0.07] px-6 py-4">
					<button type="button" onclick={() => (showGenerateModal = false)}
						class="rounded-xl border border-white/10 px-5 py-2 text-sm text-white/50 hover:text-white transition-colors">
						Cancel
					</button>
					<button type="submit" disabled={generating}
						class="rounded-xl bg-indigo-600 px-5 py-2 text-sm font-semibold text-white hover:bg-indigo-500 disabled:opacity-40 transition-colors">
						{generating ? 'Issuing…' : 'Issue Invoice'}
					</button>
				</div>
			</form>
		{/if}
	</div>
</div>
{/if}

<!-- Mark as Paid Modal -->
{#if showPayModal && payingInvoice}
<div class="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm">
	<div class="w-full max-w-xl rounded-2xl border border-white/10 bg-[#111111] shadow-2xl">
		<div class="border-b border-white/[0.07] px-6 py-4">
			<h3 class="text-base font-semibold text-white">Record Payment</h3>
			<p class="mt-0.5 text-sm text-white/40">{payingInvoice.invoice_number} · € {Number(payingInvoice.gross_amount).toLocaleString('en', {minimumFractionDigits: 2})}</p>
		</div>

		<form onsubmit={handlePay}>
			<div class="space-y-4 p-6">
				<div class="grid grid-cols-2 gap-4">
					<div>
						<label class="mb-1.5 block text-xs font-medium uppercase tracking-wider text-white/40">Payment Date</label>
						<input type="date" bind:value={pay_date} required class={inputClass} />
					</div>
					<div>
						<label class="mb-1.5 block text-xs font-medium uppercase tracking-wider text-white/40">Amount Received</label>
						<input type="number" step="0.01" bind:value={pay_amount} required class={inputClass} />
					</div>
				</div>

				<div>
					<label class="mb-1.5 block text-xs font-medium uppercase tracking-wider text-white/40">Payment Method</label>
					<select bind:value={pay_method} class={inputClass}>
						<option value="bank_transfer">Bank Transfer</option>
						<option value="direct_debit">Direct Debit</option>
						<option value="stripe">Stripe</option>
						<option value="cash">Cash</option>
						<option value="other">Other</option>
					</select>
				</div>

				<div>
					<label class="mb-1.5 block text-xs font-medium uppercase tracking-wider text-white/40">Transaction Reference <span class="normal-case font-normal text-white/20">(optional)</span></label>
					<input type="text" bind:value={pay_reference} placeholder="Bank ref / transaction ID" class={inputClass} />
				</div>

				<div>
					<label class="mb-1.5 block text-xs font-medium uppercase tracking-wider text-white/40">Notes <span class="normal-case font-normal text-white/20">(optional)</span></label>
					<input type="text" bind:value={pay_notes} class={inputClass} />
				</div>

				{#if payError}
					<div class="rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3">
						<p class="text-sm text-red-400">{payError}</p>
					</div>
				{/if}
			</div>

			<div class="flex justify-end gap-3 border-t border-white/[0.07] px-6 py-4">
				<button type="button" onclick={() => (showPayModal = false)}
					class="rounded-xl border border-white/10 px-5 py-2 text-sm text-white/50 hover:text-white transition-colors">
					Cancel
				</button>
				<button type="submit" disabled={paying}
					class="rounded-xl bg-emerald-600 px-5 py-2 text-sm font-semibold text-white hover:bg-emerald-500 disabled:opacity-40 transition-colors">
					{paying ? 'Saving…' : 'Mark as Paid'}
				</button>
			</div>
		</form>
	</div>
</div>
{/if}

<!-- Send error toast -->
{#if sendError}
<div class="fixed bottom-6 right-6 z-50 max-w-sm rounded-2xl border border-red-500/20 bg-[#1a1a1a] p-4 shadow-2xl">
	<p class="text-sm font-medium text-red-400">Failed to send invoice</p>
	<p class="mt-1 text-xs text-white/50">{sendError}</p>
	<button onclick={() => { sendError = ''; sendingInvoice = null; }}
		class="mt-3 text-xs text-white/40 hover:text-white transition-colors">Dismiss</button>
</div>
{/if}

<!-- Sending overlay -->
{#if sending}
<div class="fixed inset-0 z-40 flex items-center justify-center bg-black/50 backdrop-blur-sm">
	<div class="flex flex-col items-center gap-4 rounded-2xl border border-white/10 bg-[#111111] px-10 py-8">
		<div class="h-6 w-6 animate-spin rounded-full border-2 border-white/10 border-t-indigo-400"></div>
		<p class="text-sm text-white/60">{sendingInvoice?.pdf_s3_key ? 'Generating PDF and sending reminder…' : 'Generating PDF and sending invoice…'}</p>
	</div>
</div>
{/if}

<!-- ── Batch Billing Modal ─────────────────────────────────────────────── -->
{#if showBatchModal}
<div class="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
	<div class="w-full max-w-4xl rounded-2xl border border-white/10 bg-[#111111] shadow-2xl flex flex-col max-h-[90vh]">

		<!-- Header -->
		<div class="flex items-center justify-between border-b border-white/[0.07] px-6 py-4 shrink-0">
			<div>
				<h3 class="text-base font-semibold text-white">Batch Billing Run</h3>
				<p class="mt-0.5 text-xs text-white/40">
					{#if batchStep === 'period'}Select the billing period{/if}
					{#if batchStep === 'review'}Review and adjust before generating{/if}
					{#if batchStep === 'generating'}Creating invoices…{/if}
					{#if batchStep === 'done'}{batchCreated.length} invoice{batchCreated.length !== 1 ? 's' : ''} created{/if}
				</p>
			</div>
			{#if batchStep !== 'generating'}
				<button onclick={() => { showBatchModal = false; }} class="text-white/30 hover:text-white transition-colors text-lg">✕</button>
			{/if}
		</div>

		<!-- Body -->
		<div class="overflow-y-auto flex-1 px-6 py-5">

			<!-- Step 1: Period picker -->
			{#if batchStep === 'period'}
			<div class="max-w-sm mx-auto py-4 space-y-6">
				<div>
					<label class="mb-2 block text-xs font-semibold uppercase tracking-wider text-white/40">Billing Month</label>
					<div class="grid grid-cols-2 gap-3">
						<select bind:value={batchMonth}
							class="rounded-xl border border-white/10 bg-[#1a1a1a] px-4 py-3 text-sm text-white focus:border-indigo-500/50 focus:outline-none transition">
							{#each MONTHS as m, i}
								<option value={i + 1}>{m}</option>
							{/each}
						</select>
						<input type="number" bind:value={batchYear} min="2020" max="2040"
							class="rounded-xl border border-white/10 bg-[#1a1a1a] px-4 py-3 text-sm text-white focus:border-indigo-500/50 focus:outline-none transition" />
					</div>
					<p class="mt-3 text-xs text-white/30">
						Invoices will be generated for all active leases that haven't been billed for <strong class="text-white/50">{MONTHS[batchMonth - 1]} {batchYear}</strong> yet.
					</p>
				</div>
				{#if batchError}
					<div class="rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3">
						<p class="text-sm text-red-400">{batchError}</p>
					</div>
				{/if}
			</div>
			{/if}

			<!-- Step 2: Review table -->
			{#if batchStep === 'review'}
			{#if batchRows.length === 0}
				<div class="py-10 text-center">
					<p class="text-sm text-white/30">No active leases found for this period.</p>
				</div>
			{:else}
				<div class="overflow-x-auto">
					<table class="w-full text-sm">
						<thead>
							<tr class="border-b border-white/[0.07]">
								<th class="pb-3 pr-3 text-left"><input type="checkbox"
									checked={batchRows.filter(r => !r.already_invoiced).every(r => r.included)}
									onchange={(e) => { const v = (e.target as HTMLInputElement).checked; batchRows = batchRows.map(r => r.already_invoiced ? r : {...r, included: v}); }}
									class="rounded accent-indigo-500" /></th>
								<th class="pb-3 pr-4 text-left text-xs font-medium uppercase tracking-wider text-white/30">Unit / Lessee</th>
								<th class="pb-3 pr-4 text-left text-xs font-medium uppercase tracking-wider text-white/30">Period</th>
								<th class="pb-3 pr-4 text-left text-xs font-medium uppercase tracking-wider text-white/30">Invoice #</th>
								<th class="pb-3 pr-4 text-right text-xs font-medium uppercase tracking-wider text-white/30">Net</th>
								<th class="pb-3 pr-4 text-right text-xs font-medium uppercase tracking-wider text-white/30">VAT</th>
								<th class="pb-3 text-right text-xs font-medium uppercase tracking-wider text-white/30">Gross</th>
							</tr>
						</thead>
						<tbody>
							{#each batchRows as row, i}
							<tr class="border-b border-white/[0.04] {row.already_invoiced ? 'opacity-40' : ''}">
								<td class="py-3 pr-3">
									<input type="checkbox" bind:checked={batchRows[i].included}
										disabled={row.already_invoiced}
										class="rounded accent-indigo-500" />
								</td>
								<td class="py-3 pr-4">
									<p class="font-medium text-white text-xs">{row.unit_label}</p>
									<p class="text-white/40 text-xs">{row.lessee_name}</p>
									{#if row.already_invoiced}
										<span class="text-xs text-amber-400/70">Already invoiced</span>
									{/if}
								</td>
								<td class="py-3 pr-4 text-xs text-white/50">
									{row.billing_period_start.slice(0,10)}<br>→ {row.billing_period_end.slice(0,10)}
								</td>
								<td class="py-3 pr-4">
									<input type="text" bind:value={batchRows[i].invoice_number}
										disabled={row.already_invoiced}
										class="w-32 rounded-lg border border-white/10 bg-[#1a1a1a] px-2 py-1.5 text-xs text-white focus:border-indigo-500/50 focus:outline-none disabled:opacity-40 transition" />
								</td>
								<td class="py-3 pr-4">
									<input type="number" step="0.01" bind:value={batchRows[i].net}
										disabled={row.already_invoiced}
										class="w-24 rounded-lg border border-white/10 bg-[#1a1a1a] px-2 py-1.5 text-xs text-white text-right focus:border-indigo-500/50 focus:outline-none disabled:opacity-40 transition" />
								</td>
								<td class="py-3 pr-4">
									<input type="number" step="0.01" bind:value={batchRows[i].vat}
										disabled={row.already_invoiced}
										class="w-24 rounded-lg border border-white/10 bg-[#1a1a1a] px-2 py-1.5 text-xs text-white text-right focus:border-indigo-500/50 focus:outline-none disabled:opacity-40 transition" />
								</td>
								<td class="py-3 text-right text-xs font-medium text-white">
									{(parseFloat(row.net || '0') + parseFloat(row.vat || '0')).toLocaleString('en', {minimumFractionDigits: 2})}
								</td>
							</tr>
							{/each}
						</tbody>
					</table>
				</div>
				{#if batchError}
					<div class="mt-4 rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3">
						<p class="text-sm text-red-400">{batchError}</p>
					</div>
				{/if}
			{/if}
			{/if}

			<!-- Step 3: Generating progress -->
			{#if batchStep === 'generating'}
			<div class="flex flex-col items-center justify-center py-12 gap-5">
				<div class="h-7 w-7 animate-spin rounded-full border-2 border-white/10 border-t-indigo-400"></div>
				<p class="text-sm text-white/60">Creating invoices…</p>
				<div class="w-64 rounded-full bg-white/5 h-1.5 overflow-hidden">
					<div class="h-full bg-indigo-500 rounded-full transition-all duration-300"
						style="width:{batchGenTotal ? (batchGenProgress / batchGenTotal * 100) : 0}%"></div>
				</div>
			</div>
			{/if}

			<!-- Step 4: Done — preview / exclude / send controls -->
			{#if batchStep === 'done'}
			<div class="space-y-2">
				{#each batchCreated as inv, i}
				<div class="rounded-xl border px-4 py-3 transition-colors {inv._excluded ? 'border-white/[0.04] bg-[#111111] opacity-50' : 'border-white/[0.07] bg-[#1a1a1a]'}">
					<div class="flex items-center justify-between gap-4">
						<div class="min-w-0">
							<p class="text-sm font-medium {inv._excluded ? 'text-white/40 line-through' : 'text-white'}">{inv.invoice_number}</p>
							<p class="text-xs text-white/40">{inv.billing_period_start.slice(0,10)} → {inv.billing_period_end.slice(0,10)}</p>
						</div>
						<div class="flex items-center gap-4 shrink-0">
							<span class="text-sm font-medium text-white/70">€ {Number(inv.gross_amount).toLocaleString('en', {minimumFractionDigits: 2})}</span>
							{#if !inv._sent}
								<button onclick={() => previewCreatedInvoice(inv)} disabled={inv._previewing}
									class="text-xs text-white/40 hover:text-white disabled:opacity-40 transition-colors whitespace-nowrap">
									{inv._previewing ? '…' : '🔍 Preview'}
								</button>
							{/if}
							{#if inv._sent}
								<span class="text-xs text-emerald-400 whitespace-nowrap">✓ Sent</span>
							{:else if inv._sendError}
								<span class="text-xs text-red-400 max-w-[140px] truncate" title={inv._sendError}>{inv._sendError}</span>
							{:else if inv._sending}
								<div class="h-3.5 w-3.5 animate-spin rounded-full border border-white/10 border-t-indigo-400"></div>
							{:else if !inv._excluded}
								<button onclick={() => sendCreatedInvoice(inv)} class="text-xs text-indigo-400 hover:text-indigo-300 transition-colors whitespace-nowrap">Send</button>
							{/if}
							{#if !inv._sent}
								<button onclick={() => { batchCreated[i]._excluded = !batchCreated[i]._excluded; batchCreated = [...batchCreated]; }}
									class="text-xs transition-colors whitespace-nowrap {inv._excluded ? 'text-amber-400/70 hover:text-amber-400' : 'text-white/20 hover:text-red-400/70'}">
									{inv._excluded ? '+ Include' : '✕ Exclude'}
								</button>
							{/if}
						</div>
					</div>
					{#if inv._sendError}<p class="mt-1.5 text-xs text-red-400/70">{inv._sendError}</p>{/if}
				</div>
				{/each}
			</div>
			{/if}

		</div><!-- /body -->

		<!-- Footer -->
		<div class="flex items-center justify-between border-t border-white/[0.07] px-6 py-4 shrink-0">
			<div class="text-xs text-white/30">
				{#if batchStep === 'review'}
					{batchRows.filter(r => r.included && !r.already_invoiced).length} invoice{batchRows.filter(r => r.included && !r.already_invoiced).length !== 1 ? 's' : ''} selected
				{/if}
			</div>
			<div class="flex gap-3">
				{#if batchStep === 'period'}
					<button onclick={() => { showBatchModal = false; }}
						class="rounded-xl border border-white/10 px-5 py-2 text-sm text-white/50 hover:text-white transition-colors">Cancel</button>
					<button onclick={loadBatchPreview} disabled={batchLoading}
						class="rounded-xl bg-indigo-600 px-5 py-2 text-sm font-semibold text-white hover:bg-indigo-500 disabled:opacity-40 transition-colors">
						{batchLoading ? 'Loading…' : 'Preview →'}
					</button>
				{/if}
				{#if batchStep === 'review'}
					<button onclick={() => { batchStep = 'period'; batchError = ''; }}
						class="rounded-xl border border-white/10 px-5 py-2 text-sm text-white/50 hover:text-white transition-colors">← Back</button>
					<button onclick={runBatchGenerate}
						disabled={batchRows.filter(r => r.included && !r.already_invoiced).length === 0}
						class="rounded-xl bg-indigo-600 px-5 py-2 text-sm font-semibold text-white hover:bg-indigo-500 disabled:opacity-40 transition-colors">
						Generate {batchRows.filter(r => r.included && !r.already_invoiced).length} Invoice{batchRows.filter(r => r.included && !r.already_invoiced).length !== 1 ? 's' : ''}
					</button>
				{/if}
				{#if batchStep === 'done'}
					<button onclick={() => { showBatchModal = false; }}
						class="rounded-xl border border-white/10 px-5 py-2 text-sm text-white/50 hover:text-white transition-colors">Close</button>
					{#if batchCreated.some(i => !i._sent && !i._excluded)}
						<button onclick={sendAllCreated} disabled={batchSendingAll}
							class="rounded-xl bg-indigo-600 px-5 py-2 text-sm font-semibold text-white hover:bg-indigo-500 disabled:opacity-40 transition-colors">
							{batchSendingAll ? 'Sending…' : `Send All (${batchCreated.filter(i => !i._sent && !i._excluded).length})`}
						</button>
					{/if}
				{/if}
			</div>
		</div>

	</div>
</div>
{/if}
