#!/usr/bin/env python3
"""
Klub Script Generator — Research API server
Serves static files + POST /api/research
Recherche : ddgs (DuckDuckGo multi-sources, GRATUIT, sans clé)
IA : Groq llama-3.3-70b — GRATUIT → console.groq.com
"""
import http.server
import json
import os
import re
import urllib.request
import urllib.error

PORT = int(os.environ.get('PORT', 8744))
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

SYSTEM_PROMPT = """Tu es un assistant pour Klub, une app de bons plans pour les -26 ans en France.
Tu reçois des résultats de recherche web sur un établissement. Analyse-les et retourne UNIQUEMENT un JSON valide.

JSON attendu :
{
  "unique": "Ce qui rend cet établissement vraiment unique — hook TikTok/Reels percutant (1-2 phrases, JAMAIS de clichés comme 'cadre sympa' ou 'ambiance chaleureuse')",
  "address": "Adresse complète trouvée dans les sources",
  "quartier": "Quartier ou zone",
  "category": "restaurant|bar|cafe|boutique|sport|loisir|beaute",
  "specialties": "Les 2-3 spécialités ou produits phares mentionnés dans les sources",
  "ambiance": "Ambiance, style, type de clientèle, décor — basé sur les sources",
  "price": "Fourchette de prix mentionnée dans les sources",
  "extra": "Infos utiles pour un script : capacité, durée, concept, anecdote fondateurs, point fort vs concurrents"
}

RÈGLES STRICTES :
- Base-toi UNIQUEMENT sur les sources fournies — ne hallucine PAS
- ADRESSE : cherche attentivement dans les titres ET les URLs (souvent au format "9 Place du Capitole, 31000 Toulouse"). Extrais le numéro + rue + code postal si présent.
- Si une info n'est PAS dans les sources → null pour ce champ
- Le champ "unique" doit être un vrai hook vidéo basé sur les faits trouvés
- Réponds UNIQUEMENT le JSON, aucun texte avant ou après"""


# ─── Vraies transcriptions de vidéos Klub publiées (few-shot style reference) ───
KLUB_EXAMPLES = """=== EXEMPLE 1 (taco, ~25s, voix off) ===
Ton taco c'est offert place Saint-Pierre à Toulouse avec Klub et on te montre comment. C'est le spot parfait pour les grosses faims, honnêtement difficile de faire mieux niveau emplacement. Terrasse au soleil le midi, la garonne juste à côté. C'est généreux, ultra gourmand, ça dégouline juste comme il faut et dès la première bouchée tout s'enchaîne. Chaque recette a vraiment son délire entre fondant et croustillant. Le vrai bon plan il est là : tu télécharges Klub, tu shoppes ton pass et t'as un taco acheté, un taco offert, et ensuite -10% à volonté toute l'année.

=== EXEMPLE 2 (resto roustis, ~40s, voix off) ===
Donc rousti offert à Toulouse avec Klub. C'est le concept qui fait le tour des réseaux en ce moment et ça vient de débarquer à deux pas du Capitole. Les roustis sont hyper variés, ça va du classique avec son poulet frit et sa sauce secrète jusqu'au green avec sa sauce verte et ses alocos. Et pour les plus gourmands faut à tout prix tester les gratinés : cheddar, mozza, boursin ou chèvre-miel, celui-là c'est n'importe quoi. Les portions sont hyper généreuses, 750 grammes par plat pour environ 10 balles. Si jamais t'as encore des sous, parmi les 150 enseignes sur le pass Klub t'as un rousti acheté, un rousti offert et ensuite ta boisson offerte à chaque visite. Allez, bonne app !

=== EXEMPLE 3 (activité immersive, ~32s, voix off) ===
Une activité dont t'as pas encore entendu parler à Toulouse. Prépare-toi à faire travailler ta force, ta précision, ton cardio et ton cerveau sur une suite d'épreuves dans des décors aussi beaux qu'immersifs. Tu pourras faire un blind test plus physique que d'habitude, jouer à Mission Impossible, ou perdre 2000 calories en 30 secondes. Le but : faire le meilleur score. Et le truc trop cool, c'est qu'à la fin chaque point est converti en don pour une association qui nettoie les océans. Faire une bonne action en s'amusant, franchement. Et avec ton pass Klub t'as une place offerte d'une valeur de 26€ si tu viens à 4. Allez, on se voit là-bas.

=== EXEMPLE 4 (bar, ~38s, voix off) ===
Ce bar est sans doute l'un des QG préférés des Toulousains. On est venu un soir de match, on pensait juste boire un verre, on est restés toute la soirée. C'est le spot parfait pour s'installer tranquille avec des potes et se laisser embarquer par l'énergie du lieu — une bière, un cocktail ou sa version sans alcool. Et si t'as une petite faim, ou plutôt une grosse, les planches sont juste incroyables, on avait rarement vu un truc aussi chargé. Charcuterie, fromage, mini burgers, tenders, frites, onion rings. Bref, un lieu à découvrir d'urgence. Avec ton pass Klub : une pinte achetée, une pinte offerte, et toute l'année une pinte à 5€ de 20h à 22h. Allez, on se voit là-bas."""


