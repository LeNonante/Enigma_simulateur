"""
enigma.py — La logique de la machine Enigma I (3 rotors), sans aucune interface graphique.

Convention utilisée partout : une lettre est manipulée comme un nombre
de 0 (A) à 25 (Z). C'est beaucoup plus simple pour faire des décalages
avec l'opérateur modulo (% 26).

En ligne de commande :

    python enigma.py                                   vérifie le moteur (autotest)
    python enigma.py "BONJOUR"                         chiffre avec la clé par défaut
    python enigma.py --positions HDX --plugs "AM FI" "BONJOUR"
    python enigma.py --detail "BONJOUR"                montre le trajet de chaque lettre
    python enigma.py --json "BONJOUR"                  sortie JSON (réglages + trajets)

La machine est réciproque : la même commande déchiffre un message chiffré.
"""

import argparse
import json
import os
import sys
import unicodedata

ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def num(lettre):
    """'A' -> 0, 'B' -> 1, ..., 'Z' -> 25"""
    if not isinstance(lettre, str) or len(lettre) != 1 or lettre not in ALPHABET:
        raise ValueError(f"« {lettre} » n'est pas une lettre de A à Z.")
    return ALPHABET.index(lettre)


def lettre(n):
    """0 -> 'A', 1 -> 'B', ... (fonctionne aussi au-delà de 25 grâce au modulo)"""
    if isinstance(n, bool) or not isinstance(n, int):
        raise ValueError(f"« {n!r} » n'est pas un numéro de lettre (entier attendu).")
    return ALPHABET[n % 26]


def nettoyer(texte):
    """Garde uniquement les lettres A-Z (é -> E, espaces et ponctuation supprimés)."""
    if not isinstance(texte, str):
        raise ValueError(f"Un texte est attendu, pas « {texte!r} ».")
    sans_accents = unicodedata.normalize("NFD", texte)
    return "".join(c for c in sans_accents.upper() if c in ALPHABET)


# --------------------------------------------------------------------------
# Câblages historiques de l'Enigma I (armée allemande)
# Chaque chaîne indique où sort chaque lettre : pour le rotor I, A sort en E,
# B sort en K, etc. La seconde valeur est la lettre de l'encoche.
# --------------------------------------------------------------------------
ROTORS = {
    "I":   ("EKMFLGDQVZNTOWYHXUSPAIBRCJ", "Q"),
    "II":  ("AJDKSIRUXBLHWTMCQGZNPYFVOE", "E"),
    "III": ("BDFHJLCPRTXVZNYEIWGAKMUSQO", "V"),
    "IV":  ("ESOVPZJAYQUIRHXLNFTGKDCMWB", "J"),
    "V":   ("VZBRGITYUPSDNHLXAWMJQOFECK", "Z"),
}

REFLECTEURS = {
    "B": "YRUHQSLDPXNGOKMIEBFZCWVJAT",
    "C": "FVPJIAOYEDRZXWGCTKUQSBNMHL",
}


# --------------------------------------------------------------------------
# Vérification des réglages : une machine impossible doit être refusée tout de
# suite, avec un message qui dit quoi corriger. Sans cela, un réglage fautif ne
# se voyait que bien plus tard, sous la forme d'un « not enough values to
# unpack », ou pire, d'une machine à deux rotors qui chiffrait quand même.
# --------------------------------------------------------------------------
def bague_valide(bague):
    """Vérifie un réglage de bague (1 à 26) et le renvoie sous forme d'entier."""
    if isinstance(bague, bool) or not isinstance(bague, int):
        raise ValueError(f"Une bague est un nombre entier de 1 à 26 (reçu : {bague!r}).")
    if not 1 <= bague <= 26:
        raise ValueError(f"Les bagues vont de 1 à 26 (reçu : {bague}).")
    return bague


