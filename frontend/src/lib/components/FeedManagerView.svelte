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

  let showTriadModal = false;
  let triadCategory = 'Technologie';
  let triadFeeds = [];
  let subscribingTriadMap = {};
  let subscribedTriadMap = {};

  let showBalanceModal = false;
  let balanceCategories = [];
  let loadingBalance = false;

  const canonicalCategories = [
    'Actualités & Presse',
    'Technologie & Cyber',
    'Économie & Business',
    'Suisse & Régional',
    'International & Monde',
    'Science & Climat',
    'Culture & Société',
    'Foi & Spiritualité',
    'Général'
  ];

  async function changeFeedCategory(feed, newCategory) {
    try {
      const res = await fetch(`/api/feeds/${feed.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: feed.title,
          category: newCategory,
          language: feed.language || 'fr',
          is_full_text: feed.is_full_text !== undefined ? feed.is_full_text : true
        })
      });
      if (res.ok) {
        await fetchFeeds();
        await runAudit();
        await openCategoriesBalanceModal();
      }
    } catch (e) {
      console.error("Erreur changement catégorie:", e);
    }
  }

  let subscribingAllPacks = false;

  async function openTriadModalForCategory(category) {
    triadCategory = category || (triadAlerts.length > 0 ? triadAlerts[0].category : 'Technologie');
    showTriadModal = true;
    try {
      const res = await fetch(`/api/catalog/triad-pack?category=${encodeURIComponent(triadCategory)}`);
      if (res.ok) {
        const data = await res.json();
        triadFeeds = data.pack_feeds || [];
      } else {
        const fallbackRes = await fetch(`/api/catalog?category=${encodeURIComponent(triadCategory)}&limit=3`);
        if (fallbackRes.ok) {
          const d = await fallbackRes.json();
          triadFeeds = d.feeds || [];
        }
      }
    } catch (e) {
      console.error("Erreur chargement triade:", e);
    }
  }

  async function subscribeAllTriadFeeds() {
    if (!triadFeeds || triadFeeds.length === 0) return;
    subscribingAllPacks = true;
    try {
      for (const feed of triadFeeds) {
        if (!subscribedTriadMap[feed.url]) {
          await subscribeTriadFeed(feed);
        }
      }
    } catch (e) {
      console.error("Erreur abonnement pack triade:", e);
    } finally {
      subscribingAllPacks = false;
    }
  }

  function handleCompleteTriad() {
    openTriadModalForCategory(triadAlerts.length > 0 ? triadAlerts[0].category : 'Technologie');
  }

  async function loadBalanceData() {
    // Silent background load — does NOT open the modal
    try {
      const res = await fetch('/api/audit/categories-balance');
      if (res.ok) {
        const data = await res.json();
        balanceCategories = data.categories || [];
      }
    } catch (e) {
      console.error("Erreur bilan catégories:", e);
    }
  }

  async function openCategoriesBalanceModal() {
    showBalanceModal = true;
    loadingBalance = true;
    try {
      const res = await fetch('/api/audit/categories-balance');
      if (res.ok) {
        const data = await res.json();
        balanceCategories = data.categories || [];
      }
    } catch (e) {
      console.error("Erreur bilan catégories:", e);
    } finally {
      loadingBalance = false;
    }
  }

  async function toggleIgnoreCategory(category, currentlyIgnored) {
    try {
      const res = await fetch('/api/audit/ignore-category', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ category, ignore: !currentlyIgnored })
      });
      if (res.ok) {
        await openCategoriesBalanceModal();
        await runAudit();
      }
    } catch (e) {
      console.error("Erreur masquage catégorie:", e);
    }
  }

  async function subscribeTriadFeed(feed) {
    subscribingTriadMap[feed.url] = true;
    try {
      const res = await fetch('/api/feeds', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: feed.url, category: feed.category || triadCategory, language: feed.language || 'fr' })
      });
      if (res.ok) {
        subscribedTriadMap[feed.url] = true;
        await fetchFeeds();
        await runAudit();
        if (showBalanceModal) await openCategoriesBalanceModal();
      }
    } catch (e) {
      console.error("Erreur abonnement triade:", e);
    } finally {
      subscribingTriadMap[feed.url] = false;
      subscribingTriadMap = { ...subscribingTriadMap };
    }
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

  function getTrustBadges(feed) {
    const badges = [];
    if (!feed) return badges;

    if (feed.is_jti_certified) {
      badges.push({ text: '🛡️ Certifié JTI (RSF)', class: 'bg-primary text-primary-foreground/15 text-emerald-600 dark:text-emerald-400 border-emerald-500/30' });
    }
    if (feed.factuality_rating === 'High' || feed.factuality_rating === 'Very High') {
      badges.push({ text: '⚖️ Factuel', class: 'bg-blue-500/15 text-blue-600 dark:text-blue-400 border-blue-500/30' });
    }
    
    const bias = (feed.bias_rating || '').toLowerCase();
    if (bias === 'left' || bias === 'gauche') {
      badges.push({ text: '🔴 Gauche', class: 'bg-rose-500/15 text-rose-600 dark:text-rose-400 border-rose-500/30' });
    } else if (bias === 'left-center' || bias === 'centre-gauche') {
      badges.push({ text: '🟥 Centre-Gauche', class: 'bg-pink-500/15 text-pink-600 dark:text-pink-400 border-pink-500/30' });
    } else if (bias === 'center' || bias === 'centre' || bias === 'least biased') {
      badges.push({ text: '🌐 Centre / Neutre', class: 'bg-sky-500/15 text-sky-600 dark:text-sky-400 border-sky-500/30' });
    } else if (bias === 'right-center' || bias === 'centre-droit') {
      badges.push({ text: '🟦 Centre-Droit', class: 'bg-primary text-primary-foreground/15 text-indigo-600 dark:text-indigo-400 border-indigo-500/30' });
    } else if (bias === 'right' || bias === 'droite') {
      badges.push({ text: '🟠 Droite', class: 'bg-orange-500/15 text-orange-600 dark:text-orange-400 border-orange-500/30' });
    }

    const type = feed.media_type || 'Général';
    if (type === 'Agence') {
      badges.push({ text: '📡 Agence', class: 'bg-primary text-primary-foreground/15 text-purple-600 dark:text-purple-400 border-purple-500/30' });
    } else if (type === 'Analyse') {
      badges.push({ text: '📖 Analyse', class: 'bg-teal-500/15 text-teal-600 dark:text-teal-400 border-teal-500/30' });
    } else if (type === 'Régional') {
      badges.push({ text: '🏠 Régional', class: 'bg-amber-500/15 text-amber-600 dark:text-amber-400 border-amber-500/30' });
    }

    return badges;
  }

  onMount(() => {
    if ($feedsList.length === 0) fetchFeeds();
    runAudit();
    loadBalanceData(); // silent — no modal
  });
</script>

<div class="flex-1 h-full overflow-y-auto bg-background p-6 md:p-10 scroll-smooth">
  <div class="max-w-6xl mx-auto space-y-8">
    
    <!-- Header & Action OPML -->
    <div class="flex flex-col md:flex-row md:items-center justify-between gap-4">
      <div>
        <h1 class="text-3xl font-black text-gray-900 dark:text-white tracking-tight">Mes Flux & Audit</h1>
        <p class="text-gray-500 dark:text-gray-400 mt-1">Gérez votre veille, analysez vos sources et optimisez votre couverture.</p>
      </div>
      <div class="flex items-center gap-3">
        <button on:click={importOPML} class="px-4 py-2 bg-card text-card-foreground border border-border rounded-xl text-sm font-semibold text-gray-700 dark:text-gray-300 hover:bg-gray-50 transition-colors shadow-sm">
          📥 Import OPML
        </button>
        <button on:click={exportOPML} class="px-4 py-2 bg-card text-card-foreground border border-border rounded-xl text-sm font-semibold text-gray-700 dark:text-gray-300 hover:bg-gray-50 transition-colors shadow-sm">
          📤 Export OPML
        </button>
      </div>
    </div>

    <!-- Health Dashboard -->
    <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
      
      <!-- Jauge de Santé -->
      <div class="bg-card text-card-foreground p-6 rounded-3xl border border-border shadow-sm flex flex-col justify-between relative overflow-hidden">
        <div class="absolute -right-10 -top-10 w-40 h-40 bg-gradient-to-br from-primary-400/20 to-purple-500/20 rounded-full blur-3xl"></div>
        <div>
          <h2 class="text-sm font-bold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-4">Score d'Hygiène</h2>
          <div class="flex items-end gap-3">
            <span class="text-6xl font-black {hygieneScore > 80 ? 'text-primary' : hygieneScore > 50 ? 'text-amber-500' : 'text-rose-500'}">{hygieneScore}</span>
            <span class="text-xl font-bold text-gray-400 mb-1">/ 100</span>
          </div>
          <div class="w-full bg-gray-100 dark:bg-card h-3 rounded-full mt-4 overflow-hidden">
            <div class="h-full {hygieneScore > 80 ? 'bg-primary text-primary-foreground' : hygieneScore > 50 ? 'bg-amber-500' : 'bg-rose-500'} transition-all duration-1000" style="width: {hygieneScore}%"></div>
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
      <div class="bg-card text-card-foreground p-6 rounded-3xl border border-border shadow-sm lg:col-span-1">
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
      <div class="bg-card text-card-foreground p-6 rounded-3xl border border-border shadow-sm lg:col-span-1">
        <h2 class="text-sm font-bold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-4">Couverture</h2>
        <div class="space-y-4">
          {#each categoriesStats.slice(0, 4) as cat}
            <div>
              <div class="flex justify-between text-sm font-semibold mb-1.5">
                <span class="text-gray-700 dark:text-gray-300">{cat.name}</span>
                <span class="text-gray-400">{cat.percent}%</span>
              </div>
              <div class="w-full bg-gray-100 dark:bg-card h-2 rounded-full overflow-hidden">
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
        <button on:click={handleCleanInactive} class="w-full py-2 bg-card text-card-foreground border border-rose-200 dark:border-rose-800 text-rose-600 dark:text-rose-400 font-bold text-sm rounded-xl hover:bg-rose-100 dark:hover:bg-rose-900/50 transition-colors">
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
        <button on:click={handleMergeDuplicates} class="w-full py-2 bg-card text-card-foreground border border-amber-200 dark:border-amber-800 text-amber-600 dark:text-amber-400 font-bold text-sm rounded-xl hover:bg-amber-100 dark:hover:bg-amber-900/50 transition-colors">
          Fusionner ({semanticDuplicates.length})
        </button>
      </div>

      <div class="bg-cyan-50 dark:bg-cyan-950/20 border border-cyan-200 dark:border-cyan-900/50 p-5 rounded-2xl flex flex-col gap-3">
        <div class="flex items-center justify-between text-cyan-600 dark:text-cyan-400 font-bold">
          <div class="flex items-center gap-2">
            <span class="text-xl">💡</span> Règle des 3 Sources & Couverture
          </div>
        </div>
        <p class="text-sm text-gray-600 dark:text-gray-300 flex-1">
          {#if triadAlerts.length > 0}
            <strong>{triadAlerts.length} catégorie{triadAlerts.length > 1 ? 's' : ''} incomplète{triadAlerts.length > 1 ? 's' : ''}</strong> (ex: {triadAlerts[0].category} avec {triadAlerts[0].current_count}/3 sources).
          {:else}
            🟢 <strong>Parfait !</strong> Toutes vos catégories suivies ont au moins 3 sources.
          {/if}
        </p>
        <div class="flex items-center gap-2 pt-1">
          {#if triadAlerts.length > 0}
            <button on:click={handleCompleteTriad} class="flex-1 py-2 bg-card text-card-foreground border border-cyan-200 dark:border-cyan-800 text-cyan-600 dark:text-cyan-400 font-bold text-xs rounded-xl hover:bg-cyan-100 dark:hover:bg-cyan-900/50 transition-colors">
              + Compléter ({triadAlerts[0].category})
            </button>
          {/if}
          <button on:click={openCategoriesBalanceModal} class="flex-1 py-2 bg-cyan-600 text-white font-bold text-xs rounded-xl hover:bg-cyan-700 transition-colors shadow-sm">
            📊 Bilan des Catégories
          </button>
        </div>
      </div>
    </div>

    <!-- ── Explorer de Nouvelles Thématiques (Packs 3 Sources) ── -->
    <div class="bg-gradient-to-r from-slate-900 to-indigo-950 p-6 md:p-8 rounded-3xl border border-indigo-900/60 shadow-xl space-y-5 relative overflow-hidden">
      <div class="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary text-primary-foreground/20 border border-indigo-500/30 text-indigo-300 text-xs font-bold mb-2">
            ✨ Packs 3 Sources Équilibrées
          </div>
          <h2 class="text-xl md:text-2xl font-black text-white tracking-tight">
            Activer de Nouvelles Thématiques en 1 Clic
          </h2>
          <p class="text-sm text-indigo-200/80 mt-1 max-w-2xl">
            Enrichissez votre veille en intégrant d'autres catégories du catalogue avec un Pack de 3 sources pré-équilibrées (Agence/Factuel, Analyse, Régional).
          </p>
        </div>
        <button on:click={openCategoriesBalanceModal} class="px-5 py-2.5 bg-white/10 hover:bg-white/20 border border-white/20 text-white font-bold text-xs rounded-xl transition-all shrink-0">
          📊 Bilan Éditorial Complet
        </button>
      </div>

      <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 pt-2">
        {#each balanceCategories.filter(c => c.status === 'missing' && !c.is_ignored).slice(0, 4) as cat}
          <div class="bg-white/5 hover:bg-white/10 border border-white/10 hover:border-cyan-400/50 p-4 rounded-2xl transition-all space-y-3 flex flex-col justify-between group">
            <div>
              <div class="flex items-center justify-between">
                <span class="text-xs font-bold text-cyan-300 uppercase tracking-wide">{cat.category}</span>
                <span class="text-[10px] bg-white/10 px-2 py-0.5 rounded-md text-gray-300">0 source</span>
              </div>
              <p class="text-xs text-indigo-100/70 mt-2">
                Pack 3 sources certifiées (Agence, Analyse, Neutre).
              </p>
            </div>
            <button
              on:click={() => openTriadModalForCategory(cat.category)}
              class="w-full py-2 bg-gradient-to-r from-cyan-400 to-blue-500 hover:from-cyan-300 hover:to-blue-400 text-gray-950 font-bold text-xs rounded-xl shadow-md transition-all group-hover:scale-[1.02]"
            >
              ✨ Activer le Pack (3 Sources)
            </button>
          </div>
        {/each}
        {#if balanceCategories.filter(c => c.status === 'missing' && !c.is_ignored).length === 0}
          <div class="col-span-full p-4 rounded-2xl bg-white/5 border border-white/10 text-center text-xs text-indigo-200">
            🟢 Vous suivez déjà toutes les thématiques principales du catalogue !
          </div>
        {/if}
      </div>
    </div>

    <!-- Liste des Flux -->
    <div class="bg-card text-card-foreground rounded-3xl border border-border shadow-sm overflow-hidden">
      <div class="p-6 border-b border-border flex items-center justify-between">
        <h2 class="text-lg font-bold text-gray-900 dark:text-white">Flux Suivis ({$feedsList.length})</h2>
      </div>
      
      <div class="overflow-x-auto">
        <table class="w-full text-left border-collapse">
          <thead>
            <tr class="bg-gray-50/50 dark:bg-gray-900/20 text-xs uppercase tracking-wider text-gray-500 dark:text-gray-400 font-semibold border-b border-border">
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
              {@const badges = getTrustBadges(feed)}
              <tr class="hover:bg-gray-50/50 dark:hover:bg-card/20 transition-colors">
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
                  <select
                    value={feed.category || 'Général'}
                    on:change={(e) => changeFeedCategory(feed, e.target.value)}
                    class="bg-gray-100 dark:bg-card text-gray-800 dark:text-gray-200 text-xs font-semibold py-1 px-2 rounded-lg border border-border focus:ring-2 focus:ring-primary-500 cursor-pointer"
                  >
                    {#each canonicalCategories as catName}
                      <option value={catName}>{catName}</option>
                    {/each}
                  </select>
                </td>
                <td class="p-4">
                  <div class="flex flex-wrap gap-1">
                    {#each badges as b}
                      <span class="text-[10px] font-bold px-2 py-0.5 rounded-md border {b.class}">{b.text}</span>
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

<!-- ── Modale interactive Compléter la Triade ── -->
{#if showTriadModal}
  <div class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-in fade-in duration-200">
    <div class="bg-card text-card-foreground border border-border rounded-3xl max-w-2xl w-full p-6 md:p-8 space-y-6 shadow-2xl relative overflow-hidden">
      
      <div class="flex items-start justify-between">
        <div>
          <div class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-cyan-50 dark:bg-cyan-950/40 text-cyan-700 dark:text-cyan-400 text-xs font-bold mb-2">
            💡 Règle des 3 Sources
          </div>
          <h2 class="text-xl md:text-2xl font-black text-gray-900 dark:text-white leading-tight">
            Équilibrer votre veille "{triadCategory}"
          </h2>
        </div>
        <button on:click={() => showTriadModal = false} class="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 rounded-full hover:bg-gray-100 dark:hover:bg-card transition-colors">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
        </button>
      </div>

      <p class="text-sm text-gray-600 dark:text-gray-300 leading-relaxed bg-gray-50 dark:bg-gray-900/50 p-4 rounded-2xl border border-border">
        La Règle des 3 Sources évite la bulle de filtre. Pour la catégorie <strong>{triadCategory}</strong>, nous vous conseillons d'associer un média d'analyse et un média régional pour équilibrer la neutralité.
      </p>

      <div class="space-y-4">
        {#each triadFeeds as feed}
          {@const badges = getTrustBadges(feed)}
          <div class="p-4 rounded-2xl bg-gray-50/50 dark:bg-gray-900/30 border border-border flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div class="flex items-start gap-3 flex-1 min-w-0">
              <img src={feed.icon_url || `https://www.google.com/s2/favicons?domain=${feed.site_url || feed.url}&sz=128`} alt="" class="w-10 h-10 rounded-xl object-contain bg-white dark:bg-card p-1 shrink-0 border border-gray-100 dark:border-gray-700" />
              <div class="space-y-1">
                <h3 class="font-bold text-sm text-gray-900 dark:text-white leading-tight">{feed.title}</h3>
                <div class="flex items-center gap-1.5 flex-wrap">
                  {#each badges as b}
                    <span class="text-[10px] font-bold px-2 py-0.5 rounded-md border {b.class}">{b.text}</span>
                  {/each}
                </div>
                <p class="text-xs text-gray-500 dark:text-gray-400 line-clamp-2 mt-1">{feed.description || `Média recommandé pour équilibrer votre veille ${triadCategory}.`}</p>
              </div>
            </div>

            {#if subscribedTriadMap[feed.url]}
              <span class="px-4 py-2 text-xs font-bold text-emerald-600 dark:text-emerald-400 bg-primary/10 dark:bg-emerald-950/40 rounded-xl border border-emerald-200 dark:border-emerald-800 shrink-0">
                ✓ Ajouté
              </span>
            {:else}
              <button
                on:click={() => subscribeTriadFeed(feed)}
                disabled={subscribingTriadMap[feed.url]}
                class="px-4 py-2 bg-gradient-to-r from-gray-900 to-black dark:from-white dark:to-gray-100 text-white dark:text-gray-950 font-bold text-xs rounded-xl shadow hover:scale-[1.02] active:scale-[0.98] transition-all shrink-0 disabled:opacity-50"
              >
                {#if subscribingTriadMap[feed.url]}...{:else}+ S'abonner{/if}
              </button>
            {/if}
          </div>
        {/each}
        {#if triadFeeds.length === 0}
          <p class="text-sm text-gray-500 text-center py-6 animate-pulse">Sélection des flux complémentaires pour équilibrer votre veille...</p>
        {/if}
      </div>

      <div class="pt-2 flex items-center justify-between gap-3 border-t border-border/80">
        {#if triadFeeds.length > 0}
          <button
            on:click={subscribeAllTriadFeeds}
            disabled={subscribingAllPacks}
            class="px-5 py-2.5 bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-600 hover:to-blue-700 text-white font-bold text-sm rounded-xl shadow-lg hover:scale-[1.02] active:scale-[0.98] transition-all flex items-center gap-2 disabled:opacity-50"
          >
            {#if subscribingAllPacks}
              <span>S'abonnement en cours...</span>
            {:else}
              <span>⚡ S'abonner aux 3 sources (1 clic)</span>
            {/if}
          </button>
        {/if}
        <button on:click={() => showTriadModal = false} class="px-5 py-2.5 bg-gray-100 dark:bg-card text-gray-700 dark:text-gray-300 font-bold text-sm rounded-xl hover:bg-gray-200 transition-colors ml-auto">
          Fermer
        </button>
      </div>

    </div>
  </div>
{/if}

<!-- ── Modale Bilan d'Équilibre Éditorial par Catégorie ── -->
{#if showBalanceModal}
  <div class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-in fade-in duration-200">
    <div class="bg-card text-card-foreground border border-border rounded-3xl max-w-3xl w-full p-6 md:p-8 space-y-6 shadow-2xl relative overflow-hidden max-h-[85vh] flex flex-col">
      
      <div class="flex items-start justify-between shrink-0">
        <div>
          <div class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-primary-50 dark:bg-primary-950/40 text-primary dark:text-primary-400 text-xs font-bold mb-2">
            📊 Bilan d'Équilibre Éditorial
          </div>
          <h2 class="text-xl md:text-2xl font-black text-gray-900 dark:text-white leading-tight">
            Couverture & Règle des 3 Sources
          </h2>
        </div>
        <button on:click={() => showBalanceModal = false} class="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 rounded-full hover:bg-gray-100 dark:hover:bg-card transition-colors">
          <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
        </button>
      </div>

      <p class="text-sm text-gray-600 dark:text-gray-300 leading-relaxed shrink-0">
        Pour éviter la bulle de filtre, la Règle des 3 Sources recommande <strong>au moins 3 sources distinctes</strong> par thématique. Vous pouvez compléter une catégorie ou masquer celles qui ne vous intéressent pas.
      </p>

      <div class="overflow-y-auto space-y-3 pr-1 flex-1">
        {#each balanceCategories as cat}
          <div class="p-4 rounded-2xl border transition-all flex flex-col sm:flex-row sm:items-center justify-between gap-3 {cat.is_ignored ? 'bg-gray-100/50 dark:bg-gray-900/20 border-gray-200 dark:border-gray-800 opacity-60' : 'bg-gray-50/50 dark:bg-gray-900/40 border-border'}">
            
            <div class="space-y-1">
              <div class="flex items-center gap-2">
                <h3 class="font-bold text-sm text-gray-900 dark:text-white">{cat.category}</h3>
                {#if cat.status === 'balanced'}
                  <span class="text-[10px] font-bold px-2 py-0.5 rounded-md bg-primary text-primary-foreground/15 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30">🟢 Équilibré ({cat.count}/3 sources)</span>
                {:else if cat.status === 'incomplete'}
                  <span class="text-[10px] font-bold px-2 py-0.5 rounded-md bg-amber-500/15 text-amber-600 dark:text-amber-400 border border-amber-500/30">🟡 Incomplet ({cat.count}/3 sources)</span>
                {:else}
                  <span class="text-[10px] font-bold px-2 py-0.5 rounded-md bg-gray-500/15 text-gray-500 dark:text-gray-400 border border-gray-500/30">⚪ Non suivie</span>
                {/if}
                {#if cat.is_ignored}
                  <span class="text-[10px] font-bold px-2 py-0.5 rounded-md bg-rose-500/15 text-rose-600 dark:text-rose-400 border border-rose-500/30">Ignorée</span>
                {/if}
              </div>
              <p class="text-xs text-gray-500 dark:text-gray-400">
                {#if cat.status === 'balanced'}
                  Veille diversifiée et équilibrée.
                {:else if cat.status === 'incomplete'}
                  Il vous manque {cat.missing_count} source{cat.missing_count > 1 ? 's' : ''} pour diversifier cette thématique.
                {:else}
                  Aucune source suivie dans cette catégorie du catalogue.
                {/if}
              </p>
            </div>

            <div class="flex items-center gap-2 shrink-0">
              {#if cat.status === 'missing' && !cat.is_ignored}
                <button
                  on:click={() => openTriadModalForCategory(cat.category)}
                  class="px-3 py-1.5 bg-gradient-to-r from-primary-500 to-cyan-500 text-white font-bold text-xs rounded-xl hover:scale-[1.02] transition-all shadow-sm flex items-center gap-1"
                >
                  <span>✨ Activer (Pack 3 Sources)</span>
                </button>
              {:else if cat.status === 'incomplete' && !cat.is_ignored}
                <button
                  on:click={() => openTriadModalForCategory(cat.category)}
                  class="px-3 py-1.5 bg-cyan-600 text-white font-bold text-xs rounded-xl hover:bg-cyan-700 transition-colors shadow-sm"
                >
                  + Compléter
                </button>
              {/if}

              <button
                on:click={() => toggleIgnoreCategory(cat.category, cat.is_ignored)}
                class="px-3 py-1.5 bg-gray-200 dark:bg-card text-gray-700 dark:text-gray-300 font-bold text-xs rounded-xl hover:bg-gray-300 dark:hover:bg-gray-700 transition-colors"
              >
                {cat.is_ignored ? 'Réactiver' : 'Ignorer'}
              </button>
            </div>

          </div>
        {/each}
      </div>

      <div class="pt-2 flex justify-end shrink-0">
        <button on:click={() => showBalanceModal = false} class="px-5 py-2.5 bg-gray-100 dark:bg-card text-gray-700 dark:text-gray-300 font-bold text-sm rounded-xl hover:bg-gray-200 transition-colors">
          Fermer
        </button>
      </div>

    </div>
  </div>
{/if}
