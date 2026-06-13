<script lang="ts">
	import { browser } from '$app/environment';
	import { api } from '$lib/api/client';

	type Property = {
		id: number; name: string; property_reference: string | null; address: string;
		property_type: 'residential' | 'commercial' | 'industrial';
		is_vat_exempt: boolean; insurance_policy_number: string | null;
		insurance_provider: string | null; insurance_renewal_date: string | null;
		insurance_annual_premium: string | null; asset_value: string | null;
		maintenance_annual_budget: string;
	};

	let properties: Property[] = $state([]);
	let view: 'list' | 'form' = $state('list');
	let editing: Property | null = $state(null);
	let saving = $state(false);
	let error = $state('');

	let name = $state('');
	let property_reference = $state('');
	let address = $state('');
	let property_type: 'residential' | 'commercial' | 'industrial' = $state('residential');
	let is_vat_exempt = $state(false);
	let insurance_policy_number = $state('');
	let insurance_provider = $state('');
	let insurance_renewal_date = $state('');
	let insurance_annual_premium = $state('');
	let asset_value = $state('');
	let maintenance_annual_budget = $state('0.00');

	function load() {
		api.get<Property[]>('/properties').then((p) => { properties = p; });
	}
	if (browser) load();

	function openNew() {
		editing = null;
		name = ''; property_reference = ''; address = ''; property_type = 'residential'; is_vat_exempt = false;
		insurance_policy_number = ''; insurance_provider = ''; insurance_renewal_date = '';
		insurance_annual_premium = ''; asset_value = ''; maintenance_annual_budget = '0.00';
		error = ''; view = 'form';
	}

	function openEdit(p: Property) {
		editing = p;
		name = p.name; property_reference = p.property_reference ?? ''; address = p.address; property_type = p.property_type;
		is_vat_exempt = p.is_vat_exempt;
		insurance_policy_number = p.insurance_policy_number ?? '';
		insurance_provider = p.insurance_provider ?? '';
		insurance_renewal_date = p.insurance_renewal_date ?? '';
		insurance_annual_premium = p.insurance_annual_premium ?? '';
		asset_value = p.asset_value ?? '';
		maintenance_annual_budget = p.maintenance_annual_budget ?? '0.00';
		error = ''; view = 'form';
	}

	async function handleSubmit(e: SubmitEvent) {
		e.preventDefault(); saving = true; error = '';
		const payload = {
			name, property_reference: property_reference || null, address, property_type, is_vat_exempt,
			insurance_policy_number: insurance_policy_number || null,
			insurance_provider: insurance_provider || null,
			insurance_renewal_date: insurance_renewal_date || null,
			insurance_annual_premium: insurance_annual_premium || null,
			asset_value: asset_value || null,
			maintenance_annual_budget
		};
		try {
			editing ? await api.patch(`/properties/${editing.id}`, payload) : await api.post('/properties', payload);
			load(); view = 'list';
		} catch (err: unknown) {
			error = err instanceof Error ? err.message : 'Failed to save.';
		} finally { saving = false; }
	}

	async function handleDelete(p: Property) {
		if (!confirm(`Delete "${p.name}"? This cannot be undone.`)) return;
		try { await api.delete(`/properties/${p.id}`); load(); }
		catch (err: unknown) { alert(err instanceof Error ? err.message : 'Failed to delete.'); }
	}
</script>

