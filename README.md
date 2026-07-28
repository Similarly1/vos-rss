# Vos - Hub d'Écoute et d'Ingestion Universelle & Podcast Studio (Phase 2)

Application PWA intelligente de veille, de regroupement d'actualités et de studio de création de podcasts audio alimenté par les modèles d'Intelligence Artificielle (Mistral, Gemini).

---

## 🌟 Nouveautés de la Phase 2

1. **Ingestion Universelle Webhook & Mailhook**
   Fini le web scraping lourd et la gestion complexe des cookies côté serveur. L'application agit maintenant comme un hub d'écoute passif ultra-performant.
   - **Point d'entrée Webhook unique** (`/api/v1/webhooks/ingest`) pour ingérer n'importe quel flux (Newsletter n8n, Make, scripts Python, RSS, Mailhooks.dev).
   - **Assistant Clic & Valide (Zero Code)** : Collez un échantillon HTML brut ; Mistral IA découpe visuellement le document en blocs sémantiques. Cliquez sur ce que vous voulez garder (Titre, Corps, Auteur) pour créer un filtre de nettoyage.

2. **Moteur Audio & Podcast Ultra-Rapide**
   - **Streaming binaire direct** via MediaSource API (MSE) : Le lecteur audio web commence la lecture quasi-instantanément (~1 seconde) pendant que les segments de synthèse sont téléchargés en arrière-plan.
   - **Intonation intelligente** : Une voix/intonation par sujet pour des transitions fluides, et insertion du jingle (Whoosh Bamboo) entre chaque nouvelle.
   - **Personnalisation** : Remplacez le prompt de synthèse système et le fichier audio jingle via l'interface du Studio Podcast.

3. **Catalogue d'Images Personnalisable (Zéro Dépendance)**
   - Upload de fichiers locaux depuis les paramètres pour définir les images de catégories canoniques.
   - Recadrage systématique 1:1 (`object-fit: cover`) appliqué nativement aux jaquettes audios et podcasts.

4. **Tableau de Bord des Jetons IA (Tokens)**
   - Suivi complet et persistant de la consommation de jetons IA (Mistral, Gemini).
   - Visualisation graphique ventilée par usage (Synthèse, Webhook, Podcast) dans l'onglet Statistiques.

---

## 🛠️ Architecture

L'application repose sur une architecture découplée et légère :

* **Frontend** : SvelteKit + Vite (PWA) + Tailwind CSS
* **Backend API** : FastAPI (Python 3.11+)
* **Base de données** : SQLite (via module standard et `sqlite-vec` pour les embeddings vectoriels)
* **Intelligence Artificielle** : API Mistral (Codestral, Voxtral, Mistral Large), Google Gemini (1.5 Pro/Flash)

```mermaid
graph TD;
    A[Sources (Mail, Web, PDF)] -->|via n8n/Make| B(Webhook POST /ingest);
    B --> C{FastAPI Backend};
    C --> D[(SQLite / Vecteurs)];
    D --> E[Studio Podcast & Résumés];
    E <--> F[Mistral/Gemini API];
    E --> G[Svelte PWA Frontend];
```

---

## 🚀 Guide d'Installation

### 1. Prérequis
- **Python 3.11+**
- **Node.js 18+**

### 2. Configuration Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Sous Windows: venv\Scripts\activate
pip install -r requirements.txt
```
Copiez `.env.example` en `.env` et renseignez :
```ini
MISTRAL_API_KEY="votre_cle_mistral"
GEMINI_API_KEY="votre_cle_gemini"
```
Lancez le backend (FastAPI) :
```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 3. Configuration Frontend
```bash
cd frontend
npm install
npm run dev
```
L'application sera accessible sur `http://localhost:5173`.

---

## ☁️ Déploiement YunoHost (VPS)

### Bypass SSOWat Nginx pour les Médias & Webhooks
Sur YunoHost, les éléments média `<audio>` et le webhook `POST` ne transmettent pas forcément le cookie d'authentification YunoHost. SSOWat intercepte la requête, provoquant l'échec de la lecture ou de l'ingestion.

Créez le fichier de configuration Nginx sur votre VPS YunoHost à l'emplacement suivant :  
`/etc/nginx/conf.d/<votre_domaine.tld>.d/vos_rss.conf`

```nginx
# ==============================================================================
# CONFIGURATION NGINX YUNOHOST (BYPASS SSO RSS PODCAST, WEBHOOKS & AUDIO STREAM)
# ==============================================================================

# 1. Bypass SSO YunoHost pour le Webhook Ingest
location /api/v1/webhooks/ingest {
    access_by_lua_block { return; }
    proxy_pass http://127.0.0.1:8000/api/v1/webhooks/ingest;
    proxy_set_header Host $host;
}

# 2. Bypass SSO YunoHost pour le flux RSS XML Podcast
location /api/podcast/feed.xml {
    access_by_lua_block { return; }
    proxy_pass http://127.0.0.1:8000/api/podcast/feed.xml;
    proxy_set_header Host $host;
}

# 3. Bypass SSO YunoHost pour les fichiers MP3 audio des podcasts
location /api/audio/stream/ {
    access_by_lua_block { return; }
    proxy_pass http://127.0.0.1:8000/api/audio/stream/;
    proxy_set_header Host $host;
    proxy_force_ranges on; # Support du Seek (Range requests)
}
```
Appliquez la configuration :
```bash
sudo nginx -t && sudo systemctl reload nginx
```
