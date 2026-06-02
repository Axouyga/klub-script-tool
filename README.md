# Klub Script Generator — déploiement Render

Outil de génération de scripts vidéo partenaires (Groq + DuckDuckGo).
Dossier autonome et **sans secret** (la clé Groq est une variable d'environnement Render).

## Fichiers
- `index.html` — l'app (copie de klub-app/script-generator.html)
- `research_server.py` — serveur Python (sert l'app + endpoints /api/*)
- `requirements.txt` — dépendances (groq, ddgs)
- `render.yaml` — config Render
- `sync.sh` — recopie depuis les fichiers source de dev

## Déployer sur Render (gratuit)

1. Pousser ce dossier sur un repo GitHub (ex: `klub-script-tool`).
2. [render.com](https://render.com) → **New** → **Web Service** → connecter le repo.
3. Render détecte `render.yaml` (sinon : runtime Python, build `pip install -r requirements.txt`, start `python research_server.py`).
4. **Environment** → ajouter la variable :
   - `GROQ_API_KEY` = ta clé Groq (`gsk_...`)
5. **Create Web Service** → attendre le build → URL publique du type `https://klub-script-generator.onrender.com`
6. Envoyer cette URL à Lucas.

> Plan gratuit : le service s'endort après ~15 min d'inactivité → 1er chargement ~30 s (cold start), puis instantané.

## Notes
- La clé Groq reste **côté serveur** (jamais exposée au navigateur). Lucas n'a rien à configurer.
- Aucun fichier sensible ici (pas de creds Firebase). NE PAS copier le JSON admin Firebase dans ce dossier.
- Après une modif du code source, relancer `bash sync.sh` puis push.
