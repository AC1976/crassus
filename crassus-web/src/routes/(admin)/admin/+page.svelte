<script lang="ts">
	import { browser } from '$app/environment';
	import { api } from '$lib/api/client';

	// ── Types ────────────────────────────────────────────────────────────────

	interface OrgRow {
		org_id: number;
		org_name: string;
		owner_email: string;
		created_at: string;
		trial_ends_at: string;
		days_remaining: number;
		subscription_status: 'trial' | 'active' | 'churned' | 'exempt';
		admin_notes: string | null;
		property_count: number;
		user_count: number;
		suggested_plan: string;
	}

	// ── State ────────────────────────────────────────────────────────────────

	let orgs: OrgRow[] = $state([]);
	let loading = $state(true);
	let error = $state('');

	// Email modal
	let emailTarget: OrgRow | null = $state(null);
	let emailSubject = $state('');
	let emailBody = $state('');
	let sending = $state(false);
	let sendError = $state('');
	let sendDone = $state(false);

	// Notes modal
	let notesTarget: OrgRow | null = $state(null);
	let notesValue = $state('');
	let savingNotes = $state(false);

	// ── Data loading ─────────────────────────────────────────────────────────

	async function loadOrgs() {
		loading = true;
		error = '';
		try {
			orgs = await api.get<OrgRow[]>('/admin/orgs');
		} catch (e: unknown) {
			error = e instanceof Error ? e.message : 'Failed to load organisations.';
		} finally {
			loading = false;
		}
	}

	if (browser) loadOrgs();

	// ── Status helpers ───────────────────────────────────────────────────────

	function statusLabel(row: OrgRow): string {
		if (row.subscription_status === 'active') return 'Active';
		if (row.subscription_status === 'churned') return 'Churned';
		if (row.subscription_status === 'exempt') return 'Exempt';
		// trial
		if (row.days_remaining > 14) return 'Trial';
		if (row.days_remaining > 0) return 'Trial (expiring)';
		return 'Trial expired';
	}

	function statusClass(row: OrgRow): string {
		if (row.subscription_status === 'active')
			return 'bg-emerald-500/15 text-emerald-400 border-emerald-500/20';
		if (row.subscription_status === 'churned')
			return 'bg-zinc-500/15 text-zinc-400 border-zinc-500/20';
		if (row.subscription_status === 'exempt')
			return 'bg-sky-500/15 text-sky-400 border-sky-500/20';
		if (row.days_remaining > 14)
			return 'bg-indigo-500/15 text-indigo-300 border-indigo-500/20';
		if (row.days_remaining > 0)
			return 'bg-amber-500/15 text-amber-400 border-amber-500/20';
		return 'bg-red-500/15 text-red-400 border-red-500/20';
	}

	function planClass(plan: string): string {
		if (plan === 'Portfolio') return 'text-amber-400';
		if (plan === 'Growth') return 'text-indigo-300';
		return 'text-white/40';
	}

	function fmtDate(iso: string): string {
		return new Date(iso).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' });
	}

	// ── Status update ────────────────────────────────────────────────────────

	async function handleStatusChange(row: OrgRow, newStatus: string) {
		try {
			const updated = await api.patch<OrgRow>(`/admin/orgs/${row.org_id}`, {
				subscription_status: newStatus,
			});
			const idx = orgs.findIndex((o) => o.org_id === row.org_id);
			if (idx !== -1) orgs[idx] = updated;
		} catch {
			// silently ignore — could show a toast
		}
	}

	// ── Notes modal ──────────────────────────────────────────────────────────

	function openNotes(row: OrgRow) {
		notesTarget = row;
		notesValue = row.admin_notes ?? '';
	}

	async function saveNotes() {
		if (!notesTarget) return;
		savingNotes = true;
		try {
			const updated = await api.patch<OrgRow>(`/admin/orgs/${notesTarget.org_id}`, {
				admin_notes: notesValue,
			});
			const idx = orgs.findIndex((o) => o.org_id === notesTarget!.org_id);
			if (idx !== -1) orgs[idx] = updated;
			notesTarget = null;
		} finally {
			savingNotes = false;
		}
	}

	// ── Email modal ──────────────────────────────────────────────────────────

	function openEmail(row: OrgRow) {
		emailTarget = row;
		emailSubject = '';
		emailBody = `Hi,\n\nYour 3-month free trial of Crassus is coming to an end.\n\nBased on your portfolio size (${row.property_count} propert${row.property_count === 1 ? 'y' : 'ies'}), the ${row.suggested_plan} plan (€${{ Starter: 10, Growth: 20, Portfolio: 50 }[row.suggested_plan]}/year) would be the right fit.\n\nReply to this email and we'll get you set up.\n\nBest regards,\nThe Crassus Team`;
		sendError = '';
		sendDone = false;
	}

	async function sendEmail() {
		if (!emailTarget) return;
		sending = true;
		sendError = '';
		try {
			await api.post(`/admin/orgs/${emailTarget.org_id}/contact`, {
				subject: emailSubject,
				body: emailBody,
			});
			sendDone = true;
		} catch (e: unknown) {
			sendError = e instanceof Error ? e.message : 'Failed to send email.';
		} finally {
			sending = false;
		}
	}

	// ── Summary stats ────────────────────────────────────────────────────────

	let totalOrgs = $derived(orgs.length);
	let activeTrials = $derived(orgs.filter((o) => o.subscription_status === 'trial' && o.days_remaining > 0).length);
	let expiredTrials = $derived(orgs.filter((o) => o.subscription_status === 'trial' && o.days_remaining <= 0).length);
	let activeSubscriptions = $derived(orgs.filter((o) => o.subscription_status === 'active').length);