{#if view === 'list'}
<div class="mb-8 flex items-center justify-between">
	<div>
		<h2 class="text-2xl font-semibold text-white">Properties</h2>
		<p class="mt-1 text-sm text-white/40">Manage your real estate portfolio</p>
	</div>
	<button onclick={openNew} class="rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-500 transition-colors">+ New Property</button>
</div>

{#if properties.length === 0}
	<div class="rounded-2xl border border-white/[0.07] bg-[#111111] p-12 text-center">
		<p class="text-sm text-white/30">No properties yet. Add your first one.</p>
	</div>
{:else}
	<div class="overflow-hidden rounded-2xl border border-white/[0.07] bg-[#111111]">
		<table class="w-full text-sm">
			<thead><tr class="border-b border-white/[0.07]">
				<th class="px-5 py-3.5 text-left text-xs font-medium uppercase tracking-wider text-white/30">Name</th>
				<th class="px-5 py-3.5 text-left text-xs font-medium uppercase tracking-wider text-white/30">Type</th>
				<th class="px-5 py-3.5 text-left text-xs font-medium uppercase tracking-wider text-white/30">VAT Exempt</th>
				<th class="px-5 py-3.5 text-left text-xs font-medium uppercase tracking-wider text-white/30">Maint. Budget</th>
				<th class="px-5 py-3.5"></th>
			</tr></thead>
			<tbody>
				{#each properties as p}
				<tr class="border-b border-white/[0.04] hover:bg-white/[0.02] transition-colors">
					<td class="px-5 py-4">
						<p class="font-medium text-white">{p.name}</p>
						<p class="mt-0.5 text-xs text-white/40">{p.address}</p>
					</td>
					<td class="px-5 py-4"><span class="rounded-md bg-white/5 px-2 py-1 text-xs capitalize text-white/60">{p.property_type}</span></td>
					<td class="px-5 py-4">
						{#if p.is_vat_exempt}
							<span class="rounded-md bg-amber-500/10 px-2 py-1 text-xs text-amber-400">Exempt</span>
						{:else}
							<span class="rounded-md bg-white/5 px-2 py-1 text-xs text-white/40">No</span>
						{/if}
					</td>
					<td class="px-5 py-4 text-white/60">€ {Number(p.maintenance_annual_budget).toLocaleString()}</td>
					<td class="px-5 py-4 text-right">
						<button onclick={() => openEdit(p)} class="mr-4 text-xs text-indigo-400 hover:text-indigo-300 transition-colors">Edit</button>
						<button onclick={() => handleDelete(p)} class="text-xs text-red-400/60 hover:text-red-400 transition-colors">Delete</button>
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
	<h2 class="text-2xl font-semibold text-white">{editing ? 'Edit Property' : 'New Property'}</h2>
</div>

<form onsubmit={handleSubmit} class="max-w-2xl space-y-6">
	<div class="space-y-4 rounded-2xl border border-white/[0.07] bg-[#111111] p-6">
		<h3 class="text-xs font-semibold uppercase tracking-wider text-white/30">Details</h3>
		<div class="grid grid-cols-3 gap-4">
			<div class="col-span-2">
				<label class="mb-1.5 block text-xs font-medium uppercase tracking-wider text-white/40" for="p_name">Property Name</label>
				<input id="p_name" type="text" bind:value={name} required placeholder="e.g. Markt 2"
					class="w-full rounded-xl border border-white/10 bg-[#1a1a1a] px-4 py-3 text-sm text-white placeholder-white/20 focus:border-indigo-500/50 focus:outline-none focus:ring-1 focus:ring-indigo-500/50 transition" />
			</div>
			<div>
				<label class="mb-1.5 block text-xs font-medium uppercase tracking-wider text-white/40" for="p_ref">
					Reference <span class="normal-case font-normal text-white/20">(optional)</span>
				</label>
				<input id="p_ref" type="text" bind:value={property_reference} placeholder="e.g. M2" maxlength="10"
					class="w-full rounded-xl border border-white/10 bg-[#1a1a1a] px-4 py-3 text-sm text-white placeholder-white/20 focus:border-indigo-500/50 focus:outline-none focus:ring-1 focus:ring-indigo-500/50 transition" />
				<p class="mt-1 text-xs text-white/25">Used in invoice numbers</p>
			</div>
		</div>
		<div>
			<label class="mb-1.5 block text-xs font-medium uppercase tracking-wider text-white/40" for="p_address">Address</label>
			<textarea id="p_address" bind:value={address} required rows={2}
				class="w-full resize-none rounded-xl border border-white/10 bg-[#1a1a1a] px-4 py-3 text-sm text-white placeholder-white/20 focus:border-indigo-500/50 focus:outline-none focus:ring-1 focus:ring-indigo-500/50 transition"></textarea>
		</div>
		<div class="grid grid-cols-2 gap-4">
			<div>
				<label class="mb-1.5 block text-xs font-medium uppercase tracking-wider text-white/40" for="p_type">Type</label>
				<select id="p_type" bind:value={property_type}
					class="w-full rounded-xl border border-white/10 bg-[#1a1a1a] px-4 py-3 text-sm text-white focus:border-indigo-500/50 focus:outline-none focus:ring-1 focus:ring-indigo-500/50 transition">
					<option value="residential">Residential</option>
					<option value="commercial">Commercial</option>
					<option value="industrial">Industrial</option>
				</select>
			</div>
			<div>
				<label class="mb-1.5 block text-xs font-medium uppercase tracking-wider text-white/40" for="p_budget">Annual Maintenance Budget</label>
				<input id="p_budget" type="number" step="0.01" min="0" bind:value={maintenance_annual_budget}
					class="w-full rounded-xl border border-white/10 bg-[#1a1a1a] px-4 py-3 text-sm text-white focus:border-indigo-500/50 focus:outline-none focus:ring-1 focus:ring-indigo-500/50 transition" />
			</div>
			<div>
				<label class="mb-1.5 block text-xs font-medium uppercase tracking-wider text-white/40" for="p_asset">Asset Value <span class="normal-case font-normal text-white/20">(optional)</span></label>
				<input id="p_asset" type="number" step="0.01" min="0" bind:value={asset_value} placeholder="0.00"
					class="w-full rounded-xl border border-white/10 bg-[#1a1a1a] px-4 py-3 text-sm text-white placeholder-white/20 focus:border-indigo-500/50 focus:outline-none focus:ring-1 focus:ring-indigo-500/50 transition" />
			</div>
			<div class="flex items-end pb-1">
				<label class="flex cursor-pointer items-center gap-3">
					<div class="relative">
						<input type="checkbox" bind:checked={is_vat_exempt} class="sr-only peer" />
						<div class="h-5 w-9 rounded-full bg-white/10 transition-colors peer-checked:bg-indigo-600"></div>
						<div class="absolute left-0.5 top-0.5 h-4 w-4 rounded-full bg-white transition-transform peer-checked:translate-x-4"></div>
					</div>
					<span class="text-sm text-white/60">VAT Exempt</span>
				</label>
			</div>
		</div>
	</div>

	<div class="space-y-4 rounded-2xl border border-white/[0.07] bg-[#111111] p-6">
		<h3 class="text-xs font-semibold uppercase tracking-wider text-white/30">Insurance <span class="normal-case font-normal text-white/20">(optional)</span></h3>
		<div class="grid grid-cols-2 gap-4">
			<div>
				<label class="mb-1.5 block text-xs font-medium uppercase tracking-wider text-white/40" for="p_ins_provider">Provider</label>
				<input id="p_ins_provider" type="text" bind:value={insurance_provider} placeholder="e.g. AXA"
					class="w-full rounded-xl border border-white/10 bg-[#1a1a1a] px-4 py-3 text-sm text-white placeholder-white/20 focus:border-indigo-500/50 focus:outline-none focus:ring-1 focus:ring-indigo-500/50 transition" />
			</div>
			<div>
				<label class="mb-1.5 block text-xs font-medium uppercase tracking-wider text-white/40" for="p_ins_policy">Policy Number</label>
				<input id="p_ins_policy" type="text" bind:value={insurance_policy_number}
					class="w-full rounded-xl border border-white/10 bg-[#1a1a1a] px-4 py-3 text-sm text-white focus:border-indigo-500/50 focus:outline-none focus:ring-1 focus:ring-indigo-500/50 transition" />
			</div>
			<div>
				<label class="mb-1.5 block text-xs font-medium uppercase tracking-wider text-white/40" for="p_ins_date">Renewal Date</label>
				<input id="p_ins_date" type="date" bind:value={insurance_renewal_date}
					class="w-full rounded-xl border border-white/10 bg-[#1a1a1a] px-4 py-3 text-sm text-white focus:border-indigo-500/50 focus:outline-none focus:ring-1 focus:ring-indigo-500/50 transition" />
			</div>
			<div>
				<label class="mb-1.5 block text-xs font-medium uppercase tracking-wider text-white/40" for="p_ins_premium">Annual Premium</label>
				<input id="p_ins_premium" type="number" step="0.01" min="0" bind:value={insurance_annual_premium} placeholder="0.00"
					class="w-full rounded-xl border border-white/10 bg-[#1a1a1a] px-4 py-3 text-sm text-white placeholder-white/20 focus:border-indigo-500/50 focus:outline-none focus:ring-1 focus:ring-indigo-500/50 transition" />
			</div>
		</div>
	</div>

	{#if error}<div class="rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3"><p class="text-sm text-red-400">{error}</p></div>{/if}

	<div class="flex justify-end gap-3">
		<button type="button" onclick={() => (view = 'list')} class="rounded-xl border border-white/10 px-5 py-2.5 text-sm text-white/50 hover:text-white transition-colors">Cancel</button>
		<button type="submit" disabled={saving} class="rounded-xl bg-indigo-600 px-6 py-2.5 text-sm font-semibold text-white hover:bg-indigo-500 disabled:opacity-40 transition-colors">
			{saving ? 'Saving…' : editing ? 'Save Changes' : 'Create Property'}
		</button>
	</div>
</form>
{/if}
