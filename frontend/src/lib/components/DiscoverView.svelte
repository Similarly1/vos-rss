<script>
  import { onMount } from 'svelte';
  import { fetchFeeds, fetchArticles, feedsList, langsearchApiKey, hidePaywalledWithoutCookie } from '../stores/appState.js';

  let searchQuery = '';
  let selectedCategory = 'Tous';
  let selectedTag = 'Tous';
  let selectedLanguageFilter = 'Tous';

  let catalogFeeds = [];
  let availableTags = [];
  let loadingCatalog = false;
  let loadingMore = false;

  // Mode: 'catalog' | 'web'
  let searchMode = 'catalog';

  // Local News Search state (LangSearch API)
  let searchingLocal = false;
  let localNewsResults = [];
  let localNewsError = null;

  // Pagination state
  let currentOffset = 0;
  let limit = 30;
  let totalFeedsCount = 0;
  let hasMoreFeeds = false;

  // Auto-discovery state
  let discoveringFeed = false;
  let discoveredFeedResult = null;
  let discoveryError = null;

  // Preview Modal state
  let previewFeedObj = null;
  let previewLoading = false;
  let previewArticles = [];
  let previewError = null;

  // Subscription state maps
  let subscribingMap = {};
  let subscribedSuccessMap = {};
  let errorMap = {};

  // Focus of the day state
  let focusFeed = null;
  let loadingFocus = false;

  const THEME_HERO_WALLPAPERS = {
    'Technologie': 'https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=1600&q=80',
    'Suisse': 'https://images.unsplash.com/photo-1530122037265-a5f1f91d3b99?auto=format&fit=crop&w=1600&q=80',
    'Science': 'https://images.unsplash.com/photo-1451187580459-43490279c0fa?auto=format&fit=crop&w=1600&q=80',
    'Actualités': 'https://images.unsplash.com/photo-1504711434969-e33886168f5c?auto=format&fit=crop&w=1600&q=80',
    'Économie': 'https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?auto=format&fit=crop&w=1600&q=80',
    'Culture': 'https://images.unsplash.com/photo-1460723237483-7a6dc9d0b212?auto=format&fit=crop&w=1600&q=80',
    'Monde': 'https://images.unsplash.com/photo-1451187580459-43490279c0fa?auto=format&fit=crop&w=1600&q=80',
    'Chrétien': 'https://images.unsplash.com/photo-1507692049790-de58290a4334?auto=format&fit=crop&w=1600&q=80',
    'Général': 'https://images.unsplash.com/photo-1504711434969-e33886168f5c?auto=format&fit=crop&w=1600&q=80'
  };

  function getHeroBackgroundImage(feed) {
    if (!feed) return THEME_HERO_WALLPAPERS['Général'];
    if (feed.cover_image_url && !feed.cover_image_url.includes('favicons?domain=')) {
      return feed.cover_image_url;
    }
    const cat = feed.category || 'Général';
    return THEME_HERO_WALLPAPERS[cat] || THEME_HERO_WALLPAPERS['Général'];
  }

  function getTrustBadges(feed) {
    const badges = [];
    if (!feed) return badges;

    if (feed.is_jti_certified) {
      badges.push({ text: '🛡️ Certifié JTI (RSF)', class: 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400 border-emerald-500/30' });
    }
    if (feed.factuality_rating === 'High' || feed.factuality_rating === 'Very High') {
      badges.push({ text: '⚖️ Factuel', class: 'bg-blue-500/15 text-blue-600 dark:text-blue-400 border-blue-500/30' });
    }
    
    const bias = (feed.bias_rating || '').toLowerCase();
    if (bias === 'left' || bias === 'gauche') {
      badges.push({ text: '🔴 Gauche', class: 'bg-rose-500/15 text-rose-600 dark:text-rose-400 border-rose-500/30' });
    } else if (bias === 'left-center' || bias === 'centre-gauche') {
      badges.push({ text: '🟥 Centre-Gauche', class: 'bg-pink-500/15 text-pink-600 dark:text-pink-400 border-pink-500/30' });
    } else if (bias === 'center' || bias === 'centre' || bias === 'least biased') {
      badges.push({ text: '🌐 Centre / Neutre', class: 'bg-sky-500/15 text-sky-600 dark:text-sky-400 border-sky-500/30' });
    } else if (bias === 'right-center' || bias === 'centre-droit') {
      badges.push({ text: '🟦 Centre-Droit', class: 'bg-indigo-500/15 text-indigo-600 dark:text-indigo-400 border-indigo-500/30' });
    } else if (bias === 'right' || bias === 'droite') {
      badges.push({ text: '🟠 Droite', class: 'bg-orange-500/15 text-orange-600 dark:text-orange-400 border-orange-500/30' });
    }

    const type = feed.media_type || 'Général';
    if (type === 'Agence') {
      badges.push({ text: '📡 Agence', class: 'bg-purple-500/15 text-purple-600 dark:text-purple-400 border-purple-500/30' });
    } else if (type === 'Analyse') {
      badges.push({ text: '📖 Analyse', class: 'bg-teal-500/15 text-teal-600 dark:text-teal-400 border-teal-500/30' });
    } else if (type === 'Régional') {
      badges.push({ text: '🏠 Régional', class: 'bg-amber-500/15 text-amber-600 dark:text-amber-400 border-amber-500/30' });
    }

    return badges;
  }

  // Recommendations state
  let recommendations = [];
  let loadingRecommendations = false;

  const categories = [
    'Tous',
    'Actualités & Presse',
    'Technologie & Cyber',
    'Économie & Business',
    'Suisse & Régional',
    'International & Monde',
    'Science & Climat',
    'Culture & Société',
    'Foi & Spiritualité',
    'Général'
  ];
  const languages = [
    { code: 'Tous', label: 'Toutes les langues' },
    { code: 'fr', label: '🇫🇷 Français' },
    { code: 'en', label: '🇬🇧 Anglais' },
    { code: 'de', label: '🇩🇪 Allemand' },
    { code: 'es', label: '🇪🇸 Espagnol' }
  ];

  const localSuggestions = [
    '🇨🇭 Vaud', '🇫🇷 Lyon', '🇫🇷 Bretagne',
    '🤖 Intelligence artificielle', '🔒 Cybersécurité', '🌍 Climat',
    '🚀 Espace', '💰 Finance', '🎮 Gaming',
    '🏥 Santé', '⚽ Sport', '🎵 Musique',
    '📷 Photographie', '🧪 Science', '🏛️ Politique'
  ];

  $: filteredCatalogFeeds = catalogFeeds.filter(feed => {
    if ($hidePaywalledWithoutCookie) {
      if (feed.is_paid || feed.is_full_text === 0 || feed.is_full_text === false) {
        if (!feed.has_cookie) return false;
      }
    }
    return true;
  });

  $: groupedCatalogFeeds = filteredCatalogFeeds.reduce((acc, feed) => {
    const cat = feed.category || 'Général';
    if (!acc[cat]) acc[cat] = [];
    acc[cat].push(feed);
    return acc;
  }, {});

  $: alreadySubscribedUrls = $feedsList.map(f => (f.url || '').toLowerCase());
  $: isWebMode = searchMode === 'web';
  $: isUrlMode = searchMode === 'catalog' && isUrlCandidate(searchQuery);
  $: searchPlaceholder = isWebMode
    ? 'Chercher par sujet, région, thème… (ex : cybersécurité, Vaud, climat)'
    : 'Rechercher un sujet, un site ou coller un lien RSS…';

  let searchTimeout = null;

  onMount(() => {
    loadFocusOfTheDay();
    loadRecommendations();
    loadTags();
    loadCatalog(true);
  });

  async function loadFocusOfTheDay() {
    loadingFocus = true;
    try {
      const hidePw = $hidePaywalledWithoutCookie ? '?hide_paywalled=true' : '';
      const res = await fetch(`/api/catalog/focus-of-the-day${hidePw}`);
      if (res.ok) {
        const data = await res.json();
        if ($hidePaywalledWithoutCookie && data && (data.is_paid || data.is_full_text === 0 || data.is_full_text === false) && !data.has_cookie) {
          focusFeed = null;
        } else {
          focusFeed = data;
        }
      }
    } catch (e) {
      console.error("Erreur chargement Focus du jour:", e);
    } finally {
      loadingFocus = false;
    }
  }

  async function loadRecommendations() {
    loadingRecommendations = true;
    try {
      const hidePw = $hidePaywalledWithoutCookie ? '&hide_paywalled=true' : '';
      const res = await fetch(`/api/catalog/recommendations?limit=6${hidePw}`);
      if (res.ok) {
        const data = await res.json();
        let rawRecs = Array.isArray(data) ? data : (data.recommendations || data.feeds || []);
        if ($hidePaywalledWithoutCookie) {
          rawRecs = rawRecs.filter(r => !( (r.is_paid || r.is_full_text === 0 || r.is_full_text === false) && !r.has_cookie ));
        }
        recommendations = rawRecs;
      }
    } catch (e) {
      console.error("Erreur chargement recommandations:", e);
    } finally {
      loadingRecommendations = false;
    }
  }

  async function loadTags() {
    try {
      const res = await fetch('/api/catalog/tags');
      if (res.ok) availableTags = await res.json();
    } catch (e) {
      console.error('Erreur chargement tags catalog:', e);
    }
  }

  async function loadCatalog(reset = true) {
    if (reset) { currentOffset = 0; loadingCatalog = true; }
    else loadingMore = true;

    try {
      const params = new URLSearchParams();
      if (searchQuery.trim() && !isUrlCandidate(searchQuery.trim())) params.append('q', searchQuery.trim());
      if (selectedCategory !== 'Tous') params.append('category', selectedCategory);
      if (selectedTag !== 'Tous') params.append('tag', selectedTag);
      if (selectedLanguageFilter !== 'Tous') params.append('language', selectedLanguageFilter);
      if ($hidePaywalledWithoutCookie) params.append('hide_paywalled', 'true');
      params.append('limit', limit.toString());
      params.append('offset', currentOffset.toString());

      const res = await fetch(`/api/catalog?${params.toString()}`);
      if (res.ok) {
        const data = await res.json();
        totalFeedsCount = data.total || 0;
        hasMoreFeeds = data.has_more || false;
        catalogFeeds = reset ? (data.feeds || []) : [...catalogFeeds, ...(data.feeds || [])];
      }
    } catch (e) {
      console.error('Erreur chargement catalogue:', e);
    } finally {
      loadingCatalog = false;
      loadingMore = false;
    }
  }

  function loadMoreFeeds() {
    if (hasMoreFeeds && !loadingMore) { currentOffset += limit; loadCatalog(false); }
  }

  function isUrlCandidate(str) {
    const s = str.trim().toLowerCase();
    return s.startsWith('http://') || s.startsWith('https://') || (s.includes('.') && !s.includes(' ') && s.length > 4);
  }

  // Unified input handler — delegates based on mode
  function handleSearchInput() {
    if (isWebMode) return; // web mode fires on Enter / action only
    discoveredFeedResult = null;
    discoveryError = null;
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => loadCatalog(true), 300);
  }

  // Unified Enter / action
  function handleKeydown(e) {
    if (e.key !== 'Enter') return;
    if (isWebMode) {
      triggerWebSearch();
    } else if (isUrlCandidate(searchQuery)) {
      triggerAutoDiscovery();
    } else {
      loadCatalog(true);
    }
  }

  function handleActionClick() {
    if (isWebMode) triggerWebSearch();
    else if (isUrlCandidate(searchQuery)) triggerAutoDiscovery();
  }

  async function triggerWebSearch(queryOverride = null) {
    const q = (queryOverride ?? searchQuery).trim();
    if (!q) return;
    if (queryOverride !== null) searchQuery = queryOverride;

    searchingLocal = true;
    localNewsError = null;
    localNewsResults = [];

    try {
      const res = await fetch('/api/catalog/search-local', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: q, api_key: $langsearchApiKey })
      });
      const data = await res.json();
      if (res.ok && data.status === 'success') {
        localNewsResults = data.data || [];
        if (!localNewsResults.length) localNewsError = `Aucun média local détecté pour "${q}".`;
      } else {
        localNewsError = data.detail || data.message || 'Échec de la recherche.';
      }
    } catch {
      localNewsError = 'Erreur réseau.';
    } finally {
      searchingLocal = false;
    }
  }

  async function triggerAutoDiscovery() {
    if (!searchQuery.trim()) return;
    discoveringFeed = true;
    discoveryError = null;
    discoveredFeedResult = null;

    try {
      const res = await fetch('/api/catalog/discover', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: searchQuery.trim(), auto_save: false })
      });
      const data = await res.json();
      if (res.ok) discoveredFeedResult = data;
      else discoveryError = data.detail || "Impossible de détecter un flux RSS sur ce domaine.";
    } catch {
      discoveryError = "Erreur de connexion.";
    } finally {
      discoveringFeed = false;
    }
  }

  function toggleMode() {
    if (searchMode === 'catalog') {
      searchMode = 'web';
      searchQuery = '';
      discoveredFeedResult = null;
      discoveryError = null;
    } else {
      searchMode = 'catalog';
      localNewsResults = [];
      localNewsError = null;
      searchQuery = '';
      loadCatalog(true);
    }
  }

  function selectSuggestion(pill) {
    const q = pill.replace(/^[^\s]+\s*/, '');
    triggerWebSearch(q);
  }

  function selectTag(tagName) {
    selectedTag = selectedTag === tagName ? 'Tous' : tagName;
    loadCatalog(true);
  }

  function selectCategory(cat) { selectedCategory = cat; loadCatalog(true); }
  function selectLanguage(langCode) { selectedLanguageFilter = langCode; loadCatalog(true); }

  async function subscribeToFeed(feedUrl, category = 'Général', language = 'fr') {
    subscribingMap[feedUrl] = true;
    errorMap[feedUrl] = null;
    subscribingMap = { ...subscribingMap };

    try {
      const res = await fetch('/api/feeds', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: feedUrl, category: category || 'Général', language: language || 'fr' })
      });
      const result = await res.json();
      if (res.ok) {
        subscribedSuccessMap[feedUrl] = true;
        subscribedSuccessMap = { ...subscribedSuccessMap };
        await fetchFeeds();
        await fetchArticles();
      } else {
        errorMap[feedUrl] = result.detail || "Erreur lors de l'abonnement.";
      }
    } catch {
      errorMap[feedUrl] = "Erreur de connexion.";
    } finally {
      subscribingMap[feedUrl] = false;
      subscribingMap = { ...subscribingMap };
    }
  }

  async function openPreview(feed) {
    previewFeedObj = feed;
    previewLoading = true;
    previewArticles = [];
    previewError = null;

    try {
      const res = await fetch(`/api/catalog/preview?url=${encodeURIComponent(feed.url)}`);
      const data = await res.json();
      if (res.ok) previewArticles = data.articles || [];
      else previewError = data.detail || "Impossible de charger l'aperçu.";
    } catch {
      previewError = "Erreur de connexion.";
    } finally {
      previewLoading = false;
    }
  }

  function getCountryFlag(country, lang) {
    if (country === 'CH') return '🇨🇭';
    if (country === 'FR') return '🇫🇷';
    if (country === 'UK' || country === 'GB') return '🇬🇧';
    if (country === 'US') return '🇺🇸';
    if (country === 'ES') return '🇪🇸';
    if (country === 'DE') return '🇩🇪';
    if (country === 'VA') return '🇻🇦';
    if (lang === 'fr') return '🇫🇷';
    if (lang === 'en') return '🇬🇧';
    if (lang === 'de') return '🇩🇪';
    if (lang === 'es') return '🇪🇸';
    return '🌍';
  }
