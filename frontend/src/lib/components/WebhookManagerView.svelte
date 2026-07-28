<script>
    import { onMount } from 'svelte';

    let step = 1;
    let rawHtml = '';
    let blocks = [];
    let loading = false;
    let error = null;
    
    let sourceName = '';
    let token = '';
    let category = 'Général';
    
    let mapping = {
        title: null,
        content: null,
        author: null
    };
    
    let currentAssigning = 'title';

    onMount(() => {
        token = crypto.randomUUID();
    });

    async function analyzeHtml() {
        if (!rawHtml.trim()) {
            error = "Veuillez coller du HTML.";
            return;
        }
        loading = true;
        error = null;
        try {
            // Using absolute URL if base URL isn't configured for relative fetch in SvelteKit/Vite
            const res = await fetch('/api/v1/webhooks/analyze-sample', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ html: rawHtml })
            });
            if (!res.ok) throw new Error("Erreur de l'API");
            const data = await res.json();
            blocks = data.blocks || [];
            step = 2;
        } catch (e) {
            error = "Impossible d'analyser le HTML. Vérifiez la connexion au backend.";
        } finally {
            loading = false;
        }
    }

    function selectBlock(block) {
        mapping[currentAssigning] = block.selector;
        // Auto-advance to next assignment
        if (currentAssigning === 'title') currentAssigning = 'content';
        else if (currentAssigning === 'content') currentAssigning = 'author';
    }

    function getAssignedRole(selector) {
        if (mapping.title === selector) return 'Titre';
        if (mapping.content === selector) return 'Contenu';
        if (mapping.author === selector) return 'Auteur';
        return null;
    }

    async function saveSource() {
        if (!sourceName.trim()) {
            error = "Veuillez entrer un nom pour la source.";
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
                    css_selectors_json: JSON.stringify(mapping)
                })
            });
            if (!res.ok) throw new Error("Erreur lors de l'enregistrement");
            step = 3;
        } catch (e) {
            error = "Impossible d'enregistrer la source.";
        } finally {
            loading = false;
        }
    }
</script>

