<script lang="ts">
	import { browser } from '$app/environment';
	import { onMount } from 'svelte';
	import { api } from '$lib/api/client';

	// ── Types ────────────────────────────────────────────────────────────────

	type StatCards = {
		invoices_pending: number;
		invoices_overdue: number;
		outstanding_balance: string;
		occupancy_rate: number;
	};

	type BillingForecast = {
		net_amount: string;
		vat_amount: string;
		gross_amount: string;
		invoice_count: number;
	};

	type YtdCollection = {
		invoiced_gross: string;
		collected: string;
		collection_rate: number;
	};

	type LeaseExpiryRow = {
		agreement_uuid: string;
		property_name: string;
		unit_number: string;
		lessee_name: string;
		lease_end: string;
		days_to_expiry: number;
		notification_deadline: string;
		days_to_notification: int;
	};

	type PaymentPoint = {
		invoice_number: string;
		billing_period_start: string;
		billing_period_end: string;
		due_date: string;
		gross_amount: string;
		paid_date: string | null;
		days_delta: number | null;
		payment_method: string | null;
		amount_received: string | null;
		transaction_reference: string | null;
		notes: string | null;
	};

	type PropertyPerformance = {
		property_id: number;
		property_name: string;
		unit_number: string;
		lessee_name: string;
		agreement_uuid: string;
		points: PaymentPoint[];
	};

	type OpenExpenseStats = {
		open_count: number;
		open_total: string;
		overdue_count: number;
		overdue_total: string;
	};

	type IndexationRow = {
		agreement_uuid: string;
		property_name: string;
		unit_number: string;
		lessee_name: string;
		indexation_date: string;
		next_indexation: string;
		days_until: number;
		base_rent_amount: string;
		currency: string;
	};

	type Dashboard = {
		stats: StatCards;
		billing_forecast: BillingForecast;
		ytd_collection: YtdCollection;
		lease_expiries: LeaseExpiryRow[];
		payment_performance: PropertyPerformance[];
		open_expenses: OpenExpenseStats;
		indexations: IndexationRow[];
	};

	// ── State ─────────────────────────────────────────────────────────────────

	let data: Dashboard | null = $state(null);
	let loading = $state(true);

	// Payment detail modal
	type ModalContext = { point: PaymentPoint; property_name: string; unit_number: string; lessee_name: string };
	let modal: ModalContext | null = $state(null);

	// ── Indexation workflow modal ─────────────────────────────────────────────

	let indexModal: IndexationRow | null = $state(null);
	// 'quotient' | 'percentage'
	let indexMode: 'quotient' | 'percentage' = $state('quotient');
	let indexNumerator = $state('');
	let indexDenominator = $state('');
	let indexPercentage = $state('');
	let indexEffectiveDate = $state('');
	let indexSendEmail = $state(true);
	let indexApplying = $state(false);
	let indexError = $state('');
	let indexSuccess: { old_rent: string; new_rent: string } | null = $state(null);

	function openIndexModal(row: IndexationRow) {
		indexModal = row;
		indexMode = 'quotient';
		indexNumerator = '';
		indexDenominator = '';
		indexPercentage = '';
		indexEffectiveDate = row.next_indexation;
		indexSendEmail = true;
		indexApplying = false;
		indexError = '';
		indexSuccess = null;
	}

	// Live-computed preview of new rent
	let indexNewRent = $derived((() => {
		if (!indexModal) return null;
		const base = parseFloat(indexModal.base_rent_amount);
		if (isNaN(base)) return null;
		if (indexMode === 'quotient') {
			const num = parseFloat(indexNumerator);
			const den = parseFloat(indexDenominator);
			if (!num || !den || den === 0) return null;
			return (base * num / den).toFixed(2);
		} else {
			const pct = parseFloat(indexPercentage);
			if (isNaN(pct)) return null;
			return (base * (1 + pct / 100)).toFixed(2);
		}
	})());

	async function handleApplyIndex() {
		if (!indexModal) return;
		indexApplying = true; indexError = ''; indexSuccess = null;
		try {
			const payload: Record<string, unknown> = {
				effective_date: indexEffectiveDate,
				send_notification: indexSendEmail,
			};
			if (indexMode === 'quotient') {
				payload.index_numerator = parseFloat(indexNumerator);
				payload.index_denominator = parseFloat(indexDenominator);
			} else {
				payload.index_percentage = parseFloat(indexPercentage);
			}
			const result = await api.post<{ old_rent: string; new_rent: string }>(
				`/rental-agreements/${indexModal.agreement_uuid}/apply-index`,
				payload,
			);
			indexSuccess = result;
			// Immediately remove the row from the table
			if (data) {
				data = { ...data, indexations: data.indexations.filter(r => r.agreement_uuid !== indexModal!.agreement_uuid) };
			}
			// Refresh dashboard data in the background
			api.get<Dashboard>('/dashboard').then((d) => { data = d; });
		} catch (err: unknown) {
			indexError = err instanceof Error ? err.message : 'Failed to apply index.';
		} finally {
			indexApplying = false;
		}
	}

	// ── Load ──────────────────────────────────────────────────────────────────

	if (browser) {
		api.get<Dashboard>('/dashboard')
			.then((d) => { data = d; })
			.finally(() => { loading = false; });
	}

	// ── Chart ─────────────────────────────────────────────────────────────────

	let chartCanvases: Record<string, HTMLCanvasElement> = {};
	let chartInstances: Record<string, unknown> = {};

	async function renderCharts() {
		if (!data?.payment_performance.length) return;
		const { Chart, registerables } = await import('chart.js');
		Chart.register(...registerables);

		for (const perf of data.payment_performance) {
			const canvas = chartCanvases[perf.agreement_uuid];
			if (!canvas) continue;

			// Destroy existing instance if re-rendering
			if (chartInstances[perf.agreement_uuid]) {
				(chartInstances[perf.agreement_uuid] as { destroy(): void }).destroy();
			}

			const labels = perf.points.map((p) =>
				new Date(p.billing_period_start).toLocaleDateString('en-GB', { month: 'short', year: '2-digit' }),
			);
			const values = perf.points.map((p) => p.days_delta);

			const colors = values.map((v) =>
				v === null ? 'rgba(255,255,255,0.15)' : v <= 0 ? '#34d399' : v <= 7 ? '#fbbf24' : '#f87171',
			);

			chartInstances[perf.agreement_uuid] = new Chart(canvas, {
				type: 'bar',
				data: {
					labels,
					datasets: [
						{
							label: 'Days late (negative = early)',
							data: values,
							backgroundColor: colors,
							borderRadius: 4,
							borderSkipped: false,
						},
						{
							type: 'line' as const,
							label: 'Trend',
							data: values,
							borderColor: 'rgba(255,255,255,0.15)',
							borderWidth: 1,
							pointRadius: 0,
							tension: 0.4,
						},
					],
				},
				options: {
					responsive: true,
					maintainAspectRatio: false,
					cursor: 'pointer',
					onClick: (_evt: unknown, elements: { index: number }[]) => {
						if (!elements.length) return;
						const idx = elements[0].index;
						const point = perf.points[idx];
						modal = {
							point,
							property_name: perf.property_name,
							unit_number: perf.unit_number,
							lessee_name: perf.lessee_name,
						};
					},
					plugins: {
						legend: { display: false },
						tooltip: {
							callbacks: {
								label: (ctx) => {
									const v = ctx.parsed.y;
									if (v === null) return 'Unpaid — click for details';
									if (v < 0) return `${Math.abs(v)} days early — click for details`;
									if (v === 0) return 'On time — click for details';
									return `${v} days late — click for details`;
								},
							},
						},
					},
					scales: {
						x: {
							grid: { color: 'rgba(255,255,255,0.04)' },
							ticks: { color: 'rgba(255,255,255,0.3)', font: { size: 10 } },
						},
						y: {
							grid: { color: 'rgba(255,255,255,0.04)' },
							ticks: {
								color: 'rgba(255,255,255,0.3)',
								font: { size: 10 },
								callback: (v) => (Number(v) === 0 ? 'On time' : `${v}d`),
							},
							// Zero line highlight
							afterDataLimits: (scale) => {
								const max = Math.max(...(values.filter((v) => v !== null) as number[]), 1);
								const min = Math.min(...(values.filter((v) => v !== null) as number[]), -1);
								scale.max = max + 2;
								scale.min = min - 2;
							},
						},
					},
				},
			});
		}
	}

	$effect(() => {
		if (data) {
			// Wait a tick for canvas elements to mount
			setTimeout(renderCharts, 50);
		}
	});

	// ── Helpers ───────────────────────────────────────────────────────────────

	function fmt(amount: string | number | null | undefined): string {
		if (amount === null || amount === undefined || amount === '') return '—';
		const n = Number(amount);
		if (isNaN(n)) return '—';
		return n.toLocaleString('en-GB', { minimumFractionDigits: 0, maximumFractionDigits: 0 });
	}

	function formatDate(iso: string): string {
		return new Date(iso).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' });
	}

	function notificationClass(days: number): string {
		if (days < 0) return 'text-red-400 bg-red-500/10 border-red-500/20';
		if (days < 30) return 'text-amber-400 bg-amber-500/10 border-amber-500/20';
		if (days < 90) return 'text-yellow-400 bg-yellow-500/10 border-yellow-500/20';
		return 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20';
	}

	const PAYMENT_METHOD_LABELS: Record<string, string> = {
		bank_transfer: 'Bank Transfer',
		stripe: 'Stripe',
		direct_debit: 'Direct Debit',
		cash: 'Cash',
		other: 'Other',
	};

	const PAYMENT_METHOD_ICONS: Record<string, string> = {
		bank_transfer: '🏦',
		stripe: '💳',
		direct_debit: '🔁',
		cash: '💵',
		other: '📝',
	};

	function notificationLabel(days: number): string {
		if (days < 0) return `${Math.abs(days)}d overdue`;
		if (days === 0) return 'Today';
		return `${days}d left`;
	}

	function expiryClass(days: number): string {
		if (days < 30) return 'text-red-400';
		if (days < 90) return 'text-amber-400';
		return 'text-white/60';
	}

	function indexationClass(days: number): string {
		if (days <= 14) return 'border-amber-500/30 bg-amber-500/10 text-amber-400';
		if (days <= 60) return 'border-indigo-500/30 bg-indigo-500/10 text-indigo-300';
		return 'border-white/10 bg-white/5 text-white/40';
	}

	function indexationLabel(days: number): string {
		if (days === 0) return 'Today';
		if (days === 1) return 'Tomorrow';
		return `${days}d`;
	}

	// TypeScript doesn't know "int" — use number in TS type
	type int = number;
