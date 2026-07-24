import { writable, get } from 'svelte/store';

// 'feeds' | 'discover' | 'synthesis' | 'perplexity' | 'podcast'
export const currentView = writable('feeds');

// Responsive state
export const isMobile = writable(false);

// Selected article or cluster ID
export const selectedItemId = writable(null);

// Modals
export const showSettingsModal = writable(false);
export const showAddFeedModal = writable(false);
export const showFeedManagerModal = writable(false);

// Refreshing state indicator
export const isRefreshingFeeds = writable(false);

// Settings state
export const mistralApiKey = writable(localStorage.getItem('vos_mistral_api_key') || '');
export const selectedMistralModel = writable(localStorage.getItem('vos_mistral_model') || 'mistral-small-latest');
export const refreshIntervalMinutes = writable(parseInt(localStorage.getItem('vos_refresh_interval') || '30', 10));
export const articleRetentionDays = writable(parseInt(localStorage.getItem('vos_retention_days') || '14', 10));

// Reader Language & Full Text filter preferences
export const articleLanguageFilter = writable(localStorage.getItem('vos_article_lang') || 'fr');
export const fullTextOnlyFilter = writable(localStorage.getItem('vos_full_text_only') === 'true');

// Articles & Feeds stores
export const articlesList = writable([]);
export const feedsList = writable([]);

export function saveSettings(apiKey, model, refreshMinutes = 30, langFilter = 'fr', fullTextOnly = false, retentionDays = 14) {
  mistralApiKey.set(apiKey);
  selectedMistralModel.set(model);
  refreshIntervalMinutes.set(refreshMinutes);
  articleLanguageFilter.set(langFilter);
  fullTextOnlyFilter.set(fullTextOnly);
  articleRetentionDays.set(retentionDays);

  localStorage.setItem('vos_mistral_api_key', apiKey);
  localStorage.setItem('vos_mistral_model', model);
  localStorage.setItem('vos_refresh_interval', refreshMinutes.toString());
  localStorage.setItem('vos_article_lang', langFilter);
  localStorage.setItem('vos_full_text_only', fullTextOnly ? 'true' : 'false');
  localStorage.setItem('vos_retention_days', retentionDays.toString());

  runArticlesCleanup(retentionDays);
  setupAutoRefresh();
  fetchArticles();
}

export async function runArticlesCleanup(days) {
  try {
    const res = await fetch('/api/feeds/cleanup', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ retention_days: days })
    });
    if (res.ok) {
      await fetchArticles();
      return await res.json();
    }
  } catch (err) {
    console.error("Erreur nettoyage des articles:", err);
  }
  return null;
}

export async function fetchArticles() {
  try {
    const lang = get(articleLanguageFilter);
    const fullText = get(fullTextOnlyFilter);

    let url = `/api/articles?lang=${lang}`;
    if (fullText) {
      url += `&full_text_only=true`;
    }

    const res = await fetch(url);
    if (res.ok) {
      const data = await res.json();
      articlesList.set(data);
    }
  } catch (err) {
    console.error("Erreur lors de la récupération des articles:", err);
  }
}

export async function fetchFeeds() {
  try {
    const res = await fetch('/api/feeds');
    if (res.ok) {
      const data = await res.json();
      feedsList.set(data);
    }
  } catch (err) {
    console.error("Erreur lors de la récupération des flux:", err);
  }
}

export async function triggerFeedRefresh() {
  isRefreshingFeeds.set(true);
  const apiKey = get(mistralApiKey);
  try {
    const res = await fetch('/api/feeds/refresh', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ api_key: apiKey })
    });
    if (res.ok) {
      setTimeout(async () => {
        await fetchArticles();
        await fetchFeeds();
        isRefreshingFeeds.set(false);
      }, 2500);
      return true;
    }
  } catch (err) {
    console.error("Erreur rafraîchissement des flux:", err);
  } finally {
    setTimeout(() => isRefreshingFeeds.set(false), 3500);
  }
  return false;
}

let autoRefreshTimer = null;
export function setupAutoRefresh() {
  if (autoRefreshTimer) {
    clearInterval(autoRefreshTimer);
    autoRefreshTimer = null;
  }

  const minutes = get(refreshIntervalMinutes);
  if (minutes > 0) {
    const ms = minutes * 60 * 1000;
    autoRefreshTimer = setInterval(() => {
      console.log(`[Auto-Refresh & Auto-Vectorize] Rafraîchissement automatique (${minutes} min)...`);
      triggerFeedRefresh();
    }, ms);
  }
}

// Auto setup timer on load
setupAutoRefresh();
