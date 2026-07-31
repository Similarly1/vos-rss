<script>
    import { createEventDispatcher } from 'svelte';
    import { fade, fly } from 'svelte/transition';
    
    export let isVisible = false;
    
    const dispatch = createEventDispatcher();
    
    let step = 1;
    let rssUrl = '';
    let aiProvider = 'mistral';
    let apiKey = '';

    function nextStep() {
        if (step < 2) step++;
    }

    function skip() {
        isVisible = false;
        dispatch('skip');
    }

    function finish() {
        isVisible = false;
        dispatch('finish', { rssUrl, aiProvider, apiKey });
    }
</script>

{#if isVisible}
<div class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-background/80 backdrop-blur-sm" transition:fade>
    <div class="bg-background rounded-3xl shadow-2xl border border-slate-700/60 w-full max-w-xl overflow-hidden" 
         transition:fly="{{ y: 20, duration: 300 }}">
        
        <!-- Header -->
        <div class="px-8 py-6 border-b border-slate-800 flex justify-between items-center">
            <h2 class="text-2xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-purple-500">
                Bienvenue sur Nifty Mendel
            </h2>
            <span class="text-sm text-slate-500 font-medium">Étape {step} / 2</span>
        </div>

        <!-- Content -->
        <div class="p-8">
            {#if step === 1}
                <div in:fade>
                    <h3 class="text-xl font-medium text-white mb-2">Commençons par vos flux</h3>
                    <p class="text-slate-400 mb-6 text-sm">Ajoutez votre premier flux RSS ou importez un fichier OPML.</p>
                    
                    <div class="space-y-4">
                        <div>
                            <label for="rssUrl" class="block text-sm font-medium text-slate-300 mb-1">URL du flux RSS</label>
                            <input type="url" id="rssUrl" bind:value={rssUrl} placeholder="https://example.com/feed.xml"
                                class="w-full bg-background border border-slate-700 rounded-xl px-4 py-3 text-white placeholder-slate-600 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all"/>
                        </div>
                        
                        <div class="relative flex items-center py-2">
                            <div class="flex-grow border-t border-slate-700"></div>
                            <span class="flex-shrink-0 mx-4 text-slate-500 text-sm">OU</span>
                            <div class="flex-grow border-t border-slate-700"></div>
                        </div>

                        <div>
                            <button class="w-full py-4 border-2 border-dashed border-slate-700 rounded-xl text-slate-400 hover:text-white hover:border-slate-500 hover:bg-card/50 transition-all flex flex-col items-center justify-center">
                                <svg class="w-8 h-8 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"></path></svg>
                                <span>Importer un fichier OPML</span>
                            </button>
                        </div>
                    </div>
                </div>
            {:else if step === 2}
                <div in:fade>
                    <h3 class="text-xl font-medium text-white mb-2">Configuration de l'IA</h3>
                    <p class="text-slate-400 mb-6 text-sm">Choisissez votre fournisseur pour les résumés et la synthèse.</p>
                    
                    <div class="space-y-6">
                        <div class="grid grid-cols-2 gap-4">
                            <label class="cursor-pointer relative">
                                <input type="radio" bind:group={aiProvider} value="mistral" class="peer sr-only" />
                                <div class="p-4 rounded-xl border border-slate-700 bg-background peer-checked:border-orange-500 peer-checked:ring-1 peer-checked:ring-orange-500 transition-all">
                                    <span class="block text-white font-medium mb-1">Mistral AI</span>
                                    <span class="text-xs text-slate-500">Recommandé</span>
                                </div>
                            </label>
                            
                            <label class="cursor-pointer relative">
                                <input type="radio" bind:group={aiProvider} value="gemini" class="peer sr-only" />
                                <div class="p-4 rounded-xl border border-slate-700 bg-background peer-checked:border-blue-500 peer-checked:ring-1 peer-checked:ring-blue-500 transition-all">
                                    <span class="block text-white font-medium mb-1">Google Gemini</span>
                                    <span class="text-xs text-slate-500">Rapide & efficace</span>
                                </div>
                            </label>
                        </div>

                        <div>
                            <label for="apiKey" class="block text-sm font-medium text-slate-300 mb-1">Clé API {aiProvider === 'mistral' ? 'Mistral' : 'Gemini'}</label>
                            <input type="password" id="apiKey" bind:value={apiKey} placeholder="Entrez votre clé API..."
                                class="w-full bg-background border border-slate-700 rounded-xl px-4 py-3 text-white placeholder-slate-600 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all"/>
                            
                            <p class="mt-2 text-xs text-slate-500">
                                {#if aiProvider === 'mistral'}
                                    <a href="https://console.mistral.ai/api-keys/" target="_blank" class="text-blue-400 hover:underline">Obtenir une clé Mistral</a>
                                {:else}
                                    <a href="https://aistudio.google.com/app/apikey" target="_blank" class="text-blue-400 hover:underline">Obtenir une clé Gemini</a>
                                {/if}
                            </p>
                        </div>
                    </div>
                </div>
            {/if}
        </div>

        <!-- Footer -->
        <div class="px-8 py-4 bg-background border-t border-slate-800 flex justify-between items-center">
            <button on:click={skip} class="text-sm text-slate-400 hover:text-white transition-colors">
                Passer cette étape
            </button>
            
            {#if step === 1}
                <button on:click={nextStep} class="px-6 py-2 bg-primary text-primary-foreground hover:bg-blue-500 text-white rounded-lg font-medium transition-colors">
                    Suivant
                </button>
            {:else}
                <button on:click={finish} class="px-6 py-2 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 text-white rounded-lg font-medium transition-colors">
                    Terminer
                </button>
            {/if}
        </div>
    </div>
</div>
{/if}
