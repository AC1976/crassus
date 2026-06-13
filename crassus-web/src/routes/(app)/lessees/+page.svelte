<script lang="ts">
	import { browser } from '$app/environment';
	import { api } from '$lib/api/client';

	type Lessee = {
		id: number; lessee_uuid: string;
		first_name: string | null; last_name: string | null;
		company_legal_name: string | null; company_vat_id: string | null;
		email: string; phone: string | null; billing_address: string; bank_account: string | null;
	};

	let lessees: Lessee[] = $state([]);
	let view: 'list' | 'form' = $state('list');
	let editing: Lessee | null = $state(null);
	let saving = $state(false);
	let error = $state('');

	let first_name = $state('');
	let last_name = $state('');
	let company_legal_name = $state('');
	let company_vat_id = $state('');
	let email = $state('');
	let phone = $state('');
	let billing_address = $state('');
	let bank_account = $state('');

	function displayName(l: Lessee) {
		if (l.company_legal_name) return l.company_legal_name;
		return [l.first_name, l.last_name].filter(Boolean).join(' ') || l.email;
	}

	function load() {
		api.get<Lessee[]>('/lessees').then((l) => { lessees = l; });
	}
	if (browser) load();

	function openNew() {
		editing = null;
		first_name = ''; last_name = ''; company_legal_name = '';
		company_vat_id = ''; email = ''; phone = ''; billing_address = ''; bank_account = '';
		error = ''; view = 'form';
	}

	function openEdit(l: Lessee) {
		editing = l;
		first_name = l.first_name ?? ''; last_name = l.last_name ?? '';
		company_legal_name = l.company_legal_name ?? ''; company_vat_id = l.company_vat_id ?? '';
		email = l.email; phone = l.phone ?? ''; billing_address = l.billing_address; bank_account = l.bank_account ?? '';
		error = ''; view = 'form';
	}

	async function handleSubmit(e: SubmitEvent) {
		e.preventDefault(); saving = true; error = '';
		const payload = {
			first_name: first_name || null, last_name: last_name || null,
			company_legal_name: company_legal_name || null,
			company_vat_id: company_vat_id || null,
			email, phone: phone || null, billing_address, bank_account: bank_account || null
		};
		try {
			editing ? await api.patch(`/lessees/${editing.id}`, payload) : await api.post('/lessees', payload);
			load(); view = 'list';
		} catch (err: unknown) {
			error = err instanceof Error ? err.message : 'Failed to save.';
		} finally { saving = false; }
	}

	async function handleDelete(l: Lessee) {
		if (!confirm(`Delete lessee "${displayName(l)}"?`)) return;
		try { await api.delete(`/lessees/${l.id}`); load(); }
		catch (err: unknown) { alert(err instanceof Error ? err.message : 'Failed to delete.'); }
	}
</script>