<div class="webhook-manager">
    <header class="header">
        <h2>Création de Source Webhook (Clic & Valide)</h2>
        <div class="stepper">
            <span class="step" class:active={step >= 1}>1. Échantillon</span>
            <span class="divider"></span>
            <span class="step" class:active={step >= 2}>2. Mapping</span>
            <span class="divider"></span>
            <span class="step" class:active={step >= 3}>3. Intégration</span>
        </div>
    </header>

    {#if error}
        <div class="error-alert">{error}</div>
    {/if}

    <main class="content">
        {#if step === 1}
            <div class="step-1">
                <p>Collez un échantillon de code HTML provenant de votre source pour que notre assistant analyse la structure.</p>
                <textarea 
                    bind:value={rawHtml} 
                    placeholder="Collez le HTML ici..."
                    rows="10"
                ></textarea>
                <button class="primary-btn" on:click={analyzeHtml} disabled={loading}>
                    {#if loading} Analyse en cours... {:else} Analyser l'échantillon {/if}
                </button>
            </div>
        {/if}

        {#if step === 2}
            <div class="step-2">
                <div class="config-panel">
                    <h3>Paramètres de la source</h3>
                    <input type="text" bind:value={sourceName} placeholder="Nom de la source (ex: Mon Blog WordPress)" />
                    <input type="text" bind:value={category} placeholder="Catégorie" />
                    
                    <h3>Assignation des blocs</h3>
                    <p>Cliquez sur les blocs à droite pour leur assigner un rôle.</p>
                    <div class="roles">
                        <label>
                            <input type="radio" bind:group={currentAssigning} value="title" />
                            Titre {mapping.title ? '✅' : ''}
                        </label>
                        <label>
                            <input type="radio" bind:group={currentAssigning} value="content" />
                            Contenu (Corps) {mapping.content ? '✅' : ''}
                        </label>
                        <label>
                            <input type="radio" bind:group={currentAssigning} value="author" />
                            Auteur {mapping.author ? '✅' : ''}
                        </label>
                    </div>

                    <button class="primary-btn" on:click={saveSource} disabled={loading || !sourceName}>
                        {#if loading} Enregistrement... {:else} Enregistrer et Continuer {/if}
                    </button>
                    <button class="secondary-btn" on:click={() => step = 1}>Retour</button>
                </div>

                <div class="blocks-panel">
                    <h3>Blocs Détectés</h3>
                    {#if blocks.length === 0}
                        <p class="empty-state">Aucun bloc sémantique détecté.</p>
                    {:else}
                        {#each blocks as block}
                            <!-- svelte-ignore a11y-click-events-have-key-events -->
                            <div 
                                class="block-card" 
                                class:assigned={getAssignedRole(block.selector)}
                                on:click={() => selectBlock(block)}
                            >
                                {#if getAssignedRole(block.selector)}
                                    <span class="badge">{getAssignedRole(block.selector)}</span>
                                {/if}
                                <div class="block-text">{block.text}</div>
                                <div class="block-selector">Sélecteur: {block.selector}</div>
                            </div>
                        {/each}
                    {/if}
                </div>
            </div>
        {/if}

        {#if step === 3}
            <div class="step-3">
                <h3>Source "{sourceName}" créée avec succès ! 🎉</h3>
                <p>Votre token unique est : <strong>{token}</strong></p>
                <p>Envoyez une requête POST à l'URL suivante avec le header <code>X-Webhook-Token: {token}</code> :</p>
                <div class="url-box">
                    <code>https://votre-domaine.com/api/v1/webhooks/ingest</code>
                </div>

                <h4>Instructions d'intégration</h4>
                <div class="integrations">
                    <details>
                        <summary><strong>n8n</strong></summary>
                        <ol>
                            <li>Ajoutez un nœud <strong>HTTP Request</strong>.</li>
                            <li>Méthode : POST</li>
                            <li>URL : <code>https://votre-domaine.com/api/v1/webhooks/ingest</code></li>
                            <li>Ajoutez un header : Name = <code>X-Webhook-Token</code>, Value = <code>{token}</code></li>
                            <li>Dans le Body, envoyez un JSON avec `content` (le HTML de votre page) et optionnellement `title` ou `url`.</li>
                        </ol>
                    </details>

                    <details>
                        <summary><strong>Make (Integromat)</strong></summary>
                        <ol>
                            <li>Ajoutez un module <strong>HTTP - Make a request</strong>.</li>
                            <li>URL : <code>https://votre-domaine.com/api/v1/webhooks/ingest</code></li>
                            <li>Method : POST</li>
                            <li>Headers : Key = <code>X-Webhook-Token</code>, Value = <code>{token}</code></li>
                            <li>Body type : Raw / JSON. Insérez le champ `content` avec le HTML.</li>
                        </ol>
                    </details>

                    <details>
                        <summary><strong>Zapier</strong></summary>
                        <ol>
                            <li>Ajoutez une action <strong>Webhooks by Zapier</strong> -> <strong>Custom Request</strong>.</li>
                            <li>Method : POST</li>
                            <li>URL : <code>https://votre-domaine.com/api/v1/webhooks/ingest</code></li>
                            <li>Data : <code>{{"content": "..."}}</code></li>
                            <li>Headers : <code>X-Webhook-Token</code> = <code>{token}</code></li>
                        </ol>
                    </details>
                </div>
                
                <button class="primary-btn" on:click={() => { step = 1; rawHtml = ''; blocks = []; sourceName = ''; token = crypto.randomUUID(); mapping = {title: null, content: null, author: null}; }}>
                    Créer une nouvelle source
                </button>
            </div>
        {/if}
    </main>
</div>

<style>
    .webhook-manager {
        max-width: 1000px;
        margin: 0 auto;
        font-family: system-ui, -apple-system, sans-serif;
        background: #fff;
        border-radius: 12px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.08);
        overflow: hidden;
    }

    .header {
        background: #f8fafc;
        padding: 1.5rem 2rem;
        border-bottom: 1px solid #e2e8f0;
    }

    .header h2 {
        margin: 0 0 1rem 0;
        color: #0f172a;
    }

    .stepper {
        display: flex;
        align-items: center;
        gap: 1rem;
        font-size: 0.9rem;
        font-weight: 500;
        color: #64748b;
    }

    .step.active {
        color: #3b82f6;
    }

    .divider {
        flex: 1;
        height: 2px;
        background: #e2e8f0;
    }

    .error-alert {
        background: #fef2f2;
        color: #ef4444;
        padding: 1rem 2rem;
        border-bottom: 1px solid #f87171;
    }

    .content {
        padding: 2rem;
    }

    textarea {
        width: 100%;
        padding: 1rem;
        border: 1px solid #cbd5e1;
        border-radius: 8px;
        margin-bottom: 1rem;
        font-family: monospace;
        resize: vertical;
    }

    input[type="text"] {
        width: 100%;
        padding: 0.75rem;
        border: 1px solid #cbd5e1;
        border-radius: 6px;
        margin-bottom: 1rem;
    }

    button {
        padding: 0.75rem 1.5rem;
        border-radius: 6px;
        border: none;
        font-weight: 600;
        cursor: pointer;
        transition: opacity 0.2s;
    }

    button:disabled {
        opacity: 0.6;
        cursor: not-allowed;
    }

    .primary-btn {
        background: #3b82f6;
        color: white;
    }

    .secondary-btn {
        background: #e2e8f0;
        color: #334155;
    }

    .step-2 {
        display: grid;
        grid-template-columns: 350px 1fr;
        gap: 2rem;
    }

    .config-panel {
        background: #f8fafc;
        padding: 1.5rem;
        border-radius: 8px;
        border: 1px solid #e2e8f0;
    }

    .roles {
        display: flex;
        flex-direction: column;
        gap: 0.75rem;
        margin-bottom: 1.5rem;
    }

    .roles label {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        cursor: pointer;
        padding: 0.5rem;
        border-radius: 4px;
    }
    
    .roles label:hover {
        background: #e2e8f0;
    }

    .blocks-panel {
        display: flex;
        flex-direction: column;
        gap: 1rem;
        max-height: 600px;
        overflow-y: auto;
    }

    .block-card {
        padding: 1rem;
        border: 2px solid #e2e8f0;
        border-radius: 8px;
        cursor: pointer;
        position: relative;
        transition: all 0.2s;
    }

    .block-card:hover {
        border-color: #94a3b8;
        transform: translateY(-2px);
    }

    .block-card.assigned {
        border-color: #3b82f6;
        background: #eff6ff;
    }

    .block-text {
        font-size: 0.95rem;
        color: #334155;
        margin-bottom: 0.5rem;
    }

    .block-selector {
        font-size: 0.8rem;
        color: #64748b;
        font-family: monospace;
    }

    .badge {
        position: absolute;
        top: -10px;
        right: 10px;
        background: #3b82f6;
        color: white;
        padding: 0.2rem 0.6rem;
        border-radius: 99px;
        font-size: 0.75rem;
        font-weight: 600;
    }

    .url-box {
        background: #f1f5f9;
        padding: 1rem;
        border-radius: 6px;
        border: 1px solid #cbd5e1;
        margin-bottom: 1.5rem;
    }

    .integrations details {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 6px;
        margin-bottom: 0.5rem;
        padding: 0.5rem 1rem;
    }

    .integrations summary {
        cursor: pointer;
        outline: none;
        padding: 0.5rem 0;
    }

    .integrations ol {
        margin: 0;
        padding-left: 1.5rem;
        padding-bottom: 1rem;
        color: #475569;
        line-height: 1.6;
    }
</style>
