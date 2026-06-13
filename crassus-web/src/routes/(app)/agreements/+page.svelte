<script lang="ts">
	import { browser } from '$app/environment';
	import { api } from '$lib/api/client';

	type Property = { id: number; name: string; };
	type Unit = { id: number; property_id: number; unit_number: string; };
	type Lessee = { id: number; lessee_uuid: string; first_name: string | null; last_name: string | null; company_legal_name: string | null; email: string; };
	type Agreement = {
		id: number; agreement_uuid: string; property_id: number; unit_id: number | null; lessee_uuid: string;
		base_rent_amount: string; vat_rate_applied: string; service_charges: string;
		payment_interval: string; deposit_amount: string;
		valid_time_start: string; valid_time_end: string;
		indexation_date: string | null;
	};

	let properties: Property[] = $state([]);
	let allUnits: Unit[] = $state([]);
	let lessees: Lessee[] = $state([]);
	let agreements: Agreement[] = $state([]);
	let view: 'list' | 'form' = $state('list');
	let editing: Agreement | null = $state(null);
	let saving = $state(false);
	let error = $state('');

	let selected_property_id = $state(0);
	let unit_id = $state(0);
	let lessee_uuid = $state('');
	let base_rent_amount = $state('');
	let vat_rate_applied = $state('0.00');
	let service_charges = $state('0.00');
	let payment_interval: 'monthly' | 'quarterly' | 'annually' = $state('monthly');
	let deposit_amount = $state('0.00');
	let valid_time_start = $state('');
	let valid_time_end = $state('');
	let indexation_date = $state('');

	let filteredUnits = $derived(allUnits.filter((u) => u.property_id === selected_property_id));

	function lesseeLabel(uuid: string) {
		const l = lessees.find((x) => x.lessee_uuid === uuid);
		if (!l) return uuid;
		if (l.company_legal_name) return l.company_legal_name;
		return [l.first_name, l.last_name].filter(Boolean).join(' ') || l.email;
	}
	function agreementLabel(a: Agreement) {
		const prop = properties.find((x) => x.id === a.property_id);
		if (!a.unit_id) return prop?.name ?? '—';
		const u = allUnits.find((x) => x.id === a.unit_id);
		return u ? `${prop?.name ?? ''} — ${u.unit_number}` : (prop?.name ?? '—');
	}

	function load() {
		api.get<Property[]>('/properties').then((p) => {
			properties = p;
			if (p.length > 0 && selected_property_id === 0) { selected_property_id = p[0].id; unit_id = 0; }
		});
		api.get<Unit[]>('/units').then((u) => { allUnits = u; });
		api.get<Lessee[]>('/lessees').then((l) => { lessees = l; if (l.length > 0 && !lessee_uuid) lessee_uuid = l[0].lessee_uuid; });
		api.get<Agreement[]>('/rental-agreements').then((a) => { agreements = a; });
	}
	if (browser) load();

	function openNew() {
		editing = null;
		selected_property_id = properties[0]?.id ?? 0;
		unit_id = 0; lessee_uuid = lessees[0]?.lessee_uuid ?? '';
		base_rent_amount = ''; vat_rate_applied = '0.00'; service_charges = '0.00';
		payment_interval = 'monthly'; deposit_amount = '0.00';
		valid_time_start = ''; valid_time_end = ''; indexation_date = '';
		error = ''; view = 'form';
	}

	function openEdit(a: Agreement) {
		editing = a;
		selected_property_id = a.property_id ?? allUnits.find((x) => x.id === a.unit_id)?.property_id ?? properties[0]?.id ?? 0;
		unit_id = a.unit_id ?? 0; lessee_uuid = a.lessee_uuid;
		base_rent_amount = a.base_rent_amount; vat_rate_applied = a.vat_rate_applied;
		service_charges = a.service_charges; payment_interval = a.payment_interval as 'monthly' | 'quarterly' | 'annually';
		deposit_amount = a.deposit_amount;
		valid_time_start = a.valid_time_start.slice(0, 10);
		valid_time_end = a.valid_time_end.slice(0, 10);
		indexation_date = a.indexation_date ?? '';
		error = ''; view = 'form';
	}

	async function handleSubmit(e: SubmitEvent) {
		e.preventDefault(); saving = true; error = '';
		const payload = {
			property_id: selected_property_id,
			unit_id: unit_id || null,
			lessee_uuid, base_rent_amount, vat_rate_applied,
			service_charges, payment_interval, deposit_amount,
			valid_time_start: valid_time_start + 'T00:00:00',
			valid_time_end: valid_time_end + 'T00:00:00',
			indexation_date: indexation_date || null,
		};
		try {
			editing ? await api.patch(`/rental-agreements/${editing.id}`, payload) : await api.post('/rental-agreements', payload);
			load(); view = 'list';
		} catch (err: unknown) {
			error = err instanceof Error ? err.message : 'Failed to save.';
		} finally { saving = false; }
	}

	async function handleDelete(a: Agreement) {
		if (!confirm('Delete this rental agreement?')) return;
		try { await api.delete(`/rental-agreements/${a.id}`); load(); }
		catch (err: unknown) { alert(err instanceof Error ? err.message : 'Failed to delete.'); }
	}

	const inputClass = 'w-full rounded-xl border border-white/10 bg-[#1a1a1a] px-4 py-3 text-sm text-white placeholder-white/20 focus:border-indigo-500/50 focus:outline-none focus:ring-1 focus:ring-indigo-500/50 transition';
