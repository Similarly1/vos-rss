<script>
  import { currentView, showSettingsModal } from '../stores/appState.js';
</script>

<nav class="fixed bottom-0 left-0 right-0 bg-gray-950 border-t border-gray-800 z-40 pb-safe">
  <div class="flex justify-around items-center h-16">
    
    <button class="flex flex-col items-center justify-center w-full h-full {$currentView === 'podcast' ? 'text-purple-400 font-semibold' : 'text-gray-400'}" on:click={() => $currentView = 'podcast'}>
      <svg class="w-5 h-5 mb-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"></path></svg>
      <span class="text-[10px]">Podcast</span>
    </button>

    <button class="flex flex-col items-center justify-center w-full h-full {$currentView === 'perplexity' ? 'text-cyan-400 font-semibold' : 'text-gray-400'}" on:click={() => $currentView = 'perplexity'}>
      <svg class="w-5 h-5 mb-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>
      <span class="text-[10px]">Découvrir</span>
    </button>

    <button class="flex flex-col items-center justify-center w-full h-full {$currentView === 'feeds' ? 'text-primary-400 font-semibold' : 'text-gray-400'}" on:click={() => $currentView = 'feeds'}>
      <svg class="w-5 h-5 mb-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"></path></svg>
      <span class="text-[10px]">Flux</span>
    </button>

    <button class="flex flex-col items-center justify-center w-full h-full {$currentView === 'discover' ? 'text-indigo-400 font-semibold' : 'text-gray-400'}" on:click={() => $currentView = 'discover'}>
      <svg class="w-5 h-5 mb-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path></svg>
      <span class="text-[10px]">Catalogue</span>
    </button>

    <button class="flex flex-col items-center justify-center w-full h-full text-gray-400 hover:text-gray-200" on:click={() => $showSettingsModal = true}>
      <svg class="w-5 h-5 mb-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"></path>
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path>
      </svg>
      <span class="text-[10px]">Réglages</span>
    </button>

  </div>
</nav>

<style>
  .pb-safe {
    padding-bottom: env(safe-area-inset-bottom);
  }
</style>
