<script lang="ts">
	import { browser } from '$app/environment';
	import { onMount } from 'svelte';
	import { getMe, type User } from '$lib/auth';
	import { getToken } from '$lib/api/client';
	import { page } from '$app/stores';
	import UserMenu from '$lib/components/UserMenu.svelte';

	const { children } = $props();

	let user: User | null = $state(null);

	const navSections = [
		{
			group: null,
			items: [
				{ href: '/dashboard', label: 'Dashboard' },
			],
		},
		{
			group: 'Administration',
			items: [
				{ href: '/properties', label: 'Properties' },
				{ href: '/units',      label: 'Units' },
				{ href: '/lessees',    label: 'Lessees' },
				{ href: '/agreements', label: 'Agreements' },
			],
		},
		{
			group: 'Operations',
			items: [
				{ href: '/invoices',  label: 'Invoices' },
				{ href: '/expenses',  label: 'Expenses' },
				{ href: '/vat',       label: 'VAT Report' },
			],
		},
		{
			group: null,
			items: [
				{ href: '/documents', label: 'Documents' },
			],
		},
	];

	if (browser) {
		if (!getToken()) {
			window.location.replace('/login');
		} else {
			getMe()
				.then((u) => { user = u; })
				.catch(() => { window.location.replace('/login'); });
		}
	}

	function isActive(href: string): boolean {
		return $page.url.pathname === href || (href !== '/dashboard' && $page.url.pathname.startsWith(href));
	}
</script>

<div class="flex h-screen bg-[#0a0a0a]">
	<aside class="flex w-52 flex-shrink-0 flex-col border-r border-white/[0.07] bg-[#0a0a0a]">
		<div class="px-5 pb-2 pt-4">
			<span class="text-[10px] font-semibold uppercase tracking-widest text-white/20 select-none">Menu</span>
		</div>

		<nav class="flex-1 overflow-y-auto px-2 pb-4">
			{#each navSections as section, si}
				<!-- section gap / divider between groups -->
				{#if si > 0}
					<div class="mx-1 my-3 border-t border-white/[0.06]"></div>
				{/if}

				{#if section.group}
					<p class="mb-1 px-3 pt-0.5 text-[10px] font-semibold uppercase tracking-widest text-white/20 select-none">
						{section.group}
					</p>
				{/if}

				<div class="space-y-0.5">
					{#each section.items as item}
						<a
							href={item.href}
							class="flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm transition-all duration-100
								{isActive(item.href)
								? 'bg-white/10 text-white font-medium'
								: 'text-white/40 hover:bg-white/5 hover:text-white/80'}"
						>
							{#if isActive(item.href)}
								<span class="h-1.5 w-1.5 flex-shrink-0 rounded-full bg-indigo-400"></span>
							{:else}
								<span class="h-1.5 w-1.5 flex-shrink-0 rounded-full bg-transparent"></span>
							{/if}
							{item.label}
						</a>
					{/each}
				</div>
			{/each}
		</nav>

		<div class="border-t border-white/[0.07] px-3 py-3">
			{#if user}
				<div class="px-2 py-2">
					<p class="truncate text-xs font-medium text-white/60">{user.org_name}</p>
					<p class="truncate text-xs text-white/30">{user.email}</p>
				</div>
			{/if}
		</div>
	</aside>

	<div class="flex min-w-0 flex-1 flex-col">
		<header class="flex h-12 flex-shrink-0 items-center justify-between border-b border-white/[0.07] bg-[#0a0a0a] px-5">
			<span class="text-sm font-semibold tracking-tight text-white/70">Crassus Property Management</span>
			{#if user}
				<UserMenu {user} />
			{/if}
		</header>

		<main class="flex-1 overflow-y-auto bg-[#0a0a0a]">
			<div class="mx-auto max-w-5xl px-8 py-8">
				{@render children()}
			</div>
		</main>
	</div>
</div>
