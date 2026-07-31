<script>
  import { onMount } from 'svelte';
  import { articlesList } from '../stores/appState.js';
  import MediaCard from './MediaCard.svelte';
  import PerplexityCard from './PerplexityCard.svelte';

  const shelfConfig = [
    { type: 'music', label: 'CD & Vinyles', emoji: '🎵', color: '#4f6ef7' },
    { type: 'book', label: 'Romans & Essais', emoji: '📖', color: '#f59e0b' },
    { type: 'bd', label: 'BD & Comics', emoji: '🎨', color: '#e879f9' },
    { type: 'cinema', label: 'Cinéma & Séries', emoji: '🎬', color: '#10b981' },
  ];

  let showFeedManager = false;
  let cultureFeeds = [
    { title: "Télérama - Cinéma", url: "https://www.telerama.fr/rss/cinema.xml", active: true },
    { title: "Allociné - Actualités", url: "https://www.allocine.fr/rss/news.xml", active: true },
    { title: "SensCritique - Films", url: "https://www.senscritique.com/rss/films", active: true },
    { title: "Les Inrocks - Musique", url: "https://www.lesinrocks.com/musique/feed/", active: true },
    { title: "Livres Hebdo", url: "https://www.livreshebdo.fr/rss.xml", active: true },
    { title: "BD Gest' - Chroniques", url: "https://www.bdgest.com/rss/chroniques.xml", active: true },
    { title: "Ecran Large", url: "https://www.ecranlarge.com/rss", active: true },
    { title: "Pitchfork (US)", url: "https://pitchfork.com/rss/reviews/albums/", active: true },
    { title: "ActuaBD", url: "https://www.actuabd.com/spip.php?page=backend", active: true },
    { title: "Première", url: "https://www.premiere.fr/rss", active: true }
  ];

  let selectedItem = null;
  let cultureArticles = [];
  let clusters = [];
  let isLoading = false;

  onMount(async () => {
    isLoading = true;
    try {
      const [resArts, resClust] = await Promise.allSettled([
        fetch('/api/articles/culture').then(r => r.ok ? r.json() : []),
        fetch('/api/clustering/clusters?threshold=0.78&cluster_type=themes').then(r => r.ok ? r.json() : { clusters: [] })
      ]);

      if (resArts.status === 'fulfilled' && Array.isArray(resArts.value)) {
        cultureArticles = resArts.value;
      }
      if (resClust.status === 'fulfilled' && resClust.value && resClust.value.clusters) {
        clusters = resClust.value.clusters;
      }
    } catch (err) {
      console.error("Erreur lors de la récupération des éléments culturels:", err);
    } finally {
      isLoading = false;
    }
  });

  function parseArticleToMedia(art, idx) {
    const title = art.title || "Titre inconnu";
    const rawContent = art.content || art.description || "";
    const lower = (title + " " + rawContent + " " + (art.feed_title || "") + " " + (art.feed_url || "")).toLowerCase();
    const feedTitleUrl = ((art.feed_title || '') + ' ' + (art.feed_url || '')).toLowerCase();

    const activeFeedUrls = cultureFeeds.filter(f => f.active).map(f => f.url);
    if (activeFeedUrls.length > 0 && art.feed_url) {
      const isUrlActive = activeFeedUrls.some(u => art.feed_url.includes(u) || u.includes(art.feed_url));
      if (!isUrlActive) return null;
    }

    let type = null;
    if (/film|cin[eé]ma|s[eé]rie|r[eé]alisateur|acteur|actrice|netflix|streaming|saison|[eé]pisode|box-office|salles|ecranlarge|allocine|cineserie|premiere/i.test(lower)) {
      type = 'cinema';
    } else if (/bd|manga|comics|roman graphique|tome|bande dessin[eé]e|illustration|dessinateur|planetebd|bdgest|actuabd/i.test(lower)) {
      type = 'bd';
    } else if (/album|musique|chanson|concert|disque|vinyle|mp3|pochette|single|clip|artiste|chanteur|groupe|jazz|francemusique|musicbrainz|pitchfork|citizenjazz|lesinrocks/i.test(lower)) {
      type = 'music';
    } else if (/livre|roman|essai|auteur|parution|[eé]dition|bouquin|prix litt[eé]raire|polar|fiction|actualitte|livreshebdo/i.test(lower)) {
      type = 'book';
    }

    if (!type) {
      if (/ecranlarge|allocine|cineserie|premiere|telerama|senscritique/i.test(feedTitleUrl)) type = 'cinema';
      else if (/planetebd|bdgest|actuabd/i.test(feedTitleUrl)) type = 'bd';
      else if (/citizenjazz|francemusique|musicbrainz|pitchfork|lesinrocks/i.test(feedTitleUrl)) type = 'music';
      else type = 'book';
    }

    const coverUrl = art.image_url || "";
    const artist = art.feed_title || "Média RSS";
    const releaseDate = art.published_date ? new Date(art.published_date).toLocaleDateString("fr-FR", { day: "numeric", month: "short" }) : "Récents";

    const accentColors = ['#4f6ef7', '#f59e0b', '#e879f9', '#10b981', '#ec4899', '#8b5cf6'];
    const accentColor = accentColors[idx % accentColors.length];

    return {
      id: `art_${art.id}`,
      title,
      artist,
      type,
      coverUrl,
      accentColor,
      color: '#1a1a24',
      releaseDate,
      description: rawContent || "Aucun résumé disponible.",
      clusterObj: {
        cluster_id: `art_${art.id}`,
        topic_title: title,
        category: art.category || 'Culture',
        articles: [art],
        precomputed_synthesis: { summary: rawContent, key_takeaways: [artist, releaseDate] }
      }
    };
  }

  // Helper to map a cluster or article to a 3D MediaItem structure
  function parseClusterToMedia(cluster, idx) {
    const title = cluster.topic_title || cluster.title || "Titre inconnu";
    const rawContent = cluster.precomputed_synthesis?.summary || cluster.articles?.[0]?.content || "";
    const category = (cluster.category || "").toLowerCase();
    const lower = (title + " " + rawContent + " " + category).toLowerCase();
    
    const feedTitleUrl = ((cluster.articles?.[0]?.feed_title || '') + ' ' + (cluster.articles?.[0]?.feed_url || '')).toLowerCase();

    const activeFeedUrls = cultureFeeds.filter(f => f.active).map(f => f.url);
    const isCategoryCulture = cluster.category === "Étagère Culture" || (cluster.articles && cluster.articles.some(a => a.category === "Étagère Culture"));
    const matchesFeed = cluster.articles && cluster.articles.some(a => activeFeedUrls.includes(a.feed_url));

    if (!isCategoryCulture && !matchesFeed) {
      return null;
    }

    // Determine shelf type from content or feed keywords
    let type = null;
    if (/film|cin[eé]ma|s[eé]rie|r[eé]alisateur|acteur|actrice|netflix|streaming|saison|[eé]pisode|box-office|salles|ecranlarge|allocine|cineserie|premiere/i.test(lower + " " + feedTitleUrl)) {
      type = 'cinema';
    } else if (/bd|manga|comics|roman graphique|tome|bande dessin[eé]e|illustration|dessinateur|planetebd|bdgest|actuabd/i.test(lower + " " + feedTitleUrl)) {
      type = 'bd';
    } else if (/album|musique|chanson|concert|disque|vinyle|mp3|pochette|single|clip|artiste|chanteur|groupe|jazz|francemusique|musicbrainz|pitchfork/i.test(lower + " " + feedTitleUrl)) {
      type = 'music';
    } else if (isCategoryCulture || /livre|roman|essai|auteur|parution|[eé]dition|bouquin|prix litt[eé]raire|polar|fiction|actualitte|livreshebdo/i.test(lower + " " + feedTitleUrl)) {
      type = 'book';
    }

    if (!type) type = 'book';

    const firstArt = cluster.articles?.[0] || {};
    const coverUrl = firstArt.image_url || cluster.image_url || "";
    const artist = firstArt.feed_title || cluster.distinct_feeds?.[0] || "Média RSS";
    const releaseDate = firstArt.published_date ? new Date(firstArt.published_date).toLocaleDateString("fr-FR", { day: "numeric", month: "short" }) : "Récents";

    const accentColors = ['#4f6ef7', '#f59e0b', '#e879f9', '#10b981', '#ec4899', '#8b5cf6'];
    const accentColor = accentColors[idx % accentColors.length];

    return {
      id: cluster.cluster_id || `art_${idx}`,
      title,
      artist,
      type,
      coverUrl,
      accentColor,
      color: '#1a1a24',
      releaseDate,
      description: rawContent || "Aucun résumé disponible.",
      clusterObj: cluster
    };
  }

  $: allMediaItems = (() => {
    if (cultureArticles.length > 0) {
      return cultureArticles.map((a, i) => parseArticleToMedia(a, i)).filter(Boolean);
    }
    if (clusters.length > 0) {
      return clusters.map((c, i) => parseClusterToMedia(c, i)).filter(Boolean);
    }
    return [];
  })();

  function handleItemClick(item) {
    if (item.clusterObj) {
      selectedItem = item.clusterObj;
    } else {
      selectedItem = {
        cluster_id: item.id,
        topic_title: item.title,
        category: item.type,
        precomputed_synthesis: { summary: item.description, key_takeaways: [item.artist, item.releaseDate] },
        articles: [{ feed_title: item.artist, title: item.title, image_url: item.coverUrl, published_date: item.releaseDate }]
      };
    }
  }
