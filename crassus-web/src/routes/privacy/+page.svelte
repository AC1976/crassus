<svelte:head>
	<title>Privacy Policy — Crassus</title>
	<meta name="description" content="Privacy Policy for Crassus property management software." />
</svelte:head>

<div class="min-h-screen bg-[#0a0a0a] text-white">

	<!-- NAV -->
	<header class="fixed inset-x-0 top-0 z-50 border-b border-white/[0.06] bg-[#0a0a0a]/90 backdrop-blur-md">
		<div class="mx-auto flex h-14 max-w-3xl items-center justify-between px-6">
			<a href="/" class="text-sm font-semibold tracking-tight text-white">Crassus</a>
			<a href="/login"
				class="rounded-lg border border-white/10 bg-white/5 px-4 py-1.5 text-xs font-medium text-white/70 transition hover:border-white/20 hover:text-white">
				Sign in
			</a>
		</div>
	</header>

	<main class="mx-auto max-w-3xl px-6 pb-24 pt-28">
		<h1 class="mb-2 text-3xl font-bold tracking-tight text-white">Privacy Policy</h1>
		<p class="mb-10 text-sm text-white/30">Last updated: June 2026</p>

		<div class="space-y-8 text-sm leading-relaxed text-white/60">

			<section>
				<h2 class="mb-3 text-base font-semibold text-white">1. Who we are</h2>
				<p>Crassus ("we", "us", "our") is a property management platform operated as a private service. Our primary contact for privacy matters is <a href="mailto:support@crassus.pro" class="text-indigo-400 hover:text-indigo-300 transition-colors">support@crassus.pro</a>.</p>
			</section>

			<section>
				<h2 class="mb-3 text-base font-semibold text-white">2. What data we collect</h2>
				<p class="mb-3">We collect only the data necessary to provide the service:</p>
				<ul class="list-disc space-y-1.5 pl-5">
					<li><strong class="text-white/80">Account data</strong> — your name, email address, and organisation name, provided when your account is created by an administrator.</li>
					<li><strong class="text-white/80">Property data</strong> — property addresses, lease agreements, tenant details, invoices, and expenses that you enter into the platform.</li>
					<li><strong class="text-white/80">Usage data</strong> — standard server logs (IP address, request timestamps, browser or app version) retained for up to 90 days for security and debugging purposes.</li>
					<li><strong class="text-white/80">Email delivery data</strong> — open and delivery status of invoice emails sent via our email service provider, to help you confirm invoices were received.</li>
				</ul>
			</section>

			<section>
				<h2 class="mb-3 text-base font-semibold text-white">3. How we use your data</h2>
				<ul class="list-disc space-y-1.5 pl-5">
					<li>To provide and operate the Crassus platform and iOS companion app.</li>
					<li>To send invoices and payment reminders on your behalf to your tenants.</li>
					<li>To authenticate your account securely.</li>
					<li>To diagnose technical issues and maintain service reliability.</li>
					<li>To respond to support requests you send to us.</li>
				</ul>
				<p class="mt-3">We do not use your data for advertising, profiling, or any purpose beyond operating the service.</p>
			</section>

			<section>
				<h2 class="mb-3 text-base font-semibold text-white">4. Data sharing</h2>
				<p class="mb-3">We do not sell or rent your personal data. We share data only with the following sub-processors, strictly to deliver the service:</p>
				<ul class="list-disc space-y-1.5 pl-5">
					<li><strong class="text-white/80">Railway</strong> — cloud infrastructure hosting the backend and database.</li>
					<li><strong class="text-white/80">Amazon S3</strong> — storage for generated invoice PDF files.</li>
					<li><strong class="text-white/80">Resend</strong> — transactional email delivery (invoices and reminders).</li>
				</ul>
				<p class="mt-3">Each sub-processor is bound by data processing agreements and applicable privacy law.</p>
			</section>

			<section>
				<h2 class="mb-3 text-base font-semibold text-white">5. Data retention</h2>
				<p>We retain your account and property data for as long as your account is active. If you request deletion of your account, we will permanently delete your data within 30 days, except where retention is required by law (e.g. tax record obligations).</p>
			</section>

			<section>
				<h2 class="mb-3 text-base font-semibold text-white">6. Security</h2>
				<p>All data is transmitted over HTTPS. Passwords are stored as salted hashes and never in plain text. Access tokens expire and are not stored server-side. We apply reasonable technical and organisational measures to protect your data against unauthorised access.</p>
			</section>

			<section>
				<h2 class="mb-3 text-base font-semibold text-white">7. Your rights</h2>
				<p class="mb-3">Depending on your jurisdiction, you may have the right to:</p>
				<ul class="list-disc space-y-1.5 pl-5">
					<li>Access the personal data we hold about you.</li>
					<li>Request correction of inaccurate data.</li>
					<li>Request deletion of your account and associated data.</li>
					<li>Object to or restrict certain processing activities.</li>
					<li>Receive a copy of your data in a portable format.</li>
				</ul>
				<p class="mt-3">To exercise any of these rights, email <a href="mailto:support@crassus.pro" class="text-indigo-400 hover:text-indigo-300 transition-colors">support@crassus.pro</a>. We will respond within 30 days.</p>
			</section>

			<section>
				<h2 class="mb-3 text-base font-semibold text-white">8. iOS app</h2>
				<p>The Crassus iOS companion app connects to the same backend as the web platform using the same account credentials. It stores only an authentication token in your device's secure Keychain. No personal data is stored locally on your device beyond this token. The app does not access your contacts, location, camera roll, or any other device data beyond what you explicitly scan during expense capture (which is processed entirely on-device by Apple's Vision framework and not sent to our servers).</p>
			</section>

			<section>
				<h2 class="mb-3 text-base font-semibold text-white">9. Cookies</h2>
				<p>The Crassus web app does not use tracking cookies. Authentication state is managed via a token stored in your browser's local storage, used solely to maintain your session.</p>
			</section>

			<section>
				<h2 class="mb-3 text-base font-semibold text-white">10. Changes to this policy</h2>
				<p>We may update this policy from time to time. We will notify registered users by email if changes are material. The date at the top of this page reflects when the policy was last revised.</p>
			</section>

			<section>
				<h2 class="mb-3 text-base font-semibold text-white">11. Contact</h2>
				<p>Questions about this policy or your data: <a href="mailto:support@crassus.pro" class="text-indigo-400 hover:text-indigo-300 transition-colors">support@crassus.pro</a></p>
			</section>

		</div>
	</main>

	<footer class="border-t border-white/[0.06] py-8 text-center">
		<p class="text-xs text-white/20">© {new Date().getFullYear()} Crassus. All rights reserved.</p>
	</footer>

</div>