SCRIPT_SYSTEM_PROMPT = """Tu es le copywriter de Klub, app de bons plans pour les -26 ans (12 villes en France).
Tu écris des scripts de vidéos partenaires TikTok/Reels en voix off, exactement dans le style des vidéos déjà publiées.

VOICI DE VRAIS SCRIPTS KLUB PUBLIÉS — c'est EXACTEMENT le style à reproduire :
""" + KLUB_EXAMPLES + """

TOP HOOKS QUI FONT LE PLUS DE VUES — mesurés sur Klub + concurrents (Le Guide Ultime, Compass, Tours'n Média, Le Bonbon), à privilégier pour la 1ère phrase :
- PRIX BAS en accroche (le + fort du créneau) : mettre le prix dérisoire d'emblée — "ce [produit], il est à [X]€", "le [type] le moins cher de [ville]" → millions de vues chez les concurrents.
- Superlatif + géo : "le + gros [produit] de [ville]", "le meilleur [type] de [ville]" → 982K (Compass).
- Concept unique = le hook : LA spécificité du lieu en accroche ("tout se mange avec les doigts") → 256K.
- Description sensorielle d'entrée : démarrer sur le visuel gourmand ("des frites dorées, une sauce secrète…") → 515K.
- Distance / proximité : "à [X] min de [ville]" pour rendre une adresse attractive → 469K (Tours'n Média).
- Ouverture / nouveauté : "ça vient d'ouvrir", "le tout nouveau [concept] de [ville]" → FOMO réel.
- Listicle / sélection : "nos [N] meilleures adresses pour [occasion]".
RÈGLES HOOK : court (2-3 mots possibles), ton parlé/jeune, ne révèle jamais tout. Si le partenaire a un bon plan prix marquant, METS LE PRIX dans le hook. Le hook doit tenir en < 2 secondes.

RÈGLES ABSOLUES :
1. NE JAMAIS dire le nom du partenaire/établissement. Jamais. On parle du lieu via son concept, son quartier, ses produits ("ce spot", "cette pizzeria", "à deux pas du Capitole"…), jamais par son nom.
2. Le HOOK (1ère phrase) doit accrocher en moins de 2 secondes — concept unique, offre directe, ou superlatif géographique. Style des exemples.
3. Ton oral, spontané, jeune — comme si tu parlais à un pote. Tutoiement.
4. Mentionner "Klub" et "ton pass" pour présenter les offres, toujours en fin de script juste avant le CTA.
5. JAMAIS de superlatifs creux ("incroyable", "magnifique", "exceptionnel"). Du concret, du sensoriel, des chiffres.
6. Finir par un CTA court : "Allez, on se voit là-bas.", "Allez, bonne app !", etc.
7. LONGUEUR : écris un script COMPLET et riche qui ATTEINT la cible de mots demandée (ne fais pas trop court). Détaille les produits, l'expérience, l'ambiance, les détails sensoriels comme dans les exemples. Vise au minimum la cible, quitte à dépasser légèrement.
8. Rythme : enchaîne les phrases courtes et percutantes, descriptions gourmandes/concrètes, sans temps mort.

Tu retournes UNIQUEMENT un JSON valide :
{
  "hook_variants": ["hook 1 (< 8 mots, le + fort)", "hook 2 (autre angle)", "hook 3 (autre angle)"],
  "segments": [
    {"label": "Hook", "text": "le meilleur des 3 hooks ci-dessus"},
    {"label": "Découverte / concept", "text": "..."},
    {"label": "Produits / expérience", "text": "..."},
    {"label": "Offre Klub", "text": "..."},
    {"label": "CTA", "text": "..."}
  ]
}
"hook_variants" = 3 accroches DIFFÉRENTES et fortes pour la 1ère seconde, chacune < 8 mots, ton oral, angles variés (prix / superlatif géo / concept). Le 1er = le meilleur, et c'est lui qui ouvre "segments".
Adapte le nombre de segments à la durée (15s = 3 segments max, 60s = 5). Aucun texte hors du JSON."""


