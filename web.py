"""
web.py — Version web (Flask) du simulateur Enigma.

Lancer en local :     python web.py            puis http://localhost:8000
En production :       gunicorn --workers 1 --threads 8 --bind 0.0.0.0:8000 web:app
                      (ou docker compose up -d, voir le README)

Fonctionnement :
  - le moteur (enigma.py) et les dessins (schema.py, chapitres.py) sont les
    MÊMES que pour l'interface Tkinter ;
  - les dessins sont faits sur un CanvasSVG (svg_canvas.py) et envoyés au
    navigateur sous forme d'image SVG ;
  - chaque visiteur a sa propre machine et ses propres chapitres, gardés en
    mémoire côté serveur et retrouvés grâce à un cookie de session.
    => il faut UN SEUL processus (workers=1), avec autant de threads que voulu.
"""

import os
import re
import secrets
import threading
import time
import uuid
from collections import OrderedDict
from html import escape

from flask import Flask, jsonify, render_template, request, session

from chapitres import creer_chapitres
from enigma import ALPHABET, REFLECTEURS, ROTORS, Enigma, nettoyer
from schema import FOND, Schema, ajouter_machine, decrire_appui, dessiner_legende
from svg_canvas import CanvasSVG

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or secrets.token_hex(32)
app.config.update(SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax")

LARGEUR_MACHINE, HAUTEUR_MACHINE = 660, 600
LARGEUR_CHAPITRE, HAUTEUR_CHAPITRE = 680, 640
MAX_SESSIONS = 1000            # au-delà, on oublie les visiteurs les plus anciens
DUREE_SESSION = 6 * 3600       # secondes d'inactivité avant d'oublier un visiteur


# ======================================================================
# La machine d'un visiteur (équivalent de PageMachine dans app.py)
# ======================================================================
class MachineWeb:
    def __init__(self):
        self.reglages = {"reflecteur": "B", "rotors": ["I", "II", "III"],
                         "bagues": [1, 1, 1], "connexions": ""}
        self.machine = Enigma()
        self.depart = "AAA"
        self.entree = self.sortie = ""
        self.detail = None          # détail du dernier appui (pour le texte)
        self.trace = None           # trajet à dessiner (effacé si on change les réglages)
        self.lampe = None
        self.message = [("Appuyez sur une touche pour voir le courant traverser la machine.", "")]

    # ---------- Actions ----------
    def appliquer(self, reflecteur, rotors, bagues, connexions):
        if reflecteur not in REFLECTEURS or any(r not in ROTORS for r in rotors) or len(rotors) != 3:
            raise ValueError("Réglage inconnu.")
        if len(set(rotors)) < 3:
            raise ValueError("Chaque rotor n'existe qu'en un seul exemplaire : "
                             "choisissez trois rotors différents.")
        bagues = [int(b) for b in bagues]
        if len(bagues) != 3 or not all(1 <= b <= 26 for b in bagues):
            raise ValueError("Les bagues vont de 01 à 26.")
        machine = Enigma(rotors=rotors, positions=self.machine.positions(), bagues=bagues,
                         reflecteur=reflecteur, connexions=connexions)   # ValueError si câbles faux
        self.machine = machine
        self.reglages = {"reflecteur": reflecteur, "rotors": list(rotors), "bagues": bagues,
                         "connexions": " ".join(machine.tableau.paires)}
        self.depart = machine.positions()
        self.trace = None

    def appuyer(self, touche):
        avant = self.machine.positions()
        sortie, detail = self.machine.appuyer(touche)
        self.entree += touche
        self.sortie += sortie
        self.detail = self.trace = detail
        self.lampe = sortie
        self.message = decrire_appui(self.machine, detail, avant, sortie)

    def taper(self, texte):
        for touche in nettoyer(texte)[:2000]:
            self.appuyer(touche)

    def tourner(self, k, sens):
        rotor = self.machine.rotors[k]
        rotor.position = (rotor.position + sens) % 26
        self.depart = self.machine.positions()
        self.trace = None

    def nouveau_message(self):
        for rotor, l in zip(self.machine.rotors, self.depart):
            rotor.position = ALPHABET.index(l)
        self.entree = self.sortie = ""
        self.trace = self.lampe = None
        self.message = [(f"Rotors remis en {self.depart}. "
                         "Pour déchiffrer, tapez maintenant le message chiffré.", "")]

    # ---------- Dessin ----------
    def dessiner(self, anime=False):
        canvas = CanvasSVG(LARGEUR_MACHINE, HAUTEUR_MACHINE, fond=FOND)
        schema = Schema(canvas, x=14, y=8)
        ajouter_machine(schema, self.machine, bouges=self.trace["bouges"] if self.trace else ())
        schema.dessiner()
        schema.quand_on_clique(self.appuyer)
        if self.trace:
            schema.dessiner_trajet(self.trace["trajet"], anime=anime)
        dessiner_legende(canvas, 14, schema.bas() + 22)
        canvas.create_text(14, schema.bas() + 48, anchor="w", fill="#666", font=("Helvetica", 9),
                           text="Astuce : on peut aussi cliquer sur les lettres de la colonne « Clavier ».")
        return canvas

    def etat(self, anime=False):
        return {"svg": self.dessiner(anime).rendu(),
                "positions": self.machine.positions(),
                "depart": self.depart,
                "reglages": self.reglages,
                "entree": self.entree,
                "sortie": self.sortie,
                "lampe": self.lampe,
                "detail": self.message}


# ======================================================================
# Sessions : une machine + des chapitres par visiteur, en mémoire
# ======================================================================
_sessions = OrderedDict()
_verrou_global = threading.Lock()


def visiteur():
    """Renvoie les données du visiteur courant (créées au besoin)."""
    if "id" not in session:
        session["id"] = uuid.uuid4().hex
    ident = session["id"]
    maintenant = time.time()
    with _verrou_global:
        # Ménage : visiteurs inactifs depuis trop longtemps, ou trop nombreux
        while _sessions and (len(_sessions) >= MAX_SESSIONS or
                             maintenant - next(iter(_sessions.values()))["vu"] > DUREE_SESSION):
            _sessions.popitem(last=False)
        if ident not in _sessions:
            _sessions[ident] = {"machine": MachineWeb(), "chapitres": creer_chapitres(),
                                "verrou": threading.Lock()}
        donnees = _sessions[ident]
        donnees["vu"] = maintenant
        _sessions.move_to_end(ident)
    return donnees


def corps():
    return request.get_json(silent=True) or {}


def coordonnee(valeur):
    try:
        return float(valeur)
    except (TypeError, ValueError):
        return -1.0


def erreur(message, code=400):
    return jsonify({"erreur": message}), code


# ======================================================================
# Pages
# ======================================================================
@app.get("/")
def accueil():
    return render_template("index.html", rotors=list(ROTORS), reflecteurs=list(REFLECTEURS),
                           chapitres=[c.titre for c in creer_chapitres()],
                           clavier=["QWERTZUIO", "ASDFGHJK", "PYXCVBNML"])


@app.get("/sante")
def sante():
    return "ok"


# ======================================================================
# API de la machine
# ======================================================================
@app.get("/api/machine")
def machine_etat():
    v = visiteur()
    with v["verrou"]:
        return jsonify(v["machine"].etat())


@app.post("/api/machine/reglages")
def machine_reglages():
    v, d = visiteur(), corps()
    with v["verrou"]:
        try:
            v["machine"].appliquer(d.get("reflecteur"), d.get("rotors", []),
                                   d.get("bagues", []), str(d.get("connexions", ""))[:100])
        except (ValueError, TypeError) as e:
            return erreur(str(e))
        return jsonify(v["machine"].etat())


@app.post("/api/machine/touche")
def machine_touche():
    v, d = visiteur(), corps()
    lettre = str(d.get("lettre", "")).upper()
    if len(lettre) != 1 or lettre not in ALPHABET:
        return erreur("Touche invalide.")
    with v["verrou"]:
        v["machine"].appuyer(lettre)
        return jsonify(v["machine"].etat(anime=bool(d.get("anime"))))


@app.post("/api/machine/clic")
def machine_clic():
    """Clic sur une lettre de la colonne « Clavier » du schéma."""
    v, d = visiteur(), corps()
    with v["verrou"]:
        m = v["machine"]
        if not m.dessiner().cliquer(str(d.get("tag")), coordonnee(d.get("y"))):
            return erreur("Clic hors d'une touche.")
        return jsonify(m.etat(anime=bool(d.get("anime"))))


@app.post("/api/machine/texte")
def machine_texte():
    v, d = visiteur(), corps()
    with v["verrou"]:
        v["machine"].taper(str(d.get("texte", "")))
        return jsonify(v["machine"].etat())


@app.post("/api/machine/tourner")
def machine_tourner():
    v, d = visiteur(), corps()
    k, sens = d.get("rotor"), d.get("sens")
    if k not in (0, 1, 2) or sens not in (-1, 1):
        return erreur("Paramètres invalides.")
    with v["verrou"]:
        v["machine"].tourner(k, sens)
        return jsonify(v["machine"].etat())


@app.post("/api/machine/nouveau")
def machine_nouveau():
    v = visiteur()
    with v["verrou"]:
        v["machine"].nouveau_message()
        return jsonify(v["machine"].etat())


# ======================================================================
# API des chapitres
# ======================================================================
def texte_en_html(texte):
    """**gras** -> <strong>, `code` -> <code> (le reste est échappé)."""
    html = escape(texte)
    html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html)
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", html)


