<script lang="ts">
	import { browser } from '$app/environment';
	import { api } from '$lib/api/client';

	type Settings = {
		reporting_preference: 'monthly' | 'quarterly';
		vat_consultant_email: string | null;
		currency: string;
	};

	type VATInvoiceLine = {
		invoice_number: string;
		issue_date: string;
		billing_period_start: string;
		billing_period_end: string;
		lessee_name: string;
		unit_label: string;
		net_amount: string;
		vat_amount: string;
		gross_amount: string;
		invoice_type: string;
	};

	type VATExpenseLine = {
		expense_date: string;
		vendor_name: string;
		expense_category: string;
		description: string;
		net_amount: string;
		vat_amount: string;
		gross_amount: string;
	};

	type VATReport = {
		period_start: string;
		period_end: string;
		invoices: VATInvoiceLine[];
		expenses: VATExpenseLine[];
		invoice_net_total: string;
		invoice_vat_total: string;
		expense_net_total: string;
		expense_vat_total: string;
		vat_due: string;
	};

	// --- State ---
	let reportingPref: 'monthly' | 'quarterly' = $state('quarterly');
	let consultantEmail: string | null = $state(null);
	let currency = $state('EUR');

	// Period selection
	let selectedYear = $state(new Date().getFullYear());
	let selectedMonth = $state(new Date().getMonth() + 1); // 1-indexed
	let selectedQuarter = $state(Math.ceil((new Date().getMonth() + 1) / 3));

	let report: VATReport | null = $state(null);
	let loading = $state(false);
	let error = $state('');

	let exporting = $state(false);
	let exportError = $state('');
	let exportSuccess = $state('');

	let sending = $state(false);
	let sendError = $state('');
	let sendSuccess = $state('');

	// --- Computed period ---
	function periodBounds(): { start: string; end: string } {
		if (reportingPref === 'monthly') {
			const start = `${selectedYear}-${String(selectedMonth).padStart(2, '0')}-01`;
			const lastDay = new Date(selectedYear, selectedMonth, 0).getDate();
			const end = `${selectedYear}-${String(selectedMonth).padStart(2, '0')}-${String(lastDay).padStart(2, '0')}`;
			return { start, end };
		} else {
			const startMonth = (selectedQuarter - 1) * 3 + 1;
			const endMonth = startMonth + 2;
			const start = `${selectedYear}-${String(startMonth).padStart(2, '0')}-01`;
			const lastDay = new Date(selectedYear, endMonth, 0).getDate();
			const end = `${selectedYear}-${String(endMonth).padStart(2, '0')}-${String(lastDay).padStart(2, '0')}`;
			return { start, end };
		}
	}

	function periodLabel(): string {
		const { start, end } = periodBounds();
		if (reportingPref === 'monthly') {
			return new Date(start + 'T00:00:00').toLocaleString('default', { month: 'long', year: 'numeric' });
		}
		return `Q${selectedQuarter} ${selectedYear} (${start} → ${end})`;
	}

	// --- Load settings ---
	if (browser) {
		api.get<Settings>('/settings').then((s) => {
			reportingPref = s.reporting_preference ?? 'quarterly';
			consultantEmail = s.vat_consultant_email ?? null;
			currency = s.currency ?? 'EUR';
		}).catch(() => {});
	}

	async function loadReport() {
		loading = true; error = ''; report = null;
		const { start, end } = periodBounds();
		try {
			report = await api.get<VATReport>(`/vat-report?period_start=${start}&period_end=${end}`);
		} catch (e: unknown) {
			error = e instanceof Error ? e.message : 'Failed to load report.';
		} finally {
			loading = false;
		}
	}

	async function exportReport() {
		exporting = true; exportError = ''; exportSuccess = '';
		const { start, end } = periodBounds();
		try {
			const token = localStorage.getItem('token');
			const res = await fetch(`${import.meta.env.VITE_API_BASE_URL}/vat-report/export`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					...(token ? { Authorization: `Bearer ${token}` } : {}),
				},
				body: JSON.stringify({ period_start: start, period_end: end, upload_to_documents: true }),
			});
			if (!res.ok) {
				const err = await res.json().catch(() => ({ detail: 'Export failed' }));
				throw new Error(err.detail);
			}
			const data = await res.json() as { download_url: string };
			// Trigger browser download
			const a = document.createElement('a');
			a.href = data.download_url;
			a.download = `VAT-Report-${start}-${end}.xlsx`;
			document.body.appendChild(a);
			a.click();
			document.body.removeChild(a);
			exportSuccess = 'Excel file downloaded and saved to Documents → VAT Reports.';
		} catch (e: unknown) {
			exportError = e instanceof Error ? e.message : 'Export failed.';
		} finally {
			exporting = false;
		}
	}

	async function sendReport() {
		sending = true; sendError = ''; sendSuccess = '';
		const { start, end } = periodBounds();
		try {
			await api.post('/vat-report/send', { period_start: start, period_end: end });
			sendSuccess = `Report sent to ${consultantEmail}.`;
		} catch (e: unknown) {
			sendError = e instanceof Error ? e.message : 'Send failed.';
		} finally {
			sending = false;
		}
	}

	function fmt(v: string | number | null | undefined): string {
		if (v === null || v === undefined || v === '') return '—';
		const n = Number(v);
		if (isNaN(n)) return '—';
		return n.toLocaleString('de-DE', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
	}

	const months = ['January','February','March','April','May','June','July','August','September','October','November','December'];
	const currentYear = new Date().getFullYear();
	const years = [currentYear - 2, currentYear - 1, currentYear, currentYear + 1];
</script>

<div class="mb-8 flex items-center justify-between">
	<div>
		<h2 class="text-2xl font-semibold text-white">VAT Report</h2>
		<p class="mt-1 text-sm text-white/40">Calculate and export VAT due for a period</p>
	</div>
</div>

<!-- Period picker -->
<div class="mb-6 rounded-2xl border border-white/[0.07] bg-[#111111] p-6">
	<h3 class="mb-4 text-xs font-semibold uppercase tracking-wider text-white/30">Select Period</h3>

	<div class="flex flex-wrap items-end gap-4">
		<!-- Year -->
		<div>
			<label class="mb-1.5 block text-xs font-medium uppercase tracking-wider text-white/40">Year</label>
			<select bind:value={selectedYear}
				class="rounded-xl border border-white/10 bg-[#1a1a1a] px-4 py-2.5 text-sm text-white focus:border-indigo-500/50 focus:outline-none">
				{#each years as y}
					<option value={y}>{y}</option>
				{/each}
			</select>
		</div>

		{#if reportingPref === 'monthly'}
			<div>
				<label class="mb-1.5 block text-xs font-medium uppercase tracking-wider text-white/40">Month</label>
				<select bind:value={selectedMonth}
					class="rounded-xl border border-white/10 bg-[#1a1a1a] px-4 py-2.5 text-sm text-white focus:border-indigo-500/50 focus:outline-none">
					{#each months as m, i}
						<option value={i + 1}>{m}</option>
					{/each}
				</select>
			</div>
		{:else}
			<div>
				<label class="mb-1.5 block text-xs font-medium uppercase tracking-wider text-white/40">Quarter</label>
				<select bind:value={selectedQuarter}
					class="rounded-xl border border-white/10 bg-[#1a1a1a] px-4 py-2.5 text-sm text-white focus:border-indigo-500/50 focus:outline-none">
					<option value={1}>Q1 (Jan – Mar)</option>
					<option value={2}>Q2 (Apr – Jun)</option>
					<option value={3}>Q3 (Jul – Sep)</option>
					<option value={4}>Q4 (Oct – Dec)</option>
				</select>
			</div>
		{/if}

		<button onclick={loadReport} disabled={loading}
			class="rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-indigo-500 disabled:opacity-40 transition-colors">
			{loading ? 'Loading…' : 'Generate Report'}
		</button>
	</div>

	{#if error}
		<p class="mt-3 text-sm text-red-400">{error}</p>
	{/if}
</div>

{#if report}
<!-- Summary cards -->
<div class="mb-6 grid grid-cols-2 gap-4 sm:grid-cols-4">
	{#each [
		{ label: 'Invoice Net', value: report.invoice_net_total, color: 'text-white' },
		{ label: 'VAT Collected', value: report.invoice_vat_total, color: 'text-indigo-400' },
		{ label: 'Expense VAT (Reclaimable)', value: report.expense_vat_total, color: 'text-amber-400' },
		{ label: 'Net VAT Due', value: report.vat_due, color: Number(report.vat_due) >= 0 ? 'text-red-400' : 'text-emerald-400' },
	] as card}
		<div class="rounded-2xl border border-white/[0.07] bg-[#111111] p-5">
			<p class="text-xs font-medium uppercase tracking-wider text-white/30">{card.label}</p>
			<p class="mt-2 text-xl font-semibold {card.color}">{currency} {fmt(card.value)}</p>
		</div>
	{/each}
</div>

<!-- Actions -->
<div class="mb-6 flex flex-wrap items-center gap-3">
	<button onclick={exportReport} disabled={exporting}
		class="rounded-xl bg-emerald-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-emerald-500 disabled:opacity-40 transition-colors">
		{exporting ? 'Exporting…' : '⬇ Export Excel'}
	</button>

	{#if consultantEmail}
		<button onclick={sendReport} disabled={sending}
			class="rounded-xl border border-white/10 bg-white/5 px-5 py-2.5 text-sm font-semibold text-white/70 hover:bg-white/10 disabled:opacity-40 transition-colors">
			{sending ? 'Sending…' : `✉ Send to Consultant`}
		</button>
		<span class="text-xs text-white/30">{consultantEmail}</span>
	{:else}
		<span class="text-xs text-white/25">No consultant email set — add one in Settings.</span>
	{/if}

	{#if exportSuccess}
		<span class="text-xs text-emerald-400">{exportSuccess}</span>
	{/if}
	{#if exportError}
		<span class="text-xs text-red-400">{exportError}</span>
	{/if}
	{#if sendSuccess}
		<span class="text-xs text-emerald-400">{sendSuccess}</span>
	{/if}
	{#if sendError}
		<span class="text-xs text-red-400">{sendError}</span>
	{/if}
</div>

<!-- Invoices table -->
<div class="mb-6">
	<h3 class="mb-3 text-sm font-semibold text-white/60">
		Invoices Issued — {periodLabel()}
		<span class="ml-2 rounded-md bg-white/5 px-2 py-0.5 text-xs text-white/40">{report.invoices.length} invoices</span>
	</h3>

	{#if report.invoices.length === 0}
		<div class="rounded-2xl border border-white/[0.07] bg-[#111111] p-8 text-center">
			<p class="text-sm text-white/30">No invoices issued in this period.</p>
		</div>
	{:else}
		<div class="overflow-hidden rounded-2xl border border-white/[0.07] bg-[#111111]">
			<table class="w-full text-sm">
				<thead><tr class="border-b border-white/[0.07]">
					<th class="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-white/30">Invoice No.</th>
					<th class="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-white/30">Issue Date</th>
					<th class="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-white/30">Lessee</th>
					<th class="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-white/30">Unit</th>
					<th class="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-white/30">Billing Period</th>
					<th class="px-4 py-3 text-right text-xs font-medium uppercase tracking-wider text-white/30">Net</th>
					<th class="px-4 py-3 text-right text-xs font-medium uppercase tracking-wider text-white/30">VAT</th>
					<th class="px-4 py-3 text-right text-xs font-medium uppercase tracking-wider text-white/30">Gross</th>
				</tr></thead>
				<tbody>
					{#each report.invoices as inv}
					<tr class="border-b border-white/[0.04] hover:bg-white/[0.02] transition-colors {inv.invoice_type === 'credit_note' ? 'text-amber-400/80' : ''}">
						<td class="px-4 py-3 font-mono text-xs text-white/80">{inv.invoice_number}</td>
						<td class="px-4 py-3 text-white/50 text-xs">{inv.issue_date}</td>
						<td class="px-4 py-3 text-white/70">{inv.lessee_name}</td>
						<td class="px-4 py-3 text-white/50 text-xs">{inv.unit_label}</td>
						<td class="px-4 py-3 text-white/50 text-xs">{inv.billing_period_start} → {inv.billing_period_end}</td>
						<td class="px-4 py-3 text-right text-white/70">{fmt(inv.net_amount)}</td>
						<td class="px-4 py-3 text-right text-white/70">{fmt(inv.vat_amount)}</td>
						<td class="px-4 py-3 text-right text-white/80 font-medium">{fmt(inv.gross_amount)}</td>
					</tr>
					{/each}
					<tr class="bg-white/[0.02]">
						<td colspan="5" class="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-white/30">Total</td>
						<td class="px-4 py-3 text-right font-semibold text-white">{fmt(report.invoice_net_total)}</td>
						<td class="px-4 py-3 text-right font-semibold text-indigo-400">{fmt(report.invoice_vat_total)}</td>
						<td class="px-4 py-3 text-right font-semibold text-white">{fmt(Number(report.invoice_net_total) + Number(report.invoice_vat_total))}</td>
					</tr>
				</tbody>
			</table>
		</div>
	{/if}
</div>

<!-- Expenses table -->
<div class="mb-6">
	<h3 class="mb-3 text-sm font-semibold text-white/60">
		Expenses Incurred — {periodLabel()}
		<span class="ml-2 rounded-md bg-white/5 px-2 py-0.5 text-xs text-white/40">{report.expenses.length} expenses</span>
	</h3>

	{#if report.expenses.length === 0}
		<div class="rounded-2xl border border-white/[0.07] bg-[#111111] p-8 text-center">
			<p class="text-sm text-white/30">No expenses recorded in this period.</p>
		</div>
	{:else}
		<div class="overflow-hidden rounded-2xl border border-white/[0.07] bg-[#111111]">
			<table class="w-full text-sm">
				<thead><tr class="border-b border-white/[0.07]">
					<th class="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-white/30">Date</th>
					<th class="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-white/30">Vendor</th>
					<th class="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-white/30">Category</th>
					<th class="px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-white/30">Description</th>
					<th class="px-4 py-3 text-right text-xs font-medium uppercase tracking-wider text-white/30">Net</th>
					<th class="px-4 py-3 text-right text-xs font-medium uppercase tracking-wider text-white/30">VAT</th>
					<th class="px-4 py-3 text-right text-xs font-medium uppercase tracking-wider text-white/30">Gross</th>
				</tr></thead>
				<tbody>
					{#each report.expenses as exp}
					<tr class="border-b border-white/[0.04] hover:bg-white/[0.02] transition-colors">
						<td class="px-4 py-3 text-white/50 text-xs">{exp.expense_date}</td>
						<td class="px-4 py-3 text-white/70">{exp.vendor_name}</td>
						<td class="px-4 py-3"><span class="rounded-md bg-white/5 px-2 py-0.5 text-xs text-white/50">{exp.expense_category}</span></td>
						<td class="px-4 py-3 text-white/50 text-xs max-w-xs truncate">{exp.description}</td>
						<td class="px-4 py-3 text-right text-white/70">{fmt(exp.net_amount)}</td>
						<td class="px-4 py-3 text-right text-amber-400/80">{fmt(exp.vat_amount)}</td>
						<td class="px-4 py-3 text-right text-white/80 font-medium">{fmt(exp.gross_amount)}</td>
					</tr>
					{/each}
					<tr class="bg-white/[0.02]">
						<td colspan="4" class="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-white/30">Total</td>
						<td class="px-4 py-3 text-right font-semibold text-white">{fmt(report.expense_net_total)}</td>
						<td class="px-4 py-3 text-right font-semibold text-amber-400">{fmt(report.expense_vat_total)}</td>
						<td class="px-4 py-3 text-right font-semibold text-white">{fmt(Number(report.expense_net_total) + Number(report.expense_vat_total))}</td>
					</tr>
				</tbody>
			</table>
		</div>
	{/if}
</div>

<!-- VAT summary box -->
<div class="rounded-2xl border border-indigo-500/20 bg-indigo-500/5 p-6">
	<h3 class="mb-4 text-xs font-semibold uppercase tracking-wider text-indigo-400/60">VAT Calculation Summary</h3>
	<div class="space-y-2 text-sm">
		<div class="flex justify-between">
			<span class="text-white/50">VAT collected on invoices</span>
			<span class="font-medium text-white">{currency} {fmt(report.invoice_vat_total)}</span>
		</div>
		<div class="flex justify-between">
			<span class="text-white/50">VAT reclaimable on expenses</span>
			<span class="font-medium text-amber-400">– {currency} {fmt(report.expense_vat_total)}</span>
		</div>
		<div class="mt-3 flex justify-between border-t border-white/10 pt-3">
			<span class="font-semibold text-white">Net VAT {Number(report.vat_due) >= 0 ? 'Due' : 'Refundable'}</span>
			<span class="text-lg font-bold {Number(report.vat_due) >= 0 ? 'text-red-400' : 'text-emerald-400'}">
				{currency} {fmt(Math.abs(Number(report.vat_due)))}
			</span>
		</div>
	</div>
</div>
{/if}
