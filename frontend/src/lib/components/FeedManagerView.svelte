<script>
  import { onMount } from 'svelte';
  import { feedsList, fetchFeeds, currentView } from '../stores/appState.js';

  let hygieneScore = 85;
  let runningAudit = false;
  let auditData = null;

  let inactiveFeeds = [];
  let semanticDuplicates = [];
  let triadAlerts = [];
  let activity14d = {};
  let categoryDistribution = {};

  $: mockActivity = Object.values(activity14d).length > 0
    ? Object.values(activity14d)
    : Array.from({length: 14}, () => 0);
  $: maxActivity = Math.max(...mockActivity, 1);

  let categoriesStats = [];
  $: {
    const counts = {};
    $feedsList.forEach(f => {
      const cat = f.category || 'Général';
      counts[cat] = (counts[cat] || 0) + 1;
    });
    categoriesStats = Object.entries(counts).map(([name, count]) => ({
      name, count, percent: Math.round((count / ($feedsList.length || 1)) * 100) || 0
    })).sort((a, b) => b.count - a.count);
  }

  async function runAudit() {
    runningAudit = true;
    try {
      const res = await fetch('/api/audit/health-check');
      if (res.ok) {
        auditData = await res.json();
        hygieneScore = auditData.global_hygiene_score || 85;
        inactiveFeeds = auditData.inactive_feeds || [];
        semanticDuplicates = auditData.semantic_duplicates || [];
        triadAlerts = auditData.alerts_rule_of_3 || [];
        activity14d = auditData.activity_14_days || {};
        categoryDistribution = auditData.category_distribution || {};
      }
    } catch (e) {
      console.error("Erreur lors de l'audit des flux:", e);
    } finally {
      runningAudit = false;
    }
  }

  async function handleCleanInactive() {
    if (!inactiveFeeds || inactiveFeeds.length === 0) {
      alert("Aucun flux inactif à nettoyer.");
      return;
    }
    const ids = inactiveFeeds.map(f => f.id);
    if (!confirm(`Voulez-vous supprimer les ${ids.length} flux inactifs ?`)) return;
    
    try {
      const res = await fetch('/api/audit/clean-inactive', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ feed_ids: ids })
      });
      if (res.ok) {
        await fetchFeeds();
        await runAudit();
      }
    } catch (e) {
      console.error("Erreur lors du nettoyage des flux inactifs:", e);
    }
  }

  async function handleMergeDuplicates() {
    if (!semanticDuplicates || semanticDuplicates.length === 0) {
      alert("Aucun doublon sémantique à fusionner pour le moment.");
      return;
    }
    const dup = semanticDuplicates[0];
    if (confirm(`Fusionner et supprimer le flux doublon (ID: ${dup.feed_id}) ?`)) {
      await deleteFeed(dup.feed_id);
      await runAudit();
    }
  }

  function handleCompleteTriad() {
    currentView.set('discover');
  }

  async function deleteFeed(feedId) {
    if(!confirm("Êtes-vous sûr de vouloir supprimer ce flux ?")) return;
    try {
      const res = await fetch(`/api/feeds/${feedId}`, { method: 'DELETE' });
      if (res.ok) {
        await fetchFeeds();
        await runAudit();
      }
    } catch (e) {
      console.error(e);
    }
  }

  function importOPML() {
    currentView.set('discover');
  }
  
  function exportOPML() {
    window.open('/api/feeds/export-opml', '_blank');
  }

  function getHealthState(feed) {
    const isInactive = inactiveFeeds.some(f => f.id === feed.id);
    if (isInactive) return { label: '🔴 Inactif (>60j)', class: 'bg-rose-100 text-rose-700 dark:bg-rose-900/30 dark:text-rose-400' };
    const isDup = semanticDuplicates.some(f => f.feed_id === feed.id);
    if (isDup) return { label: '🟡 Redondant', class: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400' };
    return { label: '🟢 Actif', class: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400' };
  }

  function getBadges(feed) {
    const badges = [];
    if (feed.is_jti_certified) badges.push('🛡️ Certifié JTI (RSF)');
    if (feed.factuality_rating === 'High' || feed.factuality_rating === 'Very High') badges.push('⚖️ Factuel');
    const bias = (feed.bias_rating || '').toLowerCase();
    if (bias === 'left' || bias === 'gauche') badges.push('🔴 Gauche');
    else if (bias === 'center' || bias === 'centre') badges.push('🌐 Centre');
    else if (bias === 'right' || bias === 'droite') badges.push('🟠 Droite');
    return badges;
  }

  onMount(() => {
    if ($feedsList.length === 0) fetchFeeds();
    runAudit();
  });
</script>

<div class="flex-1 h-full overflow-y-auto bg-gray-50 dark:bg-dark-bg p-6 md:p-10 scroll-smooth">
  <div class="max-w-6xl mx-auto space-y-8">
    
    <!-- Header & Action OPML -->
    <div class="flex flex-col md:flex-row md:items-center justify-between gap-4">
      <div>
        <h1 class="text-3xl font-black text-gray-900 dark:text-white tracking-tight">Mes Flux & Audit</h1>
        <p class="text-gray-500 dark:text-gray-400 mt-1">Gérez votre veille, analysez vos sources et optimisez votre couverture.</p>
      </div>
      <div class="flex items-center gap-3">
        <button on:click={importOPML} class="px-4 py-2 bg-white dark:bg-dark-card border border-gray-200 dark:border-gray-700 rounded-xl text-sm font-semibold text-gray-700 dark:text-gray-300 hover:bg-gray-50 transition-colors shadow-sm">
          📥 Import OPML
        </button>
        <button on:click={exportOPML} class="px-4 py-2 bg-white dark:bg-dark-card border border-gray-200 dark:border-gray-700 rounded-xl text-sm font-semibold text-gray-700 dark:text-gray-300 hover:bg-gray-50 transition-colors shadow-sm">
          📤 Export OPML
        </button>
      </div>
    </div>

    <!-- Health Dashboard -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      
      <!-- Jauge de Santé -->
      <div class="bg-white dark:bg-dark-card p-6 rounded-3xl border border-gray-100 dark:border-gray-800 shadow-sm flex flex-col justify-between relative overflow-hidden">
        <div class="absolute -right-10 -top-10 w-40 h-40 bg-gradient-to-br from-primary-400/20 to-purple-500/20 rounded-full blur-3xl"></div>
        <div>
          <h2 class="text-sm font-bold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-4">Score d'Hygiène</h2>
          <div class="flex items-end gap-3">
            <span class="text-6xl font-black {hygieneScore > 80 ? 'text-emerald-500' : hygieneScore > 50 ? 'text-amber-500' : 'text-rose-500'}">{hygieneScore}</span>
            <span class="text-xl font-bold text-gray-400 mb-1">/ 100</span>
          </div>
          <div class="w-full bg-gray-100 dark:bg-gray-800 h-3 rounded-full mt-4 overflow-hidden">
            <div class="h-full {hygieneScore > 80 ? 'bg-emerald-500' : hygieneScore > 50 ? 'bg-amber-500' : 'bg-rose-500'} transition-all duration-1000" style="width: {hygieneScore}%"></div>
          </div>
          <div class="mt-3 flex items-center gap-2">
            <span class="px-2.5 py-1 text-xs font-bold rounded-lg {hygieneScore > 80 ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30' : 'bg-amber-100 text-amber-700 dark:bg-amber-900/30'}">
              {hygieneScore > 80 ? 'Excellent' : 'À améliorer'}
            </span>
          </div>
        </div>
        <button on:click={runAudit} disabled={runningAudit} class="mt-6 w-full py-3 bg-gradient-to-r from-gray-900 to-black dark:from-white dark:to-gray-200 text-white dark:text-black font-bold rounded-xl shadow-md hover:scale-[1.02] active:scale-[0.98] transition-all disabled:opacity-70 disabled:hover:scale-100 flex items-center justify-center gap-2">
          {#if runningAudit}
            <svg class="w-5 h-5 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/></svg>
            Audit en cours...
          {:else}
            🩺 Exécuter l'Audit
          {/if}
        </button>
      </div>

      <!-- Graphique d'Activité -->
      <div class="bg-white dark:bg-dark-card p-6 rounded-3xl border border-gray-100 dark:border-gray-800 shadow-sm lg:col-span-1">
        <h2 class="text-sm font-bold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-6">Activité (14j)</h2>
        <div class="flex items-end gap-1.5 h-32 w-full mt-auto">
          {#each mockActivity as val}
            <div class="flex-1 bg-primary-100 dark:bg-primary-900/30 hover:bg-primary-500 dark:hover:bg-primary-500 rounded-t-sm transition-all group relative" style="height: {(val / maxActivity) * 100}%">
              <div class="opacity-0 group-hover:opacity-100 absolute -top-8 left-1/2 -translate-x-1/2 bg-gray-900 text-white text-xs py-1 px-2 rounded-md pointer-events-none transition-opacity">
                {val} art.
              </div>
            </div>
          {/each}
        </div>
      </div>

      <!-- Couverture par Thématiques -->
      <div class="bg-white dark:bg-dark-card p-6 rounded-3xl border border-gray-100 dark:border-gray-800 shadow-sm lg:col-span-1">
        <h2 class="text-sm font-bold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-4">Couverture</h2>
        <div class="space-y-4">
          {#each categoriesStats.slice(0, 4) as cat}
            <div>
              <div class="flex justify-between text-sm font-semibold mb-1.5">
                <span class="text-gray-700 dark:text-gray-300">{cat.name}</span>
                <span class="text-gray-400">{cat.percent}%</span>
              </div>
              <div class="w-full bg-gray-100 dark:bg-gray-800 h-2 rounded-full overflow-hidden">
                <div class="h-full bg-gradient-to-r from-cyan-400 to-primary-500" style="width: {cat.percent}%"></div>
              </div>
            </div>
          {/each}
        </div>
      </div>
    </div>

    <!-- Alertes Diagnostiques -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
      <div class="bg-rose-50 dark:bg-rose-950/20 border border-rose-200 dark:border-rose-900/50 p-5 rounded-2xl flex flex-col gap-3">
        <div class="flex items-center gap-2 text-rose-600 dark:text-rose-400 font-bold">
          <span class="text-xl">🔴</span> Flux inactifs
        </div>
        <p class="text-sm text-gray-600 dark:text-gray-300 flex-1">
          {inactiveFeeds.length > 0 ? `${inactiveFeeds.length} flux n'ont rien publié depuis plus de 60 jours.` : 'Tous vos flux sont actifs et publient régulièrement.'}
        </p>
        <button on:click={handleCleanInactive} class="w-full py-2 bg-white dark:bg-dark-card border border-rose-200 dark:border-rose-800 text-rose-600 dark:text-rose-400 font-bold text-sm rounded-xl hover:bg-rose-100 dark:hover:bg-rose-900/50 transition-colors">
          Nettoyer ({inactiveFeeds.length})
        </button>
      </div>

      <div class="bg-amber-50 dark:bg-amber-950/20 border border-amber-200 dark:border-amber-900/50 p-5 rounded-2xl flex flex-col gap-3">
        <div class="flex items-center gap-2 text-amber-600 dark:text-amber-400 font-bold">
          <span class="text-xl">🟡</span> Doublons sémantiques
        </div>
        <p class="text-sm text-gray-600 dark:text-gray-300 flex-1">
          {semanticDuplicates.length > 0 ? `${semanticDuplicates.length} flux reprennent les mêmes dépêches sémantiques.` : 'Aucun doublon sémantique majeur détecté.'}
        </p>
        <button on:click={handleMergeDuplicates} class="w-full py-2 bg-white dark:bg-dark-card border border-amber-200 dark:border-amber-800 text-amber-600 dark:text-amber-400 font-bold text-sm rounded-xl hover:bg-amber-100 dark:hover:bg-amber-900/50 transition-colors">
          Fusionner ({semanticDuplicates.length})
        </button>
      </div>

      <div class="bg-cyan-50 dark:bg-cyan-950/20 border border-cyan-200 dark:border-cyan-900/50 p-5 rounded-2xl flex flex-col gap-3">
        <div class="flex items-center gap-2 text-cyan-600 dark:text-cyan-400 font-bold">
          <span class="text-xl">💡</span> Règle des 3 Sources
        </div>
        <p class="text-sm text-gray-600 dark:text-gray-300 flex-1">
          {triadAlerts.length > 0 ? `Catégorie "${triadAlerts[0].category}" dépendant d'une source unique.` : 'Vos catégories disposent de plusieurs sources complémentaires.'}
        </p>
        <button on:click={handleCompleteTriad} class="w-full py-2 bg-white dark:bg-dark-card border border-cyan-200 dark:border-cyan-800 text-cyan-600 dark:text-cyan-400 font-bold text-sm rounded-xl hover:bg-cyan-100 dark:hover:bg-cyan-900/50 transition-colors">
          Compléter la Triade
        </button>
      </div>
    </div>

    <!-- Liste des Flux -->
    <div class="bg-white dark:bg-dark-card rounded-3xl border border-gray-100 dark:border-gray-800 shadow-sm overflow-hidden">
      <div class="p-6 border-b border-gray-100 dark:border-gray-800 flex items-center justify-between">
        <h2 class="text-lg font-bold text-gray-900 dark:text-white">Flux Suivis ({$feedsList.length})</h2>
      </div>
      
      <div class="overflow-x-auto">
        <table class="w-full text-left border-collapse">
          <thead>
            <tr class="bg-gray-50/50 dark:bg-gray-900/20 text-xs uppercase tracking-wider text-gray-500 dark:text-gray-400 font-semibold border-b border-gray-100 dark:border-gray-800">
              <th class="p-4 pl-6">Source</th>
              <th class="p-4">Catégorie</th>
              <th class="p-4">Fiabilité</th>
              <th class="p-4">Santé</th>
              <th class="p-4 text-right pr-6">Actions</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-gray-50 dark:divide-gray-800/50">
            {#each $feedsList as feed (feed.id)}
              {@const health = getHealthState(feed)}
              {@const badges = getBadges(feed)}
              <tr class="hover:bg-gray-50/50 dark:hover:bg-gray-800/20 transition-colors">
                <td class="p-4 pl-6">
                  <div class="flex items-center gap-3">
                    <img src={feed.icon_url || `https://www.google.com/s2/favicons?domain=${feed.url}&sz=64`} alt="" class="w-8 h-8 rounded-lg bg-white border border-gray-100 dark:border-gray-700 object-contain p-1" />
                    <div>
                      <p class="font-bold text-sm text-gray-900 dark:text-white">{feed.title}</p>
                      <p class="text-xs text-gray-400 truncate max-w-[200px]">{feed.url}</p>
                    </div>
                  </div>
                </td>
                <td class="p-4">
                  <span class="inline-flex items-center px-2.5 py-1 rounded-md text-xs font-semibold bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300">
                    {feed.category || 'Général'}
                  </span>
                </td>
                <td class="p-4">
                  <div class="flex flex-col gap-1">
                    {#each badges as b}
                      <span class="text-[10px] font-bold text-gray-600 dark:text-gray-400 bg-gray-50 dark:bg-gray-900 px-2 py-0.5 rounded-full border border-gray-200 dark:border-gray-700 w-max">{b}</span>
                    {/each}
                    {#if badges.length === 0}
                      <span class="text-xs text-gray-400">-</span>
                    {/if}
                  </div>
                </td>
                <td class="p-4">
                  <span class="inline-flex items-center px-2.5 py-1 rounded-full text-xs font-bold {health.class}">
                    {health.label}
                  </span>
                </td>
                <td class="p-4 pr-6 text-right">
                  <button on:click={() => deleteFeed(feed.id)} class="p-2 text-gray-400 hover:text-rose-500 hover:bg-rose-50 dark:hover:bg-rose-900/30 rounded-lg transition-colors" title="Supprimer">
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
                  </button>
                </td>
              </tr>
            {/each}
            {#if $feedsList.length === 0}
              <tr>
                <td colspan="5" class="p-8 text-center text-gray-500">Aucun flux abonné. Allez dans le catalogue pour en ajouter.</td>
              </tr>
            {/if}
          </tbody>
        </table>
      </div>
    </div>
    
  </div>
</div>
