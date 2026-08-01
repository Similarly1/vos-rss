<script>
  import { onMount, onDestroy } from 'svelte';
  import * as d3 from 'd3-geo';
  import { feature } from 'topojson-client';
  import PerplexityCard from './PerplexityCard.svelte';

  const GEO_URL = "https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json";

  const CATEGORY_CONFIG = {
    "Suisse": { label: "🇨🇭 Suisse", color: "#ef4444" },
    "Europe": { label: "🇪🇺 Europe", color: "#3b82f6" },
    "Monde": { label: "🌍 Monde", color: "#10b981" },
    "Technologie": { label: "💻 Technologie", color: "#8b5cf6" },
    "Science": { label: "🔬 Science", color: "#ec4899" },
    "Économie": { label: "📈 Économie", color: "#f59e0b" },
    "Général": { label: "📁 Général", color: "#6b7280" }
  };

  // Coordinates gazetteer fallback for known locations
  const LOCATION_COORDINATES = {
    'suisse': [8.2275, 46.8182],
    'switzerland': [8.2275, 46.8182],
    'genève': [6.1432, 46.2044],
    'geneva': [6.1432, 46.2044],
    'lausanne': [6.6323, 46.5197],
    'zurich': [8.5417, 47.3769],
    'zürich': [8.5417, 47.3769],
    'berne': [7.4474, 46.9480],
    'bern': [7.4474, 46.9480],
    'vaud': [6.6323, 46.5197],
    'valais': [7.3601, 46.2331],
    'france': [2.2137, 46.2276],
    'paris': [2.3522, 48.8566],
    'ukraine': [31.1656, 48.3794],
    'kyiv': [30.5234, 50.4501],
    'kiev': [30.5234, 50.4501],
    'états-unis': [-95.7129, 37.0902],
    'usa': [-95.7129, 37.0902],
    'washington': [-77.0369, 38.9072],
    'tokyo': [139.6917, 35.6895],
    'japon': [138.2529, 36.2048],
    'royaume-uni': [-3.4360, 55.3781],
    'londres': [-0.1278, 51.5074],
    'london': [-0.1278, 51.5074],
    'allemagne': [10.4515, 51.1657],
    'berlin': [13.4050, 52.5200],
    'gaza': [34.4668, 31.5017],
    'israël': [34.8516, 31.0461],
    'chine': [104.1954, 35.8617],
    'beijing': [116.4074, 39.9042],
    'pékin': [116.4074, 39.9042]
  };

  let containerRef;
  let dimensions = { width: 960, height: 520 };
  let topoData = null;
  let clusters = [];
  let isLoading = false;
  let totalGeolocated = 0;

  let hoveredId = null;
  let tooltip = null;
  let tooltipTimer = null;
  let selectedCluster = null;

  let geoPaths = [];
  let graticulePath = "";
  let spherePath = "";
  let markerPositions = [];
  let resizeObserver;

  $: projection = d3.geoNaturalEarth1()
    .scale((dimensions.width / 640) * 100)
    .translate([dimensions.width / 2, dimensions.height / 2]);

  function getClusterCoordinates(c) {
    const synth = c.precomputed_synthesis || {};
    if (synth.longitude != null && synth.latitude != null) {
      return [Number(synth.longitude), Number(synth.latitude)];
    }
    if (c.longitude != null && c.latitude != null) {
      return [Number(c.longitude), Number(c.latitude)];
    }

    const locName = (synth.location_name || c.location_name || "").toLowerCase().trim();
    if (locName && LOCATION_COORDINATES[locName]) {
      return LOCATION_COORDINATES[locName];
    }

    // Try finding known keywords in topic title or category
    const text = ((c.topic_title || "") + " " + (c.category || "")).toLowerCase();
    for (const [key, coords] of Object.entries(LOCATION_COORDINATES)) {
      if (text.includes(key)) {
        return coords;
      }
    }

    return null;
  }

  let groupedClustersList = null;

  $: {
    if (topoData && projection) {
      const countries = feature(topoData, topoData.objects.countries);
      const pathGen = d3.geoPath().projection(projection);
      geoPaths = countries.features.map(f => pathGen(f) || "");
      graticulePath = pathGen(d3.geoGraticule()()) || "";
      spherePath = pathGen({ type: "Sphere" }) || "";

      // 1. Calculate raw screen coordinates for each cluster
      const rawPoints = [];
      clusters.forEach(c => {
        const coords = getClusterCoordinates(c);
        if (!coords) return;
        const pos = projection(coords);
        if (!pos) return;
        rawPoints.push({ cluster: c, x: pos[0], y: pos[1], coords });
      });

      // 2. Group close markers (within 28px distance) to prevent overlap
      const grouped = [];
      const visited = new Set();
      const DIST_THRESHOLD = 28;

      for (let i = 0; i < rawPoints.length; i++) {
        if (visited.has(i)) continue;
        const pt_i = rawPoints[i];
        visited.add(i);
        const group = [pt_i.cluster];
        let sumX = pt_i.x;
        let sumY = pt_i.y;

        for (let j = i + 1; j < rawPoints.length; j++) {
          if (visited.has(j)) continue;
          const pt_j = rawPoints[j];
          const dist = Math.hypot(pt_i.x - pt_j.x, pt_i.y - pt_j.y);
          if (dist < DIST_THRESHOLD) {
            visited.add(j);
            group.push(pt_j.cluster);
            sumX += pt_j.x;
            sumY += pt_j.y;
          }
        }

        grouped.push({
          id: `marker_${pt_i.cluster.cluster_id}`,
          x: sumX / group.length,
          y: sumY / group.length,
          count: group.length,
          clusters: group,
          cluster: group[0]
        });
      }

      markerPositions = grouped;
      totalGeolocated = rawPoints.length;
    }
  }

  onMount(async () => {
    isLoading = true;
    try {
      const [rGeo, rClust] = await Promise.all([
        fetch(GEO_URL).then(res => res.json()),
        fetch('/api/clustering/clusters?threshold=0.85&cluster_type=events').then(res => res.json())
      ]);
      topoData = rGeo;
      
      clusters = rClust.clusters || [];
    } catch (e) {
      console.error("Erreur chargement carte/clusters:", e);
    } finally {
      isLoading = false;
    }

    const updateDim = () => {
      if (!containerRef) return;
      const w = containerRef.clientWidth;
      const h = Math.max(340, Math.min(560, w * 0.54));
      dimensions = { width: w, height: h };
    };
    updateDim();

    resizeObserver = new ResizeObserver(updateDim);
    if (containerRef) resizeObserver.observe(containerRef);
  });

  onDestroy(() => {
    if (resizeObserver) resizeObserver.disconnect();
    if (tooltipTimer) clearTimeout(tooltipTimer);
  });

  function handleMarkerEnter(item, e) {
    if (tooltipTimer) clearTimeout(tooltipTimer);
    const rect = containerRef.getBoundingClientRect();
    const cx = e.clientX - rect.left;
    const cy = e.clientY - rect.top;
    const side = cx > dimensions.width * 0.62 ? "left" : "right";
    hoveredId = item.id;
    tooltip = { item, x: cx, y: cy, side };
  }

  function handleMarkerLeave() {
    tooltipTimer = setTimeout(() => {
      tooltip = null;
      hoveredId = null;
    }, 220);
  }

  function decodeHtmlEntities(str) {
    if (!str) return '';
    let text = str;
    text = text.replace(/&#(\d+);/g, (m, dec) => String.fromCharCode(dec));
    text = text.replace(/&#x([0-9a-fA-F]+);/g, (m, hex) => String.fromCharCode(parseInt(hex, 16)));
    text = text.replace(/&quot;/g, '"').replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&#039;/g, "'").replace(/&apos;/g, "'").replace(/&rsquo;/g, "’").replace(/&nbsp;/g, ' ');
    return text;
  }

  function cleanTextBoilerplate(str) {
    if (!str) return '';
    let text = str;
    text = text.replace(/<(script|style|header|nav|footer|form|svg|code)[^>]*>[\s\S]*?<\/\1>/gi, ' ');
    text = text.replace(/<[^>]+>/g, ' ');
    text = decodeHtmlEntities(text);
    text = text.replace(/(?:publish\s*['"][^'"]+['"]|data-sara-[a-zA-Z-]+|swiper\.[a-zA-Z.]+|x-swiper|freeMode|roundLengths|slidesPerView|slideTo|data-area|is-open|setTimeout|keyup\.escape|window\.dispatchEvent|POLYGON\s+DOM|HEADER\s+READY|EILMELDUNG\s+proto|headline|Zur\s+Merkliste|Teilen\s+X\.com|Facebook\s+E-Mail|Link\s+kopieren|Bild\s+vergrößern|Digital-Abo)[^\n.!?]*/gi, ' ');
    text = text.replace(/(?:publish|data-sara-[a-zA-Z-]+|swiper|freeMode|roundLengths|slidesPerView|slideTo|data-area|is-open|setTimeout|keyup|dispatchEvent|POLYGON|DOM|HEADER|READY|EILMELDUNG|proto|headline|Merkliste|Facebook|WhatsApp|Link\s+kopieren|Optionen|Teilen|Abo|Digital-Abo)/gi, ' ');
    text = text.replace(/(?:lg|md|sm|xl|2xl):[a-zA-Z0-9_-]+/g, ' ');
    text = text.replace(/(?:opacity-none|invisible|flex|grid|absolute|relative|overflow-hidden|hover:|focus:|opacity-none)[a-zA-Z0-9_-]*/gi, ' ');
    text = text.replace(/(?:BBC Homepage|Skip to content|Accessibility Help|Your account|Search BBC|More menu|Close menu|Menü öffnen|watchOverflow|isCollapsed|swiper-init|data-app-hidden|x-lazyload|Menü Startseite|Ausland)/gi, ' ');
    text = text.replace(/[^a-zA-Z0-9àâáäãåçéèêëìíîïñòóôöõøùúûüýÿÀÂÁÄÃÅÇÉÈÊËÌÍÎÏÑÒÓÔÖÕØÙÚÛÜÝŸæÆœŒ\s.,!?'"’«»()\[\]\-–—*_+€$@]/g, ' ');
    return text.replace(/\s+/g, ' ').trim();
  }

  function getClusterTitle(c) {
    if (c.precomputed_synthesis?.synthesis_title) {
      return cleanTextBoilerplate(c.precomputed_synthesis.synthesis_title);
    }
    return cleanTextBoilerplate(c.topic_title);
  }

  function getClusterTeaser(c) {
    const synth = c.precomputed_synthesis;
    if (synth && synth.summary && !synth.summary.startsWith('Erreur')) {
      return cleanTextBoilerplate(synth.summary);
    }
    const raw = c.articles?.[0]?.content || c.articles?.[0]?.description || c.articles?.[0]?.title || '';
    const clean = cleanTextBoilerplate(raw);
    return clean.slice(0, 180) + (clean.length > 180 ? '...' : '');
  }

  function handleMarkerClick(item) {
    if (item.count > 1) {
      groupedClustersList = item;
    } else {
      selectedCluster = item.cluster;
    }
  }
</script>

<div class="relative w-full h-full min-h-[460px] bg-background text-foreground overflow-hidden flex flex-col justify-center items-center select-none" bind:this={containerRef}>
  
  {#if isLoading}
    <div class="flex items-center justify-center gap-3 text-primary text-xs font-bold z-30">
      <div class="w-5 h-5 border-2 border-primary border-t-transparent rounded-full animate-spin"></div>
      <span class="text-muted-foreground">Analyse géographique des flux en cours...</span>
    </div>
  {:else}
    <!-- Status indicator top banner -->
    <div class="absolute top-4 left-4 z-20 flex items-center gap-2 px-3.5 py-2 rounded-full bg-card border border-border text-xs text-foreground shadow-md backdrop-blur-md">
      <span class="w-2.5 h-2.5 rounded-full {totalGeolocated > 0 ? 'bg-primary animate-pulse' : 'bg-amber-400'}"></span>
      <span class="font-bold">{totalGeolocated} événement(s) géolocalisé(s)</span>
      <span class="text-muted-foreground text-[11px]">({markerPositions.length} zones sur la carte)</span>
    </div>

    <!-- Map SVG -->
    <svg 
      viewBox="0 0 {dimensions.width} {dimensions.height}"
      class="w-full h-full max-h-[560px]"
    >
      <defs>
        <filter id="glow-sm" x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation="2.5" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
        <filter id="glow-lg" x="-100%" y="-100%" width="300%" height="300%">
          <feGaussianBlur stdDeviation="7" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>

      <!-- Graticule -->
      <path d={graticulePath} fill="none" stroke="var(--border)" stroke-width="0.5" opacity="0.4" />

      <!-- Countries -->
      <g>
        {#each geoPaths as d}
          <path
            {d}
            fill="var(--card)"
            stroke="var(--border)"
            stroke-width="0.6"
            class="transition-colors duration-200 hover:fill-primary/20 cursor-pointer"
          />
        {/each}
      </g>

      <!-- Sphere border -->
      <path d={spherePath} fill="none" stroke="rgba(148,163,184,0.15)" stroke-width="1" />

      <!-- Markers -->
      {#each markerPositions as item}
        {@const c = item.cluster}
        {@const cfg = CATEGORY_CONFIG[c.category] || CATEGORY_CONFIG["Général"]}
        {@const isHovered = hoveredId === item.id}
        {@const isGrouped = item.count > 1}
        
        <!-- svelte-ignore a11y_click_events_have_key_events -->
        <!-- svelte-ignore a11y_no_static_element_interactions -->
        <g
          transform="translate({item.x},{item.y})"
          class="cursor-pointer group"
          on:mouseenter={(e) => handleMarkerEnter(item, e)}
          on:mouseleave={handleMarkerLeave}
          on:click={() => handleMarkerClick(item)}
        >
          <!-- Outer pulse ring -->
          <circle fill={cfg.color} opacity="0" r={isGrouped ? "10" : "6"}>
            <animate attributeName="r" values={isHovered ? "12;32;12" : "8;24;8"} dur={isHovered ? "1.4s" : "2.2s"} repeatCount="indefinite" />
            <animate attributeName="opacity" values="0.4;0;0.4" dur={isHovered ? "1.4s" : "2.2s"} repeatCount="indefinite" />
          </circle>

          {#if isHovered}
            <circle r="12" fill={cfg.color} opacity="0.3" filter="url(#glow-lg)" />
          {/if}

          <!-- Main Marker Circle -->
          <circle
            r={isGrouped ? (isHovered ? 13 : 11) : (isHovered ? 8 : 6)}
            fill={cfg.color}
            stroke="rgba(255,255,255,0.9)"
            stroke-width={isHovered ? 2.5 : 1.8}
            filter="url(#glow-sm)"
            style="transition: r 0.15s, stroke-width 0.15s"
          />

          {#if isGrouped}
            <!-- Counter text inside cluster marker -->
            <text
              y="3.5"
              text-anchor="middle"
              fill="white"
              font-size="10"
              font-weight="bold"
              pointer-events="none"
            >
              {item.count}
            </text>
          {:else}
            <circle r={isHovered ? 3 : 2} fill="white" opacity="0.95" style="transition: r 0.15s" />
          {/if}
        </g>
      {/each}
    </svg>

    <!-- Tooltip -->
    {#if tooltip}
      {@const item = tooltip.item}
      {@const c = item.cluster}
      {@const cfg = CATEGORY_CONFIG[c.category] || CATEGORY_CONFIG["Général"]}
      
      <!-- svelte-ignore a11y_no_static_element_interactions -->
      <div 
        class="pointer-events-auto absolute z-30"
        style="
          left: {tooltip.side === 'right' ? Math.min(tooltip.x + 20, dimensions.width - 300) : 'auto'};
          right: {tooltip.side === 'left' ? Math.max(dimensions.width - tooltip.x + 20, 8) : 'auto'};
          top: {Math.min(Math.max(tooltip.y - 24, 8), dimensions.height - 260)}px;
        "
        on:mouseenter={() => { if (tooltipTimer) clearTimeout(tooltipTimer); }}
        on:mouseleave={handleMarkerLeave}
      >
        <!-- svelte-ignore a11y_click_events_have_key_events -->
        <!-- svelte-ignore a11y_no_static_element_interactions -->
        <div 
          on:click={() => handleMarkerClick(item)}
          class="w-72 rounded-2xl overflow-hidden shadow-2xl border border-white/10 text-white cursor-pointer hover:border-cyan-500/60 transition-all" 
          style="background: rgba(8, 16, 32, 0.97); backdrop-filter: blur(16px);"
        >
          <div class="p-3.5 space-y-2">
            <div class="flex items-center justify-between">
              <span class="inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full text-white" style="background-color: {cfg.color}">
                {cfg.label}
              </span>
              {#if item.count > 1}
                <span class="text-[10px] bg-cyan-950 text-cyan-300 px-2 py-0.5 rounded-full font-bold border border-cyan-800/50">
                  {item.count} événements ici
                </span>
              {/if}
            </div>

            <h3 class="font-bold text-white text-xs leading-snug">
              {getClusterTitle(c)}
            </h3>
            <p class="text-gray-400 text-[11px] leading-relaxed line-clamp-3">
              {getClusterTeaser(c)}
            </p>
            <button 
              on:click|stopPropagation={() => handleMarkerClick(item)}
              class="w-full pt-2 text-[10px] text-cyan-400 flex items-center gap-1 font-medium hover:text-cyan-300 hover:underline text-left cursor-pointer"
            >
              <span>{item.count > 1 ? `Voir les ${item.count} événements de cette zone ➔` : 'Cliquez pour lire la synthèse complète ➔'}</span>
            </button>
          </div>
        </div>
      </div>
    {/if}
  {/if}

</div>

<!-- Multi-event Location Drawer Modal -->
{#if groupedClustersList}
  <div class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-md">
    <div class="bg-gray-900 border border-gray-800 rounded-3xl shadow-2xl w-full max-w-lg overflow-hidden flex flex-col max-h-[85vh] text-white">
      <div class="p-5 border-b border-gray-800 flex justify-between items-center bg-background">
        <div>
          <h3 class="font-bold text-base flex items-center gap-2">
            <span>📍 Événements géolocalisés ({groupedClustersList.count})</span>
          </h3>
          <p class="text-xs text-gray-400">Sélectionnez une actualité à consulter</p>
        </div>
        <button on:click={() => groupedClustersList = null} class="text-gray-400 hover:text-white p-2 rounded-full hover:bg-card transition-colors">
          ✕
        </button>
      </div>

      <div class="p-5 overflow-y-auto flex-1 space-y-3">
        {#each groupedClustersList.clusters as c}
          {@const cfg = CATEGORY_CONFIG[c.category] || CATEGORY_CONFIG["Général"]}
          <!-- svelte-ignore a11y_click_events_have_key_events -->
          <!-- svelte-ignore a11y_no_static_element_interactions -->
          <div 
            on:click={() => { selectedCluster = c; groupedClustersList = null; }}
            class="p-4 bg-background border border-gray-800/80 hover:border-cyan-500/60 rounded-2xl cursor-pointer transition-all hover:scale-[1.01] space-y-2 group"
          >
            <div class="flex justify-between items-center text-xs">
              <span class="px-2 py-0.5 rounded-full text-[10px] font-semibold text-white" style="background-color: {cfg.color}">
                {cfg.label}
              </span>
              <span class="text-gray-400 text-[11px]">{c.latest_published_date ? new Date(c.latest_published_date).toLocaleDateString('fr-FR', {day: 'numeric', month: 'short', hour: '2-digit', minute:'2-digit'}) : ''}</span>
            </div>
            <h4 class="font-bold text-sm text-gray-100 group-hover:text-cyan-300 transition-colors leading-snug">
              {getClusterTitle(c)}
            </h4>
            <p class="text-xs text-gray-400 line-clamp-2 leading-relaxed">
              {getClusterTeaser(c)}
            </p>
          </div>
        {/each}
      </div>
    </div>
  </div>
{/if}

<!-- Drawer / Card detail modal -->
{#if selectedCluster}
  <PerplexityCard 
    cluster={selectedCluster}
    onClose={() => selectedCluster = null}
  />
{/if}
