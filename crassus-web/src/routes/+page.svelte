<script lang="ts">
	import { browser } from '$app/environment';

	// Bounce already-authenticated users straight into the app
	if (browser && localStorage.getItem('token')) {
		window.location.replace('/dashboard');
	}

	const features = [
		{
			title: 'Invoicing',
			desc: "Generate professional rent invoices automatically, track payment status, and handle credit notes.",
			icon: `<svg class="h-4 w-4 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/></svg>`,
		},
		{
			title: 'Expense tracking',
			desc: "Log maintenance, agency fees, and other property costs. Track what's paid and what's overdue.",
			icon: `<svg class="h-4 w-4 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8"><path stroke-linecap="round" stroke-linejoin="round" d="M17 9V7a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-6a2 2 0 00-2-2H9a2 2 0 00-2 2v6a2 2 0 002 2zm7-5a2 2 0 11-4 0 2 2 0 014 0z"/></svg>`,
		},
		{
			title: 'VAT reports',
			desc: 'Generate period VAT reports in seconds. Export to Excel or email directly to your accountant.',
			icon: `<svg class="h-4 w-4 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8"><path stroke-linecap="round" stroke-linejoin="round" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/></svg>`,
		},
		{
			title: 'Lease management',
			desc: 'Track all agreements, get notified before leases expire, and never miss a renewal deadline.',
			icon: `<svg class="h-4 w-4 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8"><path stroke-linecap="round" stroke-linejoin="round" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"/></svg>`,
		},
		{
			title: 'Document storage',
			desc: 'Keep leases, receipts, insurance docs, and VAT exports in one place, organised by property.',
			icon: `<svg class="h-4 w-4 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8"><path stroke-linecap="round" stroke-linejoin="round" d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"/></svg>`,
		},
		{
			title: 'Team access',
			desc: 'Invite an accountant or property manager with scoped permissions — owners, editors, or viewers.',
			icon: `<svg class="h-4 w-4 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8"><path stroke-linecap="round" stroke-linejoin="round" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z"/></svg>`,
		},
	];

	const testimonials = [
		{
			quote: "I used to dread VAT quarter-ends. Now I click a button and send the Excel straight to my accountant. Genuinely saves me half a day every three months.",
			name: "Marcus Verlinden",
			detail: "8 units across Antwerp & Ghent",
		},
		{
			quote: "The lease expiry alerts alone are worth it. I nearly missed serving notice on a tenant last year. That won't happen again.",
			name: "Sophie Hartmann",
			detail: "Landlord, 4 residential properties",
		},
		{
			quote: "Finally a tool that doesn't assume I'm a Fortune 500 company. It does exactly what I need for my two flats and nothing more.",
			name: "Tomás Reyes",
			detail: "2 properties, Barcelona",
		},
	];

	const plans = [
		{
			name: 'Starter',
			range: '1–3 properties',
			price: 10,
			featured: false,
			features: [
				'Up to 3 properties',
				'Unlimited invoices & leases',
				'Expense tracking',
				'VAT reports',
				'Document storage',
				'Email support',
			],
		},
		{
			name: 'Growth',
			range: '4–10 properties',
			price: 20,
			featured: true,
			features: [
				'Up to 10 properties',
				'Everything in Starter',
				'Team member invites',
				'Role-based access',
				'Priority support',
			],
		},
		{
			name: 'Portfolio',
			range: '11+ properties',
			price: 50,
			featured: false,
			features: [
				'Unlimited properties',
				'Everything in Growth',
				'Multiple team members',
				'Dedicated onboarding',
			],
		},
	];
</script>

<svelte:head>
	<title>Crassus — Property Management for Landlords</title>
	<meta name="description" content="Invoicing, expenses, VAT reports, lease tracking — everything a landlord needs, without the noise." />
</svelte:head>

<!-- NAV -->
<header class="fixed inset-x-0 top-0 z-50 border-b border-white/[0.06] bg-[#0a0a0a]/90 backdrop-blur-md">
	<div class="mx-auto flex h-14 max-w-5xl items-center justify-between px-6">
		<span class="text-sm font-semibold tracking-tight text-white">Crassus</span>
		<a
			href="/login"
			class="rounded-lg border border-white/10 bg-white/5 px-4 py-1.5 text-xs font-medium text-white/70 transition hover:border-white/20 hover:text-white"
		>
			Sign in
		</a>
	</div>
</header>