{#if view === 'list'}
<div class="mb-8 flex items-center justify-between">
	<div>
		<h2 class="text-2xl font-semibold text-white">Lessees</h2>
		<p class="mt-1 text-sm text-white/40">Tenants and commercial parties</p>
	</div>
	<button onclick={openNew} class="rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-500 transition-colors">+ New Lessee</button>
</div>

{#if lessees.length === 0}
	<div class="rounded-2xl border border-white/[0.07] bg-[#111111] p-12 text-center">
		<p class="text-sm text-white/30">No lessees yet. Add your first one.</p>
	</div>
{:else}
	<div class="overflow-hidden rounded-2xl border border-white/[0.07] bg-[#111111]">
		<table class="w-full text-sm">
			<thead><tr class="border-b border-white/[0.07]">
				<th class="px-5 py-3.5 text-left text-xs font-medium uppercase tracking-wider text-white/30">Name</th>
				<th class="px-5 py-3.5 text-left text-xs font-medium uppercase tracking-wider text-white/30">Email</th>
				<th class="px-5 py-3.5 text-left text-xs font-medium uppercase tracking-wider text-white/30">Phone</th>
				<th class="px-5 py-3.5 text-left text-xs font-medium uppercase tracking-wider text-white/30">Type</th>
				<th class="px-5 py-3.5"></th>
			</tr></thead>
			<tbody>
				{#each lessees as l}
				<tr class="border-b border-white/[0.04] hover:bg-white/[0.02] transition-colors">
					<td class="px-5 py-4">
						<p class="font-medium text-white">{displayName(l)}</p>
						{#if l.company_vat_id}<p class="mt-0.5 text-xs text-white/40">{l.company_vat_id}</p>{/if}
					</td>
					<td class="px-5 py-4 text-white/60">{l.email}</td>
					<td class="px-5 py-4 text-white/60">{l.phone ?? '—'}</td>
					<td class="px-5 py-4">
						{#if l.company_legal_name}
							<span class="rounded-md bg-indigo-500/10 px-2 py-1 text-xs text-indigo-400">Corporate</span>
						{:else}
							<span class="rounded-md bg-white/5 px-2 py-1 text-xs text-white/40">Individual</span>
						{/if}
					</td>
					<td class="px-5 py-4 text-right">
						<button onclick={() => openEdit(l)} class="mr-4 text-xs text-indigo-400 hover:text-indigo-300 transition-colors">Edit</button>
						<button onclick={() => handleDelete(l)} class="text-xs text-red-400/60 hover:text-red-400 transition-colors">Delete</button>
					</td>
				</tr>
				{/each}
			</tbody>
		</table>
	</div>
{/if}

{:else}
<div class="mb-8 flex items-center gap-4">
	<button onclick={() => (view = 'list')} class="text-sm text-white/40 hover:text-white transition-colors">← Back</button>
	<h2 class="text-2xl font-semibold text-white">{editing ? 'Edit Lessee' : 'New Lessee'}</h2>
</div>

<form onsubmit={handleSubmit} class="max-w-2xl space-y-6">
	<div class="space-y-4 rounded-2xl border border-white/[0.07] bg-[#111111] p-6">
		<h3 class="text-xs font-semibold uppercase tracking-wider text-white/30">Individual <span class="normal-case font-normal text-white/20">(leave blank for corporate)</span></h3>
		<div class="grid grid-cols-2 gap-4">
			<div>
				<label class="mb-1.5 block text-xs font-medium uppercase tracking-wider text-white/40" for="l_fname">First Name</label>
				<input id="l_fname" type="text" bind:value={first_name} placeholder="Jane"
					class="w-full rounded-xl border border-white/10 bg-[#1a1a1a] px-4 py-3 text-sm text-white placeholder-white/20 focus:border-indigo-500/50 focus:outline-none focus:ring-1 focus:ring-indigo-500/50 transition" />
			</div>
			<div>
				<label class="mb-1.5 block text-xs font-medium uppercase tracking-wider text-white/40" for="l_lname">Last Name</label>
				<input id="l_lname" type="text" bind:value={last_name} placeholder="Doe"
					class="w-full rounded-xl border border-white/10 bg-[#1a1a1a] px-4 py-3 text-sm text-white placeholder-white/20 focus:border-indigo-500/50 focus:outline-none focus:ring-1 focus:ring-indigo-500/50 transition" />
			</div>
		</div>
	</div>

	<div class="space-y-4 rounded-2xl border border-white/[0.07] bg-[#111111] p-6">
		<h3 class="text-xs font-semibold uppercase tracking-wider text-white/30">Corporate <span class="normal-case font-normal text-white/20">(leave blank for individual)</span></h3>
		<div class="grid grid-cols-2 gap-4">
			<div>
				<label class="mb-1.5 block text-xs font-medium uppercase tracking-wider text-white/40" for="l_company">Legal Name</label>
				<input id="l_company" type="text" bind:value={company_legal_name} placeholder="Acme Corp SA"
					class="w-full rounded-xl border border-white/10 bg-[#1a1a1a] px-4 py-3 text-sm text-white placeholder-white/20 focus:border-indigo-500/50 focus:outline-none focus:ring-1 focus:ring-indigo-500/50 transition" />
			</div>
			<div>
				<label class="mb-1.5 block text-xs font-medium uppercase tracking-wider text-white/40" for="l_vat">VAT Number</label>
				<input id="l_vat" type="text" bind:value={company_vat_id} placeholder="BE0123456789"
					class="w-full rounded-xl border border-white/10 bg-[#1a1a1a] px-4 py-3 text-sm text-white placeholder-white/20 focus:border-indigo-500/50 focus:outline-none focus:ring-1 focus:ring-indigo-500/50 transition" />
			</div>
		</div>
	</div>

	<div class="space-y-4 rounded-2xl border border-white/[0.07] bg-[#111111] p-6">
		<h3 class="text-xs font-semibold uppercase tracking-wider text-white/30">Contact</h3>
		<div class="grid grid-cols-2 gap-4">
			<div>
				<label class="mb-1.5 block text-xs font-medium uppercase tracking-wider text-white/40" for="l_email">Email *</label>
				<input id="l_email" type="email" bind:value={email} required placeholder="jane@example.com"
					class="w-full rounded-xl border border-white/10 bg-[#1a1a1a] px-4 py-3 text-sm text-white placeholder-white/20 focus:border-indigo-500/50 focus:outline-none focus:ring-1 focus:ring-indigo-500/50 transition" />
			</div>
			<div>
				<label class="mb-1.5 block text-xs font-medium uppercase tracking-wider text-white/40" for="l_phone">Phone</label>
				<input id="l_phone" type="tel" bind:value={phone} placeholder="+32 470 00 00 00"
					class="w-full rounded-xl border border-white/10 bg-[#1a1a1a] px-4 py-3 text-sm text-white placeholder-white/20 focus:border-indigo-500/50 focus:outline-none focus:ring-1 focus:ring-indigo-500/50 transition" />
			</div>
		</div>
		<div>
			<label class="mb-1.5 block text-xs font-medium uppercase tracking-wider text-white/40" for="l_billing">Billing Address *</label>
			<textarea id="l_billing" bind:value={billing_address} required rows={3}
				class="w-full resize-none rounded-xl border border-white/10 bg-[#1a1a1a] px-4 py-3 text-sm text-white placeholder-white/20 focus:border-indigo-500/50 focus:outline-none focus:ring-1 focus:ring-indigo-500/50 transition"></textarea>
		</div>
		<div>
			<label class="mb-1.5 block text-xs font-medium uppercase tracking-wider text-white/40" for="l_bank">
				Bank Account <span class="normal-case font-normal text-white/20">(printed on credit invoices)</span>
			</label>
			<input id="l_bank" type="text" bind:value={bank_account} placeholder="NL75 RABO 0314 4351 66"
				class="w-full rounded-xl border border-white/10 bg-[#1a1a1a] px-4 py-3 text-sm text-white placeholder-white/20 focus:border-indigo-500/50 focus:outline-none focus:ring-1 focus:ring-indigo-500/50 transition" />
		</div>
	</div>

	{#if error}<div class="rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3"><p class="text-sm text-red-400">{error}</p></div>{/if}

	<div class="flex justify-end gap-3">
		<button type="button" onclick={() => (view = 'list')} class="rounded-xl border border-white/10 px-5 py-2.5 text-sm text-white/50 hover:text-white transition-colors">Cancel</button>
		<button type="submit" disabled={saving} class="rounded-xl bg-indigo-600 px-6 py-2.5 text-sm font-semibold text-white hover:bg-indigo-500 disabled:opacity-40 transition-colors">
			{saving ? 'Saving…' : editing ? 'Save Changes' : 'Create Lessee'}
		</button>
	</div>
</form>
{/if}
