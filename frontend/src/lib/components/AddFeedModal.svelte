<script>
  import { showAddFeedModal, fetchArticles, fetchFeeds } from '../stores/appState.js';

  let feedUrl = '';
  let category = 'Suisse';
  let isLoading = false;
  let errorMsg = '';
  let successMsg = '';

  async function handleAddFeed() {
    if (!feedUrl.trim()) {
      errorMsg = 'Veuillez entrer l\'URL d\'un flux RSS.';
      return;
    }
    
    isLoading = true;
    errorMsg = '';
    successMsg = '';

    try {
      const res = await fetch('/api/feeds/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: feedUrl, category })
      });

      const result = await res.json();

      if (res.ok) {
        successMsg = `Flux "${result.data.title}" ajouté avec succès (${result.data.articles_added} articles importés) !`;
        feedUrl = '';
        await fetchFeeds();
        await fetchArticles();
        setTimeout(() => {
          successMsg = '';
          $showAddFeedModal = false;
        }, 1500);
      } else {
        errorMsg = result.detail || 'Impossible d\'ajouter ce flux RSS.';
      }
    } catch (err) {
      errorMsg = 'Erreur de connexion avec le serveur FastAPI.';
    } finally {
      isLoading = false;
    }
  }

  function closeModal() {
    $showAddFeedModal = false;
  }
</script>

{#if $showAddFeedModal}
  <div class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
    <div class="bg-white dark:bg-dark-card w-full max-w-lg rounded-3xl shadow-2xl overflow-hidden border border-gray-100 dark:border-gray-800">
      
      <!-- Header -->
      <div class="p-6 border-b border-gray-100 dark:border-gray-800 flex justify-between items-center bg-gray-50/50 dark:bg-dark-bg/50">
        <div class="flex items-center gap-3">
          <div class="p-2.5 bg-primary-50 dark:bg-primary-900/50 text-primary-500 rounded-2xl">
            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4"></path>
            </svg>
          </div>
          <div>
            <h3 class="text-xl font-bold">Ajouter un Flux RSS</h3>
            <p class="text-xs text-gray-500">Saisissez l'URL d'un site ou canal RSS</p>
          </div>
        </div>

        <button on:click={closeModal} class="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 rounded-full hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
          </svg>
        </button>
      </div>

      <!-- Body -->
      <div class="p-6 space-y-4">
        
        <div>
          <label for="feed-url-input" class="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
            URL du Flux RSS / Atom
          </label>
          <input 
            id="feed-url-input"
            type="url" 
            placeholder="Ex: https://news.ycombinator.com/rss ou https://www.letemps.ch/rss" 
            bind:value={feedUrl}
            class="w-full bg-gray-50 dark:bg-dark-bg border border-gray-200 dark:border-gray-700 rounded-2xl py-3 px-4 text-sm focus:ring-2 focus:ring-primary-500 focus:outline-none"
          />
        </div>

        <div>
          <label for="feed-category-select" class="block text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
            Catégorie
          </label>
          <select 
            id="feed-category-select"
            bind:value={category}
            class="w-full bg-gray-50 dark:bg-dark-bg border border-gray-200 dark:border-gray-700 rounded-2xl py-3 px-4 text-sm focus:ring-2 focus:ring-primary-500 focus:outline-none"
          >
            <option value="Suisse">🇨🇭 Suisse</option>
            <option value="Europe">🇪🇺 Europe</option>
            <option value="Monde">🌍 Monde</option>
            <option value="Technologie">💻 Technologie</option>
            <option value="Science">🔬 Science</option>
            <option value="Économie">📈 Économie</option>
            <option value="Culture">🎭 Culture</option>
            <option value="Général">📁 Général</option>
          </select>
        </div>

        <!-- Predefined Quick Suggestions -->
        <div class="pt-2">
          <span class="text-xs font-semibold text-gray-400 block mb-2">Exemples rapides à essayer :</span>
          <div class="flex flex-wrap gap-2">
            <button 
              type="button"
              on:click={() => { feedUrl = 'https://www.letemps.ch/rss'; category = 'Suisse'; }}
              class="text-xs bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 px-3 py-1.5 rounded-xl transition-colors"
            >
              Le Temps (Suisse)
            </button>
            <button 
              type="button"
              on:click={() => { feedUrl = 'https://www.lemonde.fr/rss/une.xml'; category = 'Europe'; }}
              class="text-xs bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 px-3 py-1.5 rounded-xl transition-colors"
            >
              Le Monde
            </button>
          </div>
        </div>

        {#if errorMsg}
          <div class="p-3 bg-rose-50 text-rose-600 dark:bg-rose-950/40 dark:text-rose-400 rounded-xl text-xs font-medium">
            {errorMsg}
          </div>
        {/if}

        {#if successMsg}
          <div class="p-3 bg-emerald-50 text-emerald-600 dark:bg-emerald-950/40 dark:text-emerald-400 rounded-xl text-xs font-medium">
            {successMsg}
          </div>
        {/if}

      </div>

      <!-- Footer -->
      <div class="p-4 bg-gray-50/50 dark:bg-dark-bg/50 border-t border-gray-100 dark:border-gray-800 flex justify-end gap-3">
        <button 
          type="button" 
          on:click={closeModal}
          class="px-4 py-2.5 text-xs font-semibold text-gray-500 hover:text-gray-700 dark:hover:text-gray-300 rounded-xl"
        >
          Annuler
        </button>
        <button 
          type="button" 
          on:click={handleAddFeed}
          disabled={isLoading}
          class="px-5 py-2.5 text-xs font-semibold text-white bg-primary-500 hover:bg-primary-600 rounded-xl shadow-sm transition-all disabled:opacity-50 flex items-center gap-2"
        >
          {#if isLoading}
            <svg class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
            </svg>
            <span>Importation...</span>
          {:else}
            <span>Ajouter le flux</span>
          {/if}
        </button>
      </div>

    </div>
  </div>
{/if}
