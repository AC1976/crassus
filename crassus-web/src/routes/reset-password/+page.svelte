<script lang="ts">
	import { browser } from '$app/environment';
	import { page } from '$app/stores';

	let token = $state('');
	let password = $state('');
	let confirm = $state('');
	let submitting = $state(false);
	let error = $state('');
	let done = $state(false);

	if (browser) {
		token = $page.url.searchParams.get('token') ?? '';
		if (!token) error = 'Invalid or missing reset token.';
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
				`${import.meta.env.VITE_API_BASE_URL}/auth/reset-password`,
				{
					method: 'POST',
					headers: { 'Content-Type': 'application/json' },
					body: JSON.stringify({ token, new_password: password }),
				}
			);
			if (!res.ok && res.status !== 204) {
				const data = await res.json().catch(() => ({}));
				throw new Error(data.detail ?? 'Failed to reset password.');
			}
			done = true;
		} catch (err: unknown) {
			error = err instanceof Error ? err.message : 'Something went wrong.';
		} finally {
			submitting = false;
		}
	}
</script>

<svelte:head>
	<title>Reset Password — Crassus</title>
</svelte:head>

<div class="flex min-h-screen items-center justify-center bg-[#0a0a0a] px-4">
	<div
		class="pointer-events-none fixed inset-0 opacity-[0.03]"
		style="background-image: linear-gradient(#fff 1px, transparent 1px), linear-gradient(90deg, #fff 1px, transparent 1px); background-size: 40px 40px;"
	></div>

	<div class="relative w-full max-w-sm">
		<div class="mb-8 text-center">
			<h1 class="text-3xl font-semibold tracking-tight text-white">Crassus</h1>
			<p class="mt-1 text-sm text-white/40">Property Management</p>
		</div>

		<div class="rounded-2xl border border-white/10 bg-[#111111] p-8 shadow-2xl">
			{#if done}
				<div class="text-center">
					<div class="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-emerald-500/15">
						<svg class="h-6 w-6 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
							<path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
						</svg>
					</div>
					<h2 class="text-base font-semibold text-white">Password updated!</h2>
					<p class="mt-2 text-sm text-white/50">Your password has been changed successfully.</p>
					<a
						href="/login"
						class="mt-6 inline-block rounded-xl bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-indigo-500 transition-colors"
					>
						Sign in
					</a>
				</div>

			{:else if !token}
				<div class="text-center">
					<p class="text-sm text-red-400">This reset link is invalid or has expired.</p>
					<a href="/forgot-password" class="mt-4 inline-block text-sm text-indigo-400 hover:text-indigo-300 transition-colors">
						Request a new link
					</a>
				</div>

			{:else}
				<h2 class="mb-1 text-lg font-semibold text-white">Set a new password</h2>
				<p class="mb-6 text-sm text-white/40">Choose a strong password of at least 8 characters.</p>

				<form onsubmit={handleSubmit} class="space-y-4">
					<div>
						<label class="mb-1.5 block text-xs font-medium uppercase tracking-wider text-white/50" for="rp_pw">
							New Password
						</label>
						<input
							id="rp_pw"
							type="password"
							bind:value={password}
							required
							minlength={8}
							placeholder="At least 8 characters"
							class="w-full rounded-xl border border-white/10 bg-[#1a1a1a] px-4 py-3 text-sm text-white placeholder-white/20
								focus:border-indigo-500/50 focus:outline-none focus:ring-1 focus:ring-indigo-500/50 transition"
						/>
					</div>

					<div>
						<label class="mb-1.5 block text-xs font-medium uppercase tracking-wider text-white/50" for="rp_confirm">
							Confirm Password
						</label>
						<input
							id="rp_confirm"
							type="password"
							bind:value={confirm}
							required
							placeholder="Repeat password"
							class="w-full rounded-xl border {passwordMismatch ? 'border-red-500/50' : 'border-white/10'} bg-[#1a1a1a] px-4 py-3 text-sm text-white placeholder-white/20
								focus:border-indigo-500/50 focus:outline-none focus:ring-1 focus:ring-indigo-500/50 transition"
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
						class="w-full rounded-xl bg-indigo-600 py-3 text-sm font-semibold text-white
							hover:bg-indigo-500 disabled:opacity-40 transition-colors"
					>
						{submitting ? 'Updating…' : 'Update password'}
					</button>
				</form>
			{/if}
		</div>
	</div>
</div>
