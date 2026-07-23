<script>
  import { fetchFeeds, fetchArticles, feedsList } from '../stores/appState.js';

  let searchQuery = '';
  let selectedCategory = 'Tous';
  let selectedLanguageFilter = 'Tous';
  let subscribingMap = {}; // { [feedUrl]: boolean }
  let subscribedSuccessMap = {}; // { [feedUrl]: boolean }
  let errorMap = {}; // { [feedUrl]: string }

  // Curated list with distinction between NATIVE full-text and WEB-SCRAPED full-text
  const AWESOME_FEEDS = [
    // 🇨🇭 SUISSE
    { title: "RTS Info (Radio Télévision Suisse)", category: "Suisse", lang: "fr", flag: "🇨🇭", fullTextMode: "scraped", url: "https://www.rts.ch/info/toute-info/?format=rss/news", description: "Actualité suisse et internationale (Flux officiel RTS Info)." },
    { title: "Le Temps (Suisse)", category: "Suisse", lang: "fr", flag: "🇨🇭", fullTextMode: "scraped", url: "https://www.letemps.ch/feed", description: "Journal quotidien suisse de référence." },
    
    // 🇪🇺 EUROPE
    { title: "Le Monde (À la une)", category: "Europe", lang: "fr", flag: "🇫🇷", fullTextMode: "scraped", url: "https://www.lemonde.fr/rss/une.xml", description: "À la une du journal Le Monde." },
    { title: "Mediapart", category: "Europe", lang: "fr", flag: "🇫🇷", fullTextMode: "scraped", url: "https://www.mediapart.fr/articles/feed", description: "Journal d'information numérique indépendant." },
    { title: "Der Spiegel (Schlagzeilen)", category: "Europe", lang: "de", flag: "🇩🇪", fullTextMode: "scraped", url: "https://www.spiegel.de/schlagzeilen/index.rss", description: "Premier magazine d'information en Allemagne." },
    { title: "Tagesschau (ARD)", category: "Europe", lang: "de", flag: "🇩🇪", fullTextMode: "scraped", url: "https://www.tagesschau.de/infoservices/alle-meldungen-100~rss2.xml", description: "Actualité publique allemande en continu." },
    { title: "El País Portada", category: "Europe", lang: "es", flag: "🇪🇸", fullTextMode: "scraped", url: "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada", description: "Le principal quotidien généraliste d'Espagne." },

    // 🌍 MONDE
    { title: "The Conversation France", category: "Monde", lang: "fr", flag: "🇫🇷", fullTextMode: "native", url: "https://theconversation.com/fr/articles.atom", description: "Analyses par des universitaires. Flux RSS 100% intégral natif." },
    { title: "BBC News World", category: "Monde", lang: "en", flag: "🇬🇧", fullTextMode: "scraped", url: "http://feeds.bbci.co.uk/news/world/rss.xml", description: "L'actualité mondiale BBC en direct." },
    { title: "The Guardian World", category: "Monde", lang: "en", flag: "🇬🇧", fullTextMode: "scraped", url: "https://www.theguardian.com/world/rss", description: "Journal britannique indépendant sur les enjeux mondiaux." },

    // 🚀 TECHNOLOGIE
    { title: "Next.ink (Tech & Numérique)", category: "Technologie", lang: "fr", flag: "🇫🇷", fullTextMode: "native", url: "https://next.ink/feed/", description: "Média indépendant numérique. Contenu complet natif." },
    { title: "Numerama", category: "Technologie", lang: "fr", flag: "🇫🇷", fullTextMode: "scraped", url: "https://www.numerama.com/feed/", description: "Pop culture, sciences et nouvelles technologies." },
    { title: "TechCrunch", category: "Technologie", lang: "en", flag: "🇺🇸", fullTextMode: "scraped", url: "https://techcrunch.com/feed/", description: "Actualités des startups et des technologies mondiales." },
    { title: "Ars Technica", category: "Technologie", lang: "en", flag: "🇺🇸", fullTextMode: "scraped", url: "http://feeds.arstechnica.com/arstechnica/index", description: "Analyses scientifiques et politiques tech." },
    { title: "Hacker News", category: "Technologie", lang: "en", flag: "🇺🇸", fullTextMode: "scraped", url: "https://news.ycombinator.com/rss", description: "Tech, startups et programmation par Y Combinator." },
    { title: "Xataka (Tech Español)", category: "Technologie", lang: "es", flag: "🇪🇸", fullTextMode: "scraped", url: "https://feeds.weblogssl.com/xataka", description: "Premier média technologique en espagnol." },

    // 🔬 SCIENCE
    { title: "Nature News", category: "Science", lang: "en", flag: "🇬🇧", fullTextMode: "scraped", url: "http://feeds.nature.com/nature/rss/current", description: "Recherches de la prestigieuse revue Nature." }
  ];

  const categories = ['Tous', 'Suisse', 'Europe', 'Monde', 'Technologie', 'Science', 'Général'];
  const languages = [
    { code: 'Tous', label: 'Toutes les langues' },
    { code: 'fr', label: '🇫🇷 Français' },
    { code: 'en', label: '🇬🇧 Anglais' },
    { code: 'de', label: '🇩🇪 Allemand' },
    { code: 'es', label: '🇪🇸 Espagnol' }
  ];

  $: alreadySubscribedUrls = $feedsList.map(f => f.url.toLowerCase());

  $: filteredFeeds = AWESOME_FEEDS.filter(feed => {
    const matchesCategory = selectedCategory === 'Tous' || feed.category === selectedCategory;
    const matchesLang = selectedLanguageFilter === 'Tous' || feed.lang === selectedLanguageFilter;
    const q = searchQuery.toLowerCase().trim();
    const matchesQuery = !q || feed.title.toLowerCase().includes(q) || feed.description.toLowerCase().includes(q) || feed.url.toLowerCase().includes(q);
    return matchesCategory && matchesLang && matchesQuery;
  });

  async function subscribeToFeed(feed) {
    subscribingMap[feed.url] = true;
    errorMap[feed.url] = null;
    subscribingMap = { ...subscribingMap };

    try {
      const res = await fetch('/api/feeds', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          url: feed.url, 
          category: feed.category,
          language: feed.lang
        })
      });

      const result = await res.json();

      if (res.ok) {
        subscribedSuccessMap[feed.url] = true;
        subscribedSuccessMap = { ...subscribedSuccessMap };
        await fetchFeeds();
        await fetchArticles();
      } else {
        errorMap[feed.url] = result.detail || "Erreur lors de l'abonnement.";
      }
    } catch (err) {
      errorMap[feed.url] = "Erreur de connexion.";
    } finally {
      subscribingMap[feed.url] = false;
      subscribingMap = { ...subscribingMap };
    }
  }