</script>

<div class="mb-8 flex items-center justify-between">
	<div>
		<h2 class="text-2xl font-semibold text-white">Dashboard</h2>
		<p class="mt-1 text-sm text-white/40">Portfolio overview</p>
	</div>
</div>

{#if loading}
	<div class="rounded-2xl border border-white/[0.07] bg-[#111111] p-12 text-center">
		<p class="text-sm text-white/30">Loading…</p>
	</div>
{:else if !data}
	<div class="rounded-2xl border border-white/[0.07] bg-[#111111] p-12 text-center">
		<p class="text-sm text-white/30">Could not load dashboard. Check your settings.</p>
	</div>
{:else}

<!-- ── Row 1: Stat cards ───────────────────────────────────────────────── -->
<div class="grid grid-cols-4 gap-4 mb-4">

	<div class="rounded-2xl border border-white/[0.07] bg-[#111111] p-5">
		<p class="text-xs font-medium uppercase tracking-wider text-white/30">Pending Invoices</p>
		<p class="mt-3 text-3xl font-semibold text-white">{data.stats.invoices_pending}</p>
		<a href="/invoices" class="mt-2 block text-xs text-indigo-400/60 hover:text-indigo-400 transition-colors">View ledger →</a>
	</div>

	<div class="rounded-2xl border {data.stats.invoices_overdue > 0 ? 'border-red-500/20 bg-red-500/5' : 'border-white/[0.07] bg-[#111111]'} p-5">
		<p class="text-xs font-medium uppercase tracking-wider {data.stats.invoices_overdue > 0 ? 'text-red-400/60' : 'text-white/30'}">Overdue Invoices</p>
		<p class="mt-3 text-3xl font-semibold {data.stats.invoices_overdue > 0 ? 'text-red-400' : 'text-white'}">{data.stats.invoices_overdue}</p>
		<a href="/invoices" class="mt-2 block text-xs text-indigo-400/60 hover:text-indigo-400 transition-colors">View ledger →</a>
	</div>

	<div class="rounded-2xl border border-white/[0.07] bg-[#111111] p-5">
		<p class="text-xs font-medium uppercase tracking-wider text-white/30">Outstanding Balance</p>
		<p class="mt-3 text-3xl font-semibold text-white">{fmt(data.stats.outstanding_balance)}</p>
		<p class="mt-2 text-xs text-white/20">pending + overdue</p>
	</div>

	<div class="rounded-2xl border border-white/[0.07] bg-[#111111] p-5">
		<p class="text-xs font-medium uppercase tracking-wider text-white/30">Occupancy Rate</p>
		<p class="mt-3 text-3xl font-semibold text-white">{data.stats.occupancy_rate}%</p>
		<div class="mt-3 h-1.5 w-full rounded-full bg-white/10">
			<div
				class="h-1.5 rounded-full transition-all {data.stats.occupancy_rate >= 90 ? 'bg-emerald-500' : data.stats.occupancy_rate >= 70 ? 'bg-amber-500' : 'bg-red-500'}"
				style="width: {data.stats.occupancy_rate}%"
			></div>
		</div>
	</div>

</div>

<!-- ── Row 1b: Expense stat cards ─────────────────────────────────────── -->
<div class="grid grid-cols-2 gap-4 mb-4">

	<div class="rounded-2xl border border-white/[0.07] bg-[#111111] p-5">
		<p class="text-xs font-medium uppercase tracking-wider text-white/30">Open Expenses</p>
		<p class="mt-3 text-3xl font-semibold text-white">{fmt(data.open_expenses.open_total)}</p>
		<p class="mt-2 text-xs text-white/25">{data.open_expenses.open_count} unpaid expense{data.open_expenses.open_count === 1 ? '' : 's'}</p>
		<a href="/expenses" class="mt-2 block text-xs text-indigo-400/60 hover:text-indigo-400 transition-colors">View expenses →</a>
	</div>

	<div class="rounded-2xl border {data.open_expenses.overdue_count > 0 ? 'border-red-500/20 bg-red-500/5' : 'border-white/[0.07] bg-[#111111]'} p-5">
		<p class="text-xs font-medium uppercase tracking-wider {data.open_expenses.overdue_count > 0 ? 'text-red-400/60' : 'text-white/30'}">Overdue Expenses</p>
		<p class="mt-3 text-3xl font-semibold {data.open_expenses.overdue_count > 0 ? 'text-red-400' : 'text-white/30'}">
			{data.open_expenses.overdue_count > 0 ? fmt(data.open_expenses.overdue_total) : '—'}
		</p>
		<p class="mt-2 text-xs {data.open_expenses.overdue_count > 0 ? 'text-red-400/40' : 'text-white/25'}">{data.open_expenses.overdue_count} past payment due date</p>
		<a href="/expenses" class="mt-2 block text-xs text-indigo-400/60 hover:text-indigo-400 transition-colors">View expenses →</a>
	</div>

</div>

<!-- ── Row 2: Billing forecast + YTD collection ───────────────────────── -->
<div class="grid grid-cols-2 gap-4 mb-4">

	<!-- Billing forecast -->
	<div class="rounded-2xl border border-white/[0.07] bg-[#111111] p-6">
		<p class="mb-4 text-xs font-semibold uppercase tracking-wider text-white/30">Next Billing Cycle</p>
		<div class="space-y-3">
			<div class="flex items-center justify-between">
				<span class="text-sm text-white/50">Net rent + charges</span>
				<span class="font-mono text-sm text-white">{fmt(data.billing_forecast.net_amount)}</span>
			</div>
			<div class="flex items-center justify-between">
				<span class="text-sm text-white/50">VAT</span>
				<span class="font-mono text-sm text-white/60">{fmt(data.billing_forecast.vat_amount)}</span>
			</div>
			<div class="border-t border-white/[0.07] pt-3 flex items-center justify-between">
				<span class="text-sm font-semibold text-white">Total (incl. VAT)</span>
				<span class="font-mono text-lg font-bold text-white">{fmt(data.billing_forecast.gross_amount)}</span>
			</div>
		</div>
		<p class="mt-4 text-xs text-white/25">{data.billing_forecast.invoice_count} active agreement{data.billing_forecast.invoice_count === 1 ? '' : 's'}</p>
	</div>

	<!-- YTD collection -->
	<div class="rounded-2xl border border-white/[0.07] bg-[#111111] p-6">
		<p class="mb-4 text-xs font-semibold uppercase tracking-wider text-white/30">YTD Collection</p>
		<div class="space-y-3">
			<div class="flex items-center justify-between">
				<span class="text-sm text-white/50">Invoiced (gross)</span>
				<span class="font-mono text-sm text-white">{fmt(data.ytd_collection.invoiced_gross)}</span>
			</div>
			<div class="flex items-center justify-between">
				<span class="text-sm text-white/50">Collected</span>
				<span class="font-mono text-sm text-white">{fmt(data.ytd_collection.collected)}</span>
			</div>
			<div class="border-t border-white/[0.07] pt-3 flex items-center justify-between">
				<span class="text-sm font-semibold text-white">Collection Rate</span>
				<span class="font-mono text-lg font-bold {data.ytd_collection.collection_rate >= 95 ? 'text-emerald-400' : data.ytd_collection.collection_rate >= 80 ? 'text-amber-400' : 'text-red-400'}">
					{data.ytd_collection.collection_rate}%
				</span>
			</div>
		</div>
		<div class="mt-4 h-1.5 w-full rounded-full bg-white/10">
			<div
				class="h-1.5 rounded-full transition-all {data.ytd_collection.collection_rate >= 95 ? 'bg-emerald-500' : data.ytd_collection.collection_rate >= 80 ? 'bg-amber-500' : 'bg-red-500'}"
				style="width: {Math.min(data.ytd_collection.collection_rate, 100)}%"
			></div>
		</div>
	</div>

</div>

<!-- ── Row 3: Lease expiry table ──────────────────────────────────────── -->
<div class="mb-4 rounded-2xl border border-white/[0.07] bg-[#111111]">
	<div class="border-b border-white/[0.07] px-6 py-4">
		<h3 class="text-xs font-semibold uppercase tracking-wider text-white/30">Lease Expiries <span class="ml-2 normal-case font-normal text-white/20">— next 12 months</span></h3>
	</div>

	{#if data.lease_expiries.length === 0}
		<div class="px-6 py-8 text-center">
			<p class="text-sm text-white/30">No leases expiring in the next 12 months.</p>
		</div>
	{:else}
		<table class="w-full text-sm">
			<thead>
				<tr class="border-b border-white/[0.05]">
					<th class="px-5 py-3 text-left text-xs font-medium uppercase tracking-wider text-white/25">Property / Unit</th>
					<th class="px-5 py-3 text-left text-xs font-medium uppercase tracking-wider text-white/25">Lessee</th>
					<th class="px-5 py-3 text-left text-xs font-medium uppercase tracking-wider text-white/25">Lease Ends</th>
					<th class="px-5 py-3 text-left text-xs font-medium uppercase tracking-wider text-white/25">Days to Expiry</th>
					<th class="px-5 py-3 text-left text-xs font-medium uppercase tracking-wider text-white/25">Notification Deadline</th>
					<th class="px-5 py-3 text-left text-xs font-medium uppercase tracking-wider text-white/25">Notify In</th>
				</tr>
			</thead>
			<tbody>
				{#each data.lease_expiries as row}
					<tr class="border-b border-white/[0.04] hover:bg-white/[0.02] transition-colors">
						<td class="px-5 py-4">
							<p class="font-medium text-white">{row.property_name}</p>
							<p class="text-xs text-white/40">Unit {row.unit_number}</p>
						</td>
						<td class="px-5 py-4 text-white/60">{row.lessee_name}</td>
						<td class="px-5 py-4 text-white/60">{formatDate(row.lease_end)}</td>
						<td class="px-5 py-4">
							<span class="text-sm font-medium {expiryClass(row.days_to_expiry)}">{row.days_to_expiry}d</span>
						</td>
						<td class="px-5 py-4 text-white/60">{formatDate(row.notification_deadline)}</td>
						<td class="px-5 py-4">
							<span class="rounded-md border px-2 py-1 text-xs font-medium {notificationClass(row.days_to_notification)}">
								{notificationLabel(row.days_to_notification)}
							</span>
						</td>
					</tr>
				{/each}
			</tbody>
		</table>
	{/if}
</div>

<!-- ── Indexation schedule ────────────────────────────────────────────── -->
{#if data.indexations.filter(r => r.days_until <= 90).length > 0}
<div class="mb-4 rounded-2xl border border-white/[0.07] bg-[#111111]">
	<div class="border-b border-white/[0.07] px-6 py-4">
		<h3 class="text-xs font-semibold uppercase tracking-wider text-white/30">
			Rent Indexations
			<span class="ml-2 normal-case font-normal text-white/20">— upcoming annual index dates for active leases</span>
		</h3>
	</div>
	<table class="w-full text-sm">
		<thead>
			<tr class="border-b border-white/[0.05]">
				<th class="px-5 py-3 text-left text-xs font-medium uppercase tracking-wider text-white/25">Property / Unit</th>
				<th class="px-5 py-3 text-left text-xs font-medium uppercase tracking-wider text-white/25">Lessee</th>
				<th class="px-5 py-3 text-left text-xs font-medium uppercase tracking-wider text-white/25">Current Rent</th>
				<th class="px-5 py-3 text-left text-xs font-medium uppercase tracking-wider text-white/25">Next Indexation</th>
				<th class="px-5 py-3 text-left text-xs font-medium uppercase tracking-wider text-white/25">In</th>
				<th class="px-5 py-3"></th>
			</tr>
		</thead>
		<tbody>
			{#each data.indexations.filter(r => r.days_until <= 90) as row}
				<tr class="border-b border-white/[0.04] hover:bg-white/[0.02] transition-colors">
					<td class="px-5 py-4">
						<p class="font-medium text-white">{row.property_name}</p>
						{#if row.unit_number !== '—'}
							<p class="text-xs text-white/40">Unit {row.unit_number}</p>
						{/if}
					</td>
					<td class="px-5 py-4 text-white/60">{row.lessee_name}</td>
					<td class="px-5 py-4 text-white/70 font-mono text-xs">
						{row.currency} {parseFloat(row.base_rent_amount).toLocaleString('en-GB', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
					</td>
					<td class="px-5 py-4 text-white/60">{formatDate(row.next_indexation)}</td>
					<td class="px-5 py-4">
						<span class="rounded-md border px-2 py-1 text-xs font-medium {indexationClass(row.days_until)}">
							{indexationLabel(row.days_until)}
						</span>
					</td>
					<td class="px-5 py-4 text-right">
						<button
							onclick={() => openIndexModal(row)}
							class="rounded-lg border border-indigo-500/30 bg-indigo-500/10 px-3 py-1.5 text-xs font-medium text-indigo-300 hover:bg-indigo-500/20 transition-colors"
						>Apply Index</button>
					</td>
				</tr>
			{/each}
		</tbody>
	</table>
</div>
{/if}

<!-- ── Row 4: Payment performance charts ─────────────────────────────── -->
{#if data.payment_performance.length > 0}
<div class="rounded-2xl border border-white/[0.07] bg-[#111111]">
	<div class="border-b border-white/[0.07] px-6 py-4">
		<h3 class="text-xs font-semibold uppercase tracking-wider text-white/30">Payment Performance <span class="ml-2 normal-case font-normal text-white/20">— days early / late per invoice</span></h3>
	</div>
	<div class="divide-y divide-white/[0.04]">
		{#each data.payment_performance as perf}
			<div class="px-6 py-5">
				<div class="mb-3 flex items-center justify-between">
					<div>
						<span class="text-sm font-semibold text-white">{perf.property_name}</span>
						<span class="mx-2 text-white/20">·</span>
						<span class="text-sm text-white/50">Unit {perf.unit_number}</span>
						<span class="mx-2 text-white/20">·</span>
						<span class="text-sm text-white/50">{perf.lessee_name}</span>
					</div>
					<div class="flex items-center gap-3 text-xs text-white/25">
						<span class="flex items-center gap-1"><span class="inline-block h-2 w-2 rounded-sm bg-emerald-500"></span> Early / on time</span>
						<span class="flex items-center gap-1"><span class="inline-block h-2 w-2 rounded-sm bg-amber-400"></span> ≤7d late</span>
						<span class="flex items-center gap-1"><span class="inline-block h-2 w-2 rounded-sm bg-red-400"></span> &gt;7d late</span>
					</div>
				</div>
				<div class="h-36">
					<canvas bind:this={chartCanvases[perf.agreement_uuid]}></canvas>
				</div>
			</div>
		{/each}
	</div>
</div>
{/if}

{/if}

<!-- ══════════════════════════════════════════════════════════════════════ -->
<!-- MODAL: Payment detail                                                 -->
<!-- ══════════════════════════════════════════════════════════════════════ -->
{#if modal}
	<!-- svelte-ignore a11y_no_static_element_interactions a11y_click_events_have_key_events -->
	<div
		role="presentation"
		class="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4"
		onclick={() => (modal = null)}
	>
		<div
			role="dialog"
			aria-modal="true"
			class="w-full max-w-md rounded-2xl border border-white/[0.08] bg-[#111111] shadow-2xl"
			onclick={(e) => e.stopPropagation()}
		>
			<!-- Header -->
			<div class="flex items-start justify-between border-b border-white/[0.07] px-6 py-4">
				<div>
					<p class="text-xs text-white/30">
						{modal.property_name} · Unit {modal.unit_number} · {modal.lessee_name}
					</p>
					<h3 class="mt-0.5 text-base font-semibold text-white">{modal.point.invoice_number}</h3>
					<p class="text-xs text-white/40">
						{formatDate(modal.point.billing_period_start)} – {formatDate(modal.point.billing_period_end)}
					</p>
				</div>
				<button
					onclick={() => (modal = null)}
					class="text-xl leading-none text-white/30 hover:text-white transition-colors"
				>×</button>
			</div>

			<!-- Invoice summary row -->
			<div class="grid grid-cols-2 gap-px border-b border-white/[0.07] bg-white/[0.04]">
				<div class="bg-[#111111] px-6 py-4">
					<p class="mb-1 text-xs text-white/30">Invoice Amount</p>
					<p class="text-lg font-semibold text-white">{fmt(modal.point.gross_amount)}</p>
				</div>
				<div class="bg-[#111111] px-6 py-4">
					<p class="mb-1 text-xs text-white/30">Due Date</p>
					<p class="text-lg font-semibold text-white">{formatDate(modal.point.due_date)}</p>
				</div>
			</div>

			<!-- Payment details -->
			<div class="px-6 py-5">
				{#if modal.point.paid_date}
					<div class="mb-4 flex items-center gap-3">
						<div class="flex h-10 w-10 items-center justify-center rounded-xl bg-white/5 text-xl">
							{PAYMENT_METHOD_ICONS[modal.point.payment_method ?? ''] ?? '📝'}
						</div>
						<div>
							<p class="text-sm font-semibold text-white">
								{PAYMENT_METHOD_LABELS[modal.point.payment_method ?? ''] ?? modal.point.payment_method}
							</p>
							<p class="text-xs text-white/40">Payment method</p>
						</div>
						<div class="ml-auto">
							{#if (modal.point.days_delta ?? 0) < 0}
								<span class="rounded-md bg-emerald-500/10 px-2 py-1 text-xs font-medium text-emerald-400">{Math.abs(modal.point.days_delta!)}d early</span>
							{:else if modal.point.days_delta === 0}
								<span class="rounded-md bg-emerald-500/10 px-2 py-1 text-xs font-medium text-emerald-400">On time</span>
							{:else if (modal.point.days_delta ?? 0) <= 7}
								<span class="rounded-md bg-amber-500/10 px-2 py-1 text-xs font-medium text-amber-400">{modal.point.days_delta}d late</span>
							{:else}
								<span class="rounded-md bg-red-500/10 px-2 py-1 text-xs font-medium text-red-400">{modal.point.days_delta}d late</span>
							{/if}
						</div>
					</div>

					<div class="space-y-3 rounded-xl border border-white/[0.07] bg-[#0d0d0d] px-4 py-4">
						<div class="flex justify-between text-sm">
							<span class="text-white/40">Paid on</span>
							<span class="font-medium text-white">{formatDate(modal.point.paid_date)}</span>
						</div>
						<div class="flex justify-between text-sm">
							<span class="text-white/40">Amount received</span>
							<span class="font-medium text-white">{fmt(modal.point.amount_received ?? '0')}</span>
						</div>
						{#if modal.point.transaction_reference}
							<div class="flex justify-between text-sm">
								<span class="text-white/40">Reference</span>
								<span class="font-mono text-xs text-white/70">{modal.point.transaction_reference}</span>
							</div>
						{/if}
						{#if modal.point.notes}
							<div class="border-t border-white/[0.06] pt-3 text-sm">
								<p class="text-white/40">Notes</p>
								<p class="mt-1 text-white/70">{modal.point.notes}</p>
							</div>
						{/if}
					</div>
				{:else}
					<div class="rounded-xl border border-amber-500/20 bg-amber-500/5 px-4 py-6 text-center">
						<p class="text-sm font-medium text-amber-400">Not yet paid</p>
						<p class="mt-1 text-xs text-white/30">No payment has been recorded for this invoice.</p>
					</div>
				{/if}
			</div>

			<div class="border-t border-white/[0.07] px-6 py-4">
				<button
					onclick={() => (modal = null)}
					class="w-full rounded-xl border border-white/10 py-2.5 text-sm text-white/50 hover:text-white transition-colors"
				>Close</button>
			</div>
		</div>
	</div>
{/if}

<!-- ══════════════════════════════════════════════════════════════════════ -->
<!-- MODAL: Apply rent indexation                                          -->
<!-- ══════════════════════════════════════════════════════════════════════ -->
{#if indexModal}
	<div class="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
		<div class="w-full max-w-md rounded-2xl border border-white/[0.07] bg-[#111111] shadow-2xl">

			<!-- Header -->
			<div class="border-b border-white/[0.07] px-6 py-5">
				<h3 class="text-base font-semibold text-white">Apply Rent Indexation</h3>
				<p class="mt-0.5 text-sm text-white/40">
					{indexModal.property_name}{indexModal.unit_number !== '—' ? ` — Unit ${indexModal.unit_number}` : ''} · {indexModal.lessee_name}
				</p>
			</div>

			<div class="px-6 py-5 space-y-5">

				{#if indexSuccess}
					<!-- Success state -->
					<div class="rounded-xl border border-emerald-500/20 bg-emerald-500/10 px-5 py-4 text-center">
						<p class="text-sm font-semibold text-emerald-400 mb-1">Indexation applied ✓</p>
						<p class="text-xs text-white/50">
							{indexModal.currency} {parseFloat(indexSuccess.old_rent).toLocaleString('en-GB', { minimumFractionDigits: 2 })}
							→
							<strong class="text-white">{indexModal.currency} {parseFloat(indexSuccess.new_rent).toLocaleString('en-GB', { minimumFractionDigits: 2 })}</strong>
						</p>
						{#if indexSendEmail}
							<p class="mt-2 text-xs text-white/30">Notification email sent to lessee.</p>
						{/if}
					</div>
					<button
						onclick={() => { indexModal = null; }}
						class="w-full rounded-xl border border-white/10 py-2.5 text-sm text-white/50 hover:text-white transition-colors"
					>Close</button>

				{:else}
					<!-- Current rent display -->
					<div class="flex items-center justify-between rounded-xl border border-white/[0.06] bg-white/[0.02] px-4 py-3">
						<span class="text-xs text-white/40">Current rent (excl. VAT)</span>
						<span class="font-mono text-sm font-semibold text-white">
							{indexModal.currency} {parseFloat(indexModal.base_rent_amount).toLocaleString('en-GB', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
						</span>
					</div>

					<!-- Mode toggle -->
					<div>
						<p class="mb-2 text-xs font-medium uppercase tracking-wider text-white/30">Index method</p>
						<div class="flex gap-1 rounded-xl border border-white/[0.07] bg-[#0a0a0a] p-1">
							<button
								type="button"
								onclick={() => { indexMode = 'quotient'; indexPercentage = ''; }}
								class="flex-1 rounded-lg py-2 text-xs font-medium transition-colors
									{indexMode === 'quotient' ? 'bg-white/10 text-white' : 'text-white/40 hover:text-white/70'}"
							>Quotient (a / b)</button>
							<button
								type="button"
								onclick={() => { indexMode = 'percentage'; indexNumerator = ''; indexDenominator = ''; }}
								class="flex-1 rounded-lg py-2 text-xs font-medium transition-colors
									{indexMode === 'percentage' ? 'bg-white/10 text-white' : 'text-white/40 hover:text-white/70'}"
							>Percentage (%)</button>
						</div>
					</div>

					<!-- Index input -->
					{#if indexMode === 'quotient'}
						<div>
							<p class="mb-2 text-xs font-medium uppercase tracking-wider text-white/30">Index numbers</p>
							<div class="flex flex-col items-center gap-1">
								<input
									type="number"
									bind:value={indexNumerator}
									placeholder="New index"
									min="0"
									step="any"
									class="w-full rounded-xl border border-white/10 bg-[#1a1a1a] px-4 py-2.5 text-sm text-white placeholder-white/20 focus:border-indigo-500/50 focus:outline-none focus:ring-1 focus:ring-indigo-500/50 transition font-mono"
								/>
								<span class="text-white/25 text-base select-none leading-none">÷</span>
								<input
									type="number"
									bind:value={indexDenominator}
									placeholder="Base index"
									min="0.01"
									step="any"
									class="w-full rounded-xl border border-white/10 bg-[#1a1a1a] px-4 py-2.5 text-sm text-white placeholder-white/20 focus:border-indigo-500/50 focus:outline-none focus:ring-1 focus:ring-indigo-500/50 transition font-mono"
								/>
							</div>
							{#if indexNumerator && indexDenominator && parseFloat(indexDenominator) > 0}
								<p class="mt-1.5 text-xs text-white/30">
									= {(parseFloat(indexNumerator) / parseFloat(indexDenominator) * 100 - 100).toFixed(3)}% increase
								</p>
							{/if}
						</div>
					{:else}
						<div>
							<label class="mb-2 block text-xs font-medium uppercase tracking-wider text-white/30">Percentage increase</label>
							<div class="flex items-center gap-2">
								<input
									type="number"
									bind:value={indexPercentage}
									placeholder="e.g. 3.20"
									step="0.001"
									class="flex-1 rounded-xl border border-white/10 bg-[#1a1a1a] px-4 py-2.5 text-sm text-white placeholder-white/20 focus:border-indigo-500/50 focus:outline-none focus:ring-1 focus:ring-indigo-500/50 transition font-mono"
								/>
								<span class="text-white/40 text-sm select-none pr-1">%</span>
							</div>
						</div>
					{/if}

					<!-- Live preview -->
					{#if indexNewRent}
						<div class="flex items-center justify-between rounded-xl border border-indigo-500/20 bg-indigo-500/[0.06] px-4 py-3">
							<span class="text-xs text-white/40">New rent (excl. VAT)</span>
							<span class="font-mono text-sm font-semibold text-indigo-300">
								{indexModal.currency} {parseFloat(indexNewRent).toLocaleString('en-GB', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
							</span>
						</div>
					{/if}

					<!-- Effective date -->
					<div>
						<label class="mb-2 block text-xs font-medium uppercase tracking-wider text-white/30" for="idx_effective">
							Effective date
						</label>
						<input
							id="idx_effective"
							type="date"
							bind:value={indexEffectiveDate}
							class="w-full rounded-xl border border-white/10 bg-[#1a1a1a] px-4 py-2.5 text-sm text-white focus:border-indigo-500/50 focus:outline-none focus:ring-1 focus:ring-indigo-500/50 transition"
						/>
					</div>

					<!-- Send email toggle -->
					<label class="flex cursor-pointer items-center gap-3 rounded-xl border border-white/[0.06] bg-white/[0.02] px-4 py-3">
						<input
							type="checkbox"
							bind:checked={indexSendEmail}
							class="h-4 w-4 rounded border-white/20 bg-[#1a1a1a] accent-indigo-500"
						/>
						<div>
							<p class="text-sm font-medium text-white">Send notification to lessee</p>
							<p class="text-xs text-white/30">Email in the invoice language with old rent, new rent, and effective date.</p>
						</div>
					</label>

					{#if indexError}
						<div class="rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3">
							<p class="text-sm text-red-400">{indexError}</p>
						</div>
					{/if}

					<!-- Actions -->
					<div class="flex gap-3 pt-1">
						<button
							type="button"
							onclick={() => { indexModal = null; }}
							class="flex-1 rounded-xl border border-white/10 py-2.5 text-sm font-medium text-white/50 hover:text-white hover:border-white/20 transition-colors"
						>Cancel</button>
						<button
							type="button"
							onclick={handleApplyIndex}
							disabled={indexApplying || !indexNewRent || !indexEffectiveDate}
							class="flex-1 rounded-xl bg-indigo-600 py-2.5 text-sm font-semibold text-white hover:bg-indigo-500 disabled:opacity-40 transition-colors"
						>{indexApplying ? 'Applying…' : 'Apply & confirm'}</button>
					</div>
				{/if}
			</div>
		</div>
	</div>
{/if}
