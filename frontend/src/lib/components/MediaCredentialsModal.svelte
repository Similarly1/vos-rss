<script>
  import { showMediaCredentialsModal, subscribedMediaCredentialsList, hidePaywalledWithoutCookie } from '../stores/appState.js';
  import { fade, slide } from 'svelte/transition';
  import { onMount } from 'svelte';

  let activeTab = 'tutorial'; // 'tutorial' | 'manage'
  
  // Media configuration
  const mediaList = [
    { id: 'lemonde',   name: 'Le Monde',    icon: '📰', domain: 'lemonde.fr' },
    { id: 'mediapart', name: 'Mediapart',   icon: '🔴', domain: 'mediapart.fr' },
    { id: 'letemps',   name: 'Le Temps',    icon: '⏱️', domain: 'letemps.ch' },
    { id: 'nzz',       name: 'NZZ',         icon: '🏔️', domain: 'nzz.ch' },
    { id: 'nyt',       name: 'NY Times',    icon: '🗽', domain: 'nytimes.com' },
    { id: 'wsj',       name: 'Wall Street Journal', icon: '📈', domain: 'wsj.com' },
    { id: 'lefigaro',  name: 'Le Figaro',   icon: '🖋️', domain: 'lefigaro.fr' },
    { id: 'lesechos',  name: 'Les Échos',   icon: '💼', domain: 'lesechos.fr' },
  ];

  let selectedMediaId = 'lemonde';
  let cookieValue = '';
  let isSaving = false;
  let saveStatus = null; // null | 'success' | 'error'
  let saveMessage = '';
  let autoSubscribedFeeds = [];

  // Load existing credentials from the backend
  onMount(async () => {
    try {
      const res = await fetch('/api/subscriptions/credentials');
      if (res.ok) {
        const data = await res.json();
        // Merge backend credentials into store
        const mapped = data.map(c => ({
          id: mediaList.find(m => m.domain === c.domain)?.id || c.domain,
          name: c.media_name || c.domain,
          domain: c.domain,
          active: true
        }));
        subscribedMediaCredentialsList.set(mapped);
      }
    } catch (e) {
      console.warn('[MediaCredentials] Could not load from server:', e);
    }
  });

  async function saveCookie() {
    if (!cookieValue.trim()) return;
    const mediaDef = mediaList.find(m => m.id === selectedMediaId);
    if (!mediaDef) return;

    isSaving = true;
    saveStatus = null;
    autoSubscribedFeeds = [];

    try {
      const res = await fetch('/api/subscriptions/credentials', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          domain: mediaDef.domain,
          media_name: mediaDef.name,
          cookie: cookieValue.trim()
        })
      });

      if (res.ok) {
        const data = await res.json();
        // Update local store
        const currentList = $subscribedMediaCredentialsList || [];
        const existingIndex = currentList.findIndex(item => item.domain === mediaDef.domain);
        const newEntry = { id: selectedMediaId, name: mediaDef.name, domain: mediaDef.domain, active: true };
        if (existingIndex >= 0) {
          currentList[existingIndex] = newEntry;
        } else {
          currentList.push(newEntry);
        }
        subscribedMediaCredentialsList.set([...currentList]);

        autoSubscribedFeeds = data.auto_subscribed || [];
        saveStatus = 'success';
        saveMessage = data.message || 'Cookie enregistré avec succès !';
        cookieValue = '';
        setTimeout(() => {
          activeTab = 'manage';
          saveStatus = null;
        }, 2500);
      } else {
        const err = await res.json().catch(() => ({}));
        saveStatus = 'error';
        saveMessage = err.detail || 'Erreur serveur lors de l\'enregistrement.';
      }
    } catch (e) {
      saveStatus = 'error';
      saveMessage = 'Erreur réseau : impossible de joindre le serveur.';
    } finally {
      isSaving = false;
    }
  }
  
  async function removeCookie(domain) {
    try {
      await fetch(`/api/subscriptions/credentials/${encodeURIComponent(domain)}`, { method: 'DELETE' });
    } catch (e) {
      console.warn('[MediaCredentials] Could not delete from server:', e);
    }
    subscribedMediaCredentialsList.set($subscribedMediaCredentialsList.filter(item => item.domain !== domain));
  }

  function close() {
    $showMediaCredentialsModal = false;
  }
</script>