def dessiner_chapitre(chapitre):
    canvas = CanvasSVG(LARGEUR_CHAPITRE, HAUTEUR_CHAPITRE, fond=FOND)
    chapitre.dessiner(canvas, lambda: None)
    return canvas


def etat_chapitre(chapitre):
    return {"titre": chapitre.titre, "texte": texte_en_html(chapitre.texte),
            "boutons": [libelle for libelle, _ in chapitre.boutons()],
            "svg": dessiner_chapitre(chapitre).rendu()}


def trouver_chapitre(v, n):
    if not 0 <= n < len(v["chapitres"]):
        return None
    return v["chapitres"][n]


@app.get("/api/chapitres/<int:n>")
def chapitre(n):
    v = visiteur()
    with v["verrou"]:
        ch = trouver_chapitre(v, n)
        return jsonify(etat_chapitre(ch)) if ch else erreur("Chapitre inconnu.", 404)


@app.post("/api/chapitres/<int:n>/bouton")
def chapitre_bouton(n):
    v, d = visiteur(), corps()
    with v["verrou"]:
        ch = trouver_chapitre(v, n)
        if not ch:
            return erreur("Chapitre inconnu.", 404)
        boutons = ch.boutons()
        k = d.get("index")
        if not isinstance(k, int) or not 0 <= k < len(boutons):
            return erreur("Bouton inconnu.")
        boutons[k][1]()
        return jsonify(etat_chapitre(ch))


@app.post("/api/chapitres/<int:n>/clic")
def chapitre_clic(n):
    v, d = visiteur(), corps()
    with v["verrou"]:
        ch = trouver_chapitre(v, n)
        if not ch:
            return erreur("Chapitre inconnu.", 404)
        dessiner_chapitre(ch).cliquer(str(d.get("tag")), coordonnee(d.get("y")))
        return jsonify(etat_chapitre(ch))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8000)), debug=True)
