"""
enigma.py — La logique de la machine Enigma I (3 rotors), sans aucune interface graphique.

Convention utilisée partout : une lettre est manipulée comme un nombre
de 0 (A) à 25 (Z). C'est beaucoup plus simple pour faire des décalages
avec l'opérateur modulo (% 26).
"""

import unicodedata

ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def num(lettre):
    """'A' -> 0, 'B' -> 1, ..., 'Z' -> 25"""
    return ALPHABET.index(lettre)


def lettre(n):
    """0 -> 'A', 1 -> 'B', ... (fonctionne aussi au-delà de 25 grâce au modulo)"""
    return ALPHABET[n % 26]


def nettoyer(texte):
    """Garde uniquement les lettres A-Z (é -> E, espaces et ponctuation supprimés)."""
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


class Rotor:
    """Un rotor : un disque avec un câblage interne mélangé, qui tourne."""

    def __init__(self, nom, position="A", bague=1):
        cablage, encoche = ROTORS[nom]
        self.nom = nom
        # cablage[i] = contact de sortie quand le courant entre par le contact i
        self.cablage = [num(c) for c in cablage]
        # Le même câblage parcouru dans l'autre sens (pour le retour du courant)
        self.inverse = [0] * 26
        for entree, sortie in enumerate(self.cablage):
            self.inverse[sortie] = entree
        self.encoche = num(encoche)     # lettre de la fenêtre qui entraîne le rotor suivant
        self.position = num(position)   # lettre visible dans la fenêtre
        self.bague = bague - 1          # réglage de la bague (1 à 26 -> 0 à 25)

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
        self.nom = nom
        self.cablage = [num(c) for c in REFLECTEURS[nom]]

    def renvoyer(self, contact):
        return self.cablage[contact]


class TableauConnexions:
    """Le tableau de connexions (Steckerbrett) : des câbles échangent des paires de lettres."""

    def __init__(self, paires=""):
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
        # self.rotors = [gauche, milieu, droit], comme on les voit sur la machine
        self.rotors = [Rotor(n, p, b) for n, p, b in zip(rotors, positions, bagues)]
        self.reflecteur = Reflecteur(reflecteur)
        self.tableau = TableauConnexions(connexions)

    def positions(self):
        """Les trois lettres visibles dans les fenêtres, ex : 'AAB'."""
        return "".join(r.fenetre() for r in self.rotors)

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
# Petits tests : lancer « python enigma.py »
# --------------------------------------------------------------------------
if __name__ == "__main__":
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

    print("Tous les tests passent.", chiffre)
