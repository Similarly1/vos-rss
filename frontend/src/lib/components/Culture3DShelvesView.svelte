<script>
  import { onMount } from 'svelte';
  import { articlesList } from '../stores/appState.js';
  import MediaCard from './MediaCard.svelte';
  import PerplexityCard from './PerplexityCard.svelte';

  const shelfConfig = [
    { type: 'music', label: 'CD & Vinyles', emoji: '🎵', color: '#4f6ef7' },
    { type: 'book', label: 'Romans & Essais', emoji: '📖', color: '#f59e0b' },
    { type: 'bd', label: 'BD & Comics', emoji: '🎨', color: '#e879f9' },
  ];

  let selectedItem = null;
  let clusters = [];
  let isLoading = false;

  onMount(async () => {
    isLoading = true;
    try {
      const res = await fetch('/api/clustering/clusters?threshold=0.78&cluster_type=themes');
      if (res.ok) {
        const data = await res.json();
        clusters = data.clusters || [];
      }
    } catch (err) {
      console.error("Erreur lors de la récupération des éléments culturels:", err);
    } finally {
      isLoading = false;
    }
  });

  // Helper to map a cluster or article to a 3D MediaItem structure
  function parseClusterToMedia(cluster, idx) {
    const title = cluster.topic_title || cluster.title || "Titre inconnu";
    const rawContent = cluster.precomputed_synthesis?.summary || cluster.articles?.[0]?.content || "";
    const lower = (title + " " + rawContent + " " + (cluster.category || "")).toLowerCase();
    
    let type = 'book';
    if (/album|musique|chanson|concert|disque|vinyle|mp3|pochette|single|clip/i.test(lower)) {
      type = 'music';
    } else if (/bd|manga|comics|roman graphique|tome|bande dessin[eé]e|illustration/i.test(lower)) {
      type = 'bd';
    }

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
    if (clusters.length > 0) {
      return clusters.map((c, i) => parseClusterToMedia(c, i));
    }
    // Fallback on raw articles list if clusters are empty
    if ($articlesList && $articlesList.length > 0) {
      return $articlesList.slice(0, 30).map((a, i) => parseClusterToMedia({
        cluster_id: `art_${a.id}`,
        topic_title: a.title,
        category: a.category,
        articles: [a],
        precomputed_synthesis: { summary: a.content || a.description || "" }
      }, i));
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

<style>
  .no-scrollbar::-webkit-scrollbar {
    display: none;
  }
  .no-scrollbar {
    -ms-overflow-style: none;
    scrollbar-width: none;
  }
</style>
