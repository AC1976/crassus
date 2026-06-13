<script lang="ts">
	import { login, register } from '$lib/auth';

	let mode: 'login' | 'register' = $state('login');
	let email = $state('');
	let password = $state('');
	let orgName = $state('');
	let error = $state('');
	let loading = $state(false);

	async function handleSubmit(e: SubmitEvent) {
		e.preventDefault();
		error = '';
		loading = true;
		try {
			if (mode === 'login') {
				await login(email, password);
			} else {
				await register(orgName, email, password);
			}
			window.location.href = '/dashboard';
		} catch (err: unknown) {
			error = err instanceof Error ? err.message : 'Something went wrong.';
		} finally {
			loading = false;
		}
	}
</script>

<div class="flex min-h-screen items-center justify-center bg-[#0a0a0a]">
	<!-- Subtle grid background -->
	<div
		class="pointer-events-none fixed inset-0 opacity-[0.03]"
		style="background-image: linear-gradient(#fff 1px, transparent 1px), linear-gradient(90deg, #fff 1px, transparent 1px); background-size: 40px 40px;"
	></div>

	<div class="relative w-full max-w-sm px-4">
		<!-- Logo / wordmark -->
		<div class="mb-8 text-center">
			<h1 class="text-3xl font-semibold tracking-tight text-white">Crassus</h1>
			<p class="mt-1 text-sm text-white/40">Property Management</p>
		</div>

		<!-- Card -->
		<div class="rounded-2xl border border-white/10 bg-[#111111] p-8 shadow-2xl">
			<!-- Tab toggle -->
			<div class="mb-6 flex rounded-xl bg-[#1a1a1a] p-1">
				<button
					class="flex-1 rounded-lg py-2 text-sm font-medium transition-all duration-150
						{mode === 'login' ? 'bg-[#2a2a2a] text-white shadow' : 'text-white/40 hover:text-white/70'}"
					onclick={() => (mode = 'login')}>Sign in</button
				>
				<button
					class="flex-1 rounded-lg py-2 text-sm font-medium transition-all duration-150
						{mode === 'register' ? 'bg-[#2a2a2a] text-white shadow' : 'text-white/40 hover:text-white/70'}"
					onclick={() => (mode = 'register')}>Register</button
				>
			</div>

			<form onsubmit={handleSubmit} class="space-y-4">
				{#if mode === 'register'}
					<div>
						<label class="mb-1.5 block text-xs font-medium text-white/50 uppercase tracking-wider" for="orgName">
							Organisation
						</label>
						<input
							id="orgName"
							type="text"
							bind:value={orgName}
							required
							placeholder="Acme Properties Ltd."
							class="w-full rounded-xl border border-white/10 bg-[#1a1a1a] px-4 py-3 text-sm text-white placeholder-white/20
								focus:border-indigo-500/50 focus:outline-none focus:ring-1 focus:ring-indigo-500/50 transition"
						/>
					</div>
				{/if}

				<div>
					<label class="mb-1.5 block text-xs font-medium text-white/50 uppercase tracking-wider" for="email">
						Email
					</label>
					<input
						id="email"
						type="email"
						bind:value={email}
						required
						placeholder="you@example.com"
						class="w-full rounded-xl border border-white/10 bg-[#1a1a1a] px-4 py-3 text-sm text-white placeholder-white/20
							focus:border-indigo-500/50 focus:outline-none focus:ring-1 focus:ring-indigo-500/50 transition"
					/>
				</div>

				<div>
					<div class="mb-1.5 flex items-center justify-between">
						<label class="block text-xs font-medium text-white/50 uppercase tracking-wider" for="password">
							Password
						</label>
						{#if mode === 'login'}
							<a href="/forgot-password" class="text-xs text-indigo-400 hover:text-indigo-300 transition-colors">
								Forgot password?
							</a>
						{/if}
					</div>
					<input
						id="password"
						type="password"
						bind:value={password}
						required
						minlength={8}
						placeholder="••••••••"
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
					disabled={loading}
					class="mt-2 w-full rounded-xl bg-indigo-600 px-4 py-3 text-sm font-semibold text-white
						hover:bg-indigo-500 active:bg-indigo-700 disabled:opacity-40 transition-colors"
				>
					{loading ? 'Please wait…' : mode === 'login' ? 'Sign in' : 'Create account'}
				</button>
			</form>
		</div>
	</div>
</div>
