<script>
  import { onMount } from 'svelte';
  import { fetchFeeds, fetchArticles, feedsList, langsearchApiKey } from '../stores/appState.js';

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

  const categories = ['Tous', 'Suisse', 'Monde', 'Technologie', 'Chrétien', 'Science', 'Général'];
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

  $: alreadySubscribedUrls = $feedsList.map(f => (f.url || '').toLowerCase());
  $: isWebMode = searchMode === 'web';
  $: isUrlMode = searchMode === 'catalog' && isUrlCandidate(searchQuery);
  $: searchPlaceholder = isWebMode
    ? 'Chercher par sujet, région, thème… (ex : cybersécurité, Vaud, climat)'
    : 'Rechercher un sujet, un site ou coller un lien RSS…';

  let searchTimeout = null;

  onMount(() => {
    loadTags();
    loadCatalog(true);
  });

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
<div class="flex-1 h-full overflow-y-auto bg-gray-50 dark:bg-dark-bg">
  <div class="max-w-5xl mx-auto px-6 md:px-10 py-10 space-y-8">

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
          <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {#each catalogFeeds as feed}
              {@const isAlreadySubscribed = alreadySubscribedUrls.includes((feed.url || '').toLowerCase()) || subscribedSuccessMap[feed.url]}

              <div class="group bg-white dark:bg-dark-card border border-gray-100 dark:border-gray-800 rounded-xl p-4 hover:border-gray-200 dark:hover:border-gray-700 hover:shadow-sm transition-all flex flex-col gap-3">

                <!-- Feed header -->
                <div class="flex items-start gap-3">
                  <img
                    src={feed.icon_url || `https://www.google.com/s2/favicons?domain=${feed.site_url || feed.url}&sz=128`}
                    alt=""
                    class="w-9 h-9 rounded-lg object-contain bg-gray-100 dark:bg-gray-800 p-0.5 shrink-0"
                    on:error={(e) => e.target.src = 'https://www.google.com/s2/favicons?domain=rss.com&sz=128'}
                  />
                  <div class="flex-1 min-w-0">
                    <h3 class="font-semibold text-sm text-gray-900 dark:text-white leading-snug line-clamp-2">
                      {feed.title}
                    </h3>
                    <div class="flex items-center gap-1.5 mt-1 flex-wrap">
                      <span class="text-[10px] text-gray-400">{getCountryFlag(feed.country, feed.language)}</span>
                      <span class="text-[10px] text-gray-400 uppercase tracking-wide">{feed.category || 'Général'}</span>
                      {#if feed.is_full_text}
                        <span class="text-[10px] font-medium text-emerald-600 dark:text-emerald-400">· Natif</span>
                      {:else}
                        <span class="text-[10px] font-medium text-indigo-500 dark:text-indigo-400">· Scrapé</span>
                      {/if}
                    </div>
                  </div>
                </div>

                <!-- Description -->
                {#if feed.description}
                  <p class="text-xs text-gray-500 dark:text-gray-400 leading-relaxed line-clamp-2">
                    {feed.description}
                  </p>
                {/if}

                <!-- Tags -->
                {#if feed.tags && feed.tags.length > 0}
                  <div class="flex flex-wrap gap-1">
                    {#each feed.tags.slice(0, 3) as tag}
                      <button
                        on:click={() => selectTag(tag)}
                        class="text-[10px] font-medium text-gray-500 dark:text-gray-400 bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 px-2 py-0.5 rounded-md transition-all"
                      >#{tag}</button>
                    {/each}
                  </div>
                {/if}

                <!-- Actions -->
                <div class="flex items-center gap-2 pt-1 border-t border-gray-50 dark:border-gray-800/60 mt-auto">
                  <button
                    on:click={() => openPreview(feed)}
                    class="p-1.5 rounded-lg text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 transition-all"
                    title="Aperçu des articles"
                  >
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>
                    </svg>
                  </button>

                  <div class="flex-1"/>

                  {#if isAlreadySubscribed}
                    <span class="inline-flex items-center gap-1 px-3 py-1.5 text-xs font-semibold text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-950/40 rounded-lg border border-emerald-100 dark:border-emerald-800/60">
                      <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7"/></svg>
                      Abonné
                    </span>
                  {:else}
                    <button
                      on:click={() => subscribeToFeed(feed.url, feed.category, feed.language)}
                      disabled={subscribingMap[feed.url]}
                      class="px-3 py-1.5 bg-primary-500 hover:bg-primary-600 text-white font-semibold text-xs rounded-lg shadow-sm transition-all flex items-center gap-1 disabled:opacity-50"
                    >
                      {#if subscribingMap[feed.url]}
                        <svg class="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
                      {/if}
                      + S'abonner
                    </button>
                  {/if}

                  {#if errorMap[feed.url]}
                    <p class="text-[10px] text-rose-500">{errorMap[feed.url]}</p>
                  {/if}
                </div>

              </div>
            {/each}
          </div>

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