def rotors_valides(rotors):
    """Vérifie les trois noms de rotors et les renvoie dans l'ordre gauche -> droite."""
    if isinstance(rotors, str):
        rotors = rotors.split()
    rotors = [str(r).upper() for r in rotors]
    if len(rotors) != 3:
        raise ValueError(f"Il faut exactement trois rotors (reçu : {len(rotors)}).")
    inconnus = [r for r in rotors if r not in ROTORS]
    if inconnus:
        raise ValueError(f"Rotor inconnu : {', '.join(inconnus)} "
                         f"(choix : {', '.join(ROTORS)}).")
    if len(set(rotors)) != 3:
        raise ValueError("Chaque rotor n'existe qu'en un seul exemplaire : "
                         "choisissez trois rotors différents.")
    return rotors


def positions_valides(positions):
    """Vérifie la position de départ (« AAA ») et la renvoie en majuscules."""
    positions = str(positions).upper()
    if len(positions) != 3 or any(c not in ALPHABET for c in positions):
        raise ValueError("La position de départ s'écrit avec trois lettres de A à Z "
                         f"(reçu : {positions!r}).")
    return positions


def bagues_valides(bagues):
    """Vérifie les trois réglages de bagues et les renvoie sous forme d'entiers."""
    bagues = list(bagues)
    if len(bagues) != 3:
        raise ValueError(f"Il faut exactement trois bagues (reçu : {len(bagues)}).")
    return [bague_valide(b) for b in bagues]


def lettre_unique(position):
    """Vérifie une lettre de fenêtre d'un rotor (« A » à « Z »)."""
    if not isinstance(position, str) or len(position) != 1 or position.upper() not in ALPHABET:
        raise ValueError(f"Position de rotor invalide : « {position} » "
                         "(une seule lettre de A à Z).")
    return position.upper()


class Rotor:
    """Un rotor : un disque avec un câblage interne mélangé, qui tourne."""

    def __init__(self, nom, position="A", bague=1):
        nom = str(nom).upper()
        if nom not in ROTORS:
            raise ValueError(f"Rotor inconnu : « {nom} » (choix : {', '.join(ROTORS)}).")
        cablage, encoche = ROTORS[nom]
        self.nom = nom
        # cablage[i] = contact de sortie quand le courant entre par le contact i
        self.cablage = [num(c) for c in cablage]
        # Le même câblage parcouru dans l'autre sens (pour le retour du courant)
        self.inverse = [0] * 26
        for entree, sortie in enumerate(self.cablage):
            self.inverse[sortie] = entree
        self.encoche = num(encoche)              # lettre de la fenêtre qui entraîne le rotor suivant
        self.position = num(lettre_unique(position))   # lettre visible dans la fenêtre
        self.bague = bague_valide(bague) - 1     # réglage de la bague (1 à 26 -> 0 à 25)

    def decalage(self):
        """De combien le câblage est tourné par rapport aux contacts fixes."""
        return (self.position - self.bague) % 26

    def aller(self, contact):
        """Courant qui traverse le rotor de droite à gauche."""
        d = self.decalage()
        return (self.cablage[(contact + d) % 26] - d) % 26

    def retour(self, contact):
        """Courant qui traverse le rotor de gauche à droite (après le réflecteur)."""
        d = self.decalage()
        return (self.inverse[(contact + d) % 26] - d) % 26

    def sur_encoche(self):
        return self.position == self.encoche

    def avancer(self):
        self.position = (self.position + 1) % 26

    def fenetre(self):
        return lettre(self.position)


class Reflecteur:
    """Le réflecteur relie les lettres par paires et renvoie le courant."""

    def __init__(self, nom):
        nom = str(nom).upper()
        if nom not in REFLECTEURS:
            if not nom:
                raise ValueError(f"Le réflecteur doit être {' ou '.join(REFLECTEURS)}.")
            raise ValueError(f"Réflecteur inconnu : « {nom} » "
                             f"(choix : {', '.join(REFLECTEURS)}).")
        self.nom = nom
        self.cablage = [num(c) for c in REFLECTEURS[nom]]

    def renvoyer(self, contact):
        return self.cablage[contact]


