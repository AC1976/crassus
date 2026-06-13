<script lang="ts">
	import { browser } from '$app/environment';
	import { api } from '$lib/api/client';
	import { getMe, type User } from '$lib/auth';

	type Settings = {
		id?: number;
		company_name: string;
		company_vat_number: string | null;
		company_address: string;
		billing_email_sender: string;
		default_vat_rate: string;
		currency: string;
		reporting_preference: 'monthly' | 'quarterly';
		bank_account: string | null;
		logo_s3_key: string | null;
		lease_termination_notice_days: number;
		invoice_numbering_scheme: 'sequential' | 'property_ref';
		vat_consultant_email: string | null;
		invoice_language: 'en' | 'nl';
	};

	let user: User | null = $state(null);
	let exists = $state(false);
	let saving = $state(false);
	let success = $state(false);
	let error = $state('');
	let logoKey: string | null = $state(null);
	let logoUploading = $state(false);
	let logoError = $state('');

	let company_name = $state('');
	let company_vat_number = $state('');
	let company_address = $state('');
	let billing_email_sender = $state('');
	let default_vat_rate = $state('21.00');
	let currency = $state('EUR');
	let reporting_preference: 'monthly' | 'quarterly' = $state('quarterly');
	let bank_account = $state('');
	let lease_termination_notice_days = $state(365);
	let invoice_numbering_scheme: 'sequential' | 'property_ref' = $state('sequential');
	let vat_consultant_email = $state('');
	let invoice_language: 'en' | 'nl' = $state('en');

	// ── Team management ───────────────────────────────────────────────────────

	type TeamMember = { id: number; email: string; role: string; is_active: boolean };
	type PendingInvite = { id: number; invited_email: string; role: string; expires_at: string };

	let team: TeamMember[] = $state([]);
	let pendingInvites: PendingInvite[] = $state([]);
	let teamLoading = $state(false);

	let inviteEmail = $state('');
	let inviteRole: 'editor' | 'viewer' = $state('editor');
	let inviting = $state(false);
	let inviteError = $state('');
	let inviteSuccess = $state('');

	async function loadTeam() {
		teamLoading = true;
		try {
			[team, pendingInvites] = await Promise.all([
				api.get<TeamMember[]>('/auth/team'),
				api.get<PendingInvite[]>('/auth/invitations'),
			]);
		} catch (_) {
			// non-owner can still see team list, just not invites
			try { team = await api.get<TeamMember[]>('/auth/team'); } catch (_) {}
		} finally {
			teamLoading = false;
		}
	}

	async function handleInvite(e: SubmitEvent) {
		e.preventDefault();
		inviting = true; inviteError = ''; inviteSuccess = '';
		try {
			await api.post('/auth/invite', { email: inviteEmail.trim(), role: inviteRole });
			inviteSuccess = `Invite sent to ${inviteEmail.trim()}.`;
			inviteEmail = '';
			loadTeam();
		} catch (err: unknown) {
			inviteError = err instanceof Error ? err.message : 'Failed to send invite.';
		} finally {
			inviting = false;
		}
	}

	async function handleChangeRole(member: TeamMember, newRole: string) {
		try {
			await api.patch(`/auth/team/${member.id}/role`, { role: newRole });
			loadTeam();
		} catch (err: unknown) {
			alert(err instanceof Error ? err.message : 'Failed to update role.');
		}
	}

	async function handleRemoveMember(member: TeamMember) {
		if (!confirm(`Remove ${member.email} from the team?`)) return;
		try {
			await api.delete(`/auth/team/${member.id}`);
			loadTeam();
		} catch (err: unknown) {
			alert(err instanceof Error ? err.message : 'Failed to remove member.');
		}
	}

	async function handleCancelInvite(invite: PendingInvite) {
		try {
			await api.delete(`/auth/invitations/${invite.id}`);
			loadTeam();
		} catch (err: unknown) {
			alert(err instanceof Error ? err.message : 'Failed to cancel invite.');
		}
	}

	function populate(s: Settings) {
		company_name = s.company_name ?? '';
		company_vat_number = s.company_vat_number ?? '';
		company_address = s.company_address ?? '';
		billing_email_sender = s.billing_email_sender ?? '';
		default_vat_rate = s.default_vat_rate ?? '21.00';
		currency = s.currency ?? 'EUR';
		reporting_preference = s.reporting_preference ?? 'quarterly';
		bank_account = s.bank_account ?? '';
		lease_termination_notice_days = s.lease_termination_notice_days ?? 365;
		invoice_numbering_scheme = s.invoice_numbering_scheme ?? 'sequential';
		vat_consultant_email = s.vat_consultant_email ?? '';
		invoice_language = s.invoice_language ?? 'en';
		logoKey = s.logo_s3_key ?? null;
	}

	async function handleLogoUpload(e: Event) {
		const input = e.target as HTMLInputElement;
		const file = input.files?.[0];
		if (!file) return;
		logoUploading = true; logoError = '';
		const form = new FormData();
		form.append('file', file);
		try {
			const token = (await import('$lib/api/client')).getToken();
			const res = await fetch(`${import.meta.env.VITE_API_BASE_URL}/settings/logo`, {
				method: 'POST',
				headers: token ? { Authorization: `Bearer ${token}` } : {},
				body: form,
			});
			if (!res.ok) {
				const err = await res.json().catch(() => ({ detail: 'Upload failed' }));
				throw new Error(err.detail);
			}
			const updated = await res.json() as Settings;
			logoKey = updated.logo_s3_key;
			exists = true; // a settings row now exists regardless of whether the form was saved before
		} catch (err: unknown) {
			logoError = err instanceof Error ? err.message : 'Upload failed.';
			// Re-check whether a settings row exists so the form uses the right
			// HTTP method (POST vs PATCH) regardless of what the upload did.
			api.get<Settings>('/settings')
				.then((s) => { exists = true; populate(s); })
				.catch(() => { exists = false; });
		} finally {
			logoUploading = false;
			input.value = '';
		}
	}

	async function handleRemoveLogo() {
		try {
			await api.delete('/settings/logo');
			logoKey = null;
		} catch (err: unknown) {
			logoError = err instanceof Error ? err.message : 'Failed to remove logo.';
		}
	}

	// ── Export & account deletion ─────────────────────────────────────────────

	let exporting = $state(false);
	let exportError = $state('');

	let showDeleteModal = $state(false);
	let deleteConfirmText = $state('');
	let deleting = $state(false);
	let deleteError = $state('');

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

	async function handleDeleteAccount() {
		if (deleteConfirmText !== 'DELETE') return;
		deleting = true; deleteError = '';
		try {
			await api.delete('/settings/account');
			// All data gone — redirect to login
			window.location.replace('/login');
		} catch (err: unknown) {
			deleteError = err instanceof Error ? err.message : 'Deletion failed. Please try again.';
			deleting = false;
		}
	}

	if (browser) {
		getMe().then((u) => { user = u; });

		api.get<Settings>('/settings')
			.then((s) => { exists = true; populate(s); })
			.catch(() => { exists = false; });

		loadTeam();
	}

	async function handleSubmit(e: SubmitEvent) {
		e.preventDefault();
		saving = true;
		error = '';
		success = false;

		const payload = {
			company_name,
			company_vat_number: company_vat_number || null,
			company_address,
			billing_email_sender,
			default_vat_rate,
			currency,
			reporting_preference,
			bank_account: bank_account || null,
			lease_termination_notice_days,
			invoice_numbering_scheme,
			vat_consultant_email: vat_consultant_email || null,
			invoice_language,
		};

		try {
			if (exists) {
				await api.patch('/settings', payload);
			} else {
				await api.post('/settings', payload);
				exists = true;
			}
			success = true;
		} catch (err: unknown) {
			error = err instanceof Error ? err.message : 'Failed to save settings.';
		} finally {
			saving = false;
		}
	}
