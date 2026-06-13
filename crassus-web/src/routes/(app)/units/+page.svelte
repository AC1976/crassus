<script lang="ts">
	import { browser } from '$app/environment';
	import { api } from '$lib/api/client';

	type Property = { id: number; name: string; };
	type Unit = { id: number; property_id: number; unit_number: string; floor_level: number | null; square_meters: string | null; };

	let properties: Property[] = $state([]);
	let units: Unit[] = $state([]);
	let view: 'list' | 'form' = $state('list');
	let editing: Unit | null = $state(null);
	let saving = $state(false);
	let error = $state('');

	let property_id = $state(0);
	let unit_number = $state('');
	let floor_level = $state('');
	let square_meters = $state('');

	function load() {
		api.get<Property[]>('/properties').then((p) => {
			properties = p;
			if (p.length > 0 && property_id === 0) property_id = p[0].id;
		});
		api.get<Unit[]>('/units').then((u) => { units = u; });
	}
	if (browser) load();

	function propertyName(id: number) {
		return properties.find((p) => p.id === id)?.name ?? '—';
	}

	function openNew() {
		editing = null;
		property_id = properties[0]?.id ?? 0;
		unit_number = ''; floor_level = ''; square_meters = '';
		error = ''; view = 'form';
	}

	function openEdit(u: Unit) {
		editing = u;
		property_id = u.property_id;
		unit_number = u.unit_number;
		floor_level = u.floor_level != null ? String(u.floor_level) : '';
		square_meters = u.square_meters ?? '';
		error = ''; view = 'form';
	}

	async function handleSubmit(e: SubmitEvent) {
		e.preventDefault(); saving = true; error = '';
		const payload = {
			property_id,
			unit_number,
			floor_level: floor_level !== '' ? Number(floor_level) : null,
			square_meters: square_meters || null
		};
		try {
			editing ? await api.patch(`/units/${editing.id}`, payload) : await api.post('/units', payload);
			load(); view = 'list';
		} catch (err: unknown) {
			error = err instanceof Error ? err.message : 'Failed to save.';
		} finally { saving = false; }
	}

	async function handleDelete(u: Unit) {
		if (!confirm(`Delete unit "${u.unit_number}"?`)) return;
		try { await api.delete(`/units/${u.id}`); load(); }
		catch (err: unknown) { alert(err instanceof Error ? err.message : 'Failed to delete.'); }
	}
</script>