class TableauConnexions:
    """Le tableau de connexions (Steckerbrett) : des câbles échangent des paires de lettres."""

    def __init__(self, paires=""):
        if paires is None:            # « aucun câble » arrive souvent sous cette forme
            paires = ""
        if not isinstance(paires, str):
            raise ValueError("Les connexions s'écrivent sous forme de texte, "
                             f"ex. « AM FI » (reçu : {paires!r}).")
        self.cablage = list(range(26))   # au départ, chaque lettre va sur elle-même
        self.paires = []
        for paire in paires.upper().split():
            if len(paire) != 2 or any(c not in ALPHABET for c in paire):
                raise ValueError(f"« {paire} » n'est pas une paire de deux lettres.")
            a, b = num(paire[0]), num(paire[1])
            if a == b:
                raise ValueError(f"On ne peut pas relier {paire[0]} à elle-même.")
            for x in (a, b):
                if self.cablage[x] != x:
                    raise ValueError(f"La lettre {lettre(x)} a déjà un câble.")
            self.cablage[a], self.cablage[b] = b, a
            self.paires.append(paire)

    def echanger(self, contact):
        return self.cablage[contact]


class Enigma:
    """La machine complète : tableau + 3 rotors + réflecteur."""

    def __init__(self, rotors=("I", "II", "III"), positions="AAA",
                 bagues=(1, 1, 1), reflecteur="B", connexions=""):
        rotors = rotors_valides(rotors)
        positions = positions_valides(positions)
        bagues = bagues_valides(bagues)
        # self.rotors = [gauche, milieu, droit], comme on les voit sur la machine.
        # On indexe au lieu de zipper : un zip tronqué fabriquait autrefois une
        # machine à deux rotors que rien ne signalait.
        self.rotors = [Rotor(rotors[i], positions[i], bagues[i]) for i in range(3)]
        self.reflecteur = Reflecteur(reflecteur)
        self.tableau = TableauConnexions(connexions)

    def positions(self):
        """Les trois lettres visibles dans les fenêtres, ex : 'AAB'."""
        return "".join(r.fenetre() for r in self.rotors)

    def reglages(self):
        """Les réglages complets, sous forme de dictionnaire (pratique pour JSON)."""
        return {"rotors": [r.nom for r in self.rotors],
                "positions": self.positions(),
                "bagues": [r.bague + 1 for r in self.rotors],
                "reflecteur": self.reflecteur.nom,
                "connexions": " ".join(self.tableau.paires)}

    def faire_avancer_les_rotors(self):
        """
        Mécanisme d'avancement, exécuté AVANT le passage du courant.
        Renvoie la liste des rotors qui ont bougé et des explications.
        """
        gauche, milieu, droit = self.rotors
        bouges = ["droit"]
        explications = ["Le rotor droit avance d'un cran (à chaque touche)."]

        if milieu.sur_encoche():
            # Le fameux « double pas » : le rotor du milieu avance une 2e fois
            milieu.avancer()
            gauche.avancer()
            bouges += ["milieu", "gauche"]
            explications.append("Double pas : le rotor du milieu est sur son encoche, "
                                "il avance et entraîne le rotor gauche.")
        elif droit.sur_encoche():
            milieu.avancer()
            bouges.append("milieu")
            explications.append("Le rotor droit était sur son encoche : "
                                "il entraîne le rotor du milieu.")

        droit.avancer()
        return bouges, explications

    def appuyer(self, touche):
        """
        Simule l'appui sur une touche.
        Renvoie (lettre allumée, détail) où détail contient le trajet complet.
        """
        # « AB » passait pour la touche A (str.index trouve une sous-chaîne) et
        # « a » levait un « substring not found » : on vérifie donc la touche.
        if not isinstance(touche, str) or len(touche) != 1 or touche.upper() not in ALPHABET:
            raise ValueError(f"« {touche} » n'est pas une touche de A à Z.")
        touche = touche.upper()

        bouges, explications = self.faire_avancer_les_rotors()
        gauche, milieu, droit = self.rotors

        trajet = []          # liste de (pièce, contact d'entrée, contact de sortie)
        contact = num(touche)

        def traverser(piece, fonction):
            nonlocal contact
            sortie = fonction(contact)
            trajet.append((piece, contact, sortie))
            contact = sortie

        traverser("tableau", self.tableau.echanger)      # aller
        traverser("droit", droit.aller)
        traverser("milieu", milieu.aller)
        traverser("gauche", gauche.aller)
        traverser("reflecteur", self.reflecteur.renvoyer)
        traverser("gauche", gauche.retour)                # retour
        traverser("milieu", milieu.retour)
        traverser("droit", droit.retour)
        traverser("tableau", self.tableau.echanger)

        detail = {"touche": touche, "trajet": trajet,
                  "bouges": bouges, "explications": explications}
        return lettre(contact), detail

    def chiffrer(self, texte):
        """Tape un texte entier et renvoie les lettres allumées."""
        return "".join(self.appuyer(c)[0] for c in nettoyer(texte))


