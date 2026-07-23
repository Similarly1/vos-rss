<script>
  import { currentView, showSettingsModal, showAddFeedModal, showFeedManagerModal } from '../stores/appState.js';
</script>

<aside class="w-64 h-full bg-white dark:bg-dark-card border-r border-gray-200 dark:border-gray-800 flex flex-col p-4">
  <div class="text-2xl font-bold text-primary-500 mb-6 flex items-center gap-2">
    <svg class="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"></path></svg>
    Vos
  </div>
  
  <div class="space-y-2 mb-6">
    <button 
      on:click={() => $showAddFeedModal = true}
      class="w-full bg-primary-500 hover:bg-primary-600 text-white font-medium py-2.5 px-4 rounded-xl shadow-sm transition-all flex items-center justify-center gap-2 text-xs"
    >
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"></path></svg>
      Ajouter un flux RSS
    </button>

    <button 
      on:click={() => $showFeedManagerModal = true}
      class="w-full bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700 text-gray-700 dark:text-gray-300 font-medium py-2 px-4 rounded-xl transition-all flex items-center justify-center gap-2 text-xs"
    >
      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"></path></svg>
      Gérer les flux & dossiers
    </button>
  </div>

  <nav class="space-y-1.5 flex-1">
    <button class="w-full text-left px-4 py-2.5 rounded-xl flex items-center gap-2.5 text-xs font-semibold {$currentView === 'podcast' ? 'bg-gradient-to-r from-purple-600 to-indigo-600 text-white shadow-md' : 'hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-700 dark:text-gray-300'}" on:click={() => $currentView = 'podcast'}>
      <span>🎙️</span>
      <span class="flex-1 font-bold">Studio Podcast</span>
      <span class="text-[9px] bg-purple-500 text-white font-black px-1.5 py-0.5 rounded-full uppercase">Émission</span>
    </button>

    <button class="w-full text-left px-4 py-2.5 rounded-xl flex items-center gap-2.5 text-xs font-semibold {$currentView === 'perplexity' ? 'bg-indigo-50 dark:bg-indigo-950/60 text-indigo-500' : 'hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-700 dark:text-gray-300'}" on:click={() => $currentView = 'perplexity'}>
      <span>⚡</span>
      <span class="flex-1">Fil Perplexity</span>
    </button>

    <button class="w-full text-left px-4 py-2.5 rounded-xl flex items-center gap-2.5 text-xs font-semibold {$currentView === 'feeds' ? 'bg-primary-50 dark:bg-primary-900/50 text-primary-500' : 'hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-700 dark:text-gray-300'}" on:click={() => $currentView = 'feeds'}>
      <span>📰</span>
      <span>Flux & Articles</span>
    </button>

    <button class="w-full text-left px-4 py-2.5 rounded-xl flex items-center gap-2.5 text-xs font-semibold {$currentView === 'synthesis' ? 'bg-primary-50 dark:bg-primary-900/50 text-primary-500' : 'hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-700 dark:text-gray-300'}" on:click={() => $currentView = 'synthesis'}>
      <span>🧪</span>
      <span>Synthèses IA</span>
    </button>

    <button class="w-full text-left px-4 py-2.5 rounded-xl flex items-center gap-2.5 text-xs font-semibold {$currentView === 'discover' ? 'bg-primary-50 dark:bg-primary-900/50 text-primary-500' : 'hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-700 dark:text-gray-300'}" on:click={() => $currentView = 'discover'}>
      <span>🧭</span>
      <span>Catalogue</span>
    </button>
  </nav>

  <div class="mt-auto pt-4 border-t border-gray-200 dark:border-gray-800">
    <button 
      class="w-full text-left px-4 py-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-700 dark:text-gray-300 flex items-center gap-2 text-xs"
      on:click={() => $showSettingsModal = true}
    >
      <svg class="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"></path>
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"></path>
      </svg>
      Paramètres
    </button>
  </div>
</aside>