{#if view === 'list'}
<div class="mb-8 flex items-center justify-between">
	<div>
		<h2 class="text-2xl font-semibold text-white">Units</h2>
		<p class="mt-1 text-sm text-white/40">Rentable partitions within your properties</p>
	</div>
	<button onclick={openNew} class="rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-500 transition-colors">+ New Unit</button>
</div>

{#if units.length === 0}
	<div class="rounded-2xl border border-white/[0.07] bg-[#111111] p-12 text-center">
		<p class="text-sm text-white/30">No units yet. Add your first one.</p>
	</div>
{:else}
	<div class="overflow-hidden rounded-2xl border border-white/[0.07] bg-[#111111]">
		<table class="w-full text-sm">
			<thead><tr class="border-b border-white/[0.07]">
				<th class="px-5 py-3.5 text-left text-xs font-medium uppercase tracking-wider text-white/30">Unit</th>
				<th class="px-5 py-3.5 text-left text-xs font-medium uppercase tracking-wider text-white/30">Property</th>
				<th class="px-5 py-3.5 text-left text-xs font-medium uppercase tracking-wider text-white/30">Floor</th>
				<th class="px-5 py-3.5 text-left text-xs font-medium uppercase tracking-wider text-white/30">Size (m²)</th>
				<th class="px-5 py-3.5"></th>
			</tr></thead>
			<tbody>
				{#each units as u}
				<tr class="border-b border-white/[0.04] hover:bg-white/[0.02] transition-colors">
					<td class="px-5 py-4 font-medium text-white">{u.unit_number}</td>
					<td class="px-5 py-4 text-white/60">{propertyName(u.property_id)}</td>
					<td class="px-5 py-4 text-white/60">{u.floor_level ?? '—'}</td>
					<td class="px-5 py-4 text-white/60">{u.square_meters ?? '—'}</td>
					<td class="px-5 py-4 text-right">
						<button onclick={() => openEdit(u)} class="mr-4 text-xs text-indigo-400 hover:text-indigo-300 transition-colors">Edit</button>
						<button onclick={() => handleDelete(u)} class="text-xs text-red-400/60 hover:text-red-400 transition-colors">Delete</button>
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
	<h2 class="text-2xl font-semibold text-white">{editing ? 'Edit Unit' : 'New Unit'}</h2>
</div>

<form onsubmit={handleSubmit} class="max-w-2xl space-y-6">
	<div class="space-y-4 rounded-2xl border border-white/[0.07] bg-[#111111] p-6">
		<h3 class="text-xs font-semibold uppercase tracking-wider text-white/30">Unit Details</h3>

		<div>
			<label class="mb-1.5 block text-xs font-medium uppercase tracking-wider text-white/40" for="u_property">Property</label>
			<select id="u_property" bind:value={property_id}
				class="w-full rounded-xl border border-white/10 bg-[#1a1a1a] px-4 py-3 text-sm text-white focus:border-indigo-500/50 focus:outline-none focus:ring-1 focus:ring-indigo-500/50 transition">
				{#each properties as p}
					<option value={p.id}>{p.name}</option>
				{/each}
			</select>
		</div>

		<div>
			<label class="mb-1.5 block text-xs font-medium uppercase tracking-wider text-white/40" for="u_number">Unit Number / Name</label>
			<input id="u_number" type="text" bind:value={unit_number} required placeholder="e.g. Apt 1A, Suite 5"
				class="w-full rounded-xl border border-white/10 bg-[#1a1a1a] px-4 py-3 text-sm text-white placeholder-white/20 focus:border-indigo-500/50 focus:outline-none focus:ring-1 focus:ring-indigo-500/50 transition" />
		</div>

		<div class="grid grid-cols-2 gap-4">
			<div>
				<label class="mb-1.5 block text-xs font-medium uppercase tracking-wider text-white/40" for="u_floor">Floor Level <span class="normal-case font-normal text-white/20">(optional)</span></label>
				<input id="u_floor" type="number" bind:value={floor_level} placeholder="0"
					class="w-full rounded-xl border border-white/10 bg-[#1a1a1a] px-4 py-3 text-sm text-white placeholder-white/20 focus:border-indigo-500/50 focus:outline-none focus:ring-1 focus:ring-indigo-500/50 transition" />
			</div>
			<div>
				<label class="mb-1.5 block text-xs font-medium uppercase tracking-wider text-white/40" for="u_sqm">Size (m²) <span class="normal-case font-normal text-white/20">(optional)</span></label>
				<input id="u_sqm" type="number" step="0.01" min="0" bind:value={square_meters} placeholder="0.00"
					class="w-full rounded-xl border border-white/10 bg-[#1a1a1a] px-4 py-3 text-sm text-white placeholder-white/20 focus:border-indigo-500/50 focus:outline-none focus:ring-1 focus:ring-indigo-500/50 transition" />
			</div>
		</div>
	</div>

	{#if error}<div class="rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3"><p class="text-sm text-red-400">{error}</p></div>{/if}

	<div class="flex justify-end gap-3">
		<button type="button" onclick={() => (view = 'list')} class="rounded-xl border border-white/10 px-5 py-2.5 text-sm text-white/50 hover:text-white transition-colors">Cancel</button>
		<button type="submit" disabled={saving} class="rounded-xl bg-indigo-600 px-6 py-2.5 text-sm font-semibold text-white hover:bg-indigo-500 disabled:opacity-40 transition-colors">
			{saving ? 'Saving…' : editing ? 'Save Changes' : 'Create Unit'}
		</button>
	</div>
</form>
{/if}