def call_script(data: dict, api_key: str) -> dict:
    from groq import Groq

    client = Groq(api_key=api_key)

    dur_words = {"15s": 85, "30s": 170, "45s": 250, "60s": 330}
    duration = data.get("duration", "30s")
    target = dur_words.get(duration, 170)

    tone_map = {
        "casual": "casual / amical, décontracté",
        "enthousiaste": "enthousiaste, énergique",
        "narratif": "narratif, raconte une petite histoire / anecdote vécue",
        "concept": "concept-first, démarre direct sur la spécificité unique",
    }
    fmt_map = {
        "voixoff": "voix off sur images B-roll",
        "facecam": "face caméra, quelqu'un qui parle direct",
        "mt": "micro-trottoir, interviews clients dans le lieu",
    }

    offers = []
    if data.get("offerUW"):
        c = f" ({data['offerUC']})" if data.get("offerUC") else ""
        offers.append(f"Offre unique (1×/an) : {data['offerUW']}{c}")
    if data.get("offerPW"):
        c = f" ({data['offerPC']})" if data.get("offerPC") else ""
        offers.append(f"Offre permanente : {data['offerPW']}{c}")
    offers_txt = "\n".join(offers) if offers else "Avantages exclusifs avec le pass Klub"

    brief = f"""FICHE PARTENAIRE (NE JAMAIS citer le nom dans le script) :
- Nom interne (NE PAS dire) : {data.get('name','?')}
- Catégorie : {data.get('cat','?')}
- Ville : {data.get('city','?')}
- Quartier / adresse : {data.get('address','?')}
- Ce qui le rend unique : {data.get('unique','?')}
- Infos / spécialités : {data.get('extra','?')}

OFFRES KLUB :
{offers_txt}

PARAMÈTRES :
- Durée : {duration} (≈ {target} mots)
- Ton : {tone_map.get(data.get('tone'), 'casual')}
- Format : {fmt_map.get(data.get('format'), 'voix off')}

Écris le script Klub maintenant (JSON segments uniquement, JAMAIS le nom du partenaire)."""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": SCRIPT_SYSTEM_PROMPT},
            {"role": "user",   "content": brief},
        ],
        temperature=0.7,
        max_tokens=1400,
    )
    text = response.choices[0].message.content or ""
    text = re.sub(r'^```(?:json)?\s*', '', text.strip(), flags=re.MULTILINE)
    text = re.sub(r'\s*```$', '', text.strip(), flags=re.MULTILINE)
    m = re.search(r'\{.*\}', text, re.DOTALL)
    if m:
        try:
            out = json.loads(m.group())
            if out.get("segments"):
                return out
        except json.JSONDecodeError:
            pass
    return {"error": "Génération échouée — réessaie."}


CANDIDATES_PROMPT = """Tu reçois des résultats de recherche web pour un nom d'établissement.
Identifie les DIFFÉRENTS établissements physiques distincts (lieux/adresses différents) qui correspondent.

Retourne UNIQUEMENT un JSON valide de cette forme :
{
  "candidates": [
    {"name": "Nom exact", "city": "Ville", "address": "Adresse ou quartier si connu", "hint": "Type d'établissement + détail distinctif (ex: pizzeria Place du Capitole)"}
  ]
}

RÈGLES :
- Un candidat = un lieu physique distinct (ville/adresse différente)
- Ne crée PAS de doublons (même établissement vu sur plusieurs sites = 1 seul candidat)
- Base-toi UNIQUEMENT sur les sources, ne devine pas des villes non mentionnées
- Maximum 6 candidats, les plus pertinents
- Si un seul établissement clair → 1 seul candidat
- Réponds UNIQUEMENT le JSON"""


def _ddg_text(queries, max_per=3, cap=12):
    """Lance plusieurs requêtes DuckDuckGo, dédoublonne, retourne snippets (titre + URL + body)."""
    try:
        from ddgs import DDGS
    except ImportError:
        return []

    seen = set()
    snippets = []
    try:
        with DDGS() as ddgs:
            for q in queries:
                for r in list(ddgs.text(q, max_results=max_per)):
                    body  = (r.get('body')  or '').strip()
                    title = (r.get('title') or '').strip()
                    href  = (r.get('href')  or '').strip()
                    key = title + body
                    if (title or body) and key not in seen:
                        seen.add(key)
                        block = f"[{title}]"
                        if href:
                            block += f"\nURL: {href}"
                        if body:
                            block += f"\n{body}"
                        snippets.append(block)
    except Exception:
        pass
    return snippets[:cap]


