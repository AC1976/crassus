import { writable } from 'svelte/store';
import type { User } from '$lib/auth';

export const userStore = writable<User | null>(null);
