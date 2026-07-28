import { writable } from 'svelte/store';

export const statsStore = writable({
    listeningTimeMinutes: 0,
    followedFeedsCount: 0,
    articlesRead: 0,
    articlesListened: 0,
    activityHistory: [],
    token_usage: [],
    loading: false,
    error: null
});

export async function fetchStats() {
    statsStore.update(s => ({ ...s, loading: true, error: null }));
    try {
        const res = await fetch('/api/stats');
        if (!res.ok) throw new Error('Failed to fetch stats');
        const data = await res.json();
        statsStore.update(s => ({ ...s, ...data, loading: false }));
    } catch (err) {
        statsStore.update(s => ({ ...s, error: err.message, loading: false }));
    }
}

export async function trackStat(action, amount = 1) {
    try {
        const res = await fetch('/api/stats/track', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action, amount })
        });
        if (!res.ok) throw new Error('Failed to track stat');
        const data = await res.json();
        statsStore.update(s => ({ ...s, ...data }));
    } catch (err) {
        console.error('Error tracking stat:', err);
    }
}
