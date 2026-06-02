#!/bin/bash
# Recopie les fichiers source (dev) vers le dossier de déploiement.
# À lancer après chaque modif de klub-app/script-generator.html ou research_server.py
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
SRC="$HERE/../klub-app"
cp "$SRC/script-generator.html" "$HERE/index.html"
cp "$SRC/research_server.py"   "$HERE/research_server.py"
echo "✓ index.html + research_server.py copiés vers script-tool-deploy/"
