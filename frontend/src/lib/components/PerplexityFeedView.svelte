<script>
  import { onMount, tick } from 'svelte';
  import { mistralApiKey, geminiApiKey, synthesisProvider, selectedMistralDiscoverModel, selectedGeminiDiscoverModel, currentView } from '../stores/appState.js';
  import { playTrack, selectedVoice, sanitizeTextForSpeech } from '../stores/audioStore.js';
  import ProgressiveImage from './ProgressiveImage.svelte';
  import PerplexityCard from './PerplexityCard.svelte';

  // Mode: 'events' (Strict same event) vs 'themes' (Broad thematic digest)
  let perplexityMode = 'events'; // 'events' | 'themes'
  let selectedFilter = 'Tous';
  let onlyVerified = false; // Filter for >= 3 distinct media sources
  const filters = ['Tous', '🇨🇭 Suisse', '🇪🇺 Europe', '🌍 Monde', '💻 Technologie', '🔬 Science', '📈 Économie', '📁 Général'];

  let clusters = [];
  let isLoading = false;
  let audioLoadingState = {};
  
  // Selected Cluster for Detail Overlay / Modal
  let activeCluster = null;
  let modalContainer = null;

  let syntheses = {};
  let synthLoading = {};

  const THEME_FALLBACK_IMAGES = {
    'Suisse': 'https://images.unsplash.com/photo-1530122037265-a5f1f91d3b99?auto=format&fit=crop&w=1200&q=80',
    'Europe': 'https://images.unsplash.com/photo-1467269204594-9661b134dd2b?auto=format&fit=crop&w=1200&q=80',
    'Monde': 'https://images.unsplash.com/photo-1451187580459-43490279c0fa?auto=format&fit=crop&w=1200&q=80',
    'Technologie': 'https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?auto=format&fit=crop&w=1200&q=80',
    'Science': 'https://images.unsplash.com/photo-1451187580459-43490279c0fa?auto=format&fit=crop&w=1200&q=80',
    'Économie': 'https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?auto=format&fit=crop&w=1200&q=80',
    'Général': 'https://images.unsplash.com/photo-1504711434969-e33886168f5c?auto=format&fit=crop&w=1200&q=80'
  };

  function getLanguageFlag(lang) {
    if (!lang) return "🇫🇷";
    const l = lang.toLowerCase();
    if (l === "en") return "🇬🇧";
    if (l === "de") return "🇩🇪";
    if (l === "es") return "🇪🇸";
    return "🇫🇷";
  }

  function getDistinctFeedCount(cluster) {
    if (cluster.distinct_feed_count) return cluster.distinct_feed_count;
    const feeds = new Set(cluster.articles.map(a => a.feed_title || 'RSS'));
    return feeds.size;
  }

  function decodeHtmlEntities(str) {
    if (!str) return '';
    let text = str;
    text = text.replace(/&#(\d+);/g, (m, dec) => String.fromCharCode(dec));
    text = text.replace(/&#x([0-9a-fA-F]+);/g, (m, hex) => String.fromCharCode(parseInt(hex, 16)));
    text = text.replace(/&quot;/g, '"').replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&#039;/g, "'").replace(/&nbsp;/g, ' ');
    return text;
  }

  function cleanTextBoilerplate(str) {
    if (!str) return '';
    let text = str;
    // Strip scripts, styles, header, nav, footer, form, svg, code blocks
    text = text.replace(/<(script|style|header|nav|footer|form|svg|code)[^>]*>[\s\S]*?<\/\1>/gi, ' ');
    // Strip all HTML tags cleanly FIRST to avoid attribute leakage
    text = text.replace(/<[^>]+>/g, ' ');
    text = decodeHtmlEntities(text);
    // Remove leftover CSS class names, tailwind utilities or JS fragments
    text = text.replace(/(?:lg|md|sm|xl|2xl):[a-zA-Z0-9_-]+/g, ' ');
    text = text.replace(/(?:opacity-none|invisible|flex|grid|absolute|relative|overflow-hidden|hover:|focus:|opacity-none)[a-zA-Z0-9_-]*/gi, ' ');
    text = text.replace(/(?:BBC Homepage|Skip to content|Accessibility Help|Your account|Search BBC|More menu|Close menu|Menü öffnen|watchOverflow|isCollapsed|swiper-init|data-app-hidden|x-lazyload|Menü Startseite|Ausland)/gi, ' ');
    // Remove orphaned non-text noise
    text = text.replace(/[^a-zA-Z0-9àâáäãåçéèêëìíîïñòóôöõøùúûüýÿÀÂÁÄÃÅÇÉÈÊËÌÍÎÏÑÒÓÔÖÕØÙÚÛÜÝŸæÆœŒ\s.,!?'"–-]/g, ' ');
    return text.replace(/\s+/g, ' ').trim();
  }

  function renderMarkdownHtml(text) {
    if (!text) return '';
    let clean = cleanTextBoilerplate(text);
    clean = clean.replace(/\*\*(.*?)\*\*/g, '<strong class="font-black text-cyan-200 bg-cyan-950/50 px-1.5 py-0.5 rounded border border-cyan-800/40">$1</strong>');
    clean = clean.replace(/\*(.*?)\*/g, '<em class="italic text-gray-300">$1</em>');
    const paragraphs = clean.split(/\n\s*\n/);
    return paragraphs.map(p => `<p class="leading-relaxed mb-3">${p.trim()}</p>`).join('');
  }

  function getClusterTitle(cluster) {
    const cId = cluster.cluster_id;
    if (syntheses[cId] && syntheses[cId].synthesis_title) {
      return syntheses[cId].synthesis_title;
    }
    if (cluster.precomputed_synthesis && cluster.precomputed_synthesis.synthesis_title) {
      return cluster.precomputed_synthesis.synthesis_title;
    }
    return cleanTextBoilerplate(cluster.topic_title);
  }

  function isErrorSummary(text) {
    if (!text) return true;
    return text.startsWith('Erreur') || text.includes('génération du résumé');
  }

  function isLowQualityOrEnglish(synth) {
    if (!synth) return true;
    if (synth.is_fallback) return true;
    const text = synth.summary || '';
    if (isErrorSummary(text) || text.length < 220 || text.includes('Synthèse IA en cours') || text.includes('<img') || text.includes('<p>')) return true;

    const enWords = [' the ', ' this ', ' after ', ' said ', ' with ', ' from ', ' reported ', ' market ', ' profit ', ' beat ', ' strikes ', ' island ', ' people ', ' killed ', ' live: ', ' quarterly '];
    const lower = text.toLowerCase();
    let matches = 0;
    for (const w of enWords) {
      if (lower.includes(w)) matches++;
    }
    return matches >= 2;
  }

  function openCluster(cluster) {
    activeCluster = cluster;
    const cId = cluster.cluster_id;
    const existing = syntheses[cId] || cluster.precomputed_synthesis;
    if (!existing || isLowQualityOrEnglish(existing)) {
      fetchSynthesisForCluster(cluster);
    }
    setTimeout(() => {
      if (modalContainer) {
        modalContainer.scrollTop = 0;
      }
    }, 20);
  }

  async function fetchSynthesisForCluster(cluster) {
    const cId = cluster.cluster_id;
    if (synthLoading[cId]) return;

    synthLoading[cId] = true;
    synthLoading = { ...synthLoading };

    try {
      const activeProvider = $synthesisProvider || ($mistralApiKey ? 'mistral' : 'gemini');
      const activeKey = activeProvider === 'gemini' ? $geminiApiKey : $mistralApiKey;
      const activeModel = activeProvider === 'gemini' ? $selectedGeminiDiscoverModel : $selectedMistralDiscoverModel;

      const res = await fetch('/api/clustering/synthesize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          articles: cluster.articles,
          provider: activeProvider,
          api_key: activeKey || null,
          model: activeModel
        })
      });

      const result = await res.json();
      if (res.ok && result.data) {
        syntheses[cId] = result.data;
        syntheses = { ...syntheses };
      } else if (result.detail) {
        syntheses[cId] = {
          synthesis_title: cluster.topic_title,
          summary: `⚠️ ${result.detail}`,
          is_fallback: true
        };
        syntheses = { ...syntheses };
      }
    } catch (err) {
      console.error(`Erreur synthèse cluster ${cId}:`, err);
    } finally {
      synthLoading[cId] = false;
      synthLoading = { ...synthLoading };
    }
  }

  function getTeaserSentence(cluster) {
    const cId = cluster.cluster_id;
    const synth = syntheses[cId] || cluster.precomputed_synthesis;
    if (synth && synth.summary && !isErrorSummary(synth.summary) && !isLowQualityOrEnglish(synth)) {
      const parts = synth.summary.split('. ');
      return parts.slice(0, 2).join('. ') + (parts.length > 2 ? '.' : '');
    }
    const raw = cluster.articles[0]?.content || cluster.articles[0]?.description || cluster.articles[0]?.title || '';
    const clean = cleanTextBoilerplate(raw);
    return clean.slice(0, 200) + (clean.length > 200 ? '...' : '');
  }

  function getCategoryFallbackImage(category) {
    const cat = category || 'Général';
    return THEME_FALLBACK_IMAGES[cat] || THEME_FALLBACK_IMAGES['Général'];
  }

  function getClusterImage(cluster) {
    if (cluster.articles[0] && cluster.articles[0].image_url) {
      return cluster.articles[0].image_url;
    }
    return getCategoryFallbackImage(cluster.category);
  }

  async function fetchPerplexityClusters() {
    isLoading = true;
    const threshold = perplexityMode === 'events' ? 0.91 : 0.78;
    try {
      const res = await fetch(`/api/clustering/clusters?threshold=${threshold}&cluster_type=${perplexityMode}`);
      if (res.ok) {
        const data = await res.json();
        const allC = data.clusters || [];
        clusters = allC.filter(c => {
           const text = (c.precomputed_synthesis?.synthesis_title || c.topic_title || "") + " " + (c.precomputed_synthesis?.summary || "");
           const enDeWords = /\b(the|and|is|in|at|which|were|der|die|das|und|ist|nicht)\b/i;
           const frWords = /\b(le|la|les|des|du|dans|un|une|est)\b/i;
           if (enDeWords.test(text) && !frWords.test(text)) return false;
           return true;
        });
        clusters.forEach(c => {
          if (c.precomputed_synthesis && !isLowQualityOrEnglish(c.precomputed_synthesis)) {
            syntheses[c.cluster_id] = c.precomputed_synthesis;
          }
        });
        syntheses = { ...syntheses };

        autoSynthesizeClusters(clusters);
      }
    } catch (err) {
      console.error("Erreur lors de la récupération du fil Perplexity:", err);
    } finally {
      isLoading = false;
    }
  }

  function setMode(newMode) {
    if (perplexityMode === newMode) return;
    perplexityMode = newMode;
    fetchPerplexityClusters();
  }

  async function autoSynthesizeClusters(clustersList) {
    const toSynthesize = clustersList.slice(0, 6).filter(cluster => {
      const cId = cluster.cluster_id;
      const existing = syntheses[cId] || cluster.precomputed_synthesis;
      return !(existing && !isLowQualityOrEnglish(existing)) && !synthLoading[cId];
    });
    await Promise.all(toSynthesize.map(c => fetchSynthesisForCluster(c)));
  }

  async function handleListenSummary(clusterId, title, summaryText) {
    audioLoadingState[clusterId] = true;
    audioLoadingState = { ...audioLoadingState };

    const cleanText = sanitizeTextForSpeech(summaryText || title);
    const textToRead = `${title}. ${cleanText}`;

    try {
      const res = await fetch('/api/audio/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: textToRead,
          voice: $selectedVoice || 'marie',
          api_key: $mistralApiKey || null
        })
      });

      const result = await res.json();

      if (res.ok && (result.audio_b64 || result.audio_url)) {
        playTrack(title, result.audio_b64 || result.audio_url, 'Voix Marie (Mistral Studio)');
      } else {
        alert(result.detail || "Échec de la génération de la voix Mistral.");
        if (result.detail && result.detail.includes("Clé API")) {
          $currentView = 'settings';
        }
      }
    } catch (err) {
      alert("Erreur de connexion avec le service audio.");
    } finally {
      audioLoadingState[clusterId] = false;
      audioLoadingState = { ...audioLoadingState };
    }
  }

  $: filteredClusters = clusters.filter(c => {
    const distinctCount = getDistinctFeedCount(c);
    const matchesVerified = !onlyVerified || distinctCount >= 3;

    if (selectedFilter === 'Tous') return matchesVerified;

    const cleanFilter = selectedFilter.replace(/[\u{1F300}-\u{1F9FF}]|[\u{2600}-\u{26FF}]|[\u{2700}-\u{27BF}]/gu, '').trim().toLowerCase();
    const clusterCat = (c.category || '').toLowerCase();
    const matchesCategory = clusterCat.includes(cleanFilter) || c.articles.some(a => (a.category || '').toLowerCase().includes(cleanFilter));

    return matchesCategory && matchesVerified;
  });

  $: relatedClusters = activeCluster 
    ? clusters.filter(c => c.cluster_id !== activeCluster.cluster_id && (c.category === activeCluster.category || getDistinctFeedCount(c) >= 2)).slice(0, 3)
    : [];

  onMount(() => {
    fetchPerplexityClusters();
  });
