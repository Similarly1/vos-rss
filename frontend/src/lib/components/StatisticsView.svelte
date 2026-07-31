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

<div class="p-6 bg-background text-foreground min-h-full font-sans">
    <div class="max-w-4xl mx-auto space-y-8">
        <header>
            <h2 class="text-3xl font-bold text-primary">
                Vos Statistiques
            </h2>
            <p class="text-muted-foreground mt-2">Suivez votre activité et vos habitudes de consommation.</p>
        </header>

        {#if $statsStore.loading}
            <div class="flex justify-center items-center py-20">
                <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
            </div>
        {:else if $statsStore.error}
            <div class="p-4 bg-destructive/10 border border-destructive rounded-lg text-destructive">
                Erreur: {$statsStore.error}
            </div>
        {:else}
            <!-- KPI Cards -->
            <div class="grid grid-cols-1 md:grid-cols-4 gap-6">
                <!-- Temps d'écoute -->
                <div class="bg-card text-card-foreground rounded-2xl p-6 shadow-lg border border-border hover:border-primary/50 transition-colors">
                    <div class="flex items-center space-x-3 mb-4">
                        <div class="p-3 bg-primary/20 rounded-lg text-primary">
                            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                        </div>
                        <h3 class="text-lg font-medium text-foreground">Temps d'écoute</h3>
                    </div>
                    <div class="text-4xl font-bold">
                        {hours}<span class="text-xl text-muted-foreground ml-1 mr-2">h</span>{minutes}<span class="text-xl text-muted-foreground ml-1">m</span>
                    </div>
                    <div class="mt-2 text-xs text-muted-foreground font-medium">
                        🎙️ {$statsStore.podcasts_generated_count || 0} podcasts générés
                    </div>
                </div>

                <!-- Flux suivis -->
                <div class="bg-card text-card-foreground rounded-2xl p-6 shadow-lg border border-border hover:border-primary/50 transition-colors">
                    <div class="flex items-center space-x-3 mb-4">
                        <div class="p-3 bg-primary/20 rounded-lg text-primary">
                            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 002-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"></path></svg>
                        </div>
                        <h3 class="text-lg font-medium text-foreground">Flux suivis</h3>
                    </div>
                    <div class="text-4xl font-bold">{ $statsStore.followedFeedsCount }</div>
                    <div class="mt-2 text-xs text-muted-foreground font-medium">
                        📡 Flux RSS actifs en base
                    </div>
                </div>

                <!-- Volume Articles & Ingestions -->
                <div class="bg-card text-card-foreground rounded-2xl p-6 shadow-lg border border-border hover:border-primary/50 transition-colors">
                    <div class="flex items-center space-x-3 mb-4">
                        <div class="p-3 bg-primary/20 rounded-lg text-primary">
                            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z"></path></svg>
                        </div>
                        <h3 class="text-lg font-medium text-foreground">Articles stockés</h3>
                    </div>
                    <div class="text-4xl font-bold">{ $statsStore.total_articles_count || 0 }</div>
                    <div class="mt-2 text-xs flex gap-2">
                        <span class="px-1.5 py-0.5 rounded bg-primary/20 text-primary border border-primary/30">
                            RSS: {$statsStore.ingestion_sources?.['RSS'] || 0}
                        </span>
                        <span class="px-1.5 py-0.5 rounded bg-primary/10 text-primary border border-primary/20">
                            OCR/Webhook: {$statsStore.ingestion_sources?.['Webhook / OCR'] || 0}
                        </span>
                    </div>
                </div>

                <!-- Total Interactions -->
                <div class="bg-card text-card-foreground rounded-2xl p-6 shadow-lg border border-border hover:border-primary/50 transition-colors">
                    <div class="flex items-center space-x-3 mb-4">
                        <div class="p-3 bg-primary/20 rounded-lg text-primary">
                            <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>
                        </div>
                        <h3 class="text-lg font-medium text-foreground">Interactions</h3>
                    </div>
                    <div class="text-4xl font-bold">{ totalInteractions }</div>
                    <div class="mt-2 text-xs text-muted-foreground font-medium">
                        📖 {$statsStore.articlesRead || 0} lus • 🔊 {$statsStore.articlesListened || 0} écoutés
                    </div>
                </div>
            </div>

            <!-- Ratio Chart -->
            <div class="bg-card text-card-foreground rounded-2xl p-6 shadow-lg border border-border mt-8">
                <h3 class="text-xl font-medium text-foreground mb-6">Ratio d'utilisation (Lu vs Écouté)</h3>
                
                <div class="relative pt-1">
                    <div class="flex mb-2 items-center justify-between">
                        <div>
                            <span class="text-xs font-semibold inline-block py-1 px-2 uppercase rounded-full text-primary bg-primary/20">
                                Lu ({$statsStore.articlesRead})
                            </span>
                        </div>
                        <div class="text-right">
                            <span class="text-xs font-semibold inline-block py-1 px-2 uppercase rounded-full text-foreground bg-accent">
                                Écouté ({$statsStore.articlesListened})
                            </span>
                        </div>
                    </div>
                    <div class="overflow-hidden h-4 mb-4 text-xs flex rounded-full bg-accent">
                        <div style="width: {readPercentage}%" class="shadow-none flex flex-col text-center whitespace-nowrap text-primary-foreground justify-center bg-primary transition-all duration-1000"></div>
                        <div style="width: {listenPercentage}%" class="shadow-none flex flex-col text-center whitespace-nowrap text-foreground justify-center bg-muted-foreground/40 transition-all duration-1000"></div>
                    </div>
                </div>
            </div>

            <!-- Token Usage Table -->
            <div class="bg-card text-card-foreground rounded-2xl p-6 shadow-lg border border-border mt-8">
                <h3 class="text-xl font-medium text-foreground mb-6 flex items-center gap-2">
                    <svg class="w-6 h-6 text-primary" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                    Consommation API (Tokens & Coûts)
                </h3>
                
                {#if $statsStore.token_usage && $statsStore.token_usage.length > 0}
                <div class="overflow-x-auto">
                    <table class="w-full text-left border-collapse">
                        <thead>
                            <tr class="border-b border-border text-muted-foreground text-sm">
                                <th class="pb-3 px-2 font-semibold">Type d'usage</th>
                                <th class="pb-3 px-2 font-semibold">Fournisseur</th>
                                <th class="pb-3 px-2 font-semibold text-right">Tokens In</th>
                                <th class="pb-3 px-2 font-semibold text-right">Tokens Out</th>
                                <th class="pb-3 px-2 font-semibold text-right">Coût Est. (€)</th>
                            </tr>
                        </thead>
                        <tbody class="text-foreground text-sm">
                            {#each $statsStore.token_usage as row}
                                <tr class="border-b border-border/50 hover:bg-accent/50">
                                    <td class="py-3 px-2 capitalize font-medium">{row.usage_type}</td>
                                    <td class="py-3 px-2">
                                        <span class="px-2.5 py-1 rounded-md text-[10px] font-bold uppercase tracking-wider 
                                            {row.provider.toLowerCase().includes('mistral') ? 'bg-primary/20 text-primary border border-primary/30' : 
                                            row.provider.toLowerCase().includes('gemini') ? 'bg-primary/10 text-primary border border-primary/20' : 
                                            'bg-accent text-foreground'}">
                                            {row.provider}
                                        </span>
                                    </td>
                                    <td class="py-3 px-2 text-right font-mono text-xs">{row.tokens_in.toLocaleString()}</td>
                                    <td class="py-3 px-2 text-right font-mono text-xs">{row.tokens_out.toLocaleString()}</td>
                                    <td class="py-3 px-2 text-right font-bold text-primary">{row.cost_eur > 0 ? row.cost_eur.toFixed(4) + ' €' : '-'}</td>
                                </tr>
                            {/each}
                            <!-- Total Row -->
                            <tr class="bg-background font-bold">
                                <td class="py-3 px-2 text-foreground" colspan="2">TOTAL</td>
                                <td class="py-3 px-2 text-right font-mono text-xs">
                                    {$statsStore.token_usage.reduce((sum, r) => sum + r.tokens_in, 0).toLocaleString()}
                                </td>
                                <td class="py-3 px-2 text-right font-mono text-xs">
                                    {$statsStore.token_usage.reduce((sum, r) => sum + r.tokens_out, 0).toLocaleString()}
                                </td>
                                <td class="py-3 px-2 text-right text-primary">
                                    {$statsStore.token_usage.reduce((sum, r) => sum + r.cost_eur, 0).toFixed(4)} €
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>
                {:else}
                <div class="p-6 text-center text-muted-foreground text-sm border border-dashed border-border rounded-xl">
                    ⚡ Aucune donnée de jetons enregistrée pour le moment. La consommation sera affichée ici lors des prochaines générations d'articles, synthèses ou podcasts.
                </div>
                {/if}
            </div>
        {/if}
    </div>
</div>