<div class="min-h-screen bg-[#0a0a0a] text-white">

	<!-- subtle grid texture -->
	<div
		class="pointer-events-none fixed inset-0 opacity-[0.025]"
		style="background-image: linear-gradient(#fff 1px, transparent 1px), linear-gradient(90deg, #fff 1px, transparent 1px); background-size: 48px 48px;"
	></div>

	<!-- HERO -->
	<section class="relative mx-auto max-w-5xl px-6 pb-24 pt-36 text-center">
		<div class="mb-5 inline-flex items-center gap-2 rounded-full border border-indigo-500/25 bg-indigo-500/10 px-3.5 py-1 text-xs font-medium text-indigo-300">
			<span class="h-1.5 w-1.5 rounded-full bg-indigo-400"></span>
			Free for 3 months — no credit card required
		</div>

		<h1 class="mx-auto max-w-3xl text-5xl font-bold leading-[1.1] tracking-tight text-white">
			Property management<br />
			<span class="text-white/30">without the spreadsheets.</span>
		</h1>

		<p class="mx-auto mt-6 max-w-xl text-base leading-relaxed text-white/50">
			Crassus handles invoicing, expenses, VAT reports, lease tracking, and document storage — everything you need to run a rental portfolio, nothing you don't.
		</p>

		<div class="mt-10 flex flex-col items-center gap-3 sm:flex-row sm:justify-center">
			<a
				href="/login"
				class="rounded-xl bg-indigo-600 px-7 py-3 text-sm font-semibold text-white shadow-lg shadow-indigo-900/40 transition hover:bg-indigo-500 active:bg-indigo-700"
			>
				Start free trial
			</a>
			<a
				href="#features"
				class="rounded-xl border border-white/10 px-7 py-3 text-sm font-medium text-white/60 transition hover:border-white/20 hover:text-white/90"
			>
				See what's included
			</a>
		</div>
	</section>

	<!-- FEATURES -->
	<section id="features" class="mx-auto max-w-5xl px-6 pb-24">
		<div class="mb-12 text-center">
			<h2 class="text-2xl font-bold tracking-tight text-white">Everything in one place</h2>
			<p class="mt-2 text-sm text-white/40">Built for landlords who'd rather spend time on their portfolio, not their software.</p>
		</div>

		<div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
			{#each features as f}
				<div class="rounded-2xl border border-white/[0.07] bg-[#111111] p-6">
					<div class="mb-3 flex h-9 w-9 items-center justify-center rounded-xl bg-white/5">
						{@html f.icon}
					</div>
					<h3 class="mb-1.5 text-sm font-semibold text-white">{f.title}</h3>
					<p class="text-xs leading-relaxed text-white/45">{f.desc}</p>
				</div>
			{/each}
		</div>
	</section>

	<!-- TESTIMONIALS -->
	<section class="mx-auto max-w-5xl px-6 pb-24">
		<div class="mb-12 text-center">
			<h2 class="text-2xl font-bold tracking-tight text-white">What landlords say</h2>
		</div>

		<div class="grid gap-5 sm:grid-cols-3">
			{#each testimonials as t}
				<figure class="rounded-2xl border border-white/[0.07] bg-[#111111] p-6">
					<div class="mb-4 flex gap-0.5">
						{#each {length: 5} as _}
							<svg class="h-3.5 w-3.5 text-amber-400" viewBox="0 0 20 20" fill="currentColor">
								<path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z"/>
							</svg>
						{/each}
					</div>
					<blockquote class="mb-4 text-sm leading-relaxed text-white/60">"{t.quote}"</blockquote>
					<figcaption>
						<p class="text-xs font-semibold text-white/80">{t.name}</p>
						<p class="text-xs text-white/30">{t.detail}</p>
					</figcaption>
				</figure>
			{/each}
		</div>
	</section>

	<!-- PRICING -->
	<section id="pricing" class="mx-auto max-w-5xl px-6 pb-24">
		<div class="mb-12 text-center">
			<h2 class="text-2xl font-bold tracking-tight text-white">Simple, flat pricing</h2>
			<p class="mt-2 text-sm text-white/40">Pay per year. Cancel any time. First 3 months are on us.</p>
		</div>

		<div class="grid gap-5 sm:grid-cols-3">
			{#each plans as plan}
				<div class="relative flex flex-col rounded-2xl border p-7
					{plan.featured ? 'border-indigo-500/40 bg-indigo-950/30' : 'border-white/[0.07] bg-[#111111]'}">
					{#if plan.featured}
						<div class="absolute -top-3 left-1/2 -translate-x-1/2">
							<span class="rounded-full bg-indigo-600 px-3 py-0.5 text-xs font-semibold text-white shadow">Most popular</span>
						</div>
					{/if}

					<h3 class="mb-1 text-sm font-semibold text-white">{plan.name}</h3>
					<p class="mb-5 text-xs text-white/40">{plan.range}</p>

					<div class="mb-6 flex items-end gap-1">
						<span class="text-4xl font-bold tracking-tight text-white">€{plan.price}</span>
						<span class="mb-1 text-sm text-white/40">/ year</span>
					</div>

					<ul class="mb-8 flex-1 space-y-2">
						{#each plan.features as feat}
							<li class="flex items-start gap-2 text-xs text-white/55">
								<svg class="mt-0.5 h-3.5 w-3.5 flex-shrink-0 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
									<path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/>
								</svg>
								{feat}
							</li>
						{/each}
					</ul>

					<a
						href="/login"
						class="block rounded-xl py-2.5 text-center text-sm font-semibold transition
							{plan.featured
								? 'bg-indigo-600 text-white hover:bg-indigo-500'
								: 'border border-white/10 text-white/70 hover:border-white/20 hover:text-white'}"
					>
						Start free trial
					</a>
				</div>
			{/each}
		</div>

		<p class="mt-6 text-center text-xs text-white/25">All plans include a free 3-month trial. No credit card required to start.</p>
	</section>

	<!-- FOOTER -->
	<footer class="border-t border-white/[0.06] py-8 text-center">
		<p class="text-xs text-white/20">© {new Date().getFullYear()} Crassus. All rights reserved.</p>
	</footer>

</div>