</script>

<div class="flex-1 h-full overflow-y-auto bg-gray-50 dark:bg-dark-bg p-6 md:p-10 space-y-8">
  <div class="max-w-6xl mx-auto space-y-8">
    
    <!-- Top Header -->
    <div class="space-y-3">
      <div class="inline-flex items-center gap-2 px-3.5 py-1.5 bg-primary-50 dark:bg-primary-950/50 text-primary-500 rounded-full text-xs font-bold border border-primary-200 dark:border-primary-800">
        <span>✨ Explorer les Flux RSS</span>
      </div>
      <h1 class="text-3xl font-extrabold text-gray-900 dark:text-white tracking-tight">Découvrir de nouveaux médias</h1>
      <p class="text-sm text-gray-500 dark:text-dark-muted max-w-2xl">
        Sélection de flux RSS généraux et spécialisés. Cliquez sur <strong>S'abonner</strong> pour ajouter directement le média à votre lecteur.
      </p>
    </div>

    <!-- Search and Filters Bar -->
    <div class="bg-white dark:bg-dark-card p-4 rounded-3xl border border-gray-100 dark:border-gray-800 shadow-sm space-y-4 md:space-y-0 md:flex md:items-center md:justify-between gap-4">
      
      <!-- Search Input -->
      <div class="relative flex-1">
        <svg class="w-5 h-5 absolute left-4 top-3.5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path>
        </svg>
        <input 
          type="text" 
          placeholder="Rechercher un média ou un sujet..." 
          bind:value={searchQuery}
          class="w-full bg-gray-50 dark:bg-dark-bg border border-gray-200 dark:border-gray-700 rounded-2xl py-3 pl-12 pr-4 text-sm focus:ring-2 focus:ring-primary-500 focus:outline-none transition-all"
        />
      </div>

      <!-- Filters Group -->
      <div class="flex items-center gap-3 shrink-0">
        <!-- Category Filter -->
        <select 
          bind:value={selectedCategory}
          class="bg-gray-50 dark:bg-dark-bg border border-gray-200 dark:border-gray-700 rounded-2xl py-3 px-4 text-xs font-semibold focus:ring-2 focus:ring-primary-500 focus:outline-none"
        >
          {#each categories as cat}
            <option value={cat}>{cat === 'Tous' ? 'Toutes catégories' : cat}</option>
          {/each}
        </select>

        <!-- Language Filter -->
        <select 
          bind:value={selectedLanguageFilter}
          class="bg-gray-50 dark:bg-dark-bg border border-gray-200 dark:border-gray-700 rounded-2xl py-3 px-4 text-xs font-semibold focus:ring-2 focus:ring-primary-500 focus:outline-none"
        >
          {#each languages as lang}
            <option value={lang.code}>{lang.label}</option>
          {/each}
        </select>
      </div>

    </div>

    <!-- Feeds Grid -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      {#each filteredFeeds as feed}
        {@const isAlreadySubscribed = alreadySubscribedUrls.includes(feed.url.toLowerCase()) || subscribedSuccessMap[feed.url]}

        <div class="bg-white dark:bg-dark-card border border-gray-100 dark:border-gray-800 rounded-3xl p-6 shadow-sm hover:shadow-md transition-all flex flex-col justify-between space-y-5">
          
          <div class="space-y-3">
            <div class="flex items-center justify-between">
              <span class="text-xl">{feed.flag}</span>

              <div class="flex items-center gap-1.5">
                <span class="text-[10px] font-bold uppercase tracking-wider px-2.5 py-1 rounded-full bg-gray-100 dark:bg-gray-800 text-gray-600 dark:text-gray-300">
                  {feed.category}
                </span>

                {#if feed.fullTextMode === 'native'}
                  <span class="text-[10px] font-bold uppercase tracking-wider px-2.5 py-1 rounded-full bg-emerald-50 dark:bg-emerald-950/40 text-emerald-600 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800" title="Flux natif 100% complet">
                    100% Natif
                  </span>
                {:else}
                  <span class="text-[10px] font-bold uppercase tracking-wider px-2.5 py-1 rounded-full bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400 border border-blue-200 dark:border-blue-800" title="Web Scraping automatique">
                    Web Scrapé
                  </span>
                {/if}
              </div>
            </div>

            <h3 class="font-extrabold text-base text-gray-900 dark:text-white leading-snug">
              {feed.title}
            </h3>

            <p class="text-xs text-gray-500 dark:text-dark-muted leading-relaxed line-clamp-3">
              {feed.description}
            </p>
          </div>

          <!-- Footer & Action -->
          <div class="pt-3 border-t border-gray-100 dark:border-gray-800 space-y-2">
            {#if isAlreadySubscribed}
              <div class="w-full py-2.5 px-4 bg-emerald-50 dark:bg-emerald-950/40 text-emerald-600 dark:text-emerald-400 font-bold text-xs rounded-2xl flex items-center justify-center gap-1.5 border border-emerald-200 dark:border-emerald-800">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>
                <span>Abonné</span>
              </div>
            {:else}
              <button 
                on:click={() => subscribeToFeed(feed)}
                disabled={subscribingMap[feed.url]}
                class="w-full py-2.5 px-4 bg-primary-500 hover:bg-primary-600 text-white font-extrabold text-xs rounded-2xl shadow-sm transition-all flex items-center justify-center gap-1.5 disabled:opacity-50"
              >
                {#if subscribingMap[feed.url]}
                  <svg class="w-4 h-4 animate-spin text-white" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path></svg>
                  <span>Abonnement...</span>
                {:else}
                  <span>+ S'abonner</span>
                {/if}
              </button>
            {/if}

            {#if errorMap[feed.url]}
              <p class="text-[11px] text-rose-500 text-center font-medium">{errorMap[feed.url]}</p>
            {/if}
          </div>

        </div>
      {/each}
    </div>

  </div>
</div>
