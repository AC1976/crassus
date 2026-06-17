<script lang="ts">
	import '../app.css';
	const { children } = $props();
</script>

<svelte:head>
	<!-- PWA manifest -->
	<link rel="manifest" href="/manifest.json" />

	<!-- Theme -->
	<meta name="theme-color" content="#0a0a0a" />

	<!-- iOS PWA -->
	<meta name="apple-mobile-web-app-capable" content="yes" />
	<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />
	<meta name="apple-mobile-web-app-title" content="Crassus" />

	<!-- iOS icons -->
	<link rel="apple-touch-icon" href="/icon-180.png" />

	<!-- Favicon -->
	<link rel="icon" type="image/png" sizes="32x32" href="/icon-32.png" />
	<link rel="icon" type="image/png" sizes="16x16" href="/icon-16.png" />

	<!-- Viewport -->
	<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
</svelte:head>

{@render children()}