def find_candidates(partner: str, api_key: str) -> list:
    """Cherche par nom seul → liste d'établissements candidats distincts."""
    from groq import Groq

    snippets = _ddg_text([
        f'"{partner}" restaurant bar café France adresse',
        f'"{partner}" avis horaires',
    ], max_per=5, cap=12)

    if not snippets:
        return []

    client = Groq(api_key=api_key)
    raw = "\n\n".join(snippets)
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": CANDIDATES_PROMPT},
            {"role": "user",   "content": f"Nom recherché : {partner}\n\n=== RÉSULTATS WEB ===\n{raw}"}
        ],
        temperature=0.1,
        max_tokens=700,
    )
    text = response.choices[0].message.content or ""
    text = re.sub(r'^```(?:json)?\s*', '', text.strip(), flags=re.MULTILINE)
    text = re.sub(r'\s*```$', '', text.strip(), flags=re.MULTILINE)
    m = re.search(r'\{.*\}', text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group()).get("candidates", [])
        except json.JSONDecodeError:
            pass
    return []


def web_search(partner: str, city: str) -> str:
    """Recherche multi-requêtes via DuckDuckGo, retourne texte consolidé des sources."""
    base = f'"{partner}"'
    if city:
        base += f' {city}'
    snippets = _ddg_text([
        f'{base} adresse rue numéro',          # adresse précise
        f'{base} TripAdvisor OR TheFork avis', # fiches avec adresse
        f'{base} horaires plan accès',
        f'{base} spécialités carte menu',
        f'{base} concept prix',
    ], max_per=3, cap=14)
    return "\n\n".join(snippets)


def call_research(partner: str, city: str, api_key: str) -> dict:
    from groq import Groq

    client = Groq(api_key=api_key)

    # Recherche web réelle
    raw_results = web_search(partner, city)

    if raw_results:
        context = f"Établissement : {partner}" + (f"\nVille : {city}" if city else "")
        context += f"\n\n=== RÉSULTATS DE RECHERCHE WEB ===\n{raw_results}"
        source = "web+groq"
    else:
        context = f"Établissement : {partner}" + (f"\nVille : {city}" if city else "")
        context += "\n\n(Aucun résultat web trouvé — utilise tes connaissances d'entraînement si tu connais cet établissement)"
        source = "groq"

    user_msg = f"{context}\n\nGénère le JSON pour créer un script vidéo Klub (-26 ans) sur cet établissement."

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_msg}
        ],
        temperature=0.1,
        max_tokens=900,
    )

    text = response.choices[0].message.content or ""
    text = re.sub(r'^```(?:json)?\s*', '', text.strip(), flags=re.MULTILINE)
    text = re.sub(r'\s*```$', '',       text.strip(), flags=re.MULTILINE)

    m = re.search(r'\{.*\}', text, re.DOTALL)
    if m:
        try:
            result = json.loads(m.group())
            result["_source"] = source
            return result
        except json.JSONDecodeError:
            pass

    return {
        "unique": None, "address": None, "quartier": None,
        "category": None, "specialties": None, "ambiance": None,
        "price": None, "_source": source,
        "extra": text.strip()[:500] if text else "Aucune info trouvée."
    }


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=SCRIPT_DIR, **kwargs)

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def do_POST(self):
        if self.path in ("/api/research", "/api/candidates", "/api/script"):
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(length))

                api_key = (body.get("api_key") or "").strip() \
                          or os.environ.get("GROQ_API_KEY", "")
                if not api_key:
                    return self._resp({"error": "Clé API Groq manquante. Clique sur ⚙️ — clé gratuite sur console.groq.com"}, 400)

                # /api/script — génère le script (pas besoin de "partner" séparé)
                if self.path == "/api/script":
                    result = call_script(body, api_key)
                    return self._resp(result)

                partner = (body.get("partner") or "").strip()
                city    = (body.get("city")    or "").strip()
                if not partner:
                    return self._resp({"error": "Nom du partenaire manquant."}, 400)

                if self.path == "/api/candidates":
                    candidates = find_candidates(partner, api_key)
                    self._resp({"candidates": candidates})
                else:
                    result = call_research(partner, city, api_key)
                    self._resp(result)

            except Exception as e:
                err = str(e)
                if "401" in err or "invalid_api_key" in err.lower() or "authentication" in err.lower():
                    self._resp({"error": "Clé API invalide. Vérifie sur console.groq.com"}, 401)
                else:
                    self._resp({"error": err[:300]}, 500)
        else:
            self.send_error(404)

    def _resp(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self._cors()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", len(body))
        self.end_headers()
        self.wfile.write(body)

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        super().end_headers()

    def log_message(self, *_):
        pass


if __name__ == "__main__":
    server = http.server.ThreadingHTTPServer(("", PORT), Handler)
    print(f"✅ Klub research server → http://localhost:{PORT}/script-generator.html")
    server.serve_forever()