</script>

{#if view === 'list'}
<div class="mb-8 flex items-center justify-between">
	<div>
		<h2 class="text-2xl font-semibold text-white">Agreements</h2>
		<p class="mt-1 text-sm text-white/40">Rental contracts between units and lessees</p>
	</div>
	<button onclick={openNew} class="rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-500 transition-colors">+ New Agreement</button>
</div>

{#if agreements.length === 0}
	<div class="rounded-2xl border border-white/[0.07] bg-[#111111] p-12 text-center">
		<p class="text-sm text-white/30">No agreements yet. Add your first one.</p>
	</div>
{:else}
	<div class="overflow-hidden rounded-2xl border border-white/[0.07] bg-[#111111]">
		<table class="w-full text-sm">
			<thead><tr class="border-b border-white/[0.07]">
				<th class="px-5 py-3.5 text-left text-xs font-medium uppercase tracking-wider text-white/30">Unit</th>
				<th class="px-5 py-3.5 text-left text-xs font-medium uppercase tracking-wider text-white/30">Lessee</th>
				<th class="px-5 py-3.5 text-left text-xs font-medium uppercase tracking-wider text-white/30">Rent</th>
				<th class="px-5 py-3.5 text-left text-xs font-medium uppercase tracking-wider text-white/30">Interval</th>
				<th class="px-5 py-3.5 text-left text-xs font-medium uppercase tracking-wider text-white/30">Period</th>
				<th class="px-5 py-3.5"></th>
			</tr></thead>
			<tbody>
				{#each agreements as a}
				<tr class="border-b border-white/[0.04] hover:bg-white/[0.02] transition-colors">
					<td class="px-5 py-4 font-medium text-white">{agreementLabel(a)}</td>
					<td class="px-5 py-4 text-white/60">{lesseeLabel(a.lessee_uuid)}</td>
					<td class="px-5 py-4 text-white/60">€ {Number(a.base_rent_amount).toLocaleString()}</td>
					<td class="px-5 py-4"><span class="rounded-md bg-white/5 px-2 py-1 text-xs capitalize text-white/60">{a.payment_interval}</span></td>
					<td class="px-5 py-4 text-xs text-white/40">{a.valid_time_start.slice(0,10)} → {a.valid_time_end.slice(0,10)}</td>
					<td class="px-5 py-4 text-right">
						<button onclick={() => openEdit(a)} class="mr-4 text-xs text-indigo-400 hover:text-indigo-300 transition-colors">Edit</button>
						<button onclick={() => handleDelete(a)} class="text-xs text-red-400/60 hover:text-red-400 transition-colors">Delete</button>
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
	<h2 class="text-2xl font-semibold text-white">{editing ? 'Edit Agreement' : 'New Agreement'}</h2>
</div>

<form onsubmit={handleSubmit} class="max-w-2xl space-y-6">

	<!-- Property → Unit cascade (unit optional) -->
	<div class="space-y-4 rounded-2xl border border-white/[0.07] bg-[#111111] p-6">
		<h3 class="text-xs font-semibold uppercase tracking-wider text-white/30">Property & Unit</h3>
		<div>
			<label class="mb-1.5 block text-xs font-medium uppercase tracking-wider text-white/40" for="a_property">Property *</label>
			<select id="a_property" bind:value={selected_property_id} onchange={() => (unit_id = 0)} class={inputClass}>
				{#each properties as p}<option value={p.id}>{p.name}</option>{/each}
			</select>
		</div>
		<div>
			<label class="mb-1.5 block text-xs font-medium uppercase tracking-wider text-white/40" for="a_unit">
				Unit <span class="normal-case font-normal text-white/25">(optional — leave blank for whole-property leases)</span>
			</label>
			<select id="a_unit" bind:value={unit_id} class={inputClass}>
				<option value={0}>Whole property (no specific unit)</option>
				{#each filteredUnits as u}<option value={u.id}>{u.unit_number}</option>{/each}
			</select>
		</div>
	</div>

	<!-- Lessee -->
	<div class="space-y-4 rounded-2xl border border-white/[0.07] bg-[#111111] p-6">
		<h3 class="text-xs font-semibold uppercase tracking-wider text-white/30">Lessee</h3>
		<div>
			<label class="mb-1.5 block text-xs font-medium uppercase tracking-wider text-white/40" for="a_lessee">Lessee</label>
			<select id="a_lessee" bind:value={lessee_uuid} required class={inputClass}>
				<option value="" disabled>Select a lessee…</option>
				{#each lessees as l}
					<option value={l.lessee_uuid}>{lesseeLabel(l.lessee_uuid)}</option>
				{/each}
			</select>
		</div>
	</div>

	<!-- Financial terms -->
	<div class="space-y-4 rounded-2xl border border-white/[0.07] bg-[#111111] p-6">
		<h3 class="text-xs font-semibold uppercase tracking-wider text-white/30">Financial Terms</h3>
		<div class="grid grid-cols-2 gap-4">
			<div>
				<label class="mb-1.5 block text-xs font-medium uppercase tracking-wider text-white/40" for="a_rent">Base Rent *</label>
				<input id="a_rent" type="number" step="0.01" min="0" bind:value={base_rent_amount} required placeholder="0.00" class={inputClass} />
			</div>
			<div>
				<label class="mb-1.5 block text-xs font-medium uppercase tracking-wider text-white/40" for="a_vat">VAT Rate (%)</label>
				<input id="a_vat" type="number" step="0.01" min="0" max="100" bind:value={vat_rate_applied} class={inputClass} />
			</div>
			<div>
				<label class="mb-1.5 block text-xs font-medium uppercase tracking-wider text-white/40" for="a_charges">Service Charges</label>
				<input id="a_charges" type="number" step="0.01" min="0" bind:value={service_charges} class={inputClass} />
			</div>
			<div>
				<label class="mb-1.5 block text-xs font-medium uppercase tracking-wider text-white/40" for="a_deposit">Deposit</label>
				<input id="a_deposit" type="number" step="0.01" min="0" bind:value={deposit_amount} class={inputClass} />
			</div>
		</div>

		<div>
			<label class="mb-3 block text-xs font-medium uppercase tracking-wider text-white/40">Payment Interval</label>
			<div class="flex gap-3">
				{#each ([{ value: 'monthly', label: 'Monthly' }, { value: 'quarterly', label: 'Quarterly' }, { value: 'annually', label: 'Annually' }]) as opt}
					<button type="button" onclick={() => (payment_interval = opt.value as 'monthly' | 'quarterly' | 'annually')}
						class="flex-1 rounded-xl border py-2.5 text-sm font-medium transition
							{payment_interval === opt.value ? 'border-indigo-500/50 bg-indigo-500/10 text-indigo-400' : 'border-white/10 bg-[#1a1a1a] text-white/40 hover:text-white/70'}">
						{opt.label}
					</button>
				{/each}
			</div>
		</div>
	</div>

	<!-- Validity period + indexation -->
	<div class="space-y-4 rounded-2xl border border-white/[0.07] bg-[#111111] p-6">
		<h3 class="text-xs font-semibold uppercase tracking-wider text-white/30">Lease Period</h3>
		<div class="grid grid-cols-2 gap-4">
			<div>
				<label class="mb-1.5 block text-xs font-medium uppercase tracking-wider text-white/40" for="a_start">Start Date *</label>
				<input id="a_start" type="date" bind:value={valid_time_start}
					onchange={() => { if (valid_time_start && !indexation_date) indexation_date = valid_time_start; }}
					required class={inputClass} />
			</div>
			<div>
				<label class="mb-1.5 block text-xs font-medium uppercase tracking-wider text-white/40" for="a_end">End Date *</label>
				<input id="a_end" type="date" bind:value={valid_time_end} required class={inputClass} />
			</div>
		</div>
		<div>
			<label class="mb-1.5 block text-xs font-medium uppercase tracking-wider text-white/40" for="a_idx">
				Annual Indexation Date <span class="normal-case font-normal text-white/25">(optional — day & month on which rent is indexed each year)</span>
			</label>
			<input id="a_idx" type="date" bind:value={indexation_date} class={inputClass} />
			{#if indexation_date}
				<p class="mt-1.5 text-xs text-white/30">
					Rent indexed every year on <strong class="text-white/50">{new Date(indexation_date + 'T00:00:00').toLocaleDateString('en-GB', { day: 'numeric', month: 'long' })}</strong> — the year is ignored.
				</p>
			{/if}
		</div>
	</div>

	{#if error}<div class="rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3"><p class="text-sm text-red-400">{error}</p></div>{/if}

	<div class="flex justify-end gap-3">
		<button type="button" onclick={() => (view = 'list')} class="rounded-xl border border-white/10 px-5 py-2.5 text-sm text-white/50 hover:text-white transition-colors">Cancel</button>
		<button type="submit" disabled={saving} class="rounded-xl bg-indigo-600 px-6 py-2.5 text-sm font-semibold text-white hover:bg-indigo-500 disabled:opacity-40 transition-colors">
			{saving ? 'Saving…' : editing ? 'Save Changes' : 'Create Agreement'}
		</button>
	</div>
</form>
{/if}
