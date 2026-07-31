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

  $: {
    if (topoData && projection) {
      const countries = feature(topoData, topoData.objects.countries);
      const pathGen = d3.geoPath().projection(projection);
      geoPaths = countries.features.map(f => pathGen(f) || "");
      graticulePath = pathGen(d3.geoGraticule()()) || "";
      spherePath = pathGen({ type: "Sphere" }) || "";

      markerPositions = clusters.map(c => {
        const coords = getClusterCoordinates(c);
        if (!coords) return null;
        const pos = projection(coords);
        if (!pos) return null;
        return { cluster: c, x: pos[0], y: pos[1], coords };
      }).filter(Boolean);
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
    hoveredId = item.cluster.cluster_id;
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
    text = text.replace(/&quot;/g, '"').replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&#039;/g, "'").replace(/&nbsp;/g, ' ');
    return text;
  }

  function cleanTextBoilerplate(str) {
    if (!str) return '';
    let text = str;
    text = text.replace(/<(script|style|header|nav|footer|form|svg|code)[^>]*>[\s\S]*?<\/\1>/gi, ' ');
    text = text.replace(/<[^>]+>/g, ' ');
    text = decodeHtmlEntities(text);
    text = text.replace(/(?:lg|md|sm|xl|2xl):[a-zA-Z0-9_-]+/g, ' ');
    text = text.replace(/(?:opacity-none|invisible|flex|grid|absolute|relative|overflow-hidden|hover:|focus:|opacity-none)[a-zA-Z0-9_-]*/gi, ' ');
    text = text.replace(/(?:BBC Homepage|Skip to content|Accessibility Help|Your account|Search BBC|More menu|Close menu|Menü öffnen|watchOverflow|isCollapsed|swiper-init|data-app-hidden|x-lazyload|Menü Startseite|Ausland)/gi, ' ');
    text = text.replace(/[^a-zA-Z0-9àâáäãåçéèêëìíîïñòóôöõøùúûüýÿÀÂÁÄÃÅÇÉÈÊËÌÍÎÏÑÒÓÔÖÕØÙÚÛÜÝŸæÆœŒ\s.,!?'"–-]/g, ' ');
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

  function handleMarkerClick(cluster) {
    selectedCluster = cluster;
  }
</script>

<div class="relative w-full h-full min-h-[460px] bg-[#040814] overflow-hidden flex flex-col justify-center items-center select-none" bind:this={containerRef}>
  
  {#if isLoading}
    <div class="flex items-center justify-center gap-3 text-cyan-400 text-xs font-semibold z-30">
      <div class="w-5 h-5 border-2 border-cyan-400 border-t-transparent rounded-full animate-spin"></div>
      <span>Analyse géographique des flux en cours...</span>
    </div>
  {:else}
    <!-- Status indicator top banner -->
    <div class="absolute top-4 left-4 z-20 flex items-center gap-2 px-3 py-1.5 rounded-full bg-gray-900/80 border border-white/10 text-[11px] backdrop-blur-md text-gray-300">
      <span class="w-2 h-2 rounded-full {markerPositions.length > 0 ? 'bg-emerald-400 animate-pulse' : 'bg-amber-400'}"></span>
      <span>{markerPositions.length} événement(s) géolocalisé(s) sur la carte</span>
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
      <path d={graticulePath} fill="none" stroke="rgba(148,163,184,0.05)" stroke-width="0.5" />

      <!-- Countries -->
      <g>
        {#each geoPaths as d}
          <path
            {d}
            fill="rgba(15,23,42,0.85)"
            stroke="rgba(51,65,85,0.4)"
            stroke-width="0.6"
            class="transition-colors duration-200 hover:fill-slate-800"
          />
        {/each}
      </g>

      <!-- Sphere border -->
      <path d={spherePath} fill="none" stroke="rgba(148,163,184,0.15)" stroke-width="1" />

      <!-- Markers -->
      {#each markerPositions as item}
        {@const c = item.cluster}
        {@const cfg = CATEGORY_CONFIG[c.category] || CATEGORY_CONFIG["Général"]}
        {@const isHovered = hoveredId === c.cluster_id}
        
        <!-- svelte-ignore a11y_click_events_have_key_events -->
        <!-- svelte-ignore a11y_no_static_element_interactions -->
        <g
          transform="translate({item.x},{item.y})"
          class="cursor-pointer"
          on:mouseenter={(e) => handleMarkerEnter(item, e)}
          on:mouseleave={handleMarkerLeave}
          on:click={() => handleMarkerClick(c)}
        >
          <!-- Outer pulse ring -->
          <circle fill={cfg.color} opacity="0" r="6">
            <animate attributeName="r" values={isHovered ? "8;28;8" : "6;22;6"} dur={isHovered ? "1.4s" : "2.2s"} repeatCount="indefinite" />
            <animate attributeName="opacity" values="0.35;0;0.35" dur={isHovered ? "1.4s" : "2.2s"} repeatCount="indefinite" />
          </circle>

          <!-- Mid pulse ring -->
          <circle fill={cfg.color} opacity="0" r="4">
            <animate attributeName="r" values={isHovered ? "5;18;5" : "4;14;4"} dur={isHovered ? "1.4s" : "2.2s"} begin="0.4s" repeatCount="indefinite" />
            <animate attributeName="opacity" values="0.5;0;0.5" dur={isHovered ? "1.4s" : "2.2s"} begin="0.4s" repeatCount="indefinite" />
          </circle>

          {#if isHovered}
            <circle r="10" fill={cfg.color} opacity="0.25" filter="url(#glow-lg)" />
          {/if}

          <circle
            r={isHovered ? 8 : 6}
            fill={cfg.color}
            stroke="rgba(255,255,255,0.85)"
            stroke-width={isHovered ? 2 : 1.5}
            filter="url(#glow-sm)"
            style="transition: r 0.15s, stroke-width 0.15s"
          />

          <circle r={isHovered ? 3 : 2} fill="white" opacity="0.95" style="transition: r 0.15s" />
        </g>
      {/each}
    </svg>

    <!-- Tooltip -->
    {#if tooltip}
      {@const c = tooltip.item.cluster}
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
        <div class="w-72 rounded-2xl overflow-hidden shadow-2xl border border-white/10 text-white" style="background: rgba(8, 16, 32, 0.97); backdrop-filter: blur(16px);">
          <div class="p-3.5 space-y-2">
            <span class="inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full text-white" style="background-color: {cfg.color}">
              {cfg.label}
            </span>
            <h3 class="font-bold text-white text-xs leading-snug">
              {getClusterTitle(c)}
            </h3>
            <p class="text-gray-400 text-[11px] leading-relaxed line-clamp-3">
              {getClusterTeaser(c)}
            </p>
            <div class="pt-2 text-[10px] text-cyan-400 flex items-center gap-1 font-medium">
              <span>Cliquez pour ouvrir la carte complète ➔</span>
            </div>
          </div>
        </div>
      </div>
    {/if}
  {/if}

</div>

<!-- Drawer / Card detail modal -->
{#if selectedCluster}
  <PerplexityCard 
    cluster={selectedCluster}
    onClose={() => selectedCluster = null}
  />
{/if}