</script>

<svelte:head>
	<title>Admin — Crassus</title>
</svelte:head>

<!-- Page header -->
<div class="mb-8 flex items-start justify-between">
	<div>
		<h1 class="text-xl font-bold tracking-tight text-white">Organisations</h1>
		<p class="mt-1 text-sm text-white/40">Monitor accounts, track trial status, and reach out to convert.</p>
	</div>
	<button
		onclick={loadOrgs}
		class="rounded-lg border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-white/50 transition hover:text-white/80"
	>
		Refresh
	</button>
</div>

<!-- Summary cards -->
<div class="mb-8 grid grid-cols-2 gap-4 sm:grid-cols-4">
	{#each [
		{ label: 'Total accounts', value: totalOrgs, color: 'text-white' },
		{ label: 'Active trials', value: activeTrials, color: 'text-indigo-300' },
		{ label: 'Trials expired', value: expiredTrials, color: expiredTrials > 0 ? 'text-amber-400' : 'text-white/40' },
		{ label: 'Paying', value: activeSubscriptions, color: activeSubscriptions > 0 ? 'text-emerald-400' : 'text-white/40' },
	] as card}
		<div class="rounded-2xl border border-white/[0.07] bg-[#111111] p-5">
			<p class="text-xs text-white/40">{card.label}</p>
			<p class="mt-1.5 text-3xl font-bold {card.color}">{card.value}</p>
		</div>
	{/each}
</div>

