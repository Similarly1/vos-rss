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
            error = "Veuillez coller du code HTML d'échantillon.";
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
            const data = await res.json();
            if (res.ok && data.blocks) {
                blocks = data.blocks;
                step = 3;
            } else {
                error = data.detail || "Échec de l'analyse HTML par l'IA.";
            }
        } catch (e) {
            error = "Erreur de connexion lors de l'analyse.";
        } finally {
            loading = false;
        }
    }

    function selectBlock(block) {
        if (!currentAssigning) return;
        mapping[currentAssigning] = block.selector;
        mapping = { ...mapping };
    }

    function getAssignedRole(selector) {
        if (mapping.title === selector) return 'Titre';
        if (mapping.content === selector) return 'Contenu';
        if (mapping.author === selector) return 'Auteur';
        return null;
    }

    async function saveSource(isMailhook = false) {
        if (!sourceName.trim()) {
            error = "Le nom de la source est obligatoire.";
            return;
        }

        loading = true;
        error = null;

        const payload = {
            token: token,
            name: sourceName,
            source_type: sourceType,
            category: category,
            field_mapping: isMailhook ? null : mapping
        };

        try {
            const res = await fetch('/api/v1/webhooks/sources', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (res.ok) {
                step = 4;
            } else {
                const data = await res.json();
                error = data.detail || "Échec de l'enregistrement de la source.";
            }
        } catch (e) {
            error = "Erreur réseau lors de la sauvegarde.";
        } finally {
            loading = false;
        }
    }
</script>

<div class="p-6 md:p-8 bg-background text-foreground min-h-full font-sans space-y-8 overflow-y-auto">
    
    <!-- HEADER -->
    <header class="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-border pb-6">
        <div>
            <span class="text-xs font-black uppercase tracking-wider text-primary bg-primary/20 px-3 py-1 rounded-full border border-primary/30">
                🔌 Ingestion Webhook & Mailhook
            </span>
            <h1 class="text-2xl md:text-3xl font-black text-foreground tracking-tight mt-2">Assistant de Configuration Ingestion</h1>
            <p class="text-xs text-muted-foreground mt-1">Créez une entrée Webhook sur-mesure pour vos newsletters par email ou n'importe quel site web.</p>
        </div>

        <!-- STEP INDICATOR -->
        <div class="flex items-center gap-2 text-xs font-semibold">
            <span class="px-3 py-1.5 rounded-xl transition-all {step >= 1 ? 'bg-primary text-primary-foreground shadow-sm' : 'bg-background text-muted-foreground border border-border'}">1. Type</span>
            <span class="text-muted-foreground">→</span>
            <span class="px-3 py-1.5 rounded-xl transition-all {step >= 2 ? 'bg-primary text-primary-foreground shadow-sm' : 'bg-background text-muted-foreground border border-border'}">2. Config</span>
            {#if sourceType === 'custom_html'}
                <span class="text-muted-foreground">→</span>
                <span class="px-3 py-1.5 rounded-xl transition-all {step >= 3 ? 'bg-primary text-primary-foreground shadow-sm' : 'bg-background text-muted-foreground border border-border'}">3. Clic & Valide</span>
            {/if}
            <span class="text-muted-foreground">→</span>
            <span class="px-3 py-1.5 rounded-xl transition-all {step === 4 ? 'bg-primary text-primary-foreground shadow-sm' : 'bg-background text-muted-foreground border border-border'}">Prêt !</span>
        </div>
    </header>

    {#if error}
        <div class="p-4 bg-destructive/10 border border-destructive/30 rounded-2xl text-destructive text-xs font-semibold flex items-center justify-between">
            <span>⚠️ {error}</span>
            <button on:click={() => error = null} class="text-xs font-bold">✕</button>
        </div>
    {/if}

    <!-- MAIN STEP CONTENT -->
    <div class="bg-card text-card-foreground p-6 md:p-8 rounded-3xl border border-border shadow-sm space-y-6">
        
        <!-- STEP 1: CHOICE OF SOURCE TYPE -->
        {#if step === 1}
            <div class="space-y-6">
                <div>
                    <h3 class="text-lg font-bold text-foreground">Étape 1 : Choisissez le type de source</h3>
                    <p class="text-xs text-muted-foreground mt-1">Sélectionnez la manière dont votre service externe transmettra les données.</p>
                </div>

                <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <!-- OPTION A: MAILHOOK / NEWSLETTER -->
                    <button 
                        type="button"
                        on:click={() => selectSourceType('mailhook')}
                        class="p-6 text-left rounded-3xl border-2 border-border hover:border-primary bg-background hover:bg-primary/5 transition-all group cursor-pointer space-y-4"
                    >
                        <div class="flex items-center justify-between">
                            <span class="text-4xl p-3 bg-primary/10 rounded-2xl">📧</span>
                            <span class="text-xs font-bold px-3 py-1 bg-primary text-primary-foreground rounded-full">Simple & Rapide</span>
                        </div>
                        <div>
                            <h4 class="font-bold text-base text-foreground group-hover:text-primary transition-colors">Mailhook / Email / Newsletters</h4>
                            <p class="text-xs text-muted-foreground mt-1 leading-relaxed">
                                Pour les emails (Mailhooks.dev, Zapier, Make, n8n) qui envoient déjà un JSON propre avec le titre et le texte. 
                                <strong class="text-primary">Aucun code à coller !</strong>
                            </p>
                        </div>
                    </button>

                    <!-- OPTION B: CUSTOM HTML / SCRAPING -->
                    <button 
                        type="button"
                        on:click={() => selectSourceType('custom_html')}
                        class="p-6 text-left rounded-3xl border-2 border-border hover:border-primary bg-background hover:bg-primary/5 transition-all group cursor-pointer space-y-4"
                    >
                        <div class="flex items-center justify-between">
                            <span class="text-4xl p-3 bg-primary/10 rounded-2xl">🌐</span>
                            <span class="text-xs font-bold px-3 py-1 bg-primary text-primary-foreground rounded-full">Assistant IA</span>
                        </div>
                        <div>
                            <h4 class="font-bold text-base text-foreground group-hover:text-primary transition-colors">Page Web / HTML brut / PDF (Clic & Valide)</h4>
                            <p class="text-xs text-muted-foreground mt-1 leading-relaxed">
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
                        <h3 class="text-lg font-bold text-foreground">Étape 2 : Identifiez votre Mailhook</h3>
                        <p class="text-xs text-muted-foreground mt-1">Donnez un nom explicite à cette source d'email.</p>
                    </div>

                    <div class="space-y-4">
                        <div>
                            <label class="block text-xs font-bold text-foreground mb-1">Nom de la source *</label>
                            <input type="text" bind:value={sourceName} placeholder="ex: Newsletter Tech Crunch ou Mails Substack" class="w-full bg-background border border-border rounded-xl py-2.5 px-3.5 text-xs text-foreground focus:ring-2 focus:ring-primary" />
                        </div>

                        <div>
                            <label class="block text-xs font-bold text-foreground mb-1">Catégorie cible</label>
                            <select bind:value={category} class="w-full bg-background border border-border rounded-xl py-2.5 px-3.5 text-xs text-foreground focus:ring-2 focus:ring-primary">
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
                        <button on:click={() => step = 1} class="px-4 py-2.5 bg-background border border-border text-foreground font-bold rounded-xl text-xs">
                            ← Retour
                        </button>
                        <button on:click={() => saveSource(true)} disabled={loading || !sourceName} class="flex-1 px-5 py-2.5 bg-primary text-primary-foreground font-bold rounded-xl text-xs shadow-md transition-all disabled:opacity-50">
                            {loading ? 'Création...' : "🚀 Générer l'URL Webhook Mailhook"}
                        </button>
                    </div>
                </div>
            {:else}
                <!-- CUSTOM HTML INPUT -->
                <div class="space-y-6">
                    <div>
                        <h3 class="text-lg font-bold text-foreground">Étape 2 : Collez un échantillon HTML</h3>
                        <p class="text-xs text-muted-foreground mt-1">Copiez/collez le code HTML brut de la page web ou de l'article à analyser.</p>
                    </div>

                    <textarea 
                        bind:value={rawHtml} 
                        placeholder="Collez le code HTML de votre article ici (<article><h1>Mon titre</h1>...)..." 
                        rows="8"
                        class="w-full bg-background border border-border rounded-2xl p-4 text-xs font-mono text-foreground focus:ring-2 focus:ring-primary"
                    ></textarea>

                    <div class="flex gap-3">
                        <button on:click={() => step = 1} class="px-4 py-2.5 bg-background border border-border text-foreground font-bold rounded-xl text-xs">
                            ← Retour
                        </button>
                        <button on:click={analyzeHtml} disabled={loading || !rawHtml.trim()} class="flex-1 px-5 py-2.5 bg-primary text-primary-foreground font-bold rounded-xl text-xs shadow-md transition-all disabled:opacity-50">
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
                    <h3 class="text-lg font-bold text-foreground">Étape 3 : Assistant visuel "Clic & Valide"</h3>
                    <p class="text-xs text-muted-foreground mt-1">Sélectionnez d'abord quel élément vous souhaitez définir, puis cliquez sur le bloc correspondant.</p>
                </div>

                <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
                    <!-- LEFT CONFIG PANEL -->
                    <div class="space-y-6 bg-background p-5 rounded-2xl border border-border">
                        <div class="space-y-3">
                            <label class="block text-xs font-bold text-foreground">Nom de la source *</label>
                            <input type="text" bind:value={sourceName} placeholder="ex: Blog Le Monde" class="w-full bg-card border border-border rounded-xl py-2 px-3 text-xs text-foreground" />
                        </div>

                        <div class="space-y-3">
                            <label class="block text-xs font-bold text-foreground">Rôle à assigner :</label>
                            <div class="space-y-2">
                                <label class="flex items-center gap-2 p-2 rounded-xl bg-card border border-border cursor-pointer text-xs font-semibold">
                                    <input type="radio" bind:group={currentAssigning} value="title" class="accent-primary" />
                                    📌 Titre {mapping.title ? '✅' : ''}
                                </label>
                                <label class="flex items-center gap-2 p-2 rounded-xl bg-card border border-border cursor-pointer text-xs font-semibold">
                                    <input type="radio" bind:group={currentAssigning} value="content" class="accent-primary" />
                                    📝 Corps / Contenu {mapping.content ? '✅' : ''}
                                </label>
                                <label class="flex items-center gap-2 p-2 rounded-xl bg-card border border-border cursor-pointer text-xs font-semibold">
                                    <input type="radio" bind:group={currentAssigning} value="author" class="accent-primary" />
                                    👤 Auteur {mapping.author ? '✅' : ''}
                                </label>
                            </div>
                        </div>

                        <div class="pt-4 space-y-2">
                            <button on:click={() => saveSource(false)} disabled={loading || !sourceName} class="w-full py-2.5 bg-primary text-primary-foreground font-bold rounded-xl text-xs shadow-md transition-all disabled:opacity-50">
                                {loading ? 'Sauvegarde...' : 'Enregistrer le Filtre & Continuer'}
                            </button>
                            <button on:click={() => step = 2} class="w-full py-2 bg-background border border-border text-foreground font-semibold rounded-xl text-xs">
                                Modifier l'échantillon
                            </button>
                        </div>
                    </div>

                    <!-- RIGHT BLOCKS PANEL -->
                    <div class="lg:col-span-2 space-y-3 max-h-[550px] overflow-y-auto pr-2">
                        <h4 class="font-bold text-xs uppercase tracking-wider text-muted-foreground">Blocs Visuels Détectés par l'IA :</h4>
                        {#if blocks.length === 0}
                            <p class="text-xs text-muted-foreground p-6 text-center border border-dashed border-border rounded-2xl">Aucun bloc sémantique extrait.</p>
                        {:else}
                            {#each blocks as block}
                                <div 
                                    role="button"
                                    tabindex="0"
                                    on:click={() => selectBlock(block)}
                                    on:keydown={(e) => e.key === 'Enter' && selectBlock(block)}
                                    class="p-4 rounded-2xl border transition-all cursor-pointer relative space-y-1.5 {getAssignedRole(block.selector) ? 'bg-primary/20 border-primary' : 'bg-background border-border hover:border-primary/60'}"
                                >
                                    {#if getAssignedRole(block.selector)}
                                        <span class="absolute top-2 right-3 px-2 py-0.5 bg-primary text-primary-foreground font-black text-[10px] rounded-full uppercase">
                                            {getAssignedRole(block.selector)}
                                        </span>
                                    {/if}
                                    <p class="text-xs text-foreground font-medium leading-relaxed">{block.text}</p>
                                    <span class="text-[10px] font-mono text-muted-foreground block">Selector: {block.selector}</span>
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
                <div class="flex items-center gap-3 text-primary">
                    <span class="text-3xl">🎉</span>
                    <div>
                        <h3 class="text-xl font-bold text-foreground">Source "{sourceName}" configurée avec succès !</h3>
                        <p class="text-xs text-muted-foreground">Votre token d'ingestion unique est prêt.</p>
                    </div>
                </div>

                <!-- ENDPOINT URL BOX -->
                <div class="bg-background text-foreground p-5 rounded-2xl space-y-2 border border-border font-mono text-xs">
                    <span class="text-primary font-bold block uppercase text-[10px]">URL d'ingestion POST :</span>
                    <div class="flex items-center justify-between bg-card p-3 rounded-xl gap-2 overflow-x-auto border border-border">
                        <code class="text-primary font-bold select-all">https://adrienotge.nohost.me/api/v1/webhooks/ingest</code>
                    </div>
                    <div class="pt-2 text-muted-foreground">
                        Header d'authentification : <code class="text-primary">X-Webhook-Token: {token}</code>
                    </div>
                </div>

                <!-- INTEGRATION GUIDES -->
                <div class="space-y-3">
                    <h4 class="font-bold text-sm text-foreground">Guide d'intégration pas à pas :</h4>

                    <details class="bg-background p-4 rounded-2xl border border-border text-xs">
                        <summary class="font-bold cursor-pointer text-primary">📧 Mailhooks.dev / Newsletters par Email</summary>
                        <div class="mt-3 space-y-2 text-foreground">
                            <p>1. Sur Mailhooks.dev, créez un récepteur d'email (ex: <code>my-newsletters@mailhooks.dev</code>).</p>
                            <p>2. Définissez la destination Webhook vers : <code>https://adrienotge.nohost.me/api/v1/webhooks/ingest</code></p>
                            <p>3. Ajoutez le header : <code>X-Webhook-Token = {token}</code></p>
                            <p>4. Transférez n'importe quelle newsletter à cette adresse : elle sera automatiquement ingérée et synthétisée dans Vos !</p>
                        </div>
                    </details>

                    <details class="bg-background p-4 rounded-2xl border border-border text-xs">
                        <summary class="font-bold cursor-pointer text-primary">⚡ n8n / Make / Zapier</summary>
                        <div class="mt-3 space-y-2 text-foreground">
                            <p>1. Ajoutez un nœud <strong>HTTP Request / Custom Request</strong> avec la méthode <strong>POST</strong>.</p>
                            <p>2. URL : <code>https://adrienotge.nohost.me/api/v1/webhooks/ingest</code></p>
                            <p>3. Header HTTP : <code>X-Webhook-Token: {token}</code></p>
                            <p>4. Envoyez le JSON : <code>{`{"title": "Mon Titre", "content": "Contenu de l'article", "url": "https://..."}`}</code></p>
                        </div>
                    </details>
                </div>

                <div class="pt-4 flex gap-4">
                    <button on:click={resetWizard} class="px-6 py-3 bg-primary text-primary-foreground font-bold rounded-xl text-xs shadow-md transition-all">
                        + Créer une autre source Webhook
                    </button>
                </div>
            </div>
        {/if}

    </div>
</div>
