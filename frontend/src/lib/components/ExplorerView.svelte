<script>
  import { fade, fly, slide, scale, blur } from 'svelte/transition';
  import { transitionType, transitionDuration } from '../stores/appState.js';
  import PerplexityFeedView from './PerplexityFeedView.svelte';
  import Culture3DShelvesView from './Culture3DShelvesView.svelte';
  import GeoMapView from './GeoMapView.svelte';

  const tabOrder = ['flux', 'culture', 'carte'];
  let activeTab = 'flux'; // 'flux' | 'culture' | 'carte'
  let subNavDirection = 1; // 1 = right (enters from x: 80), -1 = left (enters from x: -80)

  function selectTab(newTab) {
    if (newTab === activeTab) return;
    const prevIdx = tabOrder.indexOf(activeTab);
    const newIdx = tabOrder.indexOf(newTab);
    subNavDirection = newIdx > prevIdx ? 1 : -1;
    activeTab = newTab;
  }

  function customSubTransition(node) {
    const type = $transitionType;
    const duration = $transitionDuration;

    if (type === 'none' || duration <= 0) {
      return { duration: 0 };
    }
    if (type === 'fly') {
      // Horizontal / Lateral slide for internal sub-tabs
      return fly(node, { x: subNavDirection * 80, duration });
    }
    if (type === 'slide') {
      return slide(node, { duration });
    }
    if (type === 'scale') {
      return scale(node, { start: 0.95, duration });
    }
    if (type === 'blur') {
      return blur(node, { amount: 6, duration });
    }
    return fade(node, { duration });
  }
</script>

<div class="flex flex-col h-full bg-background text-foreground w-full overflow-hidden">
  
  <!-- Tabs Navigation Header -->
  <header class="flex items-center justify-between p-4 bg-card border-b border-border shrink-0 relative z-10 shadow-sm">
    <div class="flex items-center gap-3">
      <div class="w-8 h-8 rounded-lg bg-primary text-primary-foreground flex items-center justify-center font-black text-sm shadow-sm">
        E
      </div>
      <h1 class="text-xl font-bold tracking-tight text-foreground hidden sm:block" style="font-family: 'Playfair Display', Georgia, serif;">Explorer</h1>
    </div>

    <!-- Tab Selector -->
    <nav class="flex items-center gap-1 rounded-full p-1 border border-border bg-background">
      <button 
        on:click={() => selectTab('flux')} 
        class="flex items-center gap-1.5 px-3.5 py-1.5 rounded-full text-xs font-bold transition-all duration-200 {activeTab === 'flux' ? 'bg-primary text-primary-foreground shadow-sm' : 'bg-transparent text-muted-foreground hover:text-foreground'}"
      >
        <span class="text-sm">📰</span>
        <span class="hidden sm:inline">Flux Actus</span>
      </button>

      <button 
        on:click={() => selectTab('culture')} 
        class="flex items-center gap-1.5 px-3.5 py-1.5 rounded-full text-xs font-bold transition-all duration-200 {activeTab === 'culture' ? 'bg-primary text-primary-foreground shadow-sm' : 'bg-transparent text-muted-foreground hover:text-foreground'}"
      >
        <span class="text-sm">🎨</span>
        <span class="hidden sm:inline">Culture</span>
      </button>

      <button 
        on:click={() => selectTab('carte')} 
        class="flex items-center gap-1.5 px-3.5 py-1.5 rounded-full text-xs font-bold transition-all duration-200 {activeTab === 'carte' ? 'bg-primary text-primary-foreground shadow-sm' : 'bg-transparent text-muted-foreground hover:text-foreground'}"
      >
        <span class="text-sm">🌍</span>
        <span class="hidden sm:inline">Carte</span>
      </button>
    </nav>
  </header>

  <!-- Views Container -->
  <div class="flex-1 relative bg-background overflow-hidden">
    <div class="absolute inset-0 w-full h-full flex flex-col overflow-hidden" class:hidden={activeTab !== 'flux'}>
      <PerplexityFeedView />
    </div>
    <div class="absolute inset-0 w-full h-full flex flex-col overflow-hidden" class:hidden={activeTab !== 'culture'}>
      <Culture3DShelvesView />
    </div>
    <div class="absolute inset-0 w-full h-full flex flex-col overflow-hidden" class:hidden={activeTab !== 'carte'}>
      <GeoMapView />
    </div>
  </div>

</div>
