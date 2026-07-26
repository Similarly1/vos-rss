<script>
    import { onMount } from 'svelte';
    import { statsStore, fetchStats } from '../stores/statsStore.js';

    onMount(() => {
        fetchStats();
    });

    $: hours = Math.floor($statsStore.listeningTimeMinutes / 60);
    $: minutes = $statsStore.listeningTimeMinutes % 60;
    
    $: totalInteractions = $statsStore.articlesRead + $statsStore.articlesListened;
    $: readPercentage = totalInteractions > 0 ? ($statsStore.articlesRead / totalInteractions) * 100 : 0;
    $: listenPercentage = totalInteractions > 0 ? ($statsStore.articlesListened / totalInteractions) * 100 : 0;
</script>

<div class="p-6 bg-slate-900 text-white min-h-full font-sans">
    <div class="max-w-4xl mx-auto space-y-8">
        <header>
            <h2 class="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-indigo-500">
                Vos Statistiques
            </h2>
            <p class="text-slate-400 mt-2">Suivez votre activité et vos habitudes de consommation.</p>
        </header>

        {#if $statsStore.loading}
            <div class="flex justify-center items-center py-20">
                <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-500"></div>
            </div>
        {:else if $statsStore.error}
            <div class="p-4 bg-red-900/50 border border-red-500 rounded-lg text-red-200">
                Erreur: {$statsStore.error}
            </div>
        {:else}
            <!-- KPI Cards -->
            <div class="grid grid-cols-1 md:grid-cols-3 gap-6">
                <!-- Temps d'écoute -->
                <div class="bg-slate-800 rounded-2xl p-6 shadow-lg border border-slate-700/50 hover:border-indigo-500/50 transition-colors">
                    <div class="flex items-center space-x-3 mb-4">
                        <div class="p-3 bg-indigo-500/20 rounded-lg text-indigo-400">
                            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                        </div>
                        <h3 class="text-lg font-medium text-slate-300">Temps d'écoute</h3>
                    </div>
                    <div class="text-4xl font-bold">
                        {hours}<span class="text-xl text-slate-400 ml-1 mr-2">h</span>{minutes}<span class="text-xl text-slate-400 ml-1">m</span>
                    </div>
                </div>

                <!-- Flux suivis -->
                <div class="bg-slate-800 rounded-2xl p-6 shadow-lg border border-slate-700/50 hover:border-emerald-500/50 transition-colors">
                    <div class="flex items-center space-x-3 mb-4">
                        <div class="p-3 bg-emerald-500/20 rounded-lg text-emerald-400">
                            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 002-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"></path></svg>
                        </div>
                        <h3 class="text-lg font-medium text-slate-300">Flux suivis</h3>
                    </div>
                    <div class="text-4xl font-bold">{ $statsStore.followedFeedsCount }</div>
                </div>

                <!-- Total Articles -->
                <div class="bg-slate-800 rounded-2xl p-6 shadow-lg border border-slate-700/50 hover:border-amber-500/50 transition-colors">
                    <div class="flex items-center space-x-3 mb-4">
                        <div class="p-3 bg-amber-500/20 rounded-lg text-amber-400">
                            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>
                        </div>
                        <h3 class="text-lg font-medium text-slate-300">Interactions</h3>
                    </div>
                    <div class="text-4xl font-bold">{ totalInteractions }</div>
                </div>
            </div>

            <!-- Ratio Chart -->
            <div class="bg-slate-800 rounded-2xl p-6 shadow-lg border border-slate-700/50 mt-8">
                <h3 class="text-xl font-medium text-slate-200 mb-6">Ratio d'utilisation (Lu vs Écouté)</h3>
                
                <div class="relative pt-1">
                    <div class="flex mb-2 items-center justify-between">
                        <div>
                            <span class="text-xs font-semibold inline-block py-1 px-2 uppercase rounded-full text-blue-400 bg-blue-900/50">
                                Lu ({$statsStore.articlesRead})
                            </span>
                        </div>
                        <div class="text-right">
                            <span class="text-xs font-semibold inline-block py-1 px-2 uppercase rounded-full text-purple-400 bg-purple-900/50">
                                Écouté ({$statsStore.articlesListened})
                            </span>
                        </div>
                    </div>
                    <div class="overflow-hidden h-4 mb-4 text-xs flex rounded-full bg-slate-700">
                        <div style="width: {readPercentage}%" class="shadow-none flex flex-col text-center whitespace-nowrap text-white justify-center bg-blue-500 transition-all duration-1000"></div>
                        <div style="width: {listenPercentage}%" class="shadow-none flex flex-col text-center whitespace-nowrap text-white justify-center bg-purple-500 transition-all duration-1000"></div>
                    </div>
                </div>
            </div>
        {/if}
    </div>
</div>
