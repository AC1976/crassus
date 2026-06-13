import { api, setToken, clearToken } from './api/client';

export interface User {
	id: number;
	org_id: number;
	org_name: string;
	email: string;
	role: 'owner' | 'editor' | 'viewer';
	is_active: boolean;
}

export async function login(email: string, password: string): Promise<void> {
	const res = await api.post<{ access_token: string }>('/auth/login', { email, password });
	setToken(res.access_token);
}

export async function register(orgName: string, email: string, password: string): Promise<void> {
	const res = await api.post<{ access_token: string }>('/auth/register', {
		org_name: orgName,
		email,
		password
	});
	setToken(res.access_token);
}

export function logout(): void {
	clearToken();
	window.location.href = '/login';
}

export async function getMe(): Promise<User> {
	return api.get<User>('/auth/me');
}
