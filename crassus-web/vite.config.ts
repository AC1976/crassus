import tailwindcss from '@tailwindcss/vite';
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

const apiBaseUrl = process.env.VITE_API_BASE_URL ?? 'http://localhost:8000/v1';

export default defineConfig({
	plugins: [tailwindcss(), sveltekit()],
	define: {
		// Bake the backend URL into the client bundle at build time.
		// On Railway, set VITE_API_BASE_URL to ${{ crassus.RAILWAY_PUBLIC_DOMAIN }}.
		'import.meta.env.VITE_API_BASE_URL': JSON.stringify(apiBaseUrl)
	}
});
