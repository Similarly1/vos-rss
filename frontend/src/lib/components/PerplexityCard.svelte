<script>
  import { mistralApiKey, geminiApiKey, synthesisProvider, selectedMistralDiscoverModel, selectedGeminiDiscoverModel } from '../stores/appState.js';
  import { playTrack, selectedVoice, sanitizeTextForSpeech } from '../stores/audioStore.js';
  import ProgressiveImage from './ProgressiveImage.svelte';

  export let cluster;
  export let onClose;
  export let activeSynth = null;
  export let synthLoading = false;
  export let relatedClusters = [];
  export let onRelatedClick = (c) => {};

  // Local state for synthesis fallback if activeSynth is not provided
  let localSynthLoading = false;
  let localAudioLoading = false;
  let fetchedSynth = null;

  const THEME_FALLBACK_IMAGES = {
    'Suisse': 'https://images.unsplash.com/photo-1530122037265-a5f1f91d3b99?auto=format&fit=crop&w=1200&q=80',
    'Europe': 'https://images.unsplash.com/photo-1467269204594-9661b134dd2b?auto=format&fit=crop&w=1200&q=80',
    'Monde': 'https://images.unsplash.com/photo-1451187580459-43490279c0fa?auto=format&fit=crop&w=1200&q=80',
    'Technologie': 'https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?auto=format&fit=crop&w=1200&q=80',
    'Science': 'https://images.unsplash.com/photo-1451187580459-43490279c0fa?auto=format&fit=crop&w=1200&q=80',
    'Économie': 'https://images.unsplash.com/photo-1611974789855-9c2a0a7236a3?auto=format&fit=crop&w=1200&q=80',
    'Général': 'https://images.unsplash.com/photo-1504711434969-e33886168f5c?auto=format&fit=crop&w=1200&q=80'
  };

  $: displaySynth = activeSynth || fetchedSynth || cluster?.precomputed_synthesis;
  $: isSynthLoading = synthLoading || localSynthLoading;

  $: if (cluster) {
    checkAndFetchSynthesis(cluster);
  }

  function isLowQualityOrEnglish(synth, c) {
    if (!synth) return true;
    const text = (synth.synthesis_title || '') + ' ' + (synth.summary || '');
    if (!text || text.length < 35) return true;
    // Check if raw JS code leaked into synthesis
    if (/publish\s*['"]|swiper\.|freeMode|slidesPerView|data-sara-|data-area|is-open|POLYGON|EILMELDUNG/i.test(text)) return true;
    
    // Check if title/summary is German or English when target language should be French
    const title = synth.synthesis_title || c?.topic_title || '';
    const deWords = /\b(der|die|das|und|ist|nicht|welche|forderungen|diskutiert|werden|anschlag|auf|den|eilmeldung|stadt|um|im|mit|zur|nach|vom|über|aus)\b/i;
    const enWords = /\b(the|and|is|in|at|which|were|that|from|with|this|have|been|will|today|yesterday|says|said)\b/i;
    const frWords = /\b(le|la|les|des|du|dans|un|une|est|sur|qui|par|pour|avec|sont|aux)\b/i;

    const isGerman = deWords.test(title) && !frWords.test(title);
    const isEnglish = enWords.test(title) && !frWords.test(title);
    return isGerman || isEnglish;
  }

  async function checkAndFetchSynthesis(c) {
    if (!c || activeSynth) return;
    const current = fetchedSynth || c.precomputed_synthesis;
    if (current && !isLowQualityOrEnglish(current, c)) return;
    if (!c.articles || c.articles.length === 0) return;

    localSynthLoading = true;
    try {
      const activeProvider = $synthesisProvider || ($mistralApiKey ? 'mistral' : 'gemini');
      const activeKey = activeProvider === 'gemini' ? $geminiApiKey : $mistralApiKey;
      const activeModel = activeProvider === 'gemini' ? $selectedGeminiDiscoverModel : $selectedMistralDiscoverModel;

      const res = await fetch('/api/clustering/synthesize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          articles: c.articles,
          provider: activeProvider,
          api_key: activeKey || null,
          model: activeModel
        })
      });

      const result = await res.json();
      if (res.ok && result.data) {
        fetchedSynth = result.data;
      }
    } catch (err) {
      console.error("Erreur auto-synthèse PerplexityCard:", err);
    } finally {
      localSynthLoading = false;
    }
  }

  function decodeHtmlEntities(str) {
    if (!str) return '';
    let text = str;
    text = text.replace(/&rsquo;/g, "'").replace(/&apos;/g, "'").replace(/&#39;/g, "'").replace(/&#039;/g, "'").replace(/’/g, "'");
    text = text.replace(/&#(\d+);/g, (m, dec) => String.fromCharCode(dec));
    text = text.replace(/&#x([0-9a-fA-F]+);/g, (m, hex) => String.fromCharCode(parseInt(hex, 16)));
    text = text.replace(/&quot;/g, '"').replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&nbsp;/g, ' ');
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
    // Remove Javascript/Swiper/UI boilerplate leakage
    text = text.replace(/(?:publish\s*['"][^'"]+['"]|data-sara-[a-zA-Z-]+|swiper\.[a-zA-Z.]+|x-swiper|freeMode|roundLengths|slidesPerView|slideTo|data-area|is-open|setTimeout|keyup\.escape|window\.dispatchEvent|POLYGON\s+DOM|HEADER\s+READY|EILMELDUNG\s+proto|headline|Zur\s+Merkliste|Teilen\s+X\.com|Facebook\s+E-Mail|Link\s+kopieren|Bild\s+vergrößern|Digital-Abo)[^\n.!?]*/gi, ' ');
    text = text.replace(/(?:publish|data-sara-[a-zA-Z-]+|swiper|freeMode|roundLengths|slidesPerView|slideTo|data-area|is-open|setTimeout|keyup|dispatchEvent|POLYGON|DOM|HEADER|READY|EILMELDUNG|proto|headline|Merkliste|Facebook|WhatsApp|Link\s+kopieren|Optionen|Teilen|Abo|Digital-Abo)/gi, ' ');
    text = text.replace(/(?:lg|md|sm|xl|2xl):[a-zA-Z0-9_-]+/g, ' ');
    text = text.replace(/(?:opacity-none|invisible|flex|grid|absolute|relative|overflow-hidden|hover:|focus:|opacity-none)[a-zA-Z0-9_-]*/gi, ' ');
    text = text.replace(/(?:BBC Homepage|Skip to content|Accessibility Help|Your account|Search BBC|More menu|Close menu|Menü öffnen|watchOverflow|isCollapsed|swiper-init|data-app-hidden|x-lazyload|Menü Startseite|Ausland)/gi, ' ');
    // Remove orphaned non-text noise (preserving single quote and typographic apostrophe)
    text = text.replace(/[^a-zA-Z0-9àâáäãåçéèêëìíîïñòóôöõøùúûüýÿÀÂÁÄÃÅÇÉÈÊËÌÍÎÏÑÒÓÔÖÕØÙÚÛÜÝŸæÆœŒ\s.,!?'"’–-]/g, ' ');
    return text.replace(/\s+/g, ' ').trim();
  }

  function renderMarkdownHtml(text) {
    if (!text) return '';
    let clean = cleanTextBoilerplate(text);
    clean = clean.replace(/\*\*(.*?)\*\*/g, '<strong class="font-black text-foreground bg-primary/20 px-1.5 py-0.5 rounded border border-primary/40">$1</strong>');
    clean = clean.replace(/\*(.*?)\*/g, '<em class="italic text-muted-foreground">$1</em>');
    const paragraphs = clean.split(/\n\s*\n/);
    return paragraphs.map(p => `<p class="leading-relaxed mb-3">${p.trim()}</p>`).join('');
  }

  function getClusterTitle(c) {
    if (displaySynth && displaySynth.synthesis_title) return displaySynth.synthesis_title;
    return cleanTextBoilerplate(c.topic_title);
  }

  function getCategoryFallbackImage(category) {
    const cat = category || 'Général';
    return THEME_FALLBACK_IMAGES[cat] || THEME_FALLBACK_IMAGES['Général'];
  }

  function getClusterImage(c) {
    if (c) {
      if (c.image_url) return c.image_url;
      if (c.articles && Array.isArray(c.articles)) {
        for (const art of c.articles) {
          if (art && art.image_url && typeof art.image_url === 'string' && art.image_url.trim().length > 0) {
            return art.image_url;
          }
        }
      }
    }
    return getCategoryFallbackImage(c ? c.category : null);
  }

  async function handleListenSummary() {
    if (!displaySynth || !displaySynth.summary) return;
    localAudioLoading = true;
    const title = getClusterTitle(cluster);
    const summaryText = displaySynth.summary;
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
      }
    } catch (err) {
      alert("Erreur de connexion avec le service audio.");
    } finally {
      localAudioLoading = false;
    }
  }

  function getLanguageFlag(lang) {
    if (!lang) return "🇫🇷";
    const l = lang.toLowerCase();
    if (l === "en") return "🇬🇧";
    if (l === "de") return "🇩🇪";
    if (l === "es") return "🇪🇸";
    return "🇫🇷";
  }

  function getDistinctFeedCount(c) {
    if (!c) return 0;
    if (c.distinct_feed_count) return c.distinct_feed_count;
    if (c.articles && Array.isArray(c.articles)) {
      const feeds = new Set(c.articles.map(a => a.feed_title || 'RSS'));
      return feeds.size;
    }
    return 1;
  }

  $: activeImg = cluster ? getClusterImage(cluster) : '';
  $: activeTitle = cluster ? getClusterTitle(cluster) : '';
  $: activeFeedsCount = cluster ? getDistinctFeedCount(cluster) : 0;
  $: activeIsVerified = activeFeedsCount >= 3;
</script>

{#if cluster}
<!-- svelte-ignore a11y_click_events_have_key_events -->
<!-- svelte-ignore a11y_no_static_element_interactions -->
<div 
  on:click={onClose} 
  class="fixed inset-0 z-[100] flex items-start sm:items-center justify-center p-0 sm:p-4 bg-black/85 backdrop-blur-md overflow-hidden cursor-pointer"
>
  <!-- svelte-ignore a11y_click_events_have_key_events -->
  <!-- svelte-ignore a11y_no_static_element_interactions -->
  <div 
    on:click|stopPropagation={() => {}} 
    class="bg-card text-card-foreground w-full max-w-4xl h-[100dvh] sm:h-auto sm:max-h-[90vh] rounded-none sm:rounded-3xl shadow-2xl overflow-y-auto border-0 sm:border border-border relative flex flex-col pt-12 sm:pt-0 pb-24 sm:pb-8 cursor-default"
  >
    <button on:click={onClose} class="fixed sm:absolute top-3 right-3 sm:top-5 sm:right-5 z-50 p-2.5 sm:p-3 bg-card hover:bg-accent text-foreground rounded-full border border-border backdrop-blur-md shadow-2xl transition-all" title="Fermer la vue détaillée">
      <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
    </button>

    <div class="w-full h-64 sm:h-80 relative overflow-hidden shrink-0">
      <ProgressiveImage src={activeImg} fallbackSrc={getCategoryFallbackImage(cluster.category)} alt={activeTitle} imgClass="w-full h-full object-cover scale-105 transform transition-transform duration-700" />
      <div class="absolute inset-0 bg-gradient-to-t from-card via-card/60 to-transparent pointer-events-none"></div>
      <div class="absolute bottom-6 left-6 right-6 space-y-3">
        <div class="flex items-center gap-2">
          <span class="text-xs font-black uppercase tracking-wider px-3 py-1 rounded-full bg-card/90 text-primary border border-primary/80 backdrop-blur-md">{cluster.category || 'Général'}</span>
          {#if activeIsVerified}
            <span class="text-xs font-black uppercase tracking-wider px-3 py-1 rounded-full bg-primary/20 text-primary border border-primary/80 backdrop-blur-md">🛡️ Information Vérifiée ({activeFeedsCount} médias)</span>
          {/if}
        </div>
        <h1 class="text-2xl sm:text-3xl md:text-4xl font-black text-foreground leading-tight drop-shadow-md">{activeTitle}</h1>
      </div>
    </div>

    <div class="p-6 sm:p-8 space-y-8 flex-1">
      <div class="bg-card border border-border rounded-3xl p-6 space-y-5 shadow-xl">
        <div class="flex flex-wrap items-center justify-between gap-3 border-b border-border pb-4">
          <div class="flex items-center gap-2">
            <span class="text-xs font-black uppercase tracking-wider text-primary">✨ Synthèse Croisée Complète</span>
          </div>
          {#if displaySynth}
            <button on:click={handleListenSummary} disabled={localAudioLoading} class="px-4 py-2 bg-primary text-primary-foreground font-extrabold text-xs rounded-xl shadow-lg transition-all flex items-center gap-2 disabled:opacity-50">
              {#if localAudioLoading}
                <svg class="w-4 h-4 animate-spin text-primary-foreground" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path></svg>
                <span>Génération audio...</span>
              {:else}
                <svg class="w-4 h-4 fill-current" viewBox="0 0 24 24"><path d="M8 5v14l11-7z"></path></svg>
                <span>Écouter la synthèse (Voix Marie)</span>
              {/if}
            </button>
          {/if}
        </div>
        {#if isSynthLoading}
          <div class="space-y-4 py-2">
            <div class="flex items-center gap-3 text-xs text-primary bg-primary/10 border border-primary/20 p-3.5 rounded-2xl animate-pulse font-semibold">
              <svg class="w-4.5 h-4.5 animate-spin text-primary shrink-0" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path></svg>
              <span>Synthèse croisée par l'IA en cours de génération...</span>
            </div>
            <div class="space-y-2.5 animate-pulse">
              <div class="h-4 bg-muted/60 rounded-xl w-full"></div>
              <div class="h-4 bg-muted/60 rounded-xl w-11/12"></div>
              <div class="h-4 bg-muted/60 rounded-xl w-4/5"></div>
              <div class="h-4 bg-muted/60 rounded-xl w-5/6"></div>
            </div>
          </div>
        {:else if displaySynth}
          <div class="space-y-4">
            <div class="text-base text-foreground leading-relaxed font-sans space-y-3">
              {@html renderMarkdownHtml(displaySynth.summary)}
            </div>
            {#if (displaySynth.key_takeaways && displaySynth.key_takeaways.length > 0) || (displaySynth.key_points && displaySynth.key_points.length > 0)}
              {@const takeaways = displaySynth.key_takeaways || displaySynth.key_points}
              <div class="space-y-2 pt-4 border-t border-border">
                <span class="text-xs font-bold text-primary uppercase tracking-wider block mb-2">Points clés à retenir :</span>
                <ul class="space-y-2.5 text-xs sm:text-sm text-foreground">
                  {#each takeaways as point}
                    <li class="flex items-start gap-2.5 bg-background p-2.5 rounded-xl border border-border">
                      <span class="text-primary font-bold text-base mt-0.5">•</span>
                      <span class="leading-snug">{@html renderMarkdownHtml(point)}</span>
                    </li>
                  {/each}
                </ul>
              </div>
            {/if}
          </div>
        {:else}
          <p class="text-sm text-foreground leading-relaxed italic">{cleanTextBoilerplate(cluster.articles[0]?.content || cluster.articles[0]?.description || cluster.articles[0]?.title)}</p>
        {/if}
      </div>
      {#if cluster.articles && cluster.articles.length > 0}
        <div class="space-y-4">
          <h3 class="text-base font-bold text-foreground flex items-center gap-2"><span>📰 Sources d'information recoupées ({cluster.articles.length})</span></h3>
          <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {#each cluster.articles as art}
              <a href={art.url} target="_blank" rel="noreferrer" class="p-4 bg-card hover:bg-accent border border-border hover:border-primary/60 rounded-2xl transition-all space-y-2 group block">
                <div class="flex items-center justify-between text-xs">
                  <span class="font-extrabold text-primary flex items-center gap-1"><span>{getLanguageFlag(art.language)}</span><span>{art.feed_title || 'RSS'}</span></span>
                  <span class="text-[10px] text-muted-foreground">{art.published_date}</span>
                </div>
                <h4 class="font-bold text-sm text-foreground group-hover:text-primary transition-colors leading-snug line-clamp-2">{art.title}</h4>
                <span class="text-[11px] text-primary hover:underline flex items-center gap-1 font-semibold pt-1"><span>Lire l'article original</span><svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path></svg></span>
              </a>
            {/each}
          </div>
        </div>
      {/if}
      {#if relatedClusters && relatedClusters.length > 0}
        <div class="space-y-4 pt-4 border-t border-border">
          <h3 class="text-base font-bold text-foreground flex items-center gap-2"><span>🔗 Actualités en lien sur ce sujet</span></h3>
          <div class="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {#each relatedClusters as rel}
              {@const relImg = getClusterImage(rel)}
              {@const relTitle = getClusterTitle(rel)}
              <div on:click={() => onRelatedClick(rel)} class="bg-card hover:bg-accent border border-border hover:border-primary/60 rounded-2xl p-3.5 transition-all cursor-pointer space-y-2 group">
                <div class="w-full h-28 rounded-xl overflow-hidden relative">
                  <ProgressiveImage src={relImg} fallbackSrc={getCategoryFallbackImage(rel.category)} alt={relTitle} imgClass="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300" />
                </div>
                <span class="text-[10px] font-bold text-primary uppercase tracking-wider block">{rel.category || 'Général'}</span>
                <h4 class="font-bold text-xs text-foreground group-hover:text-primary line-clamp-2 leading-snug">{relTitle}</h4>
              </div>
            {/each}
          </div>
        </div>
      {/if}
    </div>
  </div>
</div>
{/if}
