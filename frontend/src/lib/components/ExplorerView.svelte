<script>
  import { fade } from 'svelte/transition';
  import PerplexityFeedView from './PerplexityFeedView.svelte';
  import Culture3DShelvesView from './Culture3DShelvesView.svelte';
  import GeoMapView from './GeoMapView.svelte';

  let activeTab = 'flux'; // 'flux' | 'culture' | 'carte'
</script>

<div class="flex flex-col h-full bg-gray-950 text-white w-full overflow-hidden">
  
  <!-- Tabs Navigation Header -->
  <header class="flex items-center justify-between p-4 bg-gray-900 border-b border-gray-800 shrink-0 relative z-10 shadow-sm">
    <div class="flex items-center gap-3">
      <div class="w-8 h-8 rounded-lg bg-gradient-to-tr from-cyan-500 to-purple-600 flex items-center justify-center font-black text-white text-sm shadow-[0_0_12px_rgba(79,110,247,0.4)]">
        E
      </div>
      <h1 class="text-xl font-bold tracking-tight text-white hidden sm:block" style="font-family: 'Playfair Display', Georgia, serif;">Explorer</h1>
    </div>

    <!-- Tab Selector -->
    <nav class="flex items-center gap-1 rounded-full p-1 border border-white/10 bg-white/5">
      <button 
        on:click={() => activeTab = 'flux'} 
        class="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-all duration-200 {activeTab === 'flux' ? 'bg-white/10 text-white border border-white/10' : 'bg-transparent text-white/30 border border-transparent'}"
      >
        <span class="text-sm">📰</span>
        <span class="hidden sm:inline">Flux Actus</span>
      </button>

      <button 
        on:click={() => activeTab = 'culture'} 
        class="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-all duration-200 {activeTab === 'culture' ? 'bg-white/10 text-white border border-white/10' : 'bg-transparent text-white/30 border border-transparent'}"
      >
        <span class="text-sm">🎨</span>
        <span class="hidden sm:inline">Culture</span>
      </button>

      <button 
        on:click={() => activeTab = 'carte'} 
        class="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-all duration-200 {activeTab === 'carte' ? 'bg-white/10 text-white border border-white/10' : 'bg-transparent text-white/30 border border-transparent'}"
      >
        <span class="text-sm">🌍</span>
        <span class="hidden sm:inline">Carte</span>
      </button>
    </nav>
  </header>

  <!-- Views Container -->
  <div class="flex-1 relative bg-gray-950">
    {#if activeTab === 'flux'}
      <div transition:fade={{ duration: 200 }} class="absolute inset-0 flex flex-col">
        <PerplexityFeedView />
      </div>
    {:else if activeTab === 'culture'}
      <div transition:fade={{ duration: 200 }} class="absolute inset-0 p-4 sm:p-8 overflow-y-auto">
        <Culture3DShelvesView />
      </div>
    {:else if activeTab === 'carte'}
      <div transition:fade={{ duration: 200 }} class="absolute inset-0 p-2 sm:p-6">
        <div class="h-full w-full bg-gray-900 rounded-3xl border border-gray-800 overflow-hidden shadow-2xl flex flex-col items-center justify-center relative">
            <GeoMapView />
        </div>
      </div>
    {/if}
  </div>

</div>
