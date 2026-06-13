<script lang="ts">
	import { browser } from '$app/environment';
	import { api } from '$lib/api/client';

	// ── Types ────────────────────────────────────────────────────────────────

	type Property = {
		id: number;
		name: string;
		address: string;
	};

	type Expense = {
		id: number;
		property_id: number;
		expense_category: string;
		vendor_name: string;
		description: string;
		expense_date: string;
		net_amount: string;
		vat_amount: string;
		gross_amount: string;
		invoice_reference: string | null;
		payment_due_date: string | null;
		is_paid: boolean;
		paid_date: string | null;
		created_at: string;
	};

	const CATEGORIES: Record<string, string> = {
		maintenance_repairs:   'Maintenance & Repairs',
		insurance:             'Insurance',
		property_tax:          'Property Tax',
		utilities:             'Utilities',
		legal_professional:    'Legal & Professional',
		management_fees:       'Management Fees',
		cleaning_landscaping:  'Cleaning & Landscaping',
		security:              'Security',
		capital_improvement:   'Capital Improvement',
		mortgage_interest:     'Mortgage Interest',
		other:                 'Other',
	};

	const CATEGORY_COLORS: Record<string, string> = {
		maintenance_repairs:   'text-amber-400 bg-amber-500/10',
		insurance:             'text-emerald-400 bg-emerald-500/10',
		property_tax:          'text-orange-400 bg-orange-500/10',
		utilities:             'text-sky-400 bg-sky-500/10',
		legal_professional:    'text-violet-400 bg-violet-500/10',
		management_fees:       'text-indigo-400 bg-indigo-500/10',
		cleaning_landscaping:  'text-teal-400 bg-teal-500/10',
		security:              'text-red-400 bg-red-500/10',
		capital_improvement:   'text-rose-400 bg-rose-500/10',
		mortgage_interest:     'text-pink-400 bg-pink-500/10',
		other:                 'text-white/40 bg-white/5',
	};

	// ── State ─────────────────────────────────────────────────────────────────

	let properties: Property[] = $state([]);
	let selectedProperty: Property | null = $state(null);
	let showPropertyPicker = $state(false);
	let expenses: Expense[] = $state([]);
	let loading = $state(false);

	// Modal — shared for create and edit
	let showModal = $state(false);
	let editingExpense: Expense | null = $state(null); // null = new, set = edit
	let saving = $state(false);
	let saveError = $state('');

	// Form fields
	let f_category = $state('maintenance_repairs');
	let f_vendor = $state('');
	let f_description = $state('');
	let f_date = $state('');
	let f_due_date = $state('');
	let f_net = $state('');
	let f_vat = $state('');
	let f_gross = $derived(
		f_net && f_vat
			? (parseFloat(f_net || '0') + parseFloat(f_vat || '0')).toFixed(2)
			: '',
	);
	let f_reference = $state('');

	// Receipt upload (only for new expense)
	let receiptFile: File | null = $state(null);
	let receiptError = $state('');
	let dragOver = $state(false);

	// ── Data ──────────────────────────────────────────────────────────────────

	function loadProperties() {
		api.get<Property[]>('/properties').then((p) => { properties = p; });
	}

	function loadExpenses(propertyId: number) {
		loading = true;
		api.get<Expense[]>(`/expenses?property_id=${propertyId}`)
			.then((e) => {
				expenses = e.sort((a, b) =>
					new Date(b.expense_date).getTime() - new Date(a.expense_date).getTime()
				);
			})
			.finally(() => { loading = false; });
	}

	if (browser) loadProperties();

	function selectProperty(p: Property) {
		selectedProperty = p;
		showPropertyPicker = false;
		loadExpenses(p.id);
	}

	// ── Modal helpers ─────────────────────────────────────────────────────────

	function openNew() {
		editingExpense = null;
		f_category = 'maintenance_repairs';
		f_vendor = '';
		f_description = '';
		f_date = new Date().toISOString().slice(0, 10);
		f_due_date = '';
		f_net = '';
		f_vat = '';
		f_reference = '';
		receiptFile = null;
		receiptError = '';
		saveError = '';
		showModal = true;
	}

	function openEdit(exp: Expense) {
		editingExpense = exp;
		f_category = exp.expense_category;
		f_vendor = exp.vendor_name;
		f_description = exp.description;
		f_date = exp.expense_date;
		f_due_date = exp.payment_due_date ?? '';
		f_net = exp.net_amount;
		f_vat = exp.vat_amount;
		f_reference = exp.invoice_reference ?? '';
		receiptFile = null;
		receiptError = '';
		saveError = '';
		showModal = true;
	}

	const ACCEPTED_MIME = new Set(['application/pdf', 'image/png', 'image/jpeg', 'image/heic', 'image/heif']);

	function setReceipt(file: File | null) {
		if (!file) return;
		if (!ACCEPTED_MIME.has(file.type)) {
			receiptError = 'Unsupported format. Use PDF, PNG, JPEG or HEIC.';
			return;
		}
		receiptFile = file;
		receiptError = '';
	}

	async function handleSave() {
		if (!selectedProperty) return;
		const net = parseFloat(f_net);
		const vat = parseFloat(f_vat);
		if (isNaN(net) || isNaN(vat)) { saveError = 'Enter valid amounts.'; return; }
		saving = true; saveError = '';

		const payload = {
			property_id: selectedProperty.id,
			expense_category: f_category,
			vendor_name: f_vendor.trim(),
			description: f_description.trim(),
			expense_date: f_date,
			net_amount: net.toFixed(2),
			vat_amount: vat.toFixed(2),
			gross_amount: (net + vat).toFixed(2),
			invoice_reference: f_reference.trim() || null,
			payment_due_date: f_due_date || null,
		};

		try {
			if (editingExpense) {
				// Update existing
				await api.patch(`/expenses/${editingExpense.id}`, payload);
			} else {
				// Create new + optional receipt upload
				const expense = await api.post<Expense>('/expenses', payload);

				if (receiptFile) {
					const form = new FormData();
					form.append('file', receiptFile);
					form.append('display_name', `Receipt — ${CATEGORIES[f_category]} — ${f_vendor.trim()}`);
					form.append('related_entity_type', 'expense');
					form.append('related_entity_id', String(expense.id));
					form.append('document_category', 'expense_invoice');

					const token = localStorage.getItem('token');
					const base = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000';
					const res = await fetch(`${base}/documents/upload`, {
						method: 'POST',
						headers: { Authorization: `Bearer ${token}` },
						body: form,
					});
					if (!res.ok) {
						const err = await res.json().catch(() => ({}));
						throw new Error(`Expense saved but receipt upload failed: ${err.detail ?? 'unknown error'}`);
					}
				}
			}

			showModal = false;
			loadExpenses(selectedProperty.id);
		} catch (err: unknown) {
			saveError = err instanceof Error ? err.message : 'Failed to save.';
		} finally {
			saving = false;
		}
	}

	async function handlePay(exp: Expense) {
		if (!confirm(`Mark "${exp.vendor_name}" expense as paid?`)) return;
		try {
			await api.post(`/expenses/${exp.id}/pay`, {});
			if (selectedProperty) loadExpenses(selectedProperty.id);
		} catch (err: unknown) {
			alert(err instanceof Error ? err.message : 'Failed to mark as paid.');
		}
	}

	async function handleDelete(exp: Expense) {
		if (!confirm(`Delete this expense from ${exp.vendor_name}? This cannot be undone.`)) return;
		await api.delete(`/expenses/${exp.id}`);
		if (selectedProperty) loadExpenses(selectedProperty.id);
	}

	// ── Helpers ───────────────────────────────────────────────────────────────

	function fmt(v: string | number): string {
		const n = Number(v);
		return isNaN(n) ? '—' : n.toLocaleString('en-GB', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
	}

	function formatDate(iso: string): string {
		return new Date(iso + 'T00:00:00').toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' });
	}

	function isOverdue(exp: Expense): boolean {
		if (exp.is_paid || !exp.payment_due_date) return false;
		return new Date(exp.payment_due_date + 'T00:00:00') < new Date(new Date().toDateString());
	}

	// YTD totals
	let unpaidExpenses = $derived(expenses.filter(e => !e.is_paid));
	let paidExpenses   = $derived(expenses.filter(e => e.is_paid));
	let ytdGross       = $derived(expenses.reduce((s, e) => s + parseFloat(e.gross_amount), 0));
	let ytdUnpaid      = $derived(unpaidExpenses.reduce((s, e) => s + parseFloat(e.gross_amount), 0));
	let ytdOverdue     = $derived(expenses.filter(isOverdue).reduce((s, e) => s + parseFloat(e.gross_amount), 0));
</script>

<!-- ── Header ────────────────────────────────────────────────────────────── -->
<div class="mb-8 flex items-center justify-between">
	<div>
		<h2 class="text-2xl font-semibold text-white">Expenses</h2>
		<p class="mt-1 text-sm text-white/40">Track costs per property</p>
	</div>
</div>

<!-- ── No property selected ─────────────────────────────────────────────── -->
{#if !selectedProperty}
	<div class="rounded-2xl border border-white/[0.07] bg-[#111111] p-12 text-center">
		<div class="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-white/5 text-2xl">🏢</div>
		<p class="mb-1 text-sm font-medium text-white">Select a property</p>
		<p class="mb-6 text-sm text-white/30">Choose a property to view and record its expenses.</p>
		<button
			onclick={() => (showPropertyPicker = true)}
			class="rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-indigo-500 transition-colors"
		>Select Property</button>
	</div>

{:else}
	<!-- ── Property selected header ────────────────────────────────────────── -->
	<div class="mb-5 flex items-center justify-between">
		<div class="flex items-center gap-3">
			<button
				onclick={() => { selectedProperty = null; expenses = []; }}
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
				onclick={openNew}
				class="rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-500 transition-colors"
			>+ New Expense</button>
		</div>
	</div>

	<!-- ── Summary strip ────────────────────────────────────────────────────── -->
	{#if expenses.length > 0}
		<div class="mb-4 grid grid-cols-4 gap-3">
			<div class="rounded-xl border border-white/[0.07] bg-[#111111] px-5 py-4">
				<p class="text-xs text-white/30">Total Expenses</p>
				<p class="mt-1 text-lg font-semibold text-white">{fmt(ytdGross)}</p>
				<p class="mt-0.5 text-xs text-white/25">{expenses.length} records</p>
			</div>
			<div class="rounded-xl border border-white/[0.07] bg-[#111111] px-5 py-4">
				<p class="text-xs text-white/30">Paid</p>
				<p class="mt-1 text-lg font-semibold text-emerald-400">{fmt(expenses.filter(e => e.is_paid).reduce((s, e) => s + parseFloat(e.gross_amount), 0))}</p>
				<p class="mt-0.5 text-xs text-white/25">{paidExpenses.length} expenses</p>
			</div>
			<div class="rounded-xl border border-white/[0.07] bg-[#111111] px-5 py-4">
				<p class="text-xs text-white/30">Outstanding</p>
				<p class="mt-1 text-lg font-semibold text-amber-400">{fmt(ytdUnpaid)}</p>
				<p class="mt-0.5 text-xs text-white/25">{unpaidExpenses.length} unpaid</p>
			</div>
			<div class="rounded-xl border border-white/[0.07] bg-[#111111] px-5 py-4">
				<p class="text-xs text-white/30">Overdue</p>
				<p class="mt-1 text-lg font-semibold {ytdOverdue > 0 ? 'text-red-400' : 'text-white/30'}">{fmt(ytdOverdue)}</p>
				<p class="mt-0.5 text-xs text-white/25">{expenses.filter(isOverdue).length} past due</p>
			</div>
		</div>
	{/if}

	<!-- ── Expense list ─────────────────────────────────────────────────────── -->
	{#if loading}
		<div class="rounded-2xl border border-white/[0.07] bg-[#111111] p-10 text-center">
			<p class="text-sm text-white/30">Loading…</p>
		</div>
	{:else if expenses.length === 0}
		<div class="rounded-2xl border border-white/[0.07] bg-[#111111] p-10 text-center">
			<p class="text-sm text-white/30">No expenses yet for this property.</p>
		</div>
	{:else}
		<div class="overflow-hidden rounded-2xl border border-white/[0.07] bg-[#111111]">
			<table class="w-full text-sm">
				<thead>
					<tr class="border-b border-white/[0.07]">
						<th class="px-5 py-3.5 text-left text-xs font-medium uppercase tracking-wider text-white/30">Date</th>
						<th class="px-5 py-3.5 text-left text-xs font-medium uppercase tracking-wider text-white/30">Category</th>
						<th class="px-5 py-3.5 text-left text-xs font-medium uppercase tracking-wider text-white/30">Supplier</th>
						<th class="px-5 py-3.5 text-left text-xs font-medium uppercase tracking-wider text-white/30">Description</th>
						<th class="px-5 py-3.5 text-left text-xs font-medium uppercase tracking-wider text-white/30">Due Date</th>
						<th class="px-5 py-3.5 text-left text-xs font-medium uppercase tracking-wider text-white/30">Status</th>
						<th class="px-5 py-3.5 text-right text-xs font-medium uppercase tracking-wider text-white/30">Net</th>
						<th class="px-5 py-3.5 text-right text-xs font-medium uppercase tracking-wider text-white/30">Gross</th>
						<th class="px-5 py-3.5"></th>
					</tr>
				</thead>
				<tbody>
					{#each expenses as exp}
						<tr class="border-b border-white/[0.04] hover:bg-white/[0.02] transition-colors {isOverdue(exp) ? 'bg-red-500/[0.02]' : ''}">
							<td class="px-5 py-4 text-white/50 whitespace-nowrap">{formatDate(exp.expense_date)}</td>
							<td class="px-5 py-4">
								<span class="rounded-md px-2 py-1 text-xs {CATEGORY_COLORS[exp.expense_category] ?? CATEGORY_COLORS.other}">
									{CATEGORIES[exp.expense_category] ?? exp.expense_category}
								</span>
							</td>
							<td class="px-5 py-4 font-medium text-white">{exp.vendor_name}</td>
							<td class="px-5 py-4 text-white/50 max-w-xs truncate">{exp.description}</td>
							<td class="px-5 py-4 whitespace-nowrap">
								{#if exp.payment_due_date}
									<span class="text-xs {isOverdue(exp) ? 'text-red-400 font-medium' : 'text-white/40'}">
										{isOverdue(exp) ? '⚠ ' : ''}{formatDate(exp.payment_due_date)}
									</span>
								{:else}
									<span class="text-xs text-white/20">—</span>
								{/if}
							</td>
							<td class="px-5 py-4">
								{#if exp.is_paid}
									<span class="rounded-md bg-emerald-500/10 px-2 py-1 text-xs text-emerald-400">
										Paid {exp.paid_date ? formatDate(exp.paid_date) : ''}
									</span>
								{:else if isOverdue(exp)}
									<span class="rounded-md bg-red-500/10 px-2 py-1 text-xs text-red-400">Overdue</span>
								{:else}
									<span class="rounded-md bg-white/5 px-2 py-1 text-xs text-white/40">Unpaid</span>
								{/if}
							</td>
							<td class="px-5 py-4 text-right font-mono text-sm text-white/70">{fmt(exp.net_amount)}</td>
							<td class="px-5 py-4 text-right font-mono text-sm font-medium text-white">{fmt(exp.gross_amount)}</td>
							<td class="px-5 py-4 text-right whitespace-nowrap">
								<button
									onclick={() => openEdit(exp)}
									class="mr-3 text-xs text-indigo-400 hover:text-indigo-300 transition-colors"
								>Edit</button>
								{#if !exp.is_paid}
									<button
										onclick={() => handlePay(exp)}
										class="mr-3 text-xs text-emerald-400 hover:text-emerald-300 transition-colors"
									>Pay</button>
								{/if}
								<button
									onclick={() => handleDelete(exp)}
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

<!-- ══════════════════════════════════════════════════════════════════════ -->
<!-- MODAL: Property Picker                                                -->
<!-- ══════════════════════════════════════════════════════════════════════ -->
{#if showPropertyPicker}
	<div
		class="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4"
		role="dialog" aria-modal="true"
	>
		<div class="w-full max-w-md rounded-2xl border border-white/[0.08] bg-[#111111] shadow-2xl">
			<div class="flex items-center justify-between border-b border-white/[0.07] px-6 py-4">
				<h3 class="text-base font-semibold text-white">Select Property</h3>
				<button onclick={() => (showPropertyPicker = false)} class="text-xl leading-none text-white/30 hover:text-white transition-colors">×</button>
			</div>
			{#if properties.length === 0}
				<div class="px-6 py-10 text-center">
					<p class="text-sm text-white/30">No properties found.</p>
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
<!-- MODAL: New / Edit Expense                                             -->
<!-- ══════════════════════════════════════════════════════════════════════ -->
{#if showModal}
	<div
		class="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4"
		role="dialog" aria-modal="true"
	>
		<div class="w-full max-w-lg rounded-2xl border border-white/[0.08] bg-[#111111] shadow-2xl max-h-[90vh] flex flex-col">
			<!-- Header -->
			<div class="flex items-start justify-between border-b border-white/[0.07] px-6 py-4 flex-shrink-0">
				<div>
					<h3 class="text-base font-semibold text-white">
						{editingExpense ? 'Edit Expense' : 'New Expense'}
					</h3>
					<p class="text-xs text-white/30">{selectedProperty?.name}</p>
				</div>
				<button onclick={() => (showModal = false)} class="text-xl leading-none text-white/30 hover:text-white transition-colors">×</button>
			</div>

			<!-- Body -->
			<div class="overflow-y-auto px-6 py-5 space-y-4">

				<!-- Category + Expense Date -->
				<div class="grid grid-cols-2 gap-4">
					<div>
						<label class="mb-1.5 block text-xs font-medium uppercase tracking-wider text-white/40" for="e_cat">Category *</label>
						<select id="e_cat" bind:value={f_category}
							class="w-full rounded-xl border border-white/10 bg-[#1a1a1a] px-4 py-3 text-sm text-white focus:border-indigo-500/50 focus:outline-none focus:ring-1 focus:ring-indigo-500/50 transition">
							{#each Object.entries(CATEGORIES) as [val, label]}
								<option value={val}>{label}</option>
							{/each}
						</select>
					</div>
					<div>
						<label class="mb-1.5 block text-xs font-medium uppercase tracking-wider text-white/40" for="e_date">Expense Date *</label>
						<input id="e_date" type="date" bind:value={f_date} required
							class="w-full rounded-xl border border-white/10 bg-[#1a1a1a] px-4 py-3 text-sm text-white focus:border-indigo-500/50 focus:outline-none focus:ring-1 focus:ring-indigo-500/50 transition" />
					</div>
				</div>

				<!-- Supplier -->
				<div>
					<label class="mb-1.5 block text-xs font-medium uppercase tracking-wider text-white/40" for="e_vendor">Supplier Name *</label>
					<input id="e_vendor" type="text" bind:value={f_vendor} placeholder="e.g. Plumbers R Us" required
						class="w-full rounded-xl border border-white/10 bg-[#1a1a1a] px-4 py-3 text-sm text-white placeholder-white/20 focus:border-indigo-500/50 focus:outline-none focus:ring-1 focus:ring-indigo-500/50 transition" />
				</div>

				<!-- Description -->
				<div>
					<label class="mb-1.5 block text-xs font-medium uppercase tracking-wider text-white/40" for="e_desc">Description *</label>
					<textarea id="e_desc" bind:value={f_description} rows={2} required
						placeholder="e.g. Emergency boiler repair, parts and labour"
						class="w-full resize-none rounded-xl border border-white/10 bg-[#1a1a1a] px-4 py-3 text-sm text-white placeholder-white/20 focus:border-indigo-500/50 focus:outline-none focus:ring-1 focus:ring-indigo-500/50 transition"></textarea>
				</div>

				<!-- Amounts -->
				<div class="grid grid-cols-3 gap-3">
					<div>
						<label class="mb-1.5 block text-xs font-medium uppercase tracking-wider text-white/40" for="e_net">Net (ex VAT) *</label>
						<input id="e_net" type="number" step="0.01" min="0" bind:value={f_net} required placeholder="0.00"
							class="w-full rounded-xl border border-white/10 bg-[#1a1a1a] px-4 py-3 text-sm text-white placeholder-white/20 focus:border-indigo-500/50 focus:outline-none focus:ring-1 focus:ring-indigo-500/50 transition" />
					</div>
					<div>
						<label class="mb-1.5 block text-xs font-medium uppercase tracking-wider text-white/40" for="e_vat">VAT *</label>
						<input id="e_vat" type="number" step="0.01" min="0" bind:value={f_vat} required placeholder="0.00"
							class="w-full rounded-xl border border-white/10 bg-[#1a1a1a] px-4 py-3 text-sm text-white placeholder-white/20 focus:border-indigo-500/50 focus:outline-none focus:ring-1 focus:ring-indigo-500/50 transition" />
					</div>
					<div>
						<label class="mb-1.5 block text-xs font-medium uppercase tracking-wider text-white/40">Gross (auto)</label>
						<div class="flex items-center h-[46px] rounded-xl border border-white/[0.05] bg-white/[0.03] px-4 text-sm font-medium text-white/50">
							{f_gross || '—'}
						</div>
					</div>
				</div>

				<!-- Payment due date + Reference -->
				<div class="grid grid-cols-2 gap-4">
					<div>
						<label class="mb-1.5 block text-xs font-medium uppercase tracking-wider text-white/40" for="e_due">
							Payment Due Date <span class="normal-case font-normal text-white/20">(optional)</span>
						</label>
						<input id="e_due" type="date" bind:value={f_due_date}
							class="w-full rounded-xl border border-white/10 bg-[#1a1a1a] px-4 py-3 text-sm text-white focus:border-indigo-500/50 focus:outline-none focus:ring-1 focus:ring-indigo-500/50 transition" />
					</div>
					<div>
						<label class="mb-1.5 block text-xs font-medium uppercase tracking-wider text-white/40" for="e_ref">
							Supplier Invoice Ref <span class="normal-case font-normal text-white/20">(optional)</span>
						</label>
						<input id="e_ref" type="text" bind:value={f_reference} placeholder="e.g. INV-2026-4421"
							class="w-full rounded-xl border border-white/10 bg-[#1a1a1a] px-4 py-3 text-sm text-white placeholder-white/20 focus:border-indigo-500/50 focus:outline-none focus:ring-1 focus:ring-indigo-500/50 transition" />
					</div>
				</div>

				<!-- Receipt upload — only for new expenses -->
				{#if !editingExpense}
				<div>
					<label class="mb-1.5 block text-xs font-medium uppercase tracking-wider text-white/40">
						Receipt / Invoice <span class="normal-case font-normal text-white/20">(optional — PDF, PNG, JPEG, HEIC)</span>
					</label>
					<!-- svelte-ignore a11y_interactive_supports_focus -->
					<div
						role="button"
						tabindex="0"
						class="flex cursor-pointer items-center gap-3 rounded-xl border-2 border-dashed px-4 py-4 transition-colors
							{dragOver ? 'border-indigo-500 bg-indigo-500/5' : receiptFile ? 'border-emerald-500/40 bg-emerald-500/5' : 'border-white/10 hover:border-white/20'}"
						ondragover={(e) => { e.preventDefault(); dragOver = true; }}
						ondragleave={() => (dragOver = false)}
						ondrop={(e) => { e.preventDefault(); dragOver = false; setReceipt(e.dataTransfer?.files[0] ?? null); }}
						onclick={() => (document.getElementById('expense-file-input') as HTMLInputElement)?.click()}
						onkeydown={(e) => { if (e.key === 'Enter') (document.getElementById('expense-file-input') as HTMLInputElement)?.click(); }}
					>
						<input id="expense-file-input" type="file" accept=".pdf,.png,.jpg,.jpeg,.heic,.heif" class="hidden"
							onchange={(e) => setReceipt((e.target as HTMLInputElement).files?.[0] ?? null)} />
						{#if receiptFile}
							<span class="text-xl">📄</span>
							<div class="min-w-0">
								<p class="truncate text-sm text-white">{receiptFile.name}</p>
								<p class="text-xs text-white/30">click to change</p>
							</div>
						{:else}
							<span class="text-xl text-white/20">☁</span>
							<p class="text-sm text-white/40">Drop file or <span class="text-indigo-400">browse</span></p>
						{/if}
					</div>
					{#if receiptError}
						<p class="mt-1 text-xs text-red-400">{receiptError}</p>
					{/if}
				</div>
				{/if}

				{#if saveError}
					<div class="rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3">
						<p class="text-sm text-red-400">{saveError}</p>
					</div>
				{/if}
			</div>

			<!-- Footer -->
			<div class="flex justify-end gap-3 border-t border-white/[0.07] px-6 py-4 flex-shrink-0">
				<button
					onclick={() => (showModal = false)}
					class="rounded-xl border border-white/10 px-5 py-2.5 text-sm text-white/50 hover:text-white transition-colors"
				>Cancel</button>
				<button
					onclick={handleSave}
					disabled={saving || !f_vendor.trim() || !f_description.trim() || !f_net || !f_vat || !f_date}
					class="rounded-xl bg-indigo-600 px-6 py-2.5 text-sm font-semibold text-white hover:bg-indigo-500 disabled:opacity-40 transition-colors"
				>
					{#if saving}
						Saving…
					{:else if editingExpense}
						Save Changes
					{:else if receiptFile}
						Save & Upload Receipt
					{:else}
						Save Expense
					{/if}
				</button>
			</div>
		</div>
	</div>
{/if}
