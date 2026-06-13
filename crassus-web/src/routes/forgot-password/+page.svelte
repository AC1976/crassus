<script lang="ts">
	let email = $state('');
	let submitting = $state(false);
	let error = $state('');
	let sent = $state(false);

	async function handleSubmit(e: SubmitEvent) {
		e.preventDefault();
		submitting = true;
		error = '';
		try {
			const res = await fetch(
				`${import.meta.env.VITE_API_BASE_URL}/auth/forgot-password`,
				{
					method: 'POST',
					headers: { 'Content-Type': 'application/json' },
					body: JSON.stringify({ email }),
				}
			);
			if (!res.ok && res.status !== 204) {
				const data = await res.json().catch(() => ({}));
				throw new Error(data.detail ?? 'Something went wrong.');
			}
			sent = true;
		} catch (err: unknown) {
			error = err instanceof Error ? err.message : 'Something went wrong.';
		} finally {
			submitting = false;
		}
	}
</script>

<svelte:head>
	<title>Forgot Password — Crassus</title>
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
			{#if sent}
				<div class="text-center">
					<div class="mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-emerald-500/15">
						<svg class="h-6 w-6 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
							<path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
						</svg>
					</div>
					<h2 class="text-base font-semibold text-white">Check your inbox</h2>
					<p class="mt-2 text-sm text-white/50">
						If an account exists for <strong class="text-white/70">{email}</strong>, you'll receive a reset link shortly. It expires in 60 minutes.
					</p>
					<a
						href="/login"
						class="mt-6 inline-block rounded-xl bg-[#1a1a1a] px-5 py-2.5 text-sm font-medium text-white/70 hover:text-white transition-colors"
					>
						Back to sign in
					</a>
				</div>
			{:else}
				<h2 class="mb-1 text-lg font-semibold text-white">Forgot your password?</h2>
				<p class="mb-6 text-sm text-white/40">Enter your email and we'll send you a reset link.</p>

				<form onsubmit={handleSubmit} class="space-y-4">
					<div>
						<label class="mb-1.5 block text-xs font-medium uppercase tracking-wider text-white/50" for="fp_email">
							Email
						</label>
						<input
							id="fp_email"
							type="email"
							bind:value={email}
							required
							placeholder="you@example.com"
							class="w-full rounded-xl border border-white/10 bg-[#1a1a1a] px-4 py-3 text-sm text-white placeholder-white/20
								focus:border-indigo-500/50 focus:outline-none focus:ring-1 focus:ring-indigo-500/50 transition"
						/>
					</div>

					{#if error}
						<div class="rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3">
							<p class="text-sm text-red-400">{error}</p>
						</div>
					{/if}

					<button
						type="submit"
						disabled={submitting}
						class="w-full rounded-xl bg-indigo-600 px-4 py-3 text-sm font-semibold text-white
							hover:bg-indigo-500 active:bg-indigo-700 disabled:opacity-40 transition-colors"
					>
						{submitting ? 'Sending…' : 'Send reset link'}
					</button>
				</form>

				<p class="mt-4 text-center text-xs text-white/30">
					Remembered it? <a href="/login" class="text-indigo-400 hover:text-indigo-300 transition-colors">Sign in</a>
				</p>
			{/if}
		</div>
	</div>
</div>
