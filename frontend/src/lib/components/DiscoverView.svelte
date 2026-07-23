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
    { title: "RTS Info (Radio Télévision Suisse)", category: "Suisse", lang: "fr", flag: "🇨🇭", fullTextMode: "scraped", url: "https://www.rts.ch/rss/info.xml", description: "Actualité suisse et internationale (Texte intégral extrait par notre scraper web)." },
    { title: "Le Temps (Suisse)", category: "Suisse", lang: "fr", flag: "🇨🇭", fullTextMode: "scraped", url: "https://www.letemps.ch/rss", description: "Journal quotidien suisse de référence." },
    
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
          language: feed.lang,
          is_full_text: true
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
        errorMap = { ...errorMap };
      }
    } catch (err) {
      errorMap[feed.url] = "Erreur de connexion.";
      errorMap = { ...errorMap };
    } finally {
      subscribingMap[feed.url] = false;
      subscribingMap = { ...subscribingMap };
    }
  }
</script>

<div class="flex-1 h-full overflow-y-auto bg-gray-50 dark:bg-dark-bg p-6 md:p-10 space-y-8">
  <div class="max-w-5xl mx-auto space-y-8">
    
    <!-- Header Title -->
    <div class="space-y-2">
      <div class="flex items-center gap-2">
        <span class="text-xs bg-indigo-100 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400 font-bold px-2.5 py-1 rounded-full uppercase tracking-wider">
          Catalogue Multilingue
        </span>
        <span class="text-xs bg-emerald-100 dark:bg-emerald-950/60 text-emerald-600 dark:text-emerald-400 font-bold px-2.5 py-1 rounded-full uppercase tracking-wider">
          📄 Articles Complets (Natif ou Web Scraper)
        </span>
      </div>
      <h1 class="text-3xl font-extrabold">Découvrir des Sources Internationales</h1>
      <p class="text-sm text-gray-500">
        Parcourez les sources d'actualités classées par zone géographique (<strong>Suisse</strong>, <strong>Europe</strong>, <strong>Monde</strong>) ou thématique (<strong>Technologie</strong>, <strong>Science</strong>).
      </p>
    </div>

    <!-- Search & Filter Controls -->
    <div class="space-y-4">
      <!-- Search Input -->
      <div class="relative">
        <input 
          type="text" 
          bind:value={searchQuery}
          placeholder="Rechercher par média, langue ou sujet (ex: Suisse, Le Temps, Spiegel, Tech)..." 
          class="w-full bg-white dark:bg-dark-card border border-gray-200 dark:border-gray-800 rounded-2xl py-3.5 pl-12 pr-4 shadow-sm focus:ring-2 focus:ring-primary-500 text-sm"
        />
        <svg class="w-5 h-5 absolute left-4 top-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path></svg>
      </div>

      <!-- Filter Row: Languages & Categories -->
      <div class="flex flex-wrap items-center gap-2">
        <!-- Language Filter Pills -->
        <div class="flex items-center gap-1.5 overflow-x-auto pb-1 border-r border-gray-200 dark:border-gray-800 pr-3">
          {#each languages as lang}
            <button 
              on:click={() => selectedLanguageFilter = lang.code}
              class="px-3 py-1.5 rounded-xl text-xs font-semibold whitespace-nowrap transition-all {selectedLanguageFilter === lang.code ? 'bg-primary-500 text-white shadow-sm' : 'bg-white dark:bg-dark-card border border-gray-200 dark:border-gray-800 text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'}"
            >
              {lang.label}
            </button>
          {/each}
        </div>

        <!-- Categories Pills -->
        <div class="flex items-center gap-1.5 overflow-x-auto pb-1">
          {#each categories as cat}
            <button 
              on:click={() => selectedCategory = cat}
              class="px-3 py-1.5 rounded-xl text-xs font-semibold whitespace-nowrap transition-all {selectedCategory === cat ? 'bg-gray-800 text-white dark:bg-gray-200 dark:text-gray-900 shadow-sm' : 'bg-white dark:bg-dark-card border border-gray-200 dark:border-gray-800 text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800'}"
            >
              {cat}
            </button>
          {/each}
        </div>
      </div>
    </div>

    <!-- FEEDS GRID -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {#each filteredFeeds as feed}
        <div class="bg-white dark:bg-dark-card border border-gray-200 dark:border-gray-800 rounded-3xl p-5 shadow-sm hover:shadow-md transition-all flex flex-col justify-between space-y-4">
          
          <div class="space-y-2">
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2">
                <span class="text-2xl">{feed.flag}</span>
                {#if feed.fullTextMode === 'native'}
                  <span class="text-[10px] bg-emerald-50 dark:bg-emerald-950/50 text-emerald-600 dark:text-emerald-400 font-bold px-2 py-0.5 rounded-md border border-emerald-200/50 dark:border-emerald-800/50">
                    ✨ RSS 100% Natif
                  </span>
                {:else}
                  <span class="text-[10px] bg-cyan-50 dark:bg-cyan-950/50 text-cyan-600 dark:text-cyan-400 font-bold px-2 py-0.5 rounded-md border border-cyan-200/50 dark:border-cyan-800/50">
                    🌐 Extrait par Web Scraper
                  </span>
                {/if}
              </div>
              <span class="text-[10px] bg-gray-100 dark:bg-gray-800 text-gray-500 font-semibold px-2.5 py-0.5 rounded-full">
                {feed.category}
              </span>
            </div>

            <h3 class="font-bold text-base text-gray-900 dark:text-gray-100 leading-snug">{feed.title}</h3>
            <p class="text-xs text-gray-500 leading-relaxed">{feed.description}</p>
          </div>

          <div class="pt-3 border-t border-gray-100 dark:border-gray-800 flex items-center justify-between gap-2">
            <span class="text-[11px] text-gray-400 font-mono truncate max-w-[140px]">{feed.url}</span>

            {#if alreadySubscribedUrls.includes(feed.url.toLowerCase()) || subscribedSuccessMap[feed.url]}
              <span class="px-3 py-1.5 bg-emerald-50 text-emerald-600 dark:bg-emerald-950/40 dark:text-emerald-400 text-xs font-bold rounded-xl flex items-center gap-1 shrink-0">
                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>
                <span>Abonné</span>
              </span>
            {:else}
              <button 
                on:click={() => subscribeToFeed(feed)}
                disabled={subscribingMap[feed.url]}
                class="px-4 py-1.5 bg-primary-500 hover:bg-primary-600 text-white font-semibold text-xs rounded-xl shadow-sm transition-all disabled:opacity-50 flex items-center gap-1.5 shrink-0"
              >
                {#if subscribingMap[feed.url]}
                  <svg class="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
                  </svg>
                  <span>Ajout...</span>
                {:else}
                  <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"></path></svg>
                  <span>S'abonner</span>
                {/if}
              </button>
            {/if}
          </div>

          {#if errorMap[feed.url]}
            <p class="text-[11px] text-rose-500 font-medium">{errorMap[feed.url]}</p>
          {/if}

        </div>
      {/each}
    </div>

  </div>
</div>