# --------------------------------------------------------------------------
# Autotest : valeurs de référence connues (lancer « python enigma.py »)
# --------------------------------------------------------------------------
def autotest():
    """Vérifie le moteur sur des valeurs connues. Lève AssertionError au premier écart."""
    # Valeur de référence connue : I-II-III, réflecteur B, AAA, sans câble
    assert Enigma().chiffrer("AAAAA") == "BDZGO"

    # Double pas : ADU -> ADV -> AEW -> BFX
    m = Enigma(positions="ADU")
    suite = []
    for _ in range(3):
        m.appuyer("A")
        suite.append(m.positions())
    assert suite == ["ADV", "AEW", "BFX"], suite

    # Réciprocité : chiffrer deux fois avec la même clé redonne le texte
    cle = dict(rotors=("II", "V", "III"), positions="HDX", bagues=(4, 12, 20),
               reflecteur="C", connexions="AM FI NV PS TU WZ")
    chiffre = Enigma(**cle).chiffrer("Bonjour depuis Troyes")
    assert Enigma(**cle).chiffrer(chiffre) == "BONJOURDEPUISTROYES"

    # Une lettre n'est jamais chiffrée en elle-même
    m = Enigma(**cle)
    assert all(m.appuyer("E")[0] != "E" for _ in range(1000))
    return chiffre


# --------------------------------------------------------------------------
# Ligne de commande
# --------------------------------------------------------------------------
def bague_depuis_texte(valeur):
    """« 1 » à « 26 » (ou « A » à « Z ») -> numéro de bague. Type pour argparse."""
    valeur = str(valeur).strip().upper()
    if valeur.isdigit():
        bague = int(valeur)
        if not 1 <= bague <= 26:
            raise argparse.ArgumentTypeError(f"les bagues vont de 1 à 26 (reçu : {valeur}).")
        return bague
    if len(valeur) == 1 and valeur in ALPHABET:
        return ALPHABET.index(valeur) + 1
    raise argparse.ArgumentTypeError(f"bague invalide : « {valeur} » (1 à 26, ou A à Z).")


