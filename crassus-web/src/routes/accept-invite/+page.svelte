<script lang="ts">
	import { browser } from '$app/environment';
	import { page } from '$app/stores';
	import { setToken } from '$lib/api/client';

	let token = $state('');
	let password = $state('');
	let confirm = $state('');
	let submitting = $state(false);
	let error = $state('');
	let done = $state(false);

	// Read token from URL query param
	if (browser) {
		token = $page.url.searchParams.get('token') ?? '';
		if (!token) error = 'Invalid or missing invite token.';
	}

	let passwordMismatch = $derived(confirm.length > 0 && password !== confirm);
	let canSubmit = $derived(
		token.length > 0 &&
		password.length >= 8 &&
		password === confirm &&
		!submitting
	);

	async function handleSubmit(e: SubmitEvent) {
		e.preventDefault();
		if (!canSubmit) return;
		submitting = true;
		error = '';

		try {
			const res = await fetch(
				`${import.meta.env.VITE_API_BASE_URL}/auth/accept-invite`,
				{
					method: 'POST',
					headers: { 'Content-Type': 'application/json' },
					body: JSON.stringify({ token, password }),
				}
			);
			const data = await res.json();
			if (!res.ok) throw new Error(data.detail ?? 'Failed to accept invite.');

			// Log in automatically
			setToken(data.access_token);
			done = true;
			setTimeout(() => { window.location.replace('/dashboard'); }, 1500);
		} catch (err: unknown) {
			error = err instanceof Error ? err.message : 'Something went wrong.';
		} finally {
			submitting = false;
		}
	}
</script>

<svelte:head>
	<title>Accept Invitation — Crassus</title>
</svelte:head>

<div class="flex min-h-screen items-center justify-center bg-[#0a0a0a] px-4">
	<div class="w-full max-w-md">

		<div class="mb-8 text-center">
			<span class="text-2xl font-semibold tracking-tight text-white">Crassus</span>
			<p class="mt-2 text-sm text-white/40">Create your account to accept the invitation</p>
		</div>

		{#if done}
			<div class="rounded-2xl border border-emerald-500/20 bg-emerald-500/10 p-8 text-center">
				<p class="text-base font-semibold text-emerald-400">Account created!</p>
				<p class="mt-1 text-sm text-white/40">Redirecting you to the dashboard…</p>
			</div>

		{:else if !token}
			<div class="rounded-2xl border border-red-500/20 bg-red-500/10 p-8 text-center">
				<p class="text-sm text-red-400">This invite link is invalid or has already been used.</p>
			</div>

		{:else}
			<form onsubmit={handleSubmit} class="space-y-4 rounded-2xl border border-white/[0.07] bg-[#111111] p-8">
				<div>
					<label class="mb-1.5 block text-xs font-medium uppercase tracking-wider text-white/40" for="ai_pw">
						Choose a Password
					</label>
					<input
						id="ai_pw"
						type="password"
						bind:value={password}
						required
						minlength={8}
						placeholder="At least 8 characters"
						class="w-full rounded-xl border border-white/10 bg-[#1a1a1a] px-4 py-3 text-sm text-white placeholder-white/20 focus:border-indigo-500/50 focus:outline-none focus:ring-1 focus:ring-indigo-500/50 transition"
					/>
				</div>

				<div>
					<label class="mb-1.5 block text-xs font-medium uppercase tracking-wider text-white/40" for="ai_confirm">
						Confirm Password
					</label>
					<input
						id="ai_confirm"
						type="password"
						bind:value={confirm}
						required
						placeholder="Repeat password"
						class="w-full rounded-xl border {passwordMismatch ? 'border-red-500/50' : 'border-white/10'} bg-[#1a1a1a] px-4 py-3 text-sm text-white placeholder-white/20 focus:border-indigo-500/50 focus:outline-none focus:ring-1 focus:ring-indigo-500/50 transition"
					/>
					{#if passwordMismatch}
						<p class="mt-1 text-xs text-red-400">Passwords don't match.</p>
					{/if}
				</div>

				{#if error}
					<div class="rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3">
						<p class="text-sm text-red-400">{error}</p>
					</div>
				{/if}

				<button
					type="submit"
					disabled={!canSubmit}
					class="w-full rounded-xl bg-indigo-600 py-3 text-sm font-semibold text-white hover:bg-indigo-500 disabled:opacity-40 transition-colors"
				>
					{submitting ? 'Creating account…' : 'Create Account & Join'}
				</button>
			</form>

			<p class="mt-4 text-center text-xs text-white/25">
				Already have an account? <a href="/login" class="text-indigo-400 hover:text-indigo-300 transition-colors">Sign in</a>
			</p>
		{/if}

	</div>
</div>