<!-- svelte-ignore a11y-click-events-have-key-events -->
<!-- svelte-ignore a11y-no-static-element-interactions -->
<div class="fixed inset-0 z-[100] flex items-center justify-center bg-black/60 backdrop-blur-sm p-4" transition:fade="{{duration: 200}}" on:click|self={close}>
  <div class="bg-card text-card-foreground w-full max-w-2xl rounded-3xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
    
    <!-- Header -->
    <div class="px-6 py-5 border-b border-border flex justify-between items-center bg-gray-50/50 bg-background/50">
      <div class="flex items-center gap-3">
        <div class="p-2.5 bg-primary/10 dark:bg-indigo-900/50 text-primary rounded-2xl">
          <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z"></path>
          </svg>
        </div>
        <div>
          <h2 class="text-xl font-bold">Connexion aux Médias Payants</h2>
          <p class="text-sm text-gray-500">Lisez vos articles réservés aux abonnés en intégralité.</p>
        </div>
      </div>
      <button on:click={close} class="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-card rounded-full transition-colors">
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
      </button>
    </div>

    <!-- Tabs -->
    <div class="flex border-b border-border px-6 pt-4 gap-6 bg-card text-card-foreground">
      <button 
        on:click={() => activeTab = 'tutorial'} 
        class="pb-3 text-sm font-bold border-b-2 transition-colors {activeTab === 'tutorial' ? 'border-indigo-500 text-indigo-600 dark:text-indigo-400' : 'border-transparent text-gray-500 hover:text-gray-800 dark:hover:text-gray-300'}"
      >
        📖 Comment récupérer mon cookie ?
      </button>
      <button 
        on:click={() => activeTab = 'manage'} 
        class="pb-3 text-sm font-bold border-b-2 transition-colors {activeTab === 'manage' ? 'border-indigo-500 text-indigo-600 dark:text-indigo-400' : 'border-transparent text-gray-500 hover:text-gray-800 dark:hover:text-gray-300'}"
      >
        ⚙️ Gérer mes cookies ({$subscribedMediaCredentialsList.length})
      </button>
    </div>

    <!-- Content -->
    <div class="flex-1 overflow-y-auto p-6">
      {#if activeTab === 'tutorial'}
        <div in:slide="{{duration: 200}}" class="space-y-6">
          <div class="bg-primary/10 dark:bg-indigo-900/20 border border-indigo-100 dark:border-indigo-800 p-4 rounded-2xl">
            <h3 class="font-bold text-indigo-800 dark:text-indigo-300 mb-2 text-sm flex items-center gap-2">
              <span class="text-lg">💡</span> Pourquoi ajouter un cookie ?
            </h3>
            <p class="text-sm text-indigo-700 dark:text-indigo-400">
              Pour contourner le mur payant (paywall) et récupérer le texte intégral d'un article, Nifty Mendel a besoin de savoir que vous êtes abonné(e).
              En collant votre cookie de session ici, l'application pourra s'authentifier à votre place et télécharger l'article complet.
            </p>
          </div>

          <div class="space-y-4">
            <h3 class="font-bold text-gray-900 dark:text-white">Comment faire en 3 clics ?</h3>
            
            <div class="flex gap-4">
              <div class="flex-shrink-0 w-8 h-8 bg-gray-100 dark:bg-card text-gray-600 dark:text-gray-300 rounded-full flex items-center justify-center font-bold">1</div>
              <div>
                <p class="text-sm font-semibold text-gray-800 dark:text-gray-200">Connectez-vous au site du journal</p>
                <p class="text-xs text-gray-500 mt-1">Ouvrez un nouvel onglet et connectez-vous avec votre compte abonné (ex: lemonde.fr).</p>
              </div>
            </div>

            <div class="flex gap-4">
              <div class="flex-shrink-0 w-8 h-8 bg-gray-100 dark:bg-card text-gray-600 dark:text-gray-300 rounded-full flex items-center justify-center font-bold">2</div>
              <div>
                <p class="text-sm font-semibold text-gray-800 dark:text-gray-200">Ouvrez les Outils de Développement</p>
                <p class="text-xs text-gray-500 mt-1">Faites un <strong>clic droit > Inspecter</strong> (ou appuyez sur <code>F12</code>). Allez dans l'onglet <strong>Application</strong> (Chrome) ou <strong>Stockage</strong> (Firefox), puis déroulez <strong>Cookies</strong>.</p>
              </div>
            </div>

            <div class="flex gap-4">
              <div class="flex-shrink-0 w-8 h-8 bg-gray-100 dark:bg-card text-gray-600 dark:text-gray-300 rounded-full flex items-center justify-center font-bold">3</div>
              <div>
                <p class="text-sm font-semibold text-gray-800 dark:text-gray-200">Copiez la valeur de la session</p>
                <p class="text-xs text-gray-500 mt-1">Trouvez le cookie d'authentification (ex: <code>session</code>, <code>lmid</code>, etc.) ou copiez toute la chaîne de cookies, et collez-la ci-dessous.</p>
              </div>
            </div>
          </div>
          
          <div class="pt-4 border-t border-border">
            <button on:click={() => activeTab = 'manage'} class="w-full py-3 bg-primary hover:opacity-90 text-primary-foreground rounded-xl font-bold text-sm shadow-md transition-all">
              J'ai compris, ajouter un cookie
            </button>
          </div>
        </div>
      {:else}
        <div in:slide="{{duration: 200}}" class="space-y-6">
          
          <!-- Add New Form -->
          <div class="bg-background p-5 rounded-2xl border border-border space-y-4">
            <h3 class="font-bold text-sm text-gray-900 dark:text-gray-100">Ajouter un abonnement</h3>
            
            <div class="space-y-3">
              <div>
                <label class="block text-xs font-semibold text-gray-600 dark:text-gray-400 mb-1">Journal</label>
                <select bind:value={selectedMediaId} class="w-full bg-card text-card-foreground border border-border rounded-xl py-2 px-3 text-sm focus:ring-2 focus:ring-indigo-500">
                  {#each mediaList as media}
                    <option value={media.id}>{media.icon} {media.name}</option>
                  {/each}
                </select>
              </div>

              <div>
                <label class="block text-xs font-semibold text-gray-600 dark:text-gray-400 mb-1" title="Collez la valeur complète du cookie copié depuis les outils de développement">
                  Valeur du Cookie (Session) ⓘ
                </label>
                <textarea 
                  bind:value={cookieValue} 
                  rows="3"
                  placeholder="Ex: session_id=abc123def456; other_cookie=xyz..." 
                  class="w-full bg-card text-card-foreground border border-border rounded-xl py-2 px-3 text-sm font-mono focus:ring-2 focus:ring-indigo-500"
                ></textarea>
              </div>
              
              {#if saveStatus === 'success'}
                <div class="p-3 bg-primary/10 dark:bg-emerald-900/30 border border-emerald-200 dark:border-emerald-700 rounded-xl text-sm text-emerald-800 dark:text-emerald-300 font-medium" transition:slide>
                  ✅ {saveMessage}
                  {#if autoSubscribedFeeds.length > 0}
                    <div class="mt-2 text-xs font-normal">
                      Flux ajoutés automatiquement : {autoSubscribedFeeds.join(', ')}
                    </div>
                  {/if}
                </div>
              {:else if saveStatus === 'error'}
                <div class="p-3 bg-rose-50 dark:bg-rose-900/30 border border-rose-200 dark:border-rose-700 rounded-xl text-sm text-rose-800 dark:text-rose-300 font-medium" transition:slide>
                  ❌ {saveMessage}
                </div>
              {/if}

              <button 
                on:click={saveCookie} 
                disabled={!cookieValue.trim() || isSaving}
                class="w-full py-2.5 bg-primary hover:opacity-90 text-primary-foreground rounded-xl font-bold text-sm shadow-sm transition-all disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {#if isSaving}
                  <svg class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
                  Enregistrement…
                {:else}
                  🔐 Sauvegarder l'accès
                {/if}
              </button>
            </div>
          </div>

          <!-- Existing Cookies -->
          <div>
            <h3 class="font-bold text-sm text-gray-900 dark:text-gray-100 mb-3">Vos accès configurés</h3>
            
            {#if $subscribedMediaCredentialsList.length === 0}
              <div class="p-6 text-center border-2 border-dashed border-border rounded-2xl text-gray-400 text-sm">
                Aucun journal configuré pour le moment.
              </div>
            {:else}
              <div class="space-y-2">
                {#each $subscribedMediaCredentialsList as item}
                  <div class="flex items-center justify-between p-3 bg-card text-card-foreground border border-border rounded-xl shadow-sm">
                    <div class="flex items-center gap-3">
                      <div class="w-8 h-8 bg-primary/10 text-emerald-600 rounded-lg flex items-center justify-center font-bold">
                        ✓
                      </div>
                      <div>
                        <div class="font-bold text-sm">{item.name}</div>
                        <div class="text-xs text-gray-500">{item.domain} • Cookie configuré</div>
                      </div>
                    </div>
                    <button 
                      on:click={() => removeCookie(item.domain)}
                      class="p-2 text-rose-500 hover:bg-rose-50 dark:hover:bg-rose-900/30 rounded-lg transition-colors"
                      title="Supprimer"
                    >
                      <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path></svg>
                    </button>
                  </div>
                {/each}
              </div>
            {/if}
          </div>

        </div>
      {/if}
    </div>
  </div>
</div>
