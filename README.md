# Vos - AI Reader & Podcast Studio (YunoHost Deployment & Documentation)

Application de revue de presse intelligente, clustering d'actualités et studio de création de podcasts audio alimenté par les API IA Mistral et Gemini.

---

## 🛠️ Configuration & Déploiement YunoHost (VPS)

### ⚠️ Problème fréquent : Interception YunoHost SSO (SSOWat) sur les MP3 et Flux RSS

Sur YunoHost, les éléments média `<audio>` et les agrégateurs de podcasts (AntennaPod, Apple Podcasts, etc.) ne transmettent pas le cookie de session YunoHost SSO (`SSOWatauth`).  
Si Nginx n'est pas configuré correctement, SSOWat intercepte la requête HTTP et renvoie la page de connexion HTML (`text/html`), ce qui provoque l'erreur de détection média/décodeur dans le navigateur ou les lecteurs RSS.

### 🔑 Solution : Fichier de Bypass SSOWat Nginx

Créez le fichier de configuration Nginx sur votre VPS YunoHost à l'emplacement suivant :  
`/etc/nginx/conf.d/<votre_domaine.tld>.d/vos_rss.conf`

```nginx
# ==============================================================================
# CONFIGURATION NGINX YUNOHOST (BYPASS SSO RSS PODCAST & AUDIO STREAM)
# ==============================================================================

# 1. Bypass SSO YunoHost pour le flux RSS XML Podcast
location /api/podcast/feed.xml {
    access_by_lua_block { return; }
    proxy_pass http://127.0.0.1:8000/api/podcast/feed.xml;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}

# 2. Bypass SSO YunoHost pour les fichiers MP3 audio des podcasts
location /api/audio/stream/ {
    access_by_lua_block { return; }
    proxy_pass http://127.0.0.1:8000/api/audio/stream/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    
    # Support du streaming audio / Seek (Range requests)
    proxy_force_ranges on;
}
```

> **Note cruciale** : La directive `access_by_lua_block { return; }` est indispensable car elle désactive le handler Lua d'authentification SSOWat au niveau d'Nginx.

Appliquer la configuration sur le serveur :
```bash
sudo nginx -t && sudo systemctl reload nginx
```

---

## 🎙️ Architecture Audio & Résumés

1. **Diffusion en mémoire (Data URL Base64)** :
   Lors de la génération d'un résumé audio (`POST /api/audio/generate`), l'API renvoie le contenu audio encodé en Data URL Base64 (`data:audio/mp3;base64,...`). Le lecteur web charge ce flux directement en mémoire sans déclencher de requête réseau distante, évitant 100% des redirections SSO et problèmes CORS/fingerprinting.

2. **Dossier de Cache Audio Absolu** :
   Le dossier `AUDIO_DIR` dans `backend/app/services/audio.py` est ancré de manière absolue par rapport à la racine du projet (`BASE_DIR / "audio_cache"`). Cela garantit que les fichiers générés en tâche de fond sont enregistrés et lus au même endroit sur le serveur, quel que soit le dossier de travail courant du process Python.

3. **Mise à jour du Service Worker PWA (Navigateur)** :
   L'application utilise Vite PWA. En cas de mise à jour du code frontend, désenregistrez le Service Worker dans la console de développement du navigateur (`F12 -> Stockage -> Service Workers -> Désenregistrer`) ou effectuez un rafraîchissement forcé (`Ctrl + F5`) pour recharger la nouvelle version du bundle JavaScript.