<!-- Table -->
{#if loading}
	<div class="py-20 text-center text-sm text-white/30">Loading…</div>
{:else if error}
	<div class="rounded-xl border border-red-500/20 bg-red-500/10 p-4 text-sm text-red-400">{error}</div>
{:else if orgs.length === 0}
	<div class="py-20 text-center text-sm text-white/30">No organisations yet.</div>
{:else}
	<div class="overflow-hidden rounded-2xl border border-white/[0.07]">
		<table class="w-full text-sm">
			<thead>
				<tr class="border-b border-white/[0.07] bg-[#111111]">
					<th class="px-4 py-3 text-left text-xs font-medium text-white/40">Organisation</th>
					<th class="px-4 py-3 text-left text-xs font-medium text-white/40">Owner</th>
					<th class="px-4 py-3 text-left text-xs font-medium text-white/40">Registered</th>
					<th class="px-4 py-3 text-left text-xs font-medium text-white/40">Trial ends</th>
					<th class="px-4 py-3 text-left text-xs font-medium text-white/40">Status</th>
					<th class="px-4 py-3 text-center text-xs font-medium text-white/40">Props</th>
					<th class="px-4 py-3 text-center text-xs font-medium text-white/40">Users</th>
					<th class="px-4 py-3 text-left text-xs font-medium text-white/40">Plan fit</th>
					<th class="px-4 py-3 text-right text-xs font-medium text-white/40">Actions</th>
				</tr>
			</thead>
			<tbody>
				{#each orgs as row, i}
					<tr class="border-b border-white/[0.04] {i % 2 === 0 ? 'bg-[#0d0d0d]' : 'bg-[#0a0a0a]'} hover:bg-white/[0.02] transition-colors">
						<!-- Org name + notes indicator -->
						<td class="px-4 py-3">
							<div class="flex items-center gap-2">
								<span class="font-medium text-white">{row.org_name}</span>
								{#if row.admin_notes}
									<span class="h-1.5 w-1.5 rounded-full bg-amber-400" title="Has notes"></span>
								{/if}
							</div>
						</td>

						<!-- Owner email -->
						<td class="px-4 py-3 text-white/60">{row.owner_email}</td>

						<!-- Registered -->
						<td class="px-4 py-3 text-white/50">{fmtDate(row.created_at)}</td>

						<!-- Trial ends -->
						<td class="px-4 py-3">
							<span class="text-white/50">{fmtDate(row.trial_ends_at)}</span>
							{#if row.subscription_status === 'trial'}
								<span class="ml-1.5 text-xs {row.days_remaining > 0 ? 'text-white/30' : 'text-red-400'}">
									({row.days_remaining > 0 ? `${row.days_remaining}d left` : `${Math.abs(row.days_remaining)}d ago`})
								</span>
							{/if}
						</td>

						<!-- Status dropdown -->
						<td class="px-4 py-3">
							<select
								value={row.subscription_status}
								onchange={(e) => handleStatusChange(row, (e.target as HTMLSelectElement).value)}
								class="rounded-lg border px-2.5 py-1 text-xs font-medium transition focus:outline-none {statusClass(row)} bg-transparent cursor-pointer"
							>
								<option value="trial">Trial</option>
								<option value="active">Active</option>
								<option value="churned">Churned</option>
								<option value="exempt">Exempt</option>
							</select>
						</td>

						<!-- Property count -->
						<td class="px-4 py-3 text-center font-medium text-white/70">{row.property_count}</td>

						<!-- User count -->
						<td class="px-4 py-3 text-center text-white/50">{row.user_count}</td>

						<!-- Suggested plan -->
						<td class="px-4 py-3 text-xs font-medium {planClass(row.suggested_plan)}">{row.suggested_plan}</td>

						<!-- Actions -->
						<td class="px-4 py-3">
							<div class="flex items-center justify-end gap-2">
								<button
									onclick={() => openNotes(row)}
									class="rounded-lg border border-white/10 px-2.5 py-1 text-xs text-white/50 transition hover:border-white/20 hover:text-white/80"
									title="Edit notes"
								>
									Notes
								</button>
								<button
									onclick={() => openEmail(row)}
									class="rounded-lg border border-indigo-500/30 bg-indigo-500/10 px-2.5 py-1 text-xs text-indigo-300 transition hover:bg-indigo-500/20"
								>
									Email
								</button>
							</div>
						</td>
					</tr>
				{/each}
			</tbody>
		</table>
	</div>
{/if}

<!-- ── Email modal ──────────────────────────────────────────────────────── -->
{#if emailTarget}
	<div class="fixed inset-0 z-50 flex items-center justify-center bg-black/60 px-4 backdrop-blur-sm">
		<div class="w-full max-w-lg rounded-2xl border border-white/10 bg-[#141414] p-6 shadow-2xl">

			{#if sendDone}
				<div class="py-6 text-center">
					<div class="mx-auto mb-3 flex h-10 w-10 items-center justify-center rounded-full bg-emerald-500/15">
						<svg class="h-5 w-5 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
							<path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/>
						</svg>
					</div>
					<p class="text-sm font-semibold text-white">Email sent to {emailTarget.owner_email}</p>
					<button onclick={() => (emailTarget = null)} class="mt-4 text-xs text-white/40 hover:text-white/70 transition">
						Close
					</button>
				</div>
			{:else}
				<div class="mb-5 flex items-start justify-between">
					<div>
						<h2 class="text-sm font-semibold text-white">Email {emailTarget.org_name}</h2>
						<p class="mt-0.5 text-xs text-white/40">To: {emailTarget.owner_email}</p>
					</div>
					<button onclick={() => (emailTarget = null)} class="text-white/30 hover:text-white/60 transition">
						<svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
							<path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/>
						</svg>
					</button>
				</div>

				<div class="space-y-4">
					<div>
						<label class="mb-1.5 block text-xs font-medium uppercase tracking-wider text-white/40" for="em_subject">Subject</label>
						<input
							id="em_subject"
							type="text"
							bind:value={emailSubject}
							placeholder="Your Crassus trial is ending soon"
							class="w-full rounded-xl border border-white/10 bg-[#1a1a1a] px-4 py-2.5 text-sm text-white placeholder-white/20 focus:border-indigo-500/50 focus:outline-none focus:ring-1 focus:ring-indigo-500/50 transition"
						/>
					</div>
					<div>
						<label class="mb-1.5 block text-xs font-medium uppercase tracking-wider text-white/40" for="em_body">Message</label>
						<textarea
							id="em_body"
							bind:value={emailBody}
							rows={10}
							class="w-full rounded-xl border border-white/10 bg-[#1a1a1a] px-4 py-2.5 text-sm text-white placeholder-white/20 focus:border-indigo-500/50 focus:outline-none focus:ring-1 focus:ring-indigo-500/50 transition resize-none font-mono"
						></textarea>
					</div>

					{#if sendError}
						<p class="text-xs text-red-400">{sendError}</p>
					{/if}

					<div class="flex justify-end gap-3">
						<button
							onclick={() => (emailTarget = null)}
							class="rounded-xl border border-white/10 px-4 py-2 text-sm text-white/50 transition hover:text-white/80"
						>Cancel</button>
						<button
							onclick={sendEmail}
							disabled={sending || !emailSubject.trim() || !emailBody.trim()}
							class="rounded-xl bg-indigo-600 px-5 py-2 text-sm font-semibold text-white transition hover:bg-indigo-500 disabled:opacity-40"
						>
							{sending ? 'Sending…' : 'Send email'}
						</button>
					</div>
				</div>
			{/if}
		</div>
	</div>
{/if}

<!-- ── Notes modal ──────────────────────────────────────────────────────── -->
{#if notesTarget}
	<div class="fixed inset-0 z-50 flex items-center justify-center bg-black/60 px-4 backdrop-blur-sm">
		<div class="w-full max-w-md rounded-2xl border border-white/10 bg-[#141414] p-6 shadow-2xl">
			<div class="mb-5 flex items-start justify-between">
				<div>
					<h2 class="text-sm font-semibold text-white">Internal notes</h2>
					<p class="mt-0.5 text-xs text-white/40">{notesTarget.org_name}</p>
				</div>
				<button onclick={() => (notesTarget = null)} class="text-white/30 hover:text-white/60 transition">
					<svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
						<path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/>
					</svg>
				</button>
			</div>

			<textarea
				bind:value={notesValue}
				rows={6}
				placeholder="e.g. Spoke with owner on 10 Jun. Interested in Growth plan. Follow up in 2 weeks."
				class="w-full rounded-xl border border-white/10 bg-[#1a1a1a] px-4 py-2.5 text-sm text-white placeholder-white/20 focus:border-indigo-500/50 focus:outline-none focus:ring-1 focus:ring-indigo-500/50 transition resize-none"
			></textarea>

			<div class="mt-4 flex justify-end gap-3">
				<button
					onclick={() => (notesTarget = null)}
					class="rounded-xl border border-white/10 px-4 py-2 text-sm text-white/50 transition hover:text-white/80"
				>Cancel</button>
				<button
					onclick={saveNotes}
					disabled={savingNotes}
					class="rounded-xl bg-indigo-600 px-5 py-2 text-sm font-semibold text-white transition hover:bg-indigo-500 disabled:opacity-40"
				>
					{savingNotes ? 'Saving…' : 'Save notes'}
				</button>
			</div>
		</div>
	</div>
{/if}