</script>

<div class="mb-8">
	<h2 class="text-2xl font-semibold text-white">Settings</h2>
	<p class="mt-1 text-sm text-white/40">Organisation configuration and billing preferences</p>
</div>

{#if user && user.role !== 'owner'}
	<div class="rounded-2xl border border-white/[0.07] bg-[#111111] p-8 text-center">
		<p class="text-sm text-white/30">Only the account owner can manage settings.</p>
	</div>
{:else}
	<form onsubmit={handleSubmit} class="max-w-2xl space-y-6">

		<!-- Company -->
		<div class="rounded-2xl border border-white/[0.07] bg-[#111111] p-6">
			<h3 class="mb-5 text-xs font-semibold uppercase tracking-wider text-white/30">Company</h3>
			<div class="space-y-4">
				<div>
					<label class="mb-1.5 block text-xs font-medium uppercase tracking-wider text-white/40" for="company_name">Company Name</label>
					<input id="company_name" type="text" bind:value={company_name} required placeholder="Acme Properties Ltd."
						class="w-full rounded-xl border border-white/10 bg-[#1a1a1a] px-4 py-3 text-sm text-white placeholder-white/20 focus:border-indigo-500/50 focus:outline-none focus:ring-1 focus:ring-indigo-500/50 transition" />
				</div>

				<div>
					<label class="mb-1.5 block text-xs font-medium uppercase tracking-wider text-white/40" for="company_vat_number">
						VAT Number <span class="normal-case text-white/20">(optional)</span>
					</label>
					<input id="company_vat_number" type="text" bind:value={company_vat_number} placeholder="BE0123456789"
						class="w-full rounded-xl border border-white/10 bg-[#1a1a1a] px-4 py-3 text-sm text-white placeholder-white/20 focus:border-indigo-500/50 focus:outline-none focus:ring-1 focus:ring-indigo-500/50 transition" />
				</div>

				<div>
					<label class="mb-1.5 block text-xs font-medium uppercase tracking-wider text-white/40" for="company_address">Company Address</label>
					<textarea id="company_address" bind:value={company_address} required rows={3} placeholder={"123 Main Street\nBrussels, 1000\nBelgium"}
						class="w-full resize-none rounded-xl border border-white/10 bg-[#1a1a1a] px-4 py-3 text-sm text-white placeholder-white/20 focus:border-indigo-500/50 focus:outline-none focus:ring-1 focus:ring-indigo-500/50 transition"></textarea>
				</div>
			</div>
		</div>

		<!-- Logo -->
		<div class="rounded-2xl border border-white/[0.07] bg-[#111111] p-6">
			<h3 class="mb-5 text-xs font-semibold uppercase tracking-wider text-white/30">Company Logo <span class="normal-case font-normal text-white/20">(optional — appears on invoices)</span></h3>
			{#if logoKey}
				<div class="mb-4 flex items-center gap-4">
					<span class="rounded-xl border border-emerald-500/20 bg-emerald-500/10 px-3 py-2 text-xs text-emerald-400">✓ Logo uploaded</span>
					<button type="button" onclick={handleRemoveLogo} class="text-xs text-red-400/60 hover:text-red-400 transition-colors">Remove</button>
				</div>
			{/if}
			{#if logoError}
				<div class="mb-3 rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3">
					<p class="text-sm text-red-400">{logoError}</p>
				</div>
			{/if}
			<label class="flex cursor-pointer items-center gap-3 rounded-xl border border-dashed border-white/10 bg-[#1a1a1a] px-4 py-4 hover:border-white/20 transition-colors">
				<svg class="h-5 w-5 text-white/30" fill="none" viewBox="0 0 24 24" stroke="currentColor">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
				</svg>
				<span class="text-sm text-white/40">{logoUploading ? 'Uploading…' : 'Click to upload PNG, JPEG, or SVG'}</span>
				<input type="file" accept="image/png,image/jpeg,image/svg+xml" class="sr-only" onchange={handleLogoUpload} disabled={logoUploading} />
			</label>
		</div>

		<!-- Billing & Email -->
		<div class="rounded-2xl border border-white/[0.07] bg-[#111111] p-6">
			<h3 class="mb-5 text-xs font-semibold uppercase tracking-wider text-white/30">Billing & Email</h3>
			<div class="space-y-4">
				<div>
					<label class="mb-1.5 block text-xs font-medium uppercase tracking-wider text-white/40" for="billing_email_sender">Sender Email</label>
					<input id="billing_email_sender" type="email" bind:value={billing_email_sender} required placeholder="billing@yourdomain.com"
						class="w-full rounded-xl border border-white/10 bg-[#1a1a1a] px-4 py-3 text-sm text-white placeholder-white/20 focus:border-indigo-500/50 focus:outline-none focus:ring-1 focus:ring-indigo-500/50 transition" />
				</div>

				<div>
					<label class="mb-1.5 block text-xs font-medium uppercase tracking-wider text-white/40" for="bank_account">
						Bank Account <span class="normal-case text-white/20">(printed on invoices)</span>
					</label>
					<input id="bank_account" type="text" bind:value={bank_account} placeholder="BE68 5390 0754 7034"
						class="w-full rounded-xl border border-white/10 bg-[#1a1a1a] px-4 py-3 text-sm text-white placeholder-white/20 focus:border-indigo-500/50 focus:outline-none focus:ring-1 focus:ring-indigo-500/50 transition" />
				</div>

				<div>
					<label class="mb-1.5 block text-xs font-medium uppercase tracking-wider text-white/40" for="vat_consultant_email">
						VAT Consultant Email <span class="normal-case text-white/20">(optional — for VAT report emails)</span>
					</label>
					<input id="vat_consultant_email" type="email" bind:value={vat_consultant_email} placeholder="consultant@taxfirm.com"
						class="w-full rounded-xl border border-white/10 bg-[#1a1a1a] px-4 py-3 text-sm text-white placeholder-white/20 focus:border-indigo-500/50 focus:outline-none focus:ring-1 focus:ring-indigo-500/50 transition" />
				</div>

			</div>
		</div>

		<!-- Financial Defaults -->
		<div class="rounded-2xl border border-white/[0.07] bg-[#111111] p-6">
			<h3 class="mb-5 text-xs font-semibold uppercase tracking-wider text-white/30">Financial Defaults</h3>
			<div class="grid grid-cols-2 gap-4">
				<div>
					<label class="mb-1.5 block text-xs font-medium uppercase tracking-wider text-white/40" for="default_vat_rate">Default VAT Rate (%)</label>
					<input id="default_vat_rate" type="number" step="0.01" min="0" max="100" bind:value={default_vat_rate} required
						class="w-full rounded-xl border border-white/10 bg-[#1a1a1a] px-4 py-3 text-sm text-white focus:border-indigo-500/50 focus:outline-none focus:ring-1 focus:ring-indigo-500/50 transition" />
				</div>

				<div>
					<label class="mb-1.5 block text-xs font-medium uppercase tracking-wider text-white/40" for="currency">Currency</label>
					<select id="currency" bind:value={currency}
						class="w-full rounded-xl border border-white/10 bg-[#1a1a1a] px-4 py-3 text-sm text-white focus:border-indigo-500/50 focus:outline-none focus:ring-1 focus:ring-indigo-500/50 transition">
						<option value="EUR">EUR — Euro</option>
						<option value="USD">USD — US Dollar</option>
						<option value="GBP">GBP — British Pound</option>
						<option value="CHF">CHF — Swiss Franc</option>
					</select>
				</div>

				<div>
					<label class="mb-1.5 block text-xs font-medium uppercase tracking-wider text-white/40" for="notice_days">
						Termination Notice Period <span class="normal-case text-white/20">(days)</span>
					</label>
					<input id="notice_days" type="number" min="1" max="730" bind:value={lease_termination_notice_days} required
						class="w-full rounded-xl border border-white/10 bg-[#1a1a1a] px-4 py-3 text-sm text-white focus:border-indigo-500/50 focus:outline-none focus:ring-1 focus:ring-indigo-500/50 transition" />
					<p class="mt-1.5 text-xs text-white/25">Dashboard countdown warns you this many days before lease expiry to notify your lessee. Defaults to 365.</p>
				</div>

				<div class="col-span-2">
					<label class="mb-3 block text-xs font-medium uppercase tracking-wider text-white/40">Invoice Numbering</label>
					<div class="flex gap-3">
						{#each ([
							{ value: 'sequential', label: 'Sequential', example: 'INV-2026-0001', desc: 'Auto-incrementing number per year' },
							{ value: 'property_ref', label: 'Property Reference', example: 'M2/2026/07', desc: 'Set a short code per property — credit notes become M2/2026/07/CR' },
						]) as opt}
							<button type="button" onclick={() => (invoice_numbering_scheme = opt.value as 'sequential' | 'property_ref')}
								class="flex-1 rounded-xl border p-3 text-left transition
									{invoice_numbering_scheme === opt.value
									? 'border-indigo-500/50 bg-indigo-500/10'
									: 'border-white/10 bg-[#1a1a1a] hover:border-white/20'}">
								<p class="text-sm font-medium {invoice_numbering_scheme === opt.value ? 'text-indigo-400' : 'text-white/70'}">{opt.label}</p>
								<p class="mt-0.5 font-mono text-xs {invoice_numbering_scheme === opt.value ? 'text-indigo-300/70' : 'text-white/25'}">{opt.example}</p>
								<p class="mt-1 text-xs text-white/30">{opt.desc}</p>
							</button>
						{/each}
					</div>
					{#if invoice_numbering_scheme === 'property_ref'}
						<p class="mt-2 text-xs text-amber-400/70">⚠ Set a Property Reference on each property for this to take effect. Properties without a reference fall back to sequential numbering.</p>
					{/if}
				</div>

				<div class="col-span-2">
					<label class="mb-3 block text-xs font-medium uppercase tracking-wider text-white/40">Invoice Language</label>
					<div class="flex gap-3">
						{#each ([
							{ value: 'en', label: 'English', desc: 'Invoice, Due Date, Rental Period…' },
							{ value: 'nl', label: 'Nederlands', desc: 'Factuur, Vervaldatum, Huurperiode…' },
						]) as opt}
							<button type="button" onclick={() => (invoice_language = opt.value as 'en' | 'nl')}
								class="flex-1 rounded-xl border p-3 text-left transition
									{invoice_language === opt.value
									? 'border-indigo-500/50 bg-indigo-500/10'
									: 'border-white/10 bg-[#1a1a1a] hover:border-white/20'}">
								<p class="text-sm font-medium {invoice_language === opt.value ? 'text-indigo-400' : 'text-white/70'}">{opt.label}</p>
								<p class="mt-0.5 text-xs {invoice_language === opt.value ? 'text-indigo-300/60' : 'text-white/25'}">{opt.desc}</p>
							</button>
						{/each}
					</div>
					<p class="mt-2 text-xs text-white/25">Applies to invoice and credit note PDFs, and all emails sent to lessees.</p>
				</div>

				<div class="col-span-2">
					<label class="mb-3 block text-xs font-medium uppercase tracking-wider text-white/40">VAT Reporting Period</label>
					<div class="flex gap-3">
						{#each ([{ value: 'quarterly', label: 'Quarterly' }, { value: 'monthly', label: 'Monthly' }]) as option}
							<button type="button" onclick={() => (reporting_preference = option.value as 'monthly' | 'quarterly')}
								class="flex-1 rounded-xl border py-3 text-sm font-medium transition
									{reporting_preference === option.value
									? 'border-indigo-500/50 bg-indigo-500/10 text-indigo-400'
									: 'border-white/10 bg-[#1a1a1a] text-white/40 hover:text-white/70'}">
								{option.label}
							</button>
						{/each}
					</div>
				</div>
			</div>
		</div>

		{#if error}
			<div class="rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3">
				<p class="text-sm text-red-400">{error}</p>
			</div>
		{/if}

		{#if success}
			<div class="rounded-xl border border-emerald-500/20 bg-emerald-500/10 px-4 py-3">
				<p class="text-sm text-emerald-400">Settings saved successfully.</p>
			</div>
		{/if}

		<div class="flex justify-end">
			<button type="submit" disabled={saving}
				class="rounded-xl bg-indigo-600 px-6 py-2.5 text-sm font-semibold text-white hover:bg-indigo-500 disabled:opacity-40 transition-colors">
				{saving ? 'Saving…' : exists ? 'Save Changes' : 'Create Settings'}
			</button>
		</div>

	</form>

	<!-- ── Team Management ─────────────────────────────────────────────────── -->
	{#if user?.role === 'owner'}
	<div class="mt-10 max-w-2xl space-y-6">

		<div>
			<h3 class="text-lg font-semibold text-white">Team</h3>
			<p class="mt-1 text-sm text-white/40">Invite colleagues and manage access roles.</p>
		</div>

		<!-- Current members -->
		<div class="overflow-hidden rounded-2xl border border-white/[0.07] bg-[#111111]">
			<div class="border-b border-white/[0.07] px-6 py-4">
				<h4 class="text-xs font-semibold uppercase tracking-wider text-white/30">Members</h4>
			</div>
			{#if teamLoading}
				<div class="px-6 py-6 text-center text-sm text-white/30">Loading…</div>
			{:else}
				<div class="divide-y divide-white/[0.05]">
					{#each team as member}
						<div class="flex items-center justify-between px-6 py-4">
							<div>
								<p class="text-sm font-medium text-white">{member.email}</p>
								<p class="text-xs text-white/30 capitalize">{member.role}</p>
							</div>
							{#if member.role !== 'owner'}
								<div class="flex items-center gap-4">
									<select
										value={member.role}
										onchange={(e) => handleChangeRole(member, (e.target as HTMLSelectElement).value)}
										class="rounded-lg border border-white/10 bg-[#1a1a1a] px-3 py-1.5 text-xs text-white focus:outline-none"
									>
										<option value="editor">Editor</option>
										<option value="viewer">Viewer</option>
									</select>
									<button
										onclick={() => handleRemoveMember(member)}
										class="text-xs text-red-400/60 hover:text-red-400 transition-colors"
									>Remove</button>
								</div>
							{:else}
								<span class="rounded-md bg-indigo-500/10 px-2.5 py-1 text-xs font-medium text-indigo-400">Owner</span>
							{/if}
						</div>
					{/each}
				</div>
			{/if}
		</div>

		<!-- Pending invitations -->
		{#if pendingInvites.length > 0}
		<div class="overflow-hidden rounded-2xl border border-white/[0.07] bg-[#111111]">
			<div class="border-b border-white/[0.07] px-6 py-4">
				<h4 class="text-xs font-semibold uppercase tracking-wider text-white/30">Pending Invitations</h4>
			</div>
			<div class="divide-y divide-white/[0.05]">
				{#each pendingInvites as invite}
					<div class="flex items-center justify-between px-6 py-4">
						<div>
							<p class="text-sm font-medium text-white">{invite.invited_email}</p>
							<p class="text-xs text-white/30 capitalize">
								{invite.role} · expires {new Date(invite.expires_at).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' })}
							</p>
						</div>
						<button
							onclick={() => handleCancelInvite(invite)}
							class="text-xs text-red-400/60 hover:text-red-400 transition-colors"
						>Cancel</button>
					</div>
				{/each}
			</div>
		</div>
		{/if}

		<!-- Invite form -->
		<div class="rounded-2xl border border-white/[0.07] bg-[#111111] p-6">
			<h4 class="mb-4 text-xs font-semibold uppercase tracking-wider text-white/30">Invite a Team Member</h4>
			<form onsubmit={handleInvite} class="space-y-4">
				<div class="grid grid-cols-3 gap-3">
					<div class="col-span-2">
						<label class="mb-1.5 block text-xs font-medium uppercase tracking-wider text-white/40" for="inv_email">Email Address</label>
						<input id="inv_email" type="email" bind:value={inviteEmail} required placeholder="colleague@company.com"
							class="w-full rounded-xl border border-white/10 bg-[#1a1a1a] px-4 py-3 text-sm text-white placeholder-white/20 focus:border-indigo-500/50 focus:outline-none focus:ring-1 focus:ring-indigo-500/50 transition" />
					</div>
					<div>
						<label class="mb-1.5 block text-xs font-medium uppercase tracking-wider text-white/40" for="inv_role">Role</label>
						<select id="inv_role" bind:value={inviteRole}
							class="w-full rounded-xl border border-white/10 bg-[#1a1a1a] px-4 py-3 text-sm text-white focus:border-indigo-500/50 focus:outline-none transition">
							<option value="editor">Editor</option>
							<option value="viewer">Viewer</option>
						</select>
					</div>
				</div>

				<div class="rounded-xl border border-white/[0.05] bg-white/[0.02] px-4 py-3 text-xs text-white/30 space-y-1">
					<p><strong class="text-white/50">Editor</strong> — can create and edit invoices, expenses, documents</p>
					<p><strong class="text-white/50">Viewer</strong> — read-only access to all data</p>
				</div>

				{#if inviteError}
					<div class="rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3">
						<p class="text-sm text-red-400">{inviteError}</p>
					</div>
				{/if}
				{#if inviteSuccess}
					<div class="rounded-xl border border-emerald-500/20 bg-emerald-500/10 px-4 py-3">
						<p class="text-sm text-emerald-400">{inviteSuccess}</p>
					</div>
				{/if}

				<div class="flex justify-end">
					<button type="submit" disabled={inviting || !inviteEmail.trim()}
						class="rounded-xl bg-indigo-600 px-6 py-2.5 text-sm font-semibold text-white hover:bg-indigo-500 disabled:opacity-40 transition-colors">
						{inviting ? 'Sending…' : 'Send Invitation'}
					</button>
				</div>
			</form>
		</div>

	</div>
	{/if}

	<!-- ── Danger Zone ─────────────────────────────────────────────────────── -->
	<div class="rounded-2xl border border-red-500/20 bg-[#111111] p-6">
		<h3 class="mb-1 text-xs font-semibold uppercase tracking-wider text-red-400/70">Danger Zone</h3>
		<p class="mb-5 text-xs text-white/30">These actions are permanent and cannot be undone.</p>

		<div class="space-y-4">
			<!-- Export -->
			<div class="flex items-center justify-between rounded-xl border border-white/[0.05] bg-white/[0.02] px-5 py-4">
				<div>
					<p class="text-sm font-medium text-white">Export all data</p>
					<p class="mt-0.5 text-xs text-white/30">Download a ZIP of all properties, invoices, documents and expenses.</p>
				</div>
				<button
					type="button"
					onclick={handleExport}
					disabled={exporting}
					class="ml-4 shrink-0 rounded-xl border border-white/10 bg-[#1a1a1a] px-5 py-2 text-sm font-medium text-white hover:bg-white/10 disabled:opacity-40 transition-colors"
				>{exporting ? 'Preparing…' : 'Download ZIP'}</button>
			</div>
			{#if exportError}
				<p class="text-xs text-red-400">{exportError}</p>
			{/if}

			<!-- Delete account -->
			<div class="flex items-center justify-between rounded-xl border border-red-500/20 bg-red-500/[0.04] px-5 py-4">
				<div>
					<p class="text-sm font-medium text-red-300">Delete account</p>
					<p class="mt-0.5 text-xs text-white/30">Permanently delete your organisation, all data, and all files. No recovery possible.</p>
				</div>
				<button
					type="button"
					onclick={() => { showDeleteModal = true; deleteConfirmText = ''; deleteError = ''; }}
					class="ml-4 shrink-0 rounded-xl border border-red-500/40 bg-red-500/10 px-5 py-2 text-sm font-medium text-red-400 hover:bg-red-500/20 transition-colors"
				>Delete account</button>
			</div>
		</div>
	</div>

{/if}

<!-- ── Delete account modal ──────────────────────────────────────────────── -->
{#if showDeleteModal}
	<div class="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
		<div class="w-full max-w-md rounded-2xl border border-red-500/30 bg-[#111111] p-6 shadow-2xl">
			<h3 class="mb-1 text-lg font-semibold text-red-400">Delete account</h3>
			<p class="mb-4 text-sm text-white/50">
				This will permanently delete your organisation, all properties, invoices, documents, expenses, and team members.
				<strong class="text-white/70">This cannot be undone.</strong>
			</p>

			<!-- Recommend export first -->
			<div class="mb-5 rounded-xl border border-white/[0.07] bg-white/[0.03] px-4 py-3 flex items-center justify-between gap-4">
				<p class="text-xs text-white/40">We recommend downloading your data first.</p>
				<button
					type="button"
					onclick={handleExport}
					disabled={exporting}
					class="shrink-0 rounded-lg border border-white/10 bg-[#1a1a1a] px-4 py-1.5 text-xs font-medium text-white hover:bg-white/10 disabled:opacity-40 transition-colors"
				>{exporting ? 'Preparing…' : 'Download ZIP'}</button>
			</div>

			<label class="mb-1.5 block text-xs font-medium uppercase tracking-wider text-white/40">
				Type <span class="font-mono text-red-400">DELETE</span> to confirm
			</label>
			<input
				type="text"
				bind:value={deleteConfirmText}
				placeholder="DELETE"
				class="mb-4 w-full rounded-xl border border-white/10 bg-[#1a1a1a] px-4 py-3 text-sm text-white placeholder-white/20 focus:border-red-500/50 focus:outline-none focus:ring-1 focus:ring-red-500/50 transition font-mono"
			/>

			{#if deleteError}
				<div class="mb-4 rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3">
					<p class="text-sm text-red-400">{deleteError}</p>
				</div>
			{/if}

			<div class="flex justify-end gap-3">
				<button
					type="button"
					onclick={() => { showDeleteModal = false; }}
					disabled={deleting}
					class="rounded-xl border border-white/10 px-5 py-2.5 text-sm font-medium text-white/60 hover:text-white hover:border-white/20 transition-colors"
				>Cancel</button>
				<button
					type="button"
					onclick={handleDeleteAccount}
					disabled={deleteConfirmText !== 'DELETE' || deleting}
					class="rounded-xl bg-red-600 px-6 py-2.5 text-sm font-semibold text-white hover:bg-red-500 disabled:opacity-40 transition-colors"
				>{deleting ? 'Deleting…' : 'Delete everything'}</button>
			</div>
		</div>
	</div>
{/if}
