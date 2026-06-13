const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/v1';

export function getToken(): string | null {
	if (typeof localStorage === 'undefined') return null;
	return localStorage.getItem('token');
}

export function setToken(token: string): void {
	localStorage.setItem('token', token);
}

export function clearToken(): void {
	localStorage.removeItem('token');
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
	const token = getToken();
	const headers: Record<string, string> = {
		'Content-Type': 'application/json',
		...(options.headers as Record<string, string>)
	};
	if (token) headers['Authorization'] = `Bearer ${token}`;

	const res = await fetch(`${BASE_URL}${path}`, { ...options, headers });

	if (!res.ok) {
		const err = await res.json().catch(() => ({ detail: 'Unknown error' }));
		throw new Error(err.detail ?? 'Request failed');
	}

	if (res.status === 204) return undefined as T;
	return res.json();
}

export const api = {
	get: <T>(path: string) => request<T>(path),
	post: <T>(path: string, body: unknown) =>
		request<T>(path, { method: 'POST', body: JSON.stringify(body) }),
	patch: <T>(path: string, body: unknown) =>
		request<T>(path, { method: 'PATCH', body: JSON.stringify(body) }),
	delete: (path: string) => request<void>(path, { method: 'DELETE' })
};
