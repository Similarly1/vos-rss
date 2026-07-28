<script>
    import { onMount } from 'svelte';

    // Steps: 
    // 1 = Select Source Type (Mailhook vs Custom HTML)
    // 2 = Config/Input (Mailhook details OR HTML paste)
    // 3 = HTML Mapping (only for Custom HTML)
    // 4 = Final Integration Instructions
    let step = 1;
    let sourceType = 'mailhook'; // 'mailhook' | 'custom_html'
    
    let sourceName = '';
    let category = 'Général';
    let token = '';

    let rawHtml = '';
    let blocks = [];
    let loading = false;
    let error = null;
    
    let mapping = {
        title: null,
        content: null,
        author: null
    };
    
    let currentAssigning = 'title';

    onMount(() => {
        token = crypto.randomUUID();
    });

    function resetWizard() {
        step = 1;
        sourceType = 'mailhook';
        sourceName = '';
        category = 'Général';
        token = crypto.randomUUID();
        rawHtml = '';
        blocks = [];
        error = null;
        mapping = { title: null, content: null, author: null };
    }

    function selectSourceType(type) {
        sourceType = type;
        step = 2;
    }

    async function analyzeHtml() {
        if (!rawHtml.trim()) {
            error = "Veuillez coller un échantillon HTML.";
            return;
        }
        loading = true;
        error = null;
        try {
            const res = await fetch('/api/v1/webhooks/analyze-sample', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ html: rawHtml })
            });
            if (!res.ok) throw new Error("Erreur lors de l'analyse.");
            const data = await res.json();
            blocks = data.blocks || [];
            step = 3;
        } catch (e) {
            error = "Impossible d'analyser le HTML. Vérifiez la connexion backend.";
        } finally {
            loading = false;
        }
    }

    function selectBlock(block) {
        mapping[currentAssigning] = block.selector;
        if (currentAssigning === 'title') currentAssigning = 'content';
        else if (currentAssigning === 'content') currentAssigning = 'author';
    }

    function getAssignedRole(selector) {
        if (mapping.title === selector) return 'Titre';
        if (mapping.content === selector) return 'Contenu';
        if (mapping.author === selector) return 'Auteur';
        return null;
    }

    async function saveSource(isMailhook = false) {
        if (!sourceName.trim()) {
            error = "Veuillez indiquer un nom pour cette source.";
            return;
        }
        loading = true;
        error = null;
        try {
            const res = await fetch('/api/v1/webhooks/sources', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name: sourceName,
                    token: token,
                    category: category,
                    css_selectors_json: isMailhook ? null : JSON.stringify(mapping)
                })
            });
            if (!res.ok) throw new Error("Erreur lors de la sauvegarde.");
            step = 4;
        } catch (e) {
            error = "Impossible d'enregistrer la source.";
        } finally {
            loading = false;
        }
    }
</script>

