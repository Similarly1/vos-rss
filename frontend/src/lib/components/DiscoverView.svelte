<script>
  import { onMount } from 'svelte';
  import { fetchFeeds, fetchArticles, feedsList } from '../stores/appState.js';

  let searchQuery = '';
  let selectedCategory = 'Tous';
  let selectedTag = 'Tous';
  let selectedLanguageFilter = 'Tous';

  let catalogFeeds = [];
  let availableTags = [];
  let loadingCatalog = false;
  let loadingMore = false;

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
  let subscribingMap = {}; // { [url]: bool }
  let subscribedSuccessMap = {}; // { [url]: bool }
  let errorMap = {}; // { [url]: string }

  const categories = ['Tous', 'Suisse', 'Monde', 'Technologie', 'Chrétien', 'Science', 'Général'];
  const languages = [
    { code: 'Tous', label: 'Toutes les langues' },
    { code: 'fr', label: '🇫🇷 Français' },
    { code: 'en', label: '🇬🇧 Anglais' },
    { code: 'de', label: '🇩🇪 Allemand' },
    { code: 'es', label: '🇪🇸 Espagnol' }
  ];

  $: alreadySubscribedUrls = $feedsList.map(f => (f.url || '').toLowerCase());

  // Debounce search timer
  let searchTimeout = null;

  onMount(() => {
    loadTags();
    loadCatalog(true);
  });

  async function loadTags() {
    try {
      const res = await fetch('/api/catalog/tags');
      if (res.ok) {
        availableTags = await res.json();
      }
    } catch (e) {
      console.error('Erreur chargement tags catalog:', e);
    }
  }

  async function loadCatalog(reset = true) {
    if (reset) {
      currentOffset = 0;
      loadingCatalog = true;
    } else {
      loadingMore = true;
    }

    try {
      const params = new URLSearchParams();
      if (searchQuery.trim() && !isUrlCandidate(searchQuery.trim())) {
        params.append('q', searchQuery.trim());
      }
      if (selectedCategory !== 'Tous') {
        params.append('category', selectedCategory);
      }
      if (selectedTag !== 'Tous') {
        params.append('tag', selectedTag);
      }
      if (selectedLanguageFilter !== 'Tous') {
        params.append('language', selectedLanguageFilter);
      }
      params.append('limit', limit.toString());
      params.append('offset', currentOffset.toString());

      const res = await fetch(`/api/catalog?${params.toString()}`);
      if (res.ok) {
        const data = await res.json();
        const newFeeds = data.feeds || [];
        totalFeedsCount = data.total || 0;
        hasMoreFeeds = data.has_more || false;

        if (reset) {
          catalogFeeds = newFeeds;
        } else {
          catalogFeeds = [...catalogFeeds, ...newFeeds];
        }
      }
    } catch (e) {
      console.error('Erreur chargement catalogue:', e);
    } finally {
      loadingCatalog = false;
      loadingMore = false;
    }
  }

  function loadMoreFeeds() {
    if (hasMoreFeeds && !loadingMore) {
      currentOffset += limit;
      loadCatalog(false);
    }
  }

  function isUrlCandidate(str) {
    const s = str.trim().toLowerCase();
    return s.startsWith('http://') || s.startsWith('https://') || (s.includes('.') && !s.includes(' ') && s.length > 4);
  }

  function handleSearchInput() {
    discoveredFeedResult = null;
    discoveryError = null;
    clearTimeout(searchTimeout);

    searchTimeout = setTimeout(() => {
      loadCatalog(true);
    }, 250);
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
      if (res.ok) {
        discoveredFeedResult = data;
      } else {
        discoveryError = data.detail || "Impossible d'auto-détecter un flux RSS sur ce domaine.";
      }
    } catch (err) {
      discoveryError = "Erreur de connexion lors de l'auto-détection.";
    } finally {
      discoveringFeed = false;
    }
  }

  function handleKeydown(e) {
    if (e.key === 'Enter') {
      if (isUrlCandidate(searchQuery)) {
        triggerAutoDiscovery();
      } else {
        loadCatalog(true);
      }
    }
  }

  function selectTag(tagName) {
    if (selectedTag === tagName) {
      selectedTag = 'Tous';
    } else {
      selectedTag = tagName;
    }
    loadCatalog(true);
  }

  function selectCategory(cat) {
    selectedCategory = cat;
    loadCatalog(true);
  }

  function selectLanguage(langCode) {
    selectedLanguageFilter = langCode;
    loadCatalog(true);
  }

  async function subscribeToFeed(feedUrl, category = 'Général', language = 'fr') {
    subscribingMap[feedUrl] = true;
    errorMap[feedUrl] = null;
    subscribingMap = { ...subscribingMap };

    try {
      const res = await fetch('/api/feeds', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          url: feedUrl,
          category: category || 'Général',
          language: language || 'fr'
        })
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
    } catch (err) {
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
      if (res.ok) {
        previewArticles = data.articles || [];
      } else {
        previewError = data.detail || "Impossible de charger l'aperçu.";
      }
    } catch (e) {
      previewError = "Erreur de connexion lors du chargement de l'aperçu.";
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

<div class="flex-1 h-full overflow-y-auto bg-gray-50 dark:bg-dark-bg p-6 md:p-10 space-y-8">
  <div class="max-w-6xl mx-auto space-y-8">
    
    <!-- Header -->
    <div class="space-y-3">
      <div class="inline-flex items-center gap-2 px-3.5 py-1.5 bg-sky-100 dark:bg-slate-800 text-sky-800 dark:text-sky-300 rounded-full text-xs font-bold border border-sky-200 dark:border-slate-700">
        <span>✨ Catalogue & Auto-Détection Web</span>
      </div>
      <h1 class="text-3xl font-extrabold text-gray-900 dark:text-white tracking-tight">Catalogue des flux RSS</h1>
      <p class="text-sm text-gray-500 dark:text-dark-muted max-w-2xl">
        Explorez plus de 150+ médias certifiés et répertoires d'annuaires ou tapez l'adresse d'un site web (ex: <span class="font-mono text-primary-600 dark:text-primary-400">lemonde.fr</span>) pour détecter automatiquement son flux RSS.
      </p>
    </div>

    <!-- Search & Auto-Discovery Bar -->
    <div class="bg-white dark:bg-dark-card p-4 md:p-5 rounded-3xl border border-gray-100 dark:border-gray-800 shadow-sm space-y-4">
      
      <div class="flex flex-col md:flex-row items-stretch md:items-center gap-3">
        <!-- Search Input -->
        <div class="relative flex-1">
          <svg class="w-5 h-5 absolute left-4 top-3.5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path>
          </svg>
          <input 
            type="text" 
            placeholder="Rechercher par mot-clé ou saisir une URL/domaine (ex: krebsonsecurity.com)..." 
            bind:value={searchQuery}
            on:input={handleSearchInput}
            on:keydown={handleKeydown}
            class="w-full bg-gray-50 dark:bg-dark-bg text-gray-900 dark:text-white border border-gray-200 dark:border-gray-700 rounded-2xl py-3 pl-12 pr-4 text-sm focus:ring-2 focus:ring-primary-500 focus:outline-none transition-all placeholder:text-gray-400 dark:placeholder:text-gray-500"
          />
        </div>

        <!-- Action Button (Auto-Discovery or Search) -->
        {#if isUrlCandidate(searchQuery)}
          <button
            on:click={triggerAutoDiscovery}
            disabled={discoveringFeed}
            class="px-6 py-3 bg-primary-500 hover:bg-primary-600 text-white font-extrabold text-xs rounded-2xl shadow-sm transition-all flex items-center justify-center gap-2 shrink-0 disabled:opacity-50"
          >
            {#if discoveringFeed}
              <svg class="w-4 h-4 animate-spin text-white" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path></svg>
              <span>Détection RSS...</span>
            {:else}
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>
              <span>Détecter le flux RSS</span>
            {/if}
          </button>
        {/if}

        <!-- Dropdown Filters -->
        <div class="flex items-center gap-2.5 shrink-0">
          <select 
            bind:value={selectedCategory}
            on:change={() => selectCategory(selectedCategory)}
            class="bg-gray-50 dark:bg-dark-bg text-gray-900 dark:text-white border border-gray-200 dark:border-gray-700 rounded-2xl py-3 px-3.5 text-xs font-semibold focus:ring-2 focus:ring-primary-500 focus:outline-none"
          >
            {#each categories as cat}
              <option value={cat}>{cat === 'Tous' ? 'Toutes catégories' : cat}</option>
            {/each}
          </select>

          <select 
            bind:value={selectedLanguageFilter}
            on:change={() => selectLanguage(selectedLanguageFilter)}
            class="bg-gray-50 dark:bg-dark-bg text-gray-900 dark:text-white border border-gray-200 dark:border-gray-700 rounded-2xl py-3 px-3.5 text-xs font-semibold focus:ring-2 focus:ring-primary-500 focus:outline-none"
          >
            {#each languages as lang}
              <option value={lang.code}>{lang.label}</option>
            {/each}
          </select>
        </div>
      </div>

      <!-- Hashtags Pill Bar -->
      {#if availableTags && availableTags.length > 0}
        <div class="pt-3 border-t border-gray-100 dark:border-gray-800 flex items-center gap-2 overflow-x-auto pb-1 scrollbar-thin">
          <span class="text-[11px] font-bold text-gray-400 dark:text-gray-500 uppercase tracking-wider shrink-0">Tags :</span>
          
          <button 
            on:click={() => selectTag('Tous')}
            class="px-3 py-1.5 text-xs rounded-xl font-bold transition-all shrink-0 border {selectedTag === 'Tous' ? 'bg-primary-500 text-white border-primary-500 shadow-sm' : 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-200 border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'}"
          >
            #Tous
          </button>

          {#each availableTags as tagObj}
            <button 
              on:click={() => selectTag(tagObj.name)}
              class="px-3 py-1.5 text-xs rounded-xl font-bold transition-all shrink-0 border flex items-center gap-1.5 {selectedTag === tagObj.name ? 'bg-primary-500 text-white border-primary-500 shadow-sm' : 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-200 border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'}"
            >
              <span>{tagObj.name}</span>
              <span class="text-[10px] opacity-80 px-1.5 py-0.5 rounded-full bg-black/10 dark:bg-white/15">{tagObj.count}</span>
            </button>
          {/each}
        </div>
      {/if}

    </div>

    <!-- Auto-Discovery Results Alert -->
    {#if discoveringFeed}
      <div class="p-6 bg-primary-50/50 dark:bg-primary-950/30 border border-primary-200 dark:border-primary-800/80 rounded-3xl flex items-center gap-4 animate-pulse">
        <svg class="w-6 h-6 animate-spin text-primary-500" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path></svg>
        <div>
          <h4 class="font-extrabold text-sm text-gray-900 dark:text-white">Analyse du site web en cours...</h4>
          <p class="text-xs text-gray-500 dark:text-gray-400">Recherche des balises XML RSS/Atom et test des chemins d'accès standards.</p>
        </div>
      </div>
    {:else if discoveryError}
      <div class="p-4 bg-rose-50 dark:bg-rose-950/30 border border-rose-200 dark:border-rose-800/80 rounded-2xl flex items-center justify-between text-xs text-rose-600 dark:text-rose-400 font-semibold">
        <span>⚠️ {discoveryError}</span>
        <button on:click={() => discoveryError = null} class="underline text-rose-500 hover:text-rose-700">Fermer</button>
      </div>
    {:else if discoveredFeedResult}
      {@const isAlreadySub = alreadySubscribedUrls.includes(discoveredFeedResult.feed_url.toLowerCase()) || subscribedSuccessMap[discoveredFeedResult.feed_url]}
      
      <div class="p-6 bg-emerald-50/80 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 rounded-3xl space-y-4 shadow-sm">
        <div class="flex items-start justify-between gap-4">
          <div class="flex items-center gap-3">
            <img src={discoveredFeedResult.icon_url} alt="Icon" class="w-10 h-10 rounded-xl bg-white p-1 border border-emerald-200 dark:border-emerald-800 object-contain" />
            <div>
              <div class="inline-flex items-center gap-1.5 px-2.5 py-0.5 bg-emerald-100 dark:bg-emerald-900/60 text-emerald-800 dark:text-emerald-300 rounded-full text-[10px] font-bold">
                ⚡ Flux RSS Détecté en Direct !
              </div>
              <h3 class="text-lg font-extrabold text-gray-900 dark:text-white leading-tight mt-1">{discoveredFeedResult.title}</h3>
              <p class="text-xs text-gray-600 dark:text-gray-300">{discoveredFeedResult.description}</p>
            </div>
          </div>

          <div class="shrink-0">
            {#if isAlreadySub}
              <span class="px-4 py-2 bg-emerald-500 text-white font-bold text-xs rounded-2xl inline-flex items-center gap-1">
                ✓ Abonné
              </span>
            {:else}
              <button 
                on:click={() => subscribeToFeed(discoveredFeedResult.feed_url, 'Général', 'fr')}
                disabled={subscribingMap[discoveredFeedResult.feed_url]}
                class="px-5 py-2.5 bg-emerald-600 hover:bg-emerald-700 text-white font-extrabold text-xs rounded-2xl shadow-sm transition-all flex items-center gap-1.5"
              >
                + S'abonner à ce flux
              </button>
            {/if}
          </div>
        </div>

        {#if discoveredFeedResult.preview_articles && discoveredFeedResult.preview_articles.length > 0}
          <div class="pt-3 border-t border-emerald-200/60 dark:border-emerald-800/60 space-y-2">
            <span class="text-[11px] font-extrabold text-emerald-800 dark:text-emerald-300 uppercase tracking-wider">Derniers articles publiés :</span>
            <div class="grid grid-cols-1 md:grid-cols-3 gap-2">
              {#each discoveredFeedResult.preview_articles as art}
                <a href={art.link} target="_blank" rel="noopener noreferrer" class="p-3 bg-white dark:bg-dark-card rounded-xl border border-emerald-100 dark:border-emerald-900/40 text-xs font-semibold text-gray-800 dark:text-gray-200 hover:text-primary-500 transition-colors line-clamp-2">
                  • {art.title}
                </a>
              {/each}
            </div>
          </div>
        {/if}
      </div>
    {/if}

    <!-- Catalog Feeds Grid -->
    <div>
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-lg font-extrabold text-gray-900 dark:text-white flex items-center gap-2">
          <span>Catalogue de médias</span>
          <span class="text-xs font-bold px-2.5 py-0.5 rounded-full bg-gray-200 dark:bg-gray-800 text-gray-700 dark:text-gray-300">
            {catalogFeeds.length} sur {totalFeedsCount}
          </span>
        </h2>

        {#if loadingCatalog}
          <span class="text-xs text-primary-500 font-bold animate-pulse">Chargement du catalogue...</span>
        {/if}
      </div>

      {#if catalogFeeds.length === 0 && !loadingCatalog}
        <div class="text-center py-16 bg-white dark:bg-dark-card rounded-3xl border border-gray-100 dark:border-gray-800 space-y-3">
          <div class="text-4xl">🔍</div>
          <h3 class="text-base font-extrabold text-gray-900 dark:text-white">Aucun flux ne correspond à votre recherche</h3>
          <p class="text-xs text-gray-500 dark:text-gray-400 max-w-sm mx-auto">
            Essayez de modifier les filtres ou tapez le nom de domaine complet d'un site dans la barre ci-dessus pour lancer l'auto-détection.
          </p>
        </div>
      {:else}
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {#each catalogFeeds as feed}
            {@const isAlreadySubscribed = alreadySubscribedUrls.includes((feed.url || '').toLowerCase()) || subscribedSuccessMap[feed.url]}

            <div class="bg-white dark:bg-dark-card border border-gray-100 dark:border-gray-800 rounded-3xl p-6 shadow-sm hover:shadow-md transition-all flex flex-col justify-between space-y-5">
              
              <div class="space-y-3">
                <!-- Header Flags & Badges -->
                <div class="flex items-center justify-between">
                  <div class="flex items-center gap-2">
                    <img 
                      src={feed.icon_url || `https://www.google.com/s2/favicons?domain=${feed.site_url || feed.url}&sz=128`} 
                      alt="Favicon"
                      class="w-6 h-6 rounded-md object-contain bg-gray-100 dark:bg-gray-800 p-0.5" 
                      on:error={(e) => e.target.src = 'https://www.google.com/s2/favicons?domain=rss.com&sz=128'}
                    />
                    <span class="text-sm font-bold">{getCountryFlag(feed.country, feed.language)}</span>
                  </div>

                  <div class="flex items-center gap-1.5">
                    <span class="text-[10px] font-bold uppercase tracking-wider px-2.5 py-1 rounded-full bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-200 border border-gray-200 dark:border-gray-700">
                      {feed.category || 'Général'}
                    </span>

                    {#if feed.is_full_text}
                      <span class="text-[10px] font-bold uppercase tracking-wider px-2.5 py-1 rounded-full bg-emerald-50 dark:bg-emerald-950/60 text-emerald-700 dark:text-emerald-300 border border-emerald-200 dark:border-emerald-800/80" title="Flux 100% natif complet">
                        ✨ Natif
                      </span>
                    {:else}
                      <span class="text-[10px] font-bold uppercase tracking-wider px-2.5 py-1 rounded-full bg-indigo-50 dark:bg-indigo-950/60 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800/80" title="Articles complets via Vos">
                        📄 Scrapé
                      </span>
                    {/if}
                  </div>
                </div>

                <!-- Feed Title & Description -->
                <h3 class="font-extrabold text-base text-gray-900 dark:text-white leading-snug">
                  {feed.title}
                </h3>

                <p class="text-xs text-gray-500 dark:text-dark-muted leading-relaxed line-clamp-3">
                  {feed.description || "Aucune description disponible pour ce flux."}
                </p>

                <!-- Tags Badges -->
                {#if feed.tags && feed.tags.length > 0}
                  <div class="flex flex-wrap gap-1.5 pt-1">
                    {#each feed.tags as tag}
                      <button 
                        on:click={() => selectTag(tag)}
                        class="text-[11px] font-extrabold text-sky-800 dark:text-sky-300 bg-sky-100 dark:bg-slate-800 border border-sky-200 dark:border-slate-700 hover:bg-sky-200 dark:hover:bg-slate-700 px-2.5 py-1 rounded-lg transition-all"
                      >
                        {tag}
                      </button>
                    {/each}
                  </div>
                {/if}
              </div>

              <!-- Footer Actions -->
              <div class="pt-3 border-t border-gray-100 dark:border-gray-800 space-y-2">
                <div class="flex items-center gap-2">
                  <button 
                    on:click={() => openPreview(feed)}
                    class="px-3.5 py-2.5 bg-gray-100 hover:bg-gray-200 dark:bg-gray-800 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-200 font-bold text-xs rounded-xl border border-gray-200 dark:border-gray-700 transition-all flex items-center justify-center gap-1.5 shrink-0"
                    title="Prévisualiser les 3 derniers articles"
                  >
                    👁️ Aperçu
                  </button>

                  {#if isAlreadySubscribed}
                    <div class="flex-1 py-2.5 px-4 bg-emerald-500/10 dark:bg-emerald-950/50 text-emerald-600 dark:text-emerald-400 font-bold text-xs rounded-xl flex items-center justify-center gap-1.5 border border-emerald-500/30 dark:border-emerald-800/80">
                      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>
                      <span>Abonné</span>
                    </div>
                  {:else}
                    <button 
                      on:click={() => subscribeToFeed(feed.url, feed.category, feed.language)}
                      disabled={subscribingMap[feed.url]}
                      class="flex-1 py-2.5 px-4 bg-primary-500 hover:bg-primary-600 text-white font-extrabold text-xs rounded-xl shadow-sm transition-all flex items-center justify-center gap-1.5 disabled:opacity-50"
                    >
                      {#if subscribingMap[feed.url]}
                        <svg class="w-4 h-4 animate-spin text-white" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path></svg>
                        <span>Abonnement...</span>
                      {:else}
                        <span>+ S'abonner</span>
                      {/if}
                    </button>
                  {/if}
                </div>

                {#if errorMap[feed.url]}
                  <p class="text-[11px] text-rose-500 text-center font-medium">{errorMap[feed.url]}</p>
                {/if}
              </div>

            </div>
          {/each}
        </div>

        <!-- Load More Pagination Button -->
        {#if hasMoreFeeds}
          <div class="pt-8 flex justify-center">
            <button
              on:click={loadMoreFeeds}
              disabled={loadingMore}
              class="px-8 py-3.5 bg-white dark:bg-dark-card hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-800 dark:text-white font-extrabold text-xs rounded-2xl border border-gray-200 dark:border-gray-700 shadow-sm transition-all flex items-center gap-2 disabled:opacity-50"
            >
              {#if loadingMore}
                <svg class="w-4 h-4 animate-spin text-primary-500" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path></svg>
                <span>Chargement des flux suivants...</span>
              {:else}
                <span>Charger plus de médias ({totalFeedsCount - catalogFeeds.length} restants)</span>
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path></svg>
              {/if}
            </button>
          </div>
        {/if}
      {/if}
    </div>

  </div>
</div>

<!-- Article Preview Modal -->
{#if previewFeedObj}
  <div class="fixed inset-0 z-50 bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
    <div class="bg-white dark:bg-dark-card border border-gray-200 dark:border-gray-800 rounded-3xl max-w-2xl w-full p-6 md:p-8 space-y-6 shadow-2xl overflow-hidden flex flex-col max-h-[85vh]">
      
      <!-- Modal Header -->
      <div class="flex items-start justify-between gap-4 pb-4 border-b border-gray-100 dark:border-gray-800">
        <div class="flex items-center gap-3">
          <img 
            src={previewFeedObj.icon_url || `https://www.google.com/s2/favicons?domain=${previewFeedObj.site_url || previewFeedObj.url}&sz=128`} 
            alt="Icon" 
            class="w-10 h-10 rounded-xl bg-gray-100 dark:bg-gray-800 p-1 object-contain"
          />
          <div>
            <h3 class="text-lg font-extrabold text-gray-900 dark:text-white leading-tight">{previewFeedObj.title}</h3>
            <p class="text-xs text-gray-500 dark:text-gray-400">Aperçu en direct des 3 derniers articles</p>
          </div>
        </div>

        <button 
          on:click={() => previewFeedObj = null}
          class="w-8 h-8 rounded-full bg-gray-100 dark:bg-gray-800 flex items-center justify-center text-gray-500 hover:text-gray-900 dark:hover:text-white transition-colors"
        >
          ✕
        </button>
      </div>

      <!-- Modal Body -->
      <div class="flex-1 overflow-y-auto space-y-4 pr-1">
        {#if previewLoading}
          <div class="text-center py-12 space-y-3">
            <svg class="w-8 h-8 animate-spin text-primary-500 mx-auto" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path></svg>
            <p class="text-xs font-bold text-gray-500">Chargement des articles en direct...</p>
          </div>
        {:else if previewError}
          <div class="p-4 bg-rose-50 dark:bg-rose-950/30 text-rose-600 dark:text-rose-400 text-xs rounded-2xl font-bold text-center">
            ⚠️ {previewError}
          </div>
        {:else if previewArticles.length === 0}
          <div class="text-center py-8 text-xs text-gray-500">
            Aucun article trouvé dans le flux XML.
          </div>
        {:else}
          <div class="space-y-4">
            {#each previewArticles as art}
              <div class="p-4 bg-gray-50 dark:bg-dark-bg rounded-2xl border border-gray-100 dark:border-gray-800 space-y-2">
                <div class="flex items-start justify-between gap-3">
                  <h4 class="font-extrabold text-sm text-gray-900 dark:text-white leading-snug">
                    <a href={art.link} target="_blank" rel="noopener noreferrer" class="hover:text-primary-500 transition-colors">
                      {art.title}
                    </a>
                  </h4>
                  {#if art.published}
                    <span class="text-[10px] font-semibold text-gray-400 shrink-0">{art.published.slice(0, 16)}</span>
                  {/if}
                </div>

                {#if art.summary}
                  <p class="text-xs text-gray-600 dark:text-gray-300 leading-relaxed line-clamp-3">
                    {art.summary}
                  </p>
                {/if}
              </div>
            {/each}
          </div>
        {/if}
      </div>

      <!-- Modal Footer -->
      <div class="pt-4 border-t border-gray-100 dark:border-gray-800 flex items-center justify-end gap-3">
        <button 
          on:click={() => previewFeedObj = null}
          class="px-5 py-2.5 bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 font-bold text-xs rounded-2xl hover:bg-gray-200 transition-colors"
        >
          Fermer
        </button>

        {#if alreadySubscribedUrls.includes((previewFeedObj.url || '').toLowerCase()) || subscribedSuccessMap[previewFeedObj.url]}
          <span class="px-5 py-2.5 bg-emerald-50 dark:bg-emerald-950/40 text-emerald-600 font-bold text-xs rounded-2xl border border-emerald-200 dark:border-emerald-800">
            ✓ Déjà abonné
          </span>
        {:else}
          <button 
            on:click={() => {
              subscribeToFeed(previewFeedObj.url, previewFeedObj.category, previewFeedObj.language);
              previewFeedObj = null;
            }}
            class="px-6 py-2.5 bg-primary-500 hover:bg-primary-600 text-white font-extrabold text-xs rounded-2xl shadow-sm transition-all"
          >
            + S'abonner à ce flux
          </button>
        {/if}
      </div>

    </div>
  </div>
{/if}
