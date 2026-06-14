<script lang="ts">
	import { logout, type User } from '$lib/auth';

	const { user }: { user: User } = $props();

	let open = $state(false);

	function initials(u: User): string {
		return u.email.slice(0, 2).toUpperCase();
	}

	function toggle(e: MouseEvent) {
		e.stopPropagation();
		open = !open;
	}

	function closeOnOutside() {
		if (open) open = false;
	}
</script>

<svelte:window onclick={closeOnOutside} />

<div class="relative">
	<button
		onclick={toggle}
		data-onboarding="onboarding-settings"
		class="flex items-center gap-2.5 rounded-lg px-2.5 py-1.5 transition hover:bg-white/5"
	>
		<div class="flex h-7 w-7 items-center justify-center rounded-full bg-indigo-600 text-[11px] font-bold text-white">
			{initials(user)}
		</div>
		<div class="text-left">
			<p class="text-xs font-medium text-white/90">{user.org_name}</p>
			<p class="text-[11px] text-white/40">{user.email}</p>
		</div>
		<svg
			class="h-3.5 w-3.5 text-white/30 transition-transform {open ? 'rotate-180' : ''}"
			fill="none" viewBox="0 0 24 24" stroke="currentColor"
		>
			<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
		</svg>
	</button>

	{#if open}
		<!-- svelte-ignore a11y_no_static_element_interactions -->
		<div
			onclick={(e) => e.stopPropagation()}
			onkeydown={() => {}}
			class="absolute right-0 top-full z-50 mt-2 w-60 overflow-hidden rounded-xl border border-white/10 bg-[#1a1a1a] shadow-2xl"
		>
			<!-- Header -->
			<div class="border-b border-white/[0.07] px-4 py-3">
				<p class="text-xs font-semibold text-white">{user.org_name}</p>
				<p class="mt-0.5 truncate text-xs text-white/40">{user.email}</p>
				<span class="mt-2 inline-block rounded-md bg-indigo-500/15 px-2 py-0.5 text-[11px] font-medium capitalize text-indigo-400">
					{user.role}
				</span>
			</div>

			<!-- Settings -->
			<div class="py-1">
				<a
					href="/settings"
					onclick={() => (open = false)}
					class="flex items-center gap-3 px-4 py-2.5 text-sm text-white/60 transition-colors hover:bg-white/5 hover:text-white"
				>
					<svg class="h-4 w-4 text-white/30" fill="none" viewBox="0 0 24 24" stroke="currentColor">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
					</svg>
					Settings
				</a>
			</div>

			<!-- Sign out -->
			<div class="border-t border-white/[0.07] py-1">
				<button
					onclick={logout}
					class="flex w-full items-center gap-3 px-4 py-2.5 text-sm text-red-400/80 transition-colors hover:bg-red-500/10 hover:text-red-400"
				>
					<svg class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
					</svg>
					Sign out
				</button>
			</div>
		</div>
	{/if}
</div>
