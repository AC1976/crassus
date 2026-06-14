<script lang="ts">
	import { onMount, tick } from 'svelte';

	const STORAGE_KEY = 'crassus_onboarding_v1';

	type Placement = 'right' | 'below-left' | 'center';

	interface Step {
		target: string | null;
		placement: Placement;
		title: string;
		body: string;
	}

	const steps: Step[] = [
		{
			target: 'onboarding-settings',
			placement: 'below-left',
			title: 'Start with Settings',
			body: 'Open your account menu to reach Settings. Fill in your company name, billing email, bank details, logo, and invoice numbering scheme before creating your first invoice.',
		},
		{
			target: 'onboarding-properties',
			placement: 'right',
			title: 'Add your Properties',
			body: 'Register the buildings or addresses you manage, then add the individual units within them that you rent out.',
		},
		{
			target: 'onboarding-lessees',
			placement: 'right',
			title: 'Add Lessees',
			body: 'Create tenant records — individuals or companies — that you will be billing. You can attach multiple agreements to one lessee.',
		},
		{
			target: 'onboarding-agreements',
			placement: 'right',
			title: 'Create Agreements',
			body: 'Link a lessee to a unit with a rental agreement. Set the rent, service charges, VAT rate, payment interval, and lease start and end dates.',
		},
		{
			target: 'onboarding-documents',
			placement: 'right',
			title: 'Documents',
			body: 'Upload contracts, certificates, or any file linked to a property, unit, or lessee. Invoice PDFs are archived here automatically when sent.',
		},
		{
			target: null,
			placement: 'center',
			title: "You're ready to go!",
			body: '',
		},
	];

	let visible = $state(false);
	let stepIndex = $state(0);

	// Tooltip position
	let tooltipTop = $state(0);
	let tooltipLeft = $state(0);
	let tooltipRight: number | null = $state(null);
	let arrowSide: 'left' | 'top-right' | 'none' = $state('none');

	onMount(() => {
		if (!localStorage.getItem(STORAGE_KEY)) {
			visible = true;
			positionTooltip();
		}
	});

	async function positionTooltip() {
		await tick();
		const s = steps[stepIndex];
		if (!s.target || s.placement === 'center') {
			arrowSide = 'none';
			return;
		}
		const el = document.querySelector<HTMLElement>(`[data-onboarding="${s.target}"]`);
		if (!el) { arrowSide = 'none'; return; }

		const r = el.getBoundingClientRect();

		if (s.placement === 'right') {
			tooltipTop = r.top + r.height / 2;
			tooltipLeft = r.right + 20;
			tooltipRight = null;
			arrowSide = 'left';
		} else if (s.placement === 'below-left') {
			tooltipTop = r.bottom + 12;
			tooltipRight = window.innerWidth - r.right - 4;
			tooltipLeft = 0;
			arrowSide = 'top-right';
		}
	}

	async function next() {
		if (stepIndex < steps.length - 1) {
			stepIndex++;
			await positionTooltip();
		} else {
			dismiss();
		}
	}

	function dismiss() {
		localStorage.setItem(STORAGE_KEY, '1');
		visible = false;
	}

	function progress() {
		return `${stepIndex + 1} / ${steps.length}`;
	}

	const isLast = $derived(stepIndex === steps.length - 1);
	const isCentered = $derived(steps[stepIndex].placement === 'center');

	const tooltipStyle = $derived(
		isCentered
			? ''
			: tooltipRight !== null
				? `top:${tooltipTop}px;right:${tooltipRight}px;`
				: `top:${tooltipTop}px;left:${tooltipLeft}px;transform:translateY(-50%);`
	);
</script>