def analyser_arguments():
    """Construit l'analyseur de la ligne de commande."""
    p = argparse.ArgumentParser(
        prog="enigma.py",
        description="Chiffre (ou déchiffre : la machine est réciproque) un texte avec une Enigma I.",
        epilog="Sans argument, lance l'autotest du moteur. "
               "Sans texte, lit l'entrée standard.")
    p.add_argument("texte", nargs="*", help="texte à chiffrer (accents et ponctuation ignorés)")
    p.add_argument("--rotors", nargs=3, default=["I", "II", "III"],
                   metavar=("GAUCHE", "MILIEU", "DROIT"),
                   help="modèles des trois rotors (I à V), défaut : I II III")
    p.add_argument("--positions", default="AAA", metavar="LTR",
                   help="position de départ des fenêtres, défaut : AAA")
    p.add_argument("--bagues", "--rings", nargs=3, type=bague_depuis_texte, default=[1, 1, 1],
                   metavar=("GAUCHE", "MILIEU", "DROIT"),
                   help="réglage des bagues, 1 à 26 ou A à Z, défaut : 1 1 1")
    p.add_argument("--reflecteur", "--reflector", default="B", choices=list(REFLECTEURS),
                   help="réflecteur B ou C, défaut : B")
    p.add_argument("--connexions", "--plugs", default="", metavar="PAIRES",
                   help='câbles du tableau, ex : "AM FI NV" (défaut : aucun)')
    p.add_argument("--detail", action="store_true",
                   help="affiche, pour chaque lettre, l'avancement des rotors et le trajet")
    p.add_argument("--json", action="store_true", help="sortie JSON (réglages, lettres, trajets)")
    p.add_argument("--grouper", type=int, default=0, metavar="N",
                   help="présente le résultat par groupes de N lettres (0 = sans groupes)")
    p.add_argument("--selftest", "--autotest", action="store_true",
                   help="vérifie le moteur sur des valeurs connues")
    return p


def en_groupes(texte, taille):
    """« BONJOUR » en groupes de 5 -> « BONJO UR »."""
    if taille <= 0:
        return texte
    return " ".join(texte[i:i + taille] for i in range(0, len(texte), taille))


def trajet_lisible(detail):
    """Les dix contacts traversés, de la touche à la lampe : « A G D … »."""
    contacts = [detail["trajet"][0][1]] + [sortie for _, _, sortie in detail["trajet"]]
    return " ".join(ALPHABET[c] for c in contacts)


def principal(argv=None):
    """Point d'entrée de la ligne de commande. Renvoie le code de sortie."""
    argv = sys.argv[1:] if argv is None else list(argv)
    analyseur = analyser_arguments()

    if not argv and sys.stdin.isatty():    # comportement historique : autotest
        autotest()
        print("Tous les tests passent.")
        return 0

    args = analyseur.parse_args(argv)
    if args.selftest:
        print("Tous les tests passent.", autotest())
        return 0

    texte = " ".join(args.texte)
    if not texte:
        if sys.stdin.isatty():
            analyseur.print_help(sys.stderr)
            return 2
        texte = sys.stdin.read()

    try:
        machine = Enigma(rotors=args.rotors, positions=args.positions, bagues=args.bagues,
                         reflecteur=args.reflecteur, connexions=args.connexions)
    except ValueError as erreur:
        print(f"Réglage invalide : {erreur}", file=sys.stderr)
        return 2

    reglages = machine.reglages()      # avant de taper, donc les positions de départ
    clair = nettoyer(texte)
    lettres = []
    for touche in clair:
        avant = machine.positions()
        sortie, detail = machine.appuyer(touche)
        lettres.append({"entree": touche, "sortie": sortie,
                        "avant": avant, "apres": machine.positions(),
                        "bouges": detail["bouges"],
                        "trajet": trajet_lisible(detail)})

    chiffre = "".join(l["sortie"] for l in lettres)

    if args.json:
        json.dump({"clair": clair, "chiffre": chiffre,
                   "reglages": reglages, "lettres": lettres},
                  sys.stdout, ensure_ascii=False, indent=2)
        print()
        return 0

    if args.detail:
        for l in lettres:
            print(f"{l['entree']} -> {l['sortie']}   rotors {l['avant']} -> {l['apres']}"
                  f"   trajet {l['trajet']}")
        print()
    print(en_groupes(chiffre, args.grouper))
    return 0


if __name__ == "__main__":
    try:
        code = principal()
        sys.stdout.flush()
    except BrokenPipeError:      # « enigma.py ... | head » ferme le tuyau avant la fin
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        code = 0
    raise SystemExit(code)