<div class="p-6 md:p-10 max-w-5xl mx-auto space-y-8 font-sans text-gray-900 dark:text-gray-100">
    
    <!-- HEADER -->
    <header class="bg-white dark:bg-dark-card p-6 md:p-8 rounded-3xl border border-gray-100 dark:border-gray-800 shadow-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
        <div>
            <div class="flex items-center gap-3">
                <span class="p-3 bg-emerald-500/10 text-emerald-500 rounded-2xl text-2xl">🔌</span>
                <div>
                    <h2 class="text-2xl font-bold">Assistant d'Ingestion Webhook</h2>
                    <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">Créez des portes d'entrée pour ingérer automatiquement vos contenus sans code.</p>
                </div>
            </div>
        </div>

        <!-- STEPPER BADGES -->
        <div class="flex items-center gap-2 text-xs font-semibold">
            <span class="px-3 py-1.5 rounded-xl transition-all {step >= 1 ? 'bg-emerald-500 text-white shadow-sm' : 'bg-gray-100 dark:bg-gray-800 text-gray-400'}">1. Type</span>
            <span class="text-gray-300 dark:text-gray-700">→</span>
            <span class="px-3 py-1.5 rounded-xl transition-all {step >= 2 ? 'bg-emerald-500 text-white shadow-sm' : 'bg-gray-100 dark:bg-gray-800 text-gray-400'}">2. Config</span>
            {#if sourceType === 'custom_html'}
                <span class="text-gray-300 dark:text-gray-700">→</span>
                <span class="px-3 py-1.5 rounded-xl transition-all {step >= 3 ? 'bg-emerald-500 text-white shadow-sm' : 'bg-gray-100 dark:bg-gray-800 text-gray-400'}">3. Clic & Valide</span>
            {/if}
            <span class="text-gray-300 dark:text-gray-700">→</span>
            <span class="px-3 py-1.5 rounded-xl transition-all {step === 4 ? 'bg-emerald-500 text-white shadow-sm' : 'bg-gray-100 dark:bg-gray-800 text-gray-400'}">Prêt !</span>
        </div>
    </header>

    {#if error}
        <div class="p-4 bg-rose-500/10 border border-rose-500/30 rounded-2xl text-rose-500 text-xs font-semibold flex items-center justify-between">
            <span>⚠️ {error}</span>
            <button on:click={() => error = null} class="text-xs font-bold">✕</button>
        </div>
    {/if}

    <!-- MAIN STEP CONTENT -->
    <div class="bg-white dark:bg-dark-card p-6 md:p-8 rounded-3xl border border-gray-100 dark:border-gray-800 shadow-sm space-y-6">
        
        <!-- STEP 1: CHOICE OF SOURCE TYPE -->
        {#if step === 1}
            <div class="space-y-6">
                <div>
                    <h3 class="text-lg font-bold text-gray-900 dark:text-white">Étape 1 : Choisissez le type de source</h3>
                    <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">Sélectionnez la manière dont votre service externe transmettra les données.</p>
                </div>

                <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <!-- OPTION A: MAILHOOK / NEWSLETTER -->
                    <button 
                        type="button"
                        on:click={() => selectSourceType('mailhook')}
                        class="p-6 text-left rounded-3xl border-2 border-gray-200 dark:border-gray-700 hover:border-emerald-500 dark:hover:border-emerald-500 bg-gray-50/50 dark:bg-dark-bg/50 hover:bg-emerald-500/5 transition-all group cursor-pointer space-y-4"
                    >
                        <div class="flex items-center justify-between">
                            <span class="text-4xl p-3 bg-emerald-500/10 rounded-2xl">📧</span>
                            <span class="text-xs font-bold px-3 py-1 bg-emerald-500 text-white rounded-full">Simple & Rapide</span>
                        </div>
                        <div>
                            <h4 class="font-bold text-base text-gray-900 dark:text-white group-hover:text-emerald-500 transition-colors">Mailhook / Email / Newsletters</h4>
                            <p class="text-xs text-gray-500 dark:text-gray-400 mt-1 leading-relaxed">
                                Pour les emails (Mailhooks.dev, Zapier, Make, n8n) qui envoient déjà un JSON propre avec le titre et le texte. 
                                <strong class="text-emerald-600 dark:text-emerald-400">Aucun code à coller !</strong>
                            </p>
                        </div>
                    </button>

                    <!-- OPTION B: CUSTOM HTML / SCRAPING -->
                    <button 
                        type="button"
                        on:click={() => selectSourceType('custom_html')}
                        class="p-6 text-left rounded-3xl border-2 border-gray-200 dark:border-gray-700 hover:border-indigo-500 dark:hover:border-indigo-500 bg-gray-50/50 dark:bg-dark-bg/50 hover:bg-indigo-500/5 transition-all group cursor-pointer space-y-4"
                    >
                        <div class="flex items-center justify-between">
                            <span class="text-4xl p-3 bg-indigo-500/10 rounded-2xl">🌐</span>
                            <span class="text-xs font-bold px-3 py-1 bg-indigo-500 text-white rounded-full">Assistant IA</span>
                        </div>
                        <div>
                            <h4 class="font-bold text-base text-gray-900 dark:text-white group-hover:text-indigo-500 transition-colors">Page Web / HTML brut / PDF (Clic & Valide)</h4>
                            <p class="text-xs text-gray-500 dark:text-gray-400 mt-1 leading-relaxed">
                                Pour les sites web bruts. Vous collez un extrait HTML, l'IA découpe les blocs et vous cliquez sur les éléments à extraire.
                            </p>
                        </div>
                    </button>
                </div>
            </div>
        {/if}

        <!-- STEP 2: CONFIG FOR MAILHOOK OR HTML INPUT FOR CUSTOM -->
        {#if step === 2}
            {#if sourceType === 'mailhook'}
                <!-- MAILHOOK CONFIG -->
                <div class="space-y-6 max-w-xl">
                    <div>
                        <h3 class="text-lg font-bold text-gray-900 dark:text-white">Étape 2 : Identifiez votre Mailhook</h3>
                        <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">Donnez un nom explicite à cette source d'email.</p>
                    </div>

                    <div class="space-y-4">
                        <div>
                            <label class="block text-xs font-bold text-gray-700 dark:text-gray-300 mb-1">Nom de la source *</label>
                            <input type="text" bind:value={sourceName} placeholder="ex: Newsletter Tech Crunch ou Mails Substack" class="w-full bg-gray-50 dark:bg-dark-bg border border-gray-200 dark:border-gray-700 rounded-xl py-2.5 px-3.5 text-xs focus:ring-2 focus:ring-emerald-500" />
                        </div>

                        <div>
                            <label class="block text-xs font-bold text-gray-700 dark:text-gray-300 mb-1">Catégorie cible</label>
                            <select bind:value={category} class="w-full bg-gray-50 dark:bg-dark-bg border border-gray-200 dark:border-gray-700 rounded-xl py-2.5 px-3.5 text-xs focus:ring-2 focus:ring-emerald-500">
                                <option value="Général">Général</option>
                                <option value="Technologie">Technologie</option>
                                <option value="Économie">Économie</option>
                                <option value="Science">Science</option>
                                <option value="International">International</option>
                                <option value="Culture">Culture</option>
                            </select>
                        </div>
                    </div>

                    <div class="flex gap-3 pt-4">
                        <button on:click={() => step = 1} class="px-4 py-2.5 bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 font-bold rounded-xl text-xs">
                            ← Retour
                        </button>
                        <button on:click={() => saveSource(true)} disabled={loading || !sourceName} class="flex-1 px-5 py-2.5 bg-emerald-500 hover:bg-emerald-600 text-white font-bold rounded-xl text-xs shadow-md transition-all disabled:opacity-50">
                            {loading ? 'Création...' : "🚀 Générer l'URL Webhook Mailhook"}
                        </button>
                    </div>
                </div>
            {:else}
                <!-- CUSTOM HTML INPUT -->
                <div class="space-y-6">
                    <div>
                        <h3 class="text-lg font-bold text-gray-900 dark:text-white">Étape 2 : Collez un échantillon HTML</h3>
                        <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">Copiez/collez le code HTML brut de la page web ou de l'article à analyser.</p>
                    </div>

                    <textarea 
                        bind:value={rawHtml} 
                        placeholder="Collez le code HTML de votre article ici (<article><h1>Mon titre</h1>...)..." 
                        rows="8"
                        class="w-full bg-gray-50 dark:bg-dark-bg border border-gray-200 dark:border-gray-700 rounded-2xl p-4 text-xs font-mono focus:ring-2 focus:ring-indigo-500"
                    ></textarea>

                    <div class="flex gap-3">
                        <button on:click={() => step = 1} class="px-4 py-2.5 bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 font-bold rounded-xl text-xs">
                            ← Retour
                        </button>
                        <button on:click={analyzeHtml} disabled={loading || !rawHtml.trim()} class="flex-1 px-5 py-2.5 bg-indigo-500 hover:bg-indigo-600 text-white font-bold rounded-xl text-xs shadow-md transition-all disabled:opacity-50">
                            {loading ? 'Analyse par l\'IA en cours...' : '🔍 Analyser l\'échantillon (IA)'}
                        </button>
                    </div>
                </div>
            {/if}
        {/if}

        <!-- STEP 3: VISUAL MAPPING (FOR CUSTOM HTML) -->
        {#if step === 3 && sourceType === 'custom_html'}
            <div class="space-y-6">
                <div>
                    <h3 class="text-lg font-bold text-gray-900 dark:text-white">Étape 3 : Assistant visuel "Clic & Valide"</h3>
                    <p class="text-xs text-gray-500 dark:text-gray-400 mt-1">Sélectionnez d'abord quel élément vous souhaitez définir, puis cliquez sur le bloc correspondant.</p>
                </div>

                <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
                    <!-- LEFT CONFIG PANEL -->
                    <div class="space-y-6 bg-gray-50 dark:bg-dark-bg p-5 rounded-2xl border border-gray-100 dark:border-gray-800">
                        <div class="space-y-3">
                            <label class="block text-xs font-bold text-gray-700 dark:text-gray-300">Nom de la source *</label>
                            <input type="text" bind:value={sourceName} placeholder="ex: Blog Le Monde" class="w-full bg-white dark:bg-dark-card border border-gray-200 dark:border-gray-700 rounded-xl py-2 px-3 text-xs" />
                        </div>

                        <div class="space-y-3">
                            <label class="block text-xs font-bold text-gray-700 dark:text-gray-300">Rôle à assigner :</label>
                            <div class="space-y-2">
                                <label class="flex items-center gap-2 p-2 rounded-xl bg-white dark:bg-dark-card border border-gray-200 dark:border-gray-700 cursor-pointer text-xs font-semibold">
                                    <input type="radio" bind:group={currentAssigning} value="title" class="accent-indigo-500" />
                                    📌 Titre {mapping.title ? '✅' : ''}
                                </label>
                                <label class="flex items-center gap-2 p-2 rounded-xl bg-white dark:bg-dark-card border border-gray-200 dark:border-gray-700 cursor-pointer text-xs font-semibold">
                                    <input type="radio" bind:group={currentAssigning} value="content" class="accent-indigo-500" />
                                    📝 Corps / Contenu {mapping.content ? '✅' : ''}
                                </label>
                                <label class="flex items-center gap-2 p-2 rounded-xl bg-white dark:bg-dark-card border border-gray-200 dark:border-gray-700 cursor-pointer text-xs font-semibold">
                                    <input type="radio" bind:group={currentAssigning} value="author" class="accent-indigo-500" />
                                    👤 Auteur {mapping.author ? '✅' : ''}
                                </label>
                            </div>
                        </div>

                        <div class="pt-4 space-y-2">
                            <button on:click={() => saveSource(false)} disabled={loading || !sourceName} class="w-full py-2.5 bg-indigo-500 hover:bg-indigo-600 text-white font-bold rounded-xl text-xs shadow-md transition-all disabled:opacity-50">
                                {loading ? 'Sauvegarde...' : 'Enregistrer le Filtre & Continuer'}
                            </button>
                            <button on:click={() => step = 2} class="w-full py-2 bg-gray-200 dark:bg-gray-700 text-gray-700 dark:text-gray-300 font-semibold rounded-xl text-xs">
                                Modifer l'échantillon
                            </button>
                        </div>
                    </div>

                    <!-- RIGHT BLOCKS PANEL -->
                    <div class="lg:col-span-2 space-y-3 max-h-[550px] overflow-y-auto pr-2">
                        <h4 class="font-bold text-xs uppercase tracking-wider text-gray-400">Blocs Visuels Détectés par l'IA :</h4>
                        {#if blocks.length === 0}
                            <p class="text-xs text-gray-400 p-6 text-center border border-dashed rounded-2xl">Aucun bloc sémantique extrait.</p>
                        {:else}
                            {#each blocks as block}
                                <div 
                                    role="button"
                                    tabindex="0"
                                    on:click={() => selectBlock(block)}
                                    on:keydown={(e) => e.key === 'Enter' && selectBlock(block)}
                                    class="p-4 rounded-2xl border transition-all cursor-pointer relative space-y-1.5 {getAssignedRole(block.selector) ? 'bg-indigo-50/80 dark:bg-indigo-950/40 border-indigo-500' : 'bg-gray-50 dark:bg-dark-bg border-gray-200 dark:border-gray-800 hover:border-indigo-300'}"
                                >
                                    {#if getAssignedRole(block.selector)}
                                        <span class="absolute top-2 right-3 px-2 py-0.5 bg-indigo-500 text-white font-black text-[10px] rounded-full uppercase">
                                            {getAssignedRole(block.selector)}
                                        </span>
                                    {/if}
                                    <p class="text-xs text-gray-800 dark:text-gray-200 font-medium leading-relaxed">{block.text}</p>
                                    <span class="text-[10px] font-mono text-gray-400 block">Selector: {block.selector}</span>
                                </div>
                            {/each}
                        {/if}
                    </div>
                </div>
            </div>
        {/if}

        <!-- STEP 4: FINAL INTEGRATION INSTRUCTIONS -->
        {#if step === 4}
            <div class="space-y-6">
                <div class="flex items-center gap-3 text-emerald-500">
                    <span class="text-3xl">🎉</span>
                    <div>
                        <h3 class="text-xl font-bold text-gray-900 dark:text-white">Source "{sourceName}" configurée avec succès !</h3>
                        <p class="text-xs text-gray-500 dark:text-gray-400">Votre token d'ingestion unique est prêt.</p>
                    </div>
                </div>

                <!-- ENDPOINT URL BOX -->
                <div class="bg-gray-900 text-white p-5 rounded-2xl space-y-2 border border-gray-800 font-mono text-xs">
                    <span class="text-emerald-400 font-bold block uppercase text-[10px]">URL d'ingestion POST :</span>
                    <div class="flex items-center justify-between bg-black/50 p-3 rounded-xl gap-2 overflow-x-auto">
                        <code class="text-emerald-300 font-bold select-all">https://adrienotge.nohost.me/api/v1/webhooks/ingest</code>
                    </div>
                    <div class="pt-2 text-gray-400">
                        Header d'authentification : <code class="text-yellow-400">X-Webhook-Token: {token}</code>
                    </div>
                </div>

                <!-- INTEGRATION GUIDES -->
                <div class="space-y-3">
                    <h4 class="font-bold text-sm text-gray-900 dark:text-white">Guide d'intégration pas à pas :</h4>

                    <details class="bg-gray-50 dark:bg-dark-bg p-4 rounded-2xl border border-gray-200 dark:border-gray-800 text-xs">
                        <summary class="font-bold cursor-pointer text-emerald-600 dark:text-emerald-400">📧 Mailhooks.dev / Newsletters par Email</summary>
                        <div class="mt-3 space-y-2 text-gray-600 dark:text-gray-300">
                            <p>1. Sur Mailhooks.dev, créez un récepteur d'email (ex: <code>my-newsletters@mailhooks.dev</code>).</p>
                            <p>2. Définissez la destination Webhook vers : <code>https://adrienotge.nohost.me/api/v1/webhooks/ingest</code></p>
                            <p>3. Ajoutez le header : <code>X-Webhook-Token = {token}</code></p>
                            <p>4. Transférez n'importe quelle newsletter à cette adresse : elle sera automatiquement ingérée et synthétisée dans Vos !</p>
                        </div>
                    </details>

                    <details class="bg-gray-50 dark:bg-dark-bg p-4 rounded-2xl border border-gray-200 dark:border-gray-800 text-xs">
                        <summary class="font-bold cursor-pointer text-indigo-600 dark:text-indigo-400">⚡ n8n / Make / Zapier</summary>
                        <div class="mt-3 space-y-2 text-gray-600 dark:text-gray-300">
                            <p>1. Ajoutez un nœud <strong>HTTP Request / Custom Request</strong> avec la méthode <strong>POST</strong>.</p>
                            <p>2. URL : <code>https://adrienotge.nohost.me/api/v1/webhooks/ingest</code></p>
                            <p>3. Header HTTP : <code>X-Webhook-Token: {token}</code></p>
                            <p>4. Envoyez le JSON : <code>{`{"title": "Mon Titre", "content": "Contenu de l'article", "url": "https://..."}`}</code></p>
                        </div>
                    </details>
                </div>

                <div class="pt-4 flex gap-4">
                    <button on:click={resetWizard} class="px-6 py-3 bg-emerald-500 hover:bg-emerald-600 text-white font-bold rounded-xl text-xs shadow-md transition-all">
                        + Créer une autre source Webhook
                    </button>
                </div>
            </div>
        {/if}

    </div>
</div>