</script>

<!-- SCROLL CONTAINER WITH MANDATORY CSS SNAP -->
<div class="flex-1 h-full overflow-y-auto snap-y snap-proximity scroll-smooth bg-gray-950 text-gray-100 p-4 md:p-8">
  <div class="max-w-3xl mx-auto space-y-6">
    
    <!-- Top Header Bar -->
    <div class="flex items-center justify-between pt-2">
      <div class="flex items-center gap-2">
        <div class="w-8 h-8 rounded-full bg-gradient-to-tr from-cyan-500 to-blue-600 flex items-center justify-center font-black text-white text-xs shadow-lg">
          P
        </div>
        <h1 class="text-xl font-black tracking-tight text-white">Fil Perplexity (Croisement IA)</h1>
      </div>

      <button 
        on:click={fetchPerplexityClusters} 
        disabled={isLoading}
        class="p-2 bg-gray-900 hover:bg-gray-800 text-gray-300 rounded-full border border-gray-800 transition-all text-xs font-bold flex items-center gap-1.5 px-3"
      >
        <svg class="w-3.5 h-3.5 {isLoading ? 'animate-spin text-cyan-400' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
        </svg>
        <span>Rafraîchir</span>
      </button>
    </div>

    <!-- TAB SELECTOR: STRICT EVENTS vs BROAD THEMES -->
    <div class="bg-gray-900/90 p-1.5 rounded-2xl border border-gray-800 grid grid-cols-2 gap-1.5 shadow-xl">
      <button 
        on:click={() => setMode('events')}
        class="py-3 px-4 rounded-xl text-xs font-extrabold transition-all flex items-center justify-center gap-2 {perplexityMode === 'events' ? 'bg-cyan-500 text-gray-950 shadow-lg' : 'text-gray-400 hover:text-white hover:bg-gray-800/60'}"
      >
        <span>🎯 Événements Précis (Croisement Strict)</span>
      </button>

      <button 
        on:click={() => setMode('themes')}
        class="py-3 px-4 rounded-xl text-xs font-extrabold transition-all flex items-center justify-center gap-2 {perplexityMode === 'themes' ? 'bg-purple-600 text-white shadow-lg' : 'text-gray-400 hover:text-white hover:bg-gray-800/60'}"
      >
        <span>📰 Revues Thématiques (Regroupement Général)</span>
      </button>
    </div>

    <!-- Category Filter Pills & Only Verified Filter Toggle -->
    <div class="space-y-3">
      <div class="flex items-center gap-2 overflow-x-auto pb-1 no-scrollbar">
        {#each filters as filter}
          <button 
            on:click={() => selectedFilter = filter}
            class="px-3.5 py-1.5 rounded-full text-xs font-bold whitespace-nowrap transition-all {selectedFilter === filter ? 'bg-white text-gray-950 shadow-md' : 'bg-gray-900/80 text-gray-400 hover:text-white border border-gray-800'}"
          >
            {filter}
          </button>
        {/each}
      </div>

      <!-- FILTER ONLY VERIFIED SOURCES TOGGLE -->
      <div class="flex items-center justify-between p-3.5 bg-gray-900/60 rounded-2xl border border-gray-800/80">
        <div class="flex items-center gap-2 text-xs">
          <span class="text-emerald-400 font-bold">🛡️ Sources vérifiées uniquement</span>
          <span class="text-gray-500 text-[11px]">(au moins 3 médias distincts)</span>
        </div>
        <input 
          type="checkbox" 
          bind:checked={onlyVerified}
          class="w-4 h-4 accent-emerald-500 rounded cursor-pointer"
        />
      </div>
    </div>

    <!-- CLUSTERS FEED LIST (MAGNETIC TILES) -->
    {#if isLoading}
      <div class="text-center py-16 space-y-3">
        <svg class="w-8 h-8 animate-spin text-cyan-400 mx-auto" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
        </svg>
        <p class="text-xs text-gray-400">Chargement instantané des tuiles Perplexity...</p>
      </div>
    {:else if filteredClusters.length === 0}
      <div class="bg-gray-900/40 border border-gray-800 rounded-3xl p-8 text-center text-gray-400 space-y-2">
        <p class="text-sm font-semibold">Aucun événement ne correspond aux filtres sélectionnés.</p>
        <p class="text-xs text-gray-500">Essayez de décocher 'Sources vérifiées' ou de changer de catégorie.</p>
      </div>
    {:else}
      <div class="space-y-6">
        {#each filteredClusters as cluster, idx}
          {@const distinctFeeds = getDistinctFeedCount(cluster)}
          {@const isVerified = distinctFeeds >= 3}
          {@const coverImg = getClusterImage(cluster)}
          {@const titleText = getClusterTitle(cluster)}
          {@const teaserText = getTeaserSentence(cluster)}

          <!-- COMPACT TILE CARD (SNAP-START MAGNET) -->
          <div 
            on:click={() => openCluster(cluster)}
            class="snap-start scroll-mt-4 sm:scroll-mt-6 bg-gradient-to-b from-gray-900 to-gray-950 border border-gray-800/80 hover:border-cyan-500/60 rounded-3xl overflow-hidden shadow-2xl transition-all cursor-pointer group space-y-0 relative"
          >
            
            <!-- Cover Image Preview -->
            <div class="w-full h-44 sm:h-52 overflow-hidden relative">
              <ProgressiveImage 
                src={coverImg} 
                fallbackSrc={getCategoryFallbackImage(cluster.category)}
                alt={titleText} 
                imgClass="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
              />
              <div class="absolute inset-0 bg-gradient-to-t from-gray-950 via-gray-950/40 to-transparent pointer-events-none"></div>
              
              <!-- Badges on top of Image -->
              <div class="absolute top-4 left-4 flex items-center gap-2">
                <span class="text-[10px] font-black uppercase tracking-wider px-2.5 py-1 rounded-full bg-gray-950/90 text-cyan-400 border border-cyan-800/60 backdrop-blur-md">
                  {cluster.category || 'Général'}
                </span>

                {#if isVerified}
                  <span class="text-[10px] font-black uppercase tracking-wider px-2.5 py-1 rounded-full bg-emerald-950/90 text-emerald-400 border border-emerald-700/80 backdrop-blur-md flex items-center gap-1 shadow-lg">
                    <span>🛡️ Vérifié ({distinctFeeds} médias)</span>
                  </span>
                {/if}
              </div>
            </div>

            <!-- Tile Body: Title + Short Teaser -->
            <div class="p-5 sm:p-6 space-y-3">
              
              <h2 class="text-xl sm:text-2xl font-black text-white group-hover:text-cyan-400 transition-colors leading-snug">
                {titleText}
              </h2>

              <p class="text-sm text-gray-300 font-normal leading-relaxed line-clamp-2">
                {teaserText}
              </p>

              <!-- Media badges & Click Prompt -->
              <div class="pt-2 border-t border-gray-900 flex items-center justify-between gap-2">
                <div class="flex flex-wrap items-center gap-1.5">
                  <span class="text-[11px] font-bold text-gray-500">Recoupé par :</span>
                  {#each cluster.articles.slice(0, 3) as art}
                    <span class="text-[10px] font-bold bg-gray-900 text-purple-300 px-2 py-0.5 rounded-md border border-gray-800">
                      {getLanguageFlag(art.language)} {art.feed_title || 'RSS'}
                    </span>
                  {/each}
                  {#if cluster.articles.length > 3}
                    <span class="text-[10px] text-gray-500 font-bold">+{cluster.articles.length - 3}</span>
                  {/if}
                </div>

                <span class="text-xs font-bold text-cyan-400 group-hover:underline flex items-center gap-1 shrink-0">
                  <span>Tout voir</span>
                  <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"></path></svg>
                </span>
              </div>

            </div>

          </div>
        {/each}
      </div>
    {/if}

  </div>
</div>

<!-- FULL DETAIL VIEW / MODAL (PARALLAX HERO HEADER & FULL SUMMARY) -->
{#if activeCluster}
  <PerplexityCard 
    cluster={activeCluster}
    onClose={() => activeCluster = null}
    activeSynth={syntheses[activeCluster.cluster_id] || activeCluster.precomputed_synthesis}
    synthLoading={synthLoading[activeCluster.cluster_id]}
    relatedClusters={relatedClusters}
    onRelatedClick={openCluster}
  />
{/if}