</script>

<!-- ═══════════════════════════════════════════════ MAIN LAYOUT ══ -->
<div class="flex-1 h-full overflow-y-auto bg-gray-50 dark:bg-dark-bg scroll-smooth">
  <div class="max-w-5xl mx-auto px-4 sm:px-6 md:px-10 py-6 md:py-10 space-y-8">

    <!-- ── Focus du Jour (Hero Banner HD) ── -->
    {#if focusFeed}
      {@const isSubbedFocus = alreadySubscribedUrls.includes((focusFeed.url || '').toLowerCase()) || subscribedSuccessMap[focusFeed.url]}
      {@const heroBg = getHeroBackgroundImage(focusFeed)}
      <div class="relative w-full rounded-3xl overflow-hidden shadow-2xl group border border-gray-100 dark:border-gray-800/80">
        <!-- Background HD Wallpaper with Gradient Overlay -->
        <div class="absolute inset-0 bg-gradient-to-t from-gray-950 via-gray-950/65 to-black/30 z-10"></div>
        <img 
          src={heroBg} 
          alt={focusFeed.title} 
          class="w-full h-64 md:h-72 object-cover group-hover:scale-105 transition-transform duration-700" 
          on:error={(e) => e.target.src = THEME_HERO_WALLPAPERS['Général']}
        />
        
        <!-- Content on top of Background -->
        <div class="absolute bottom-0 left-0 right-0 p-5 md:p-8 z-20 flex flex-col md:flex-row md:items-end justify-between gap-5">
          <div class="space-y-3 min-w-0 flex-1">
            <div class="flex items-center gap-2 flex-wrap">
              <span class="inline-flex items-center gap-1.5 px-3 py-1 text-xs font-black bg-gradient-to-r from-amber-500 to-orange-500 text-white rounded-full uppercase tracking-wider shadow-md">
                🌟 Focus du jour
              </span>
              {#if focusFeed.category}
                <span class="inline-block px-3 py-1 text-[11px] font-extrabold bg-white/20 backdrop-blur-md text-white rounded-full uppercase tracking-wider border border-white/20">
                  {focusFeed.category}
                </span>
              {/if}
            </div>

            <!-- Crisp Logo Badge + Title -->
            <div class="flex items-center gap-3.5 pt-1">
              {#if focusFeed.icon_url}
                <img 
                  src={focusFeed.icon_url} 
                  alt="" 
                  class="w-12 h-12 md:w-14 md:h-14 rounded-2xl object-contain bg-white/95 dark:bg-gray-900/95 p-2 shadow-xl border border-white/20 shrink-0" 
                  on:error={(e) => e.target.style.display = 'none'}
                />
              {/if}
              <h2 class="text-xl md:text-3xl font-black text-white leading-tight drop-shadow-md">
                {focusFeed.title}
              </h2>
            </div>

            <p class="text-xs md:text-sm text-gray-200 line-clamp-2 max-w-2xl leading-relaxed font-medium">
              {focusFeed.enriched_description || focusFeed.description || "Découvrez ce flux incontournable sélectionné aujourd'hui pour votre veille d'actualité."}
            </p>
          </div>

          <div class="flex items-center gap-3 shrink-0">
            <button 
              on:click={() => openPreview(focusFeed)} 
              class="px-4 py-2.5 min-h-[44px] bg-black/50 hover:bg-black/70 text-white font-bold text-xs rounded-xl backdrop-blur-md border border-white/20 transition-all flex items-center justify-center gap-1.5 shadow-lg"
            >
              👁️ Aperçu
            </button>

            {#if isSubbedFocus}
              <span class="px-5 py-2.5 min-h-[44px] bg-emerald-500/90 text-white font-bold text-xs md:text-sm rounded-xl shadow-xl flex items-center justify-center gap-1.5 backdrop-blur-md border border-emerald-400/30">
                ✓ Abonné
              </span>
            {:else}
              <button 
                on:click={() => subscribeToFeed(focusFeed.url, focusFeed.category, focusFeed.language)} 
                disabled={subscribingMap[focusFeed.url]}
                class="px-5 py-2.5 min-h-[44px] bg-white hover:bg-gray-100 text-gray-950 font-black text-xs md:text-sm rounded-xl shadow-xl hover:scale-[1.02] active:scale-[0.98] transition-all flex items-center justify-center gap-2 disabled:opacity-50"
              >
                {#if subscribingMap[focusFeed.url]}
                  <svg class="w-4 h-4 animate-spin text-gray-950" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
                {/if}
                + S'abonner
              </button>
            {/if}
          </div>
        </div>
      </div>
    {/if}

    <!-- ── Recommandations ── -->
    {#if recommendations && recommendations.length > 0}
      <div class="space-y-5 animate-in fade-in slide-in-from-bottom-4 duration-700 ease-out">
        <div class="flex items-center gap-3">
          <h2 class="text-xl md:text-2xl font-black text-gray-900 dark:text-white tracking-tight flex items-center gap-2">
            <span class="text-2xl">💡</span> Recommandés pour vous
          </h2>
          <span class="hidden md:inline-block px-3 py-1 rounded-full bg-cyan-50 dark:bg-cyan-500/10 text-cyan-700 dark:text-cyan-400 text-xs font-bold">6 flux pour enrichir vos abonnements</span>
        </div>
        
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {#each recommendations as rec}
            {@const isAlreadySub = alreadySubscribedUrls.includes((rec.url || '').toLowerCase()) || subscribedSuccessMap[rec.url]}
            <!-- svelte-ignore a11y-click-events-have-key-events -->
            <!-- svelte-ignore a11y-no-static-element-interactions -->
            <div 
              class="group relative bg-white dark:bg-dark-card border border-gray-100 dark:border-gray-800 rounded-2xl p-5 hover:border-cyan-300 dark:hover:border-purple-500/50 shadow-sm hover:shadow-2xl hover:shadow-cyan-500/10 dark:hover:shadow-purple-500/10 transition-all duration-300 flex flex-col gap-4 cursor-pointer overflow-hidden transform hover:-translate-y-1"
              on:click={() => openPreview(rec)}
            >
              <!-- Gradient glow effect on hover -->
              <div class="absolute inset-0 bg-gradient-to-br from-cyan-500/5 to-purple-500/5 opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none"></div>

              <div class="relative z-10 flex items-start gap-4">
                <img
                  src={rec.icon_url || `https://www.google.com/s2/favicons?domain=${rec.site_url || rec.url}&sz=128`}
                  alt=""
                  class="w-14 h-14 rounded-xl object-contain bg-gray-50 dark:bg-gray-800/80 p-1.5 shrink-0 shadow-sm border border-gray-100 dark:border-gray-700/50 group-hover:scale-105 transition-transform duration-300"
                  on:error={(e) => e.target.src = 'https://www.google.com/s2/favicons?domain=rss.com&sz=128'}
                />
                <div class="flex-1 min-w-0">
                  <h3 class="font-extrabold text-base text-gray-900 dark:text-white leading-tight line-clamp-2 group-hover:text-transparent group-hover:bg-clip-text group-hover:bg-gradient-to-r group-hover:from-cyan-600 group-hover:to-purple-600 dark:group-hover:from-cyan-400 dark:group-hover:to-purple-400 transition-all">
                    {rec.title}
                  </h3>
                  {#if rec.relevance_score || rec.score}
                    <div class="mt-2 w-max inline-flex items-center px-2 py-0.5 rounded-md bg-gradient-to-r from-cyan-50 to-purple-50 dark:from-cyan-500/10 dark:to-purple-500/10 text-cyan-700 dark:text-cyan-300 text-[11px] font-black tracking-wide border border-cyan-100 dark:border-cyan-500/20 shadow-sm">
                      🎯 {rec.relevance_score || rec.score}% de pertinence
                    </div>
                  {/if}
                </div>
              </div>

              {#if rec.explanation}
                <div class="relative z-10 px-3 py-2.5 rounded-xl bg-gray-50/50 dark:bg-gray-800/30 border border-gray-100/50 dark:border-gray-700/30">
                  <p class="text-[13px] font-semibold text-transparent bg-clip-text bg-gradient-to-r from-cyan-600 to-purple-600 dark:from-cyan-400 dark:to-purple-400 italic">
                    « {rec.explanation} »
                  </p>
                </div>
              {/if}

              <p class="relative z-10 text-sm text-gray-600 dark:text-gray-400 leading-relaxed line-clamp-2 flex-1 font-medium">
                {rec.enriched_description || rec.description || `Découvrez les actualités de ${rec.title}.`}
              </p>
              
              <div class="relative z-10 mt-auto pt-4 border-t border-gray-100 dark:border-gray-800/60 flex items-center justify-between" on:click|stopPropagation>
                <div class="flex items-center gap-1.5 flex-wrap">
                  <span class="text-xs">{getCountryFlag(rec.country, rec.language)}</span>
                  <span class="text-[10px] uppercase font-black tracking-wider text-gray-500 dark:text-gray-400 bg-gray-100 dark:bg-gray-800 px-2 py-1 rounded-md">{rec.category || 'Recommandation'}</span>
                </div>
                
                {#if isAlreadySub}
                  <span class="inline-flex items-center gap-1.5 px-4 py-2 min-h-[38px] text-sm font-bold text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/40 rounded-xl border border-emerald-100 dark:border-emerald-800/60 shadow-sm">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7"/></svg>
                    Abonné
                  </span>
                {:else}
                  <button
                    on:click={() => subscribeToFeed(rec.url, rec.category, rec.language)}
                    disabled={subscribingMap[rec.url]}
                    class="px-4 py-2 min-h-[38px] bg-gradient-to-r from-gray-900 to-gray-800 hover:from-black hover:to-gray-900 dark:from-white dark:to-gray-100 dark:hover:from-gray-100 dark:hover:to-gray-200 text-white dark:text-gray-900 font-bold text-sm rounded-xl shadow-md hover:shadow-lg hover:scale-[1.02] active:scale-[0.98] transition-all flex items-center gap-2 disabled:opacity-50 disabled:hover:scale-100"
                  >
                    {#if subscribingMap[rec.url]}
                      <svg class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
                    {/if}
                    + S'abonner
                  </button>
                {/if}
              </div>
            </div>
          {/each}
        </div>
      </div>
    {/if}

    <!-- ── Header ── -->
    <div>
      <h1 class="text-2xl font-bold text-gray-900 dark:text-white">Sources</h1>
      <p class="mt-1 text-sm text-gray-500 dark:text-gray-400">
        Explorez le catalogue ou saisissez une URL pour détecter un flux RSS.
      </p>
    </div>

    <!-- ── Unified Search Block ── -->
    <div class="space-y-2.5">

      <!-- Search bar row -->
      <div class="flex items-center gap-2">
        <!-- Input -->
        <div class="relative flex-1">
          <!-- Icon: magnifier (catalog) or pin (web) -->
          {#if isWebMode}
            <span class="absolute left-3.5 top-1/2 -translate-y-1/2 text-sm pointer-events-none select-none">📍</span>
          {:else}
            <svg class="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
            </svg>
          {/if}
          <input
            type="text"
            placeholder={searchPlaceholder}
            bind:value={searchQuery}
            on:input={handleSearchInput}
            on:keydown={handleKeydown}
            class="w-full bg-white dark:bg-dark-card text-gray-900 dark:text-white border rounded-xl py-2.5 pl-10 pr-4 text-sm focus:ring-2 focus:outline-none transition-all placeholder:text-gray-400 dark:placeholder:text-gray-500
              {isWebMode
                ? 'border-primary-300 dark:border-primary-700 focus:ring-primary-500 focus:border-transparent'
                : 'border-gray-200 dark:border-gray-700 focus:ring-primary-500 focus:border-transparent'}"
          />
        </div>

        <!-- Catalog-only filters (hidden in web mode) -->
        {#if !isWebMode}
          <select
            bind:value={selectedCategory}
            on:change={() => selectCategory(selectedCategory)}
            class="bg-white dark:bg-dark-card text-gray-700 dark:text-gray-300 border border-gray-200 dark:border-gray-700 rounded-xl py-2.5 px-3 text-sm focus:ring-2 focus:ring-primary-500 focus:outline-none"
          >
            {#each categories as cat}
              <option value={cat}>{cat === 'Tous' ? 'Catégorie' : cat}</option>
            {/each}
          </select>

          <select
            bind:value={selectedLanguageFilter}
            on:change={() => selectLanguage(selectedLanguageFilter)}
            class="bg-white dark:bg-dark-card text-gray-700 dark:text-gray-300 border border-gray-200 dark:border-gray-700 rounded-xl py-2.5 px-3 text-sm focus:ring-2 focus:ring-primary-500 focus:outline-none"
          >
            {#each languages as lang}
              <option value={lang.code}>{lang.label}</option>
            {/each}
          </select>
        {/if}

        <!-- Action button: shown when URL detected OR in web mode -->
        {#if isWebMode || isUrlMode}
          <button
            on:click={handleActionClick}
            disabled={discoveringFeed || searchingLocal}
            class="px-4 py-2.5 font-semibold text-sm rounded-xl shadow-sm transition-all flex items-center gap-1.5 shrink-0 disabled:opacity-50
              {isWebMode ? 'bg-primary-500 hover:bg-primary-600 text-white' : 'bg-primary-500 hover:bg-primary-600 text-white'}"
          >
            {#if discoveringFeed || searchingLocal}
              <svg class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
              {isWebMode ? 'Recherche…' : 'Détection…'}
            {:else if isWebMode}
              Chercher
            {:else}
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/></svg>
              Détecter
            {/if}
          </button>
        {/if}

        <!-- Mode toggle -->
        <div class="flex items-center gap-1.5 select-none shrink-0" title="Recherche de médias et contenus via LangSearch">
          <button
            role="switch"
            aria-checked={isWebMode}
            on:click={toggleMode}
            style="width:32px;height:18px;"
            class="relative rounded-full transition-colors duration-200 focus:outline-none cursor-pointer {isWebMode ? 'bg-primary-500' : 'bg-gray-300 dark:bg-gray-600'}"
          >
            <span
              style="width:14px;height:14px;"
              class="absolute top-0.5 left-0.5 rounded-full bg-white shadow transition-transform duration-200 {isWebMode ? 'translate-x-3.5' : 'translate-x-0'}"
            />
          </button>
          <span class="text-xs text-gray-500 dark:text-gray-400 cursor-pointer" on:click={toggleMode}>Recherche web</span>
        </div>
      </div>

      <!-- Sub-row: tags (catalog mode) OR region suggestions (web mode) -->
      {#if isWebMode}
        <!-- Region suggestions -->
        <div class="flex items-center gap-1.5 flex-wrap">
          <span class="text-xs text-gray-400 dark:text-gray-500 shrink-0">Explorer :</span>
          {#each localSuggestions as pill}
            <button
              on:click={() => selectSuggestion(pill)}
              class="px-2.5 py-1 text-xs bg-white dark:bg-dark-card border border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-300 hover:border-primary-400 hover:text-primary-500 rounded-lg font-medium transition-all"
            >
              {pill}
            </button>
          {/each}
        </div>
      {:else if availableTags && availableTags.length > 0}
        <!-- Tag pills -->
        <div class="flex items-center gap-1.5 overflow-x-auto pb-0.5 scrollbar-thin">
          <button
            on:click={() => selectTag('Tous')}
            class="px-2.5 py-1 text-xs rounded-lg font-medium transition-all shrink-0 {selectedTag === 'Tous' ? 'bg-primary-500 text-white' : 'bg-white dark:bg-dark-card text-gray-600 dark:text-gray-300 border border-gray-200 dark:border-gray-700 hover:border-gray-300'}"
          >
            Tous
          </button>
          {#each availableTags as tagObj}
            <button
              on:click={() => selectTag(tagObj.name)}
              class="px-2.5 py-1 text-xs rounded-lg font-medium transition-all shrink-0 flex items-center gap-1 {selectedTag === tagObj.name ? 'bg-primary-500 text-white' : 'bg-white dark:bg-dark-card text-gray-600 dark:text-gray-300 border border-gray-200 dark:border-gray-700 hover:border-gray-300'}"
            >
              {tagObj.name}<span class="opacity-50 text-[10px]">{tagObj.count}</span>
            </button>
          {/each}
        </div>
      {/if}
    </div>

    <!-- ══════════ RESULTS AREA ══════════ -->

    <!-- Auto-discovery feedback -->
    {#if discoveringFeed}
      <div class="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
        <svg class="w-4 h-4 animate-spin text-primary-500 shrink-0" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
        Analyse du site en cours…
      </div>
    {:else if discoveryError}
      <div class="p-3.5 bg-rose-50 dark:bg-rose-950/30 border border-rose-200 dark:border-rose-800/60 rounded-xl flex items-center justify-between text-sm text-rose-600 dark:text-rose-400">
        <span>⚠️ {discoveryError}</span>
        <button on:click={() => discoveryError = null} class="text-rose-400 hover:text-rose-600 ml-3 transition-colors">✕</button>
      </div>
    {:else if discoveredFeedResult}
      {@const isAlreadySub = alreadySubscribedUrls.includes(discoveredFeedResult.feed_url.toLowerCase()) || subscribedSuccessMap[discoveredFeedResult.feed_url]}
      <div class="p-4 bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800/60 rounded-xl flex items-center justify-between gap-4">
        <div class="flex items-center gap-3 min-w-0">
          <img src={discoveredFeedResult.icon_url} alt="" class="w-9 h-9 rounded-lg bg-white border border-emerald-100 dark:border-emerald-800 object-contain shrink-0 p-1" />
          <div class="min-w-0">
            <div class="text-[10px] font-bold text-emerald-600 dark:text-emerald-400 uppercase tracking-wider mb-0.5">Flux RSS détecté</div>
            <h3 class="font-bold text-sm text-gray-900 dark:text-white truncate">{discoveredFeedResult.title}</h3>
            {#if discoveredFeedResult.description}
              <p class="text-xs text-gray-500 dark:text-gray-400 truncate">{discoveredFeedResult.description}</p>
            {/if}
          </div>
        </div>
        {#if isAlreadySub}
          <span class="px-3 py-1.5 bg-emerald-100 dark:bg-emerald-900/60 text-emerald-700 dark:text-emerald-300 font-semibold text-xs rounded-lg shrink-0">✓ Abonné</span>
        {:else}
          <button
            on:click={() => subscribeToFeed(discoveredFeedResult.feed_url, 'Général', 'fr')}
            disabled={subscribingMap[discoveredFeedResult.feed_url]}
            class="px-4 py-1.5 bg-emerald-600 hover:bg-emerald-700 text-white font-semibold text-sm rounded-lg shadow-sm transition-all shrink-0 disabled:opacity-50"
          >+ S'abonner</button>
        {/if}
      </div>

      {#if discoveredFeedResult.preview_articles?.length > 0}
        <div class="grid grid-cols-1 md:grid-cols-3 gap-2">
          {#each discoveredFeedResult.preview_articles as art}
            <a href={art.link} target="_blank" rel="noopener noreferrer"
              class="p-3 bg-white dark:bg-dark-card rounded-xl border border-gray-100 dark:border-gray-800 text-xs text-gray-700 dark:text-gray-300 hover:text-primary-500 transition-colors line-clamp-2 leading-relaxed"
            >{art.title}</a>
          {/each}
        </div>
      {/if}
    {/if}

    <!-- Web search results -->
    {#if isWebMode}
      {#if searchingLocal}
        <div class="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
          <svg class="w-4 h-4 animate-spin text-primary-500 shrink-0" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
          Recherche de médias locaux…
        </div>
      {:else if localNewsError}
        <div class="p-3 bg-amber-50 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-800/40 rounded-xl text-xs text-amber-600 dark:text-amber-400">
          ⚠️ {localNewsError}
        </div>
      {:else if localNewsResults.length > 0}
        <div class="space-y-3">
          <div class="flex items-center justify-between">
            <span class="text-sm font-semibold text-gray-700 dark:text-gray-300">{localNewsResults.length} médias locaux trouvés</span>
            <button on:click={() => { localNewsResults = []; searchQuery = ''; }} class="text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 transition-colors">Effacer</button>
          </div>
          <div class="grid grid-cols-1 md:grid-cols-2 gap-3">
            {#each localNewsResults as item}
              <div class="bg-white dark:bg-dark-card border border-gray-100 dark:border-gray-800 rounded-xl p-4 flex items-center gap-3">
                <img src={item.favicon} alt="" class="w-8 h-8 rounded-lg object-cover shrink-0"
                  on:error={(e) => e.target.src = 'https://www.google.com/s2/favicons?domain=' + item.site_url}
                />
                <div class="flex-1 min-w-0">
                  <h3 class="font-semibold text-sm text-gray-900 dark:text-white truncate">{item.title}</h3>
                  {#if item.description}
                    <p class="text-xs text-gray-500 dark:text-gray-400 line-clamp-1 mt-0.5">{item.description}</p>
                  {/if}
                </div>
                {#if item.already_subscribed || subscribedSuccessMap[item.feed_url]}
                  <span class="text-xs font-semibold text-emerald-500 shrink-0">✓</span>
                {:else}
                  <button
                    on:click={() => subscribeToFeed(item.feed_url, 'Général', 'fr')}
                    disabled={subscribingMap[item.feed_url]}
                    class="px-3 py-1.5 bg-primary-500 hover:bg-primary-600 text-white font-semibold text-xs rounded-lg transition-all shrink-0 disabled:opacity-50"
                  >{subscribingMap[item.feed_url] ? '…' : '+ Ajouter'}</button>
                {/if}
              </div>
            {/each}
          </div>
        </div>
      {/if}
    {/if}

    <!-- ── Catalog Section (hidden in web mode) ── -->
    {#if !isWebMode}
      <div class="space-y-4">
        <div class="flex items-center justify-between">
          <h2 class="text-sm font-semibold text-gray-700 dark:text-gray-300">
            Catalogue
            {#if !loadingCatalog}
              <span class="ml-1.5 text-gray-400 dark:text-gray-500 font-normal">{catalogFeeds.length} / {totalFeedsCount}</span>
            {/if}
          </h2>
          {#if loadingCatalog}
            <span class="text-xs text-gray-400 dark:text-gray-500 animate-pulse">Chargement…</span>
          {/if}
        </div>

        {#if catalogFeeds.length === 0 && !loadingCatalog}
          <div class="py-16 text-center space-y-2">
            <div class="text-3xl">🔍</div>
            <p class="text-sm font-semibold text-gray-700 dark:text-gray-300">Aucun résultat</p>
            <p class="text-xs text-gray-400 dark:text-gray-500">Modifiez les filtres ou entrez un domaine pour l'auto-détection.</p>
          </div>
        {:else}
          {#each Object.entries(groupedCatalogFeeds) as [categoryName, categoryFeeds]}
            <div class="mt-8 mb-4">
              <h3 class="text-lg font-bold text-gray-900 dark:text-white mb-2 flex items-center gap-2">
                <span class="w-2 h-6 bg-primary-500 rounded-full"></span>
                {categoryName}
                <span class="text-xs text-gray-400 font-normal ml-2">({categoryFeeds.length})</span>
              </h3>
            </div>
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {#each categoryFeeds as feed}
                {@const isAlreadySubscribed = alreadySubscribedUrls.includes((feed.url || '').toLowerCase()) || subscribedSuccessMap[feed.url]}

                <div class="group bg-white dark:bg-dark-card border border-gray-100 dark:border-gray-800 rounded-xl p-4 hover:border-gray-200 dark:hover:border-gray-700 hover:shadow-sm transition-all flex flex-col gap-3 relative">
                  
                  <!-- Tooltip explicatif (visible au hover via une classe ou un title global, ici sur le titre) -->
                  <!-- Feed header -->
                  <div class="flex items-start gap-3">
                    <img
                      src={feed.icon_url || `https://www.google.com/s2/favicons?domain=${feed.site_url || feed.url}&sz=128`}
                      alt=""
                      class="w-10 h-10 md:w-9 md:h-9 rounded-lg object-contain bg-gray-100 dark:bg-gray-800 p-0.5 shrink-0"
                      on:error={(e) => e.target.src = 'https://www.google.com/s2/favicons?domain=rss.com&sz=128'}
                    />
                    <div class="flex-1 min-w-0">
                      <h3 class="font-semibold text-sm md:text-[15px] text-gray-900 dark:text-white leading-snug line-clamp-2" title={feed.description || feed.title}>
                        {feed.title}
                      </h3>
                      <div class="flex items-center gap-1.5 mt-1 flex-wrap">
                        <span class="text-[10px] md:text-[11px] text-gray-400">{getCountryFlag(feed.country, feed.language)}</span>
                        <span class="text-[10px] md:text-[11px] text-gray-400 uppercase tracking-wide">{feed.category || 'Général'}</span>
                        {#each getTrustBadges(feed) as badge}
                          <span class="text-[10px] font-bold px-1.5 py-0.5 rounded-md border {badge.class}">
                            {badge.text}
                          </span>
                        {/each}
                        {#if feed.is_full_text}
                          <span class="text-[10px] md:text-[11px] font-medium text-emerald-600 dark:text-emerald-400">· Natif</span>
                        {:else}
                          <span class="text-[10px] md:text-[11px] font-medium text-indigo-500 dark:text-indigo-400">· Scrapé</span>
                        {/if}
                      </div>
                    </div>
                  </div>

                  <!-- Description enrichie / Présentation 1-2 phrases -->
                  <p class="text-xs md:text-sm text-gray-500 dark:text-gray-400 leading-relaxed line-clamp-3">
                    {feed.description || `Flux d'actualité et de veille d'information spécialisé en ${feed.category || 'Général'}.`}
                  </p>

                  <!-- Tags -->
                  {#if feed.tags && feed.tags.length > 0}
                    <div class="flex flex-wrap gap-1.5">
                      {#each feed.tags.slice(0, 3) as tag}
                        <button
                          on:click={() => selectTag(tag)}
                          class="text-[10px] md:text-xs font-medium text-gray-500 dark:text-gray-400 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 px-2 py-1 rounded-md transition-all min-h-[32px] min-w-[32px] flex items-center"
                        >#{tag.replace(/^#+/, '')}</button>
                      {/each}
                    </div>
                  {/if}

                  <!-- Actions -->
                  <div class="flex items-center gap-3 pt-2 border-t border-gray-50 dark:border-gray-800/60 mt-auto">
                    <button
                      on:click={() => openPreview(feed)}
                      class="p-2 md:p-1.5 rounded-lg text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 transition-all min-h-[44px] min-w-[44px] flex items-center justify-center"
                      title="Aperçu des articles"
                    >
                      <svg class="w-5 h-5 md:w-4 md:h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>
                      </svg>
                    </button>

                    <div class="flex-1"/>

                    {#if isAlreadySubscribed}
                      <span class="inline-flex items-center gap-1 px-3 py-2 md:py-1.5 text-xs md:text-sm font-semibold text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/40 rounded-xl md:rounded-lg border border-emerald-100 dark:border-emerald-800/60 min-h-[44px] md:min-h-0 flex items-center">
                        <svg class="w-4 h-4 md:w-3.5 md:h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7"/></svg>
                        Abonné
                      </span>
                    {:else}
                      <button
                        on:click={() => subscribeToFeed(feed.url, feed.category, feed.language)}
                        disabled={subscribingMap[feed.url]}
                        class="px-4 py-2 md:py-1.5 bg-primary-500 hover:bg-primary-600 text-white font-semibold text-xs md:text-sm rounded-xl md:rounded-lg shadow-sm transition-all flex items-center justify-center gap-2 disabled:opacity-50 min-h-[44px]"
                      >
                        {#if subscribingMap[feed.url]}
                          <svg class="w-4 h-4 md:w-3.5 md:h-3.5 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
                        {/if}
                        + S'abonner
                      </button>
                    {/if}

                    {#if errorMap[feed.url]}
                      <p class="text-[10px] text-rose-500 absolute bottom-[-16px]">{errorMap[feed.url]}</p>
                    {/if}
                  </div>

                </div>
              {/each}
            </div>
          {/each}

          {#if hasMoreFeeds}
            <div class="pt-4 flex justify-center">
              <button
                on:click={loadMoreFeeds}
                disabled={loadingMore}
                class="px-6 py-2.5 bg-white dark:bg-dark-card hover:bg-gray-50 dark:hover:bg-gray-800 text-gray-700 dark:text-gray-300 font-semibold text-sm rounded-xl border border-gray-200 dark:border-gray-700 shadow-sm transition-all flex items-center gap-2 disabled:opacity-50"
              >
                {#if loadingMore}
                  <svg class="w-4 h-4 animate-spin text-primary-500" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
                  Chargement…
                {:else}
                  Voir plus <span class="text-gray-400 font-normal ml-1">({totalFeedsCount - catalogFeeds.length} restants)</span>
                {/if}
              </button>
            </div>
          {/if}
        {/if}
      </div>
    {/if}

  </div>
</div>

<!-- ═══════════════════════════════════════════════ PREVIEW MODAL ══ -->
{#if previewFeedObj}
  <!-- svelte-ignore a11y-click-events-have-key-events -->
  <!-- svelte-ignore a11y-no-static-element-interactions -->
  <div class="fixed inset-0 z-50 bg-black/50 backdrop-blur-sm flex items-center justify-center p-4" on:click|self={() => previewFeedObj = null}>
    <div class="bg-white dark:bg-dark-card border border-gray-200 dark:border-gray-800 rounded-2xl max-w-xl w-full shadow-2xl flex flex-col max-h-[80vh] overflow-hidden">

      <div class="flex items-center gap-3 px-5 py-4 border-b border-gray-100 dark:border-gray-800">
        <img
          src={previewFeedObj.icon_url || `https://www.google.com/s2/favicons?domain=${previewFeedObj.site_url || previewFeedObj.url}&sz=128`}
          alt=""
          class="w-8 h-8 rounded-lg bg-gray-100 dark:bg-gray-800 object-contain p-0.5 shrink-0"
        />
        <div class="flex-1 min-w-0">
          <h3 class="font-bold text-sm text-gray-900 dark:text-white truncate">{previewFeedObj.title}</h3>
          <p class="text-xs text-gray-400">Derniers articles</p>
        </div>
        <button
          on:click={() => previewFeedObj = null}
          class="w-7 h-7 rounded-lg bg-gray-100 dark:bg-gray-800 flex items-center justify-center text-gray-500 hover:text-gray-800 dark:hover:text-white text-xs transition-colors"
        >✕</button>
      </div>

      <div class="flex-1 overflow-y-auto px-5 py-4 space-y-3">
        {#if previewLoading}
          <div class="py-10 flex items-center justify-center gap-2 text-sm text-gray-400">
            <svg class="w-4 h-4 animate-spin text-primary-500" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
            Chargement…
          </div>
        {:else if previewError}
          <div class="p-3 bg-rose-50 dark:bg-rose-950/30 text-rose-600 dark:text-rose-400 text-xs rounded-xl text-center">⚠️ {previewError}</div>
        {:else if previewArticles.length === 0}
          <div class="py-8 text-center text-xs text-gray-400">Aucun article disponible.</div>
        {:else}
          {#each previewArticles as art}
            <div class="p-3 bg-gray-50 dark:bg-dark-bg rounded-xl border border-gray-100 dark:border-gray-800 space-y-1">
              <div class="flex items-start justify-between gap-2">
                <a href={art.link} target="_blank" rel="noopener noreferrer"
                  class="font-semibold text-sm text-gray-900 dark:text-white hover:text-primary-500 transition-colors leading-snug line-clamp-2"
                >{art.title}</a>
                {#if art.published}
                  <span class="text-[10px] text-gray-400 shrink-0">{art.published.slice(0, 10)}</span>
                {/if}
              </div>
              {#if art.summary}
                <p class="text-xs text-gray-500 dark:text-gray-400 leading-relaxed line-clamp-3">{art.summary}</p>
              {/if}
            </div>
          {/each}
        {/if}
      </div>

      <div class="flex items-center justify-end gap-2 px-5 py-3 border-t border-gray-100 dark:border-gray-800">
        <button
          on:click={() => previewFeedObj = null}
          class="px-4 py-2 bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 font-semibold text-sm rounded-lg hover:bg-gray-200 dark:hover:bg-gray-700 transition-colors"
        >Fermer</button>

        {#if alreadySubscribedUrls.includes((previewFeedObj.url || '').toLowerCase()) || subscribedSuccessMap[previewFeedObj.url]}
          <span class="px-4 py-2 bg-emerald-50 dark:bg-emerald-950/40 text-emerald-600 font-semibold text-sm rounded-lg border border-emerald-100 dark:border-emerald-800">✓ Abonné</span>
        {:else}
          <button
            on:click={() => { subscribeToFeed(previewFeedObj.url, previewFeedObj.category, previewFeedObj.language); previewFeedObj = null; }}
            class="px-4 py-2 bg-primary-500 hover:bg-primary-600 text-white font-semibold text-sm rounded-lg shadow-sm transition-all"
          >+ S'abonner</button>
        {/if}
      </div>

    </div>
  </div>
{/if}
