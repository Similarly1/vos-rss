import { writable, get } from 'svelte/store';

// 'feeds' | 'discover' | 'synthesis'
export const currentView = writable('feeds');

// Responsive state
export const isMobile = writable(false);

// Selected article or cluster ID
export const selectedItemId = writable(null);

// Modals
export const showSettingsModal = writable(false);
export const showAddFeedModal = writable(false);
export const showFeedManagerModal = writable(false);

// Settings state
export const mistralApiKey = writable(localStorage.getItem('vos_mistral_api_key') || '');
export const selectedMistralModel = writable(localStorage.getItem('vos_mistral_model') || 'mistral-small-latest');
export const refreshIntervalMinutes = writable(parseInt(localStorage.getItem('vos_refresh_interval') || '30', 10));

// Reader Language & Full Text filter preferences
export const articleLanguageFilter = writable(localStorage.getItem('vos_article_lang') || 'fr');
export const fullTextOnlyFilter = writable(localStorage.getItem('vos_full_text_only') === 'true');

// Articles & Feeds stores
export const articlesList = writable([]);
export const feedsList = writable([]);

export function saveSettings(apiKey, model, refreshMinutes = 30, langFilter = 'fr', fullTextOnly = false) {
  mistralApiKey.set(apiKey);
  selectedMistralModel.set(model);
  refreshIntervalMinutes.set(refreshMinutes);
  articleLanguageFilter.set(langFilter);
  fullTextOnlyFilter.set(fullTextOnly);

  localStorage.setItem('vos_mistral_api_key', apiKey);
  localStorage.setItem('vos_mistral_model', model);
  localStorage.setItem('vos_refresh_interval', refreshMinutes.toString());
  localStorage.setItem('vos_article_lang', langFilter);
  localStorage.setItem('vos_full_text_only', fullTextOnly ? 'true' : 'false');

  setupAutoRefresh();
  fetchArticles();
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
      const apiKey = get(mistralApiKey);
      console.log(`[Auto-Refresh & Auto-Vectorize] Rafraîchissement automatique (${minutes} min)...`);
      fetch('/api/feeds/refresh', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ api_key: apiKey })
      })
        .then(() => {
          fetchArticles();
          fetchFeeds();
        })
        .catch(err => console.error("Erreur auto-refresh:", err));
    }, ms);
  }
}