{#if visible}
	<!-- Subtle dim backdrop — pointer-events-none so the user can still click the app -->
	<div class="pointer-events-none fixed inset-0 z-40 bg-black/30"></div>

	{#if isCentered}
		<!-- Final "ready to go" step — centered card -->
		<div class="fixed inset-0 z-50 flex items-center justify-center p-4">
			<div class="w-full max-w-sm rounded-2xl border border-white/10 bg-[#111111] p-6 shadow-2xl">
				<div class="mb-1 flex items-center gap-2">
					<span class="text-lg">🎉</span>
					<h3 class="text-base font-semibold text-white">{steps[stepIndex].title}</h3>
				</div>
				<p class="mb-5 mt-2 text-sm leading-relaxed text-white/50">
					With your setup complete you can now:
				</p>
				<ul class="mb-5 space-y-3">
					<li class="flex items-start gap-3">
						<span class="mt-0.5 flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full bg-indigo-500/20 text-[11px] font-bold text-indigo-400">1</span>
						<div>
							<p class="text-sm font-medium text-white">Invoices</p>
							<p class="text-xs text-white/40">Batch-generate or create individual invoices, send by email, and record payments.</p>
						</div>
					</li>
					<li class="flex items-start gap-3">
						<span class="mt-0.5 flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full bg-indigo-500/20 text-[11px] font-bold text-indigo-400">2</span>
						<div>
							<p class="text-sm font-medium text-white">Expenses</p>
							<p class="text-xs text-white/40">Log property expenses and track what has been paid.</p>
						</div>
					</li>
					<li class="flex items-start gap-3">
						<span class="mt-0.5 flex h-5 w-5 flex-shrink-0 items-center justify-center rounded-full bg-indigo-500/20 text-[11px] font-bold text-indigo-400">3</span>
						<div>
							<p class="text-sm font-medium text-white">VAT Reports</p>
							<p class="text-xs text-white/40">Export or email a VAT summary for any period directly to your accountant.</p>
						</div>
					</li>
				</ul>
				<div class="flex items-center justify-between">
					<span class="text-xs text-white/20">{progress()}</span>
					<button
						onclick={dismiss}
						class="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-indigo-500"
					>
						Get started
					</button>
				</div>
			</div>
		</div>
	{:else}
		<!-- Anchored tooltip -->
		<div
			class="pointer-events-auto fixed z-50 w-72 rounded-xl border border-white/10 bg-[#111111] p-4 shadow-2xl"
			style={tooltipStyle}
		>
			<!-- Arrow: points left (tooltip is to the right of a sidebar item) -->
			{#if arrowSide === 'left'}
				<div class="absolute -left-[9px] top-1/2 -translate-y-1/2">
					<!-- border outline -->
					<div class="h-0 w-0 border-y-[8px] border-r-[9px] border-y-transparent border-r-white/10"></div>
					<!-- fill -->
					<div class="absolute left-[1px] top-1/2 h-0 w-0 -translate-y-1/2 border-y-[7px] border-r-[8px] border-y-transparent border-r-[#111111]"></div>
				</div>
			{/if}

			<!-- Arrow: points up-right (tooltip is below the user menu button) -->
			{#if arrowSide === 'top-right'}
				<div class="absolute -top-[9px] right-4">
					<!-- border outline -->
					<div class="h-0 w-0 border-b-[9px] border-x-[8px] border-b-white/10 border-x-transparent"></div>
					<!-- fill -->
					<div class="absolute left-1/2 top-[1px] h-0 w-0 -translate-x-1/2 border-b-[8px] border-x-[7px] border-b-[#111111] border-x-transparent"></div>
				</div>
			{/if}

			<h3 class="mb-1.5 text-sm font-semibold text-white">{steps[stepIndex].title}</h3>
			<p class="mb-4 text-xs leading-relaxed text-white/50">{steps[stepIndex].body}</p>

			<div class="flex items-center justify-between">
				<span class="text-xs text-white/20">{progress()}</span>
				<div class="flex items-center gap-2">
					<button
						onclick={dismiss}
						class="rounded-md px-3 py-1.5 text-xs text-white/30 transition hover:text-white/60"
					>
						Skip
					</button>
					<button
						onclick={next}
						class="rounded-md bg-indigo-600 px-3 py-1.5 text-xs font-medium text-white transition hover:bg-indigo-500"
					>
						{isLast ? 'Done' : 'Next →'}
					</button>
				</div>
			</div>
		</div>
	{/if}
{/if}