</script>

<div class="relative rounded-2xl overflow-hidden p-6 md:p-10 h-full overflow-y-auto" style="background: linear-gradient(160deg, rgba(255,255,255,0.018) 0%, rgba(255,255,255,0.008) 100%); border: 1px solid rgba(255,255,255,0.05);">
  <div class="absolute inset-0 pointer-events-none" style="background-image: radial-gradient(circle, rgba(255,255,255,0.04) 1px, transparent 1px); background-size: 28px 28px; mask-image: radial-gradient(ellipse 100% 100% at 50% 0%, black 0%, transparent 75%);"></div>
  <div class="absolute inset-0 pointer-events-none rounded-2xl" style="background: radial-gradient(ellipse 80% 50% at 50% 0%, rgba(79,110,247,0.05) 0%, transparent 70%);"></div>

  <div class="flex justify-between items-center mb-6 relative z-10">
    <h2 class="text-xl font-bold text-gray-800 dark:text-gray-200"></h2>
    <button on:click={() => showFeedManager = true} class="px-4 py-2 bg-white dark:bg-dark-card border border-gray-200 dark:border-gray-800 rounded-xl text-sm font-semibold hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors shadow-sm">
      ⚙️ Gérer les flux de l'étagère
    </button>
  </div>

  {#if isLoading}
    <div class="flex items-center justify-center h-64 text-gray-400 gap-3">
      <div class="w-6 h-6 border-2 border-cyan-500 border-t-transparent rounded-full animate-spin"></div>
      <span class="text-sm font-medium">Chargement des œuvres culturelles depuis vos flux...</span>
    </div>
  {:else}
    {#each shelfConfig as meta}
      {@const items = allMediaItems.filter(i => i.type === meta.type)}
      <div class="mb-16 last:mb-4 relative z-10">
        <div class="flex items-center gap-3 mb-6 px-1">
          <div style="display: inline-flex; align-items: center; gap: 7px; padding: 4px 12px; border-radius: 100px; background: {meta.color}16; border: 1px solid {meta.color}30; color: {meta.color}; font-size: 11px; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase;">
            <span style="font-size: 13px;">{meta.emoji}</span>
            <span>{meta.label}</span>
          </div>
          <div style="flex: 1; height: 1px; background: linear-gradient(to right, {meta.color}30, transparent);"></div>
          <span style="color: rgba(255,255,255,0.28); font-size: 11px; font-weight: 600;">{items.length} œuvres dans le flux</span>
        </div>

        <div style="perspective: 1400px; perspective-origin: 50% 60%;">
          <!-- Back wall -->
          <div style="background: linear-gradient(180deg, rgba(8,8,12,0.6) 0%, rgba(14,14,20,0.8) 100%); border-radius: 8px 8px 0 0; padding: 16px 20px 0 20px; position: relative; overflow: hidden; min-height: 170px;">
            <div style="position: absolute; inset: 0; background-image: linear-gradient(rgba(255,255,255,0.015) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.015) 1px, transparent 1px); background-size: 60px 60px; pointer-events: none; opacity: 0.5;"></div>
            <div style="position: absolute; top: 0; left: 0; bottom: 0; width: 32px; background: linear-gradient(to right, rgba(0,0,0,0.3), transparent); pointer-events: none;"></div>
            <div style="position: absolute; top: 0; right: 0; bottom: 0; width: 32px; background: linear-gradient(to left, rgba(0,0,0,0.3), transparent); pointer-events: none;"></div>

            {#if items.length > 0}
              <div class="flex items-end gap-[18px] pb-2 overflow-x-auto relative z-10 no-scrollbar">
                {#each items as item, i}
                  <div style="flex-shrink: 0;">
                    <MediaCard {item} index={i} onClick={() => handleItemClick(item)} />
                  </div>
                {/each}
                <div style="width: 20px; flex-shrink: 0;"></div>
              </div>
            {:else}
              <div class="h-32 flex flex-col items-center justify-center text-gray-500 text-xs gap-1.5 opacity-60">
                <span class="text-xl">{meta.emoji}</span>
                <span>Aucune œuvre de type {meta.label} dans vos flux RSS récents.</span>
              </div>
            {/if}
          </div>

          <!-- Shelf board -->
          <div style="height: 16px; margin-left: -2px; margin-right: -2px; background: linear-gradient(180deg, #2e2824 0%, #1c1612 50%, #0e0b08 100%); border-top: 1px solid rgba(255,255,255,0.07); box-shadow: 0 6px 30px rgba(0,0,0,0.8), 0 2px 8px rgba(0,0,0,0.5); position: relative;">
            <div style="position: absolute; inset: 0; background: repeating-linear-gradient(90deg, transparent, transparent 120px, rgba(255,255,255,0.015) 120px, rgba(255,255,255,0.015) 121px);"></div>
          </div>
          <!-- Shadow -->
          <div style="height: 12px; margin-left: 12px; margin-right: 12px; background: rgba(0,0,0,0.5); filter: blur(10px); transform: scaleY(0.4); transform-origin: top; margin-top: -4px;"></div>
        </div>
      </div>
    {/each}
  {/if}
</div>

{#if selectedItem}
  <PerplexityCard 
    cluster={selectedItem}
    onClose={() => selectedItem = null}
  />
{/if}

{#if showFeedManager}
  <div class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
    <div class="bg-white dark:bg-dark-card rounded-2xl shadow-xl border border-gray-200 dark:border-gray-800 w-full max-w-lg overflow-hidden flex flex-col max-h-[85vh]">
      <div class="p-5 border-b border-gray-100 dark:border-gray-800 flex justify-between items-center bg-gray-50 dark:bg-dark-bg">
        <h3 class="font-bold text-lg">⚙️ Flux du Pack Culture</h3>
        <button on:click={() => showFeedManager = false} class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200">
          ✕
        </button>
      </div>
      <div class="p-5 overflow-y-auto flex-1 space-y-3">
        <p class="text-xs text-gray-500 mb-4">Cochez les sources que vous souhaitez afficher sur les étagères 3D.</p>
        {#each cultureFeeds as feed}
          <label class="flex items-center justify-between p-3 bg-gray-50 dark:bg-dark-bg border border-gray-100 dark:border-gray-800 rounded-xl cursor-pointer hover:border-primary-300 transition-colors">
            <div class="flex flex-col">
              <span class="text-sm font-semibold text-gray-900 dark:text-white">{feed.title}</span>
              <span class="text-xs text-gray-500 truncate max-w-[250px]">{feed.url}</span>
            </div>
            <input type="checkbox" bind:checked={feed.active} class="w-5 h-5 accent-primary-500 rounded" />
          </label>
        {/each}
      </div>
      <div class="p-4 border-t border-gray-100 dark:border-gray-800 bg-gray-50 dark:bg-dark-bg text-right">
        <button on:click={() => { showFeedManager = false; clusters = [...clusters]; }} class="px-5 py-2.5 bg-primary-500 hover:bg-primary-600 text-white font-bold rounded-xl text-sm transition-all shadow-sm">
          Fermer et Appliquer
        </button>
      </div>
    </div>
  </div>
{/if}

<style>
  .no-scrollbar::-webkit-scrollbar {
    display: none;
  }
  .no-scrollbar {
    -ms-overflow-style: none;
    scrollbar-width: none;
  }
</style>
