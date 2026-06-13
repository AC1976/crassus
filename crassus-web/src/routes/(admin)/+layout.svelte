<script lang="ts">
	import { browser } from '$app/environment';
	import { getToken } from '$lib/api/client';
	import { api } from '$lib/api/client';

	const { children } = $props();

	let checking = $state(true);
	let allowed = $state(false);

	if (browser) {
		if (!getToken()) {
			window.location.replace('/login');
		} else {
			api.get<{ is_admin: boolean }>('/admin/me')
				.then((r) => {
					if (!r.is_admin) {
						window.location.replace('/dashboard');
					} else {
						allowed = true;
					}
				})
				.catch(() => window.location.replace('/login'))
				.finally(() => { checking = false; });
		}
	}
</script>

{#if !browser || checking}
	<div class="flex min-h-screen items-center justify-center bg-[#0a0a0a]">
		<span class="text-sm text-white/30">Checking access…</span>
	</div>
{:else if allowed}
	<div class="min-h-screen bg-[#0a0a0a] text-white">
		<header class="border-b border-white/[0.07] bg-[#0a0a0a]">
			<div class="mx-auto flex h-12 max-w-6xl items-center justify-between px-6">
				<div class="flex items-center gap-3">
					<span class="text-sm font-semibold tracking-tight text-white">Crassus</span>
					<span class="rounded-md bg-indigo-600/20 px-2 py-0.5 text-xs font-medium text-indigo-300">Admin</span>
				</div>
				<a href="/dashboard" class="text-xs text-white/30 transition hover:text-white/60">
					← Back to app
				</a>
			</div>
		</header>

		<main class="mx-auto max-w-6xl px-6 py-8">
			{@render children()}
		</main>
	</div>
{/if}
