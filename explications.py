"""
explications.py — L'onglet « Comment ça marche ? ».

Chaque chapitre est une petite classe avec :
  - titre    : le titre affiché
  - texte    : l'explication (les **mots** entre doubles étoiles sont en gras,
               les `passages` entre accents graves en police fixe)
  - boutons(): les boutons propres au chapitre
  - dessiner(canvas, rafraichir) : l'illustration, faite avec le même module
               schema.py que l'onglet Machine
"""

import math
import re
import tkinter as tk
from textwrap import dedent
from tkinter import ttk

from enigma import ALPHABET, Enigma, Rotor, Reflecteur, TableauConnexions, ROTORS
from schema import (Schema, ajouter_rotor_depuis, ajouter_machine, dessiner_legende,
                    FOND, PIECE, BORD, ALLER, RETOUR, FENETRE, BOUGE, LAMPE, TEXTE,
                    POLICE_TITRE)

GRAND = ("Helvetica", 13, "bold")
MOYEN = ("Helvetica", 11)
MOYEN_GRAS = ("Helvetica", 11, "bold")


def texte(s):
    return dedent(s).strip()


def resultat(canvas, x, y, message, couleur=TEXTE):
    canvas.create_text(x, y, text=message, anchor="w", font=GRAND, fill=couleur)


def boite(canvas, x, y, lettre, fond=PIECE, taille=18, police=("Courier", 13, "bold")):
    canvas.create_rectangle(x - taille / 2, y - taille / 2, x + taille / 2, y + taille / 2,
                            fill=fond, outline=BORD)
    canvas.create_text(x, y, text=lettre, font=police)


class Chapitre:
    titre = ""
    texte = ""

    def boutons(self):
        return []

    def dessiner(self, canvas, rafraichir):
        pass


# ======================================================================
class VueEnsemble(Chapitre):
    titre = "Enigma en bref"
    texte = texte("""
        Enigma est une **machine à chiffrer électromécanique** inventée en Allemagne après la Première Guerre mondiale, et utilisée massivement par l'armée allemande pendant la Seconde.

        Elle ressemble à une machine à écrire : quand on appuie sur une touche, **une lampe s'allume** sous une autre lettre. L'opérateur note la lettre allumée : c'est le message chiffré.

        Entre la touche et la lampe, le courant traverse plusieurs pièces qui mélangent les lettres :
          1. le **tableau de connexions** ;
          2. **trois rotors** ;
          3. le **réflecteur**, qui renvoie le courant ;
          4. à nouveau les trois rotors et le tableau, dans l'autre sens.

        L'idée géniale : **les rotors tournent à chaque touche**. Le mélange change donc à chaque lettre : appuyer cinq fois sur A ne donne pas cinq fois la même lettre (exemple sous le schéma).

        Dans tous les schémas, le courant **aller** est en rouge et le **retour** en bleu, comme dans l'onglet Machine.
    """)

    def dessiner(self, c, rafraichir):
        noms = ["Réflecteur", "Rotor\ngauche", "Rotor\nmilieu", "Rotor\ndroit",
                "Tableau de\nconnexions", "Clavier\n\n\n\n\nLampes"]
        x0, y0, l, h, esp = 20, 40, 86, 190, 22
        ya, yr = y0 + 70, y0 + 140          # hauteur du courant aller / retour
        xs = [x0 + k * (l + esp) for k in range(6)]
        for x, nom in zip(xs, noms):
            c.create_rectangle(x, y0, x + l, y0 + h, fill=PIECE, outline=BORD, width=2)
            c.create_text(x + l / 2, y0 + 22, text=nom, font=POLICE_TITRE, justify="center", anchor="n")

        xg, xd = xs[0] + l / 2, xs[5] + l / 2
        c.create_line(xd, ya, xg, ya, fill=ALLER, width=2)
        c.create_line(xg, ya, xg, yr, fill=ALLER, width=2)       # demi-tour dans le réflecteur
        c.create_line(xg, yr, xd, yr, fill=RETOUR, width=2)
        for k in range(5):     # flèches entre les pièces
            xa, xb = xs[k] + l, xs[k + 1]
            c.create_line(xb, ya, xa, ya, arrow="last", fill=ALLER, width=4, arrowshape=(10, 12, 5))
            c.create_line(xa, yr, xb, yr, arrow="last", fill=RETOUR, width=4, arrowshape=(10, 12, 5))
        c.create_oval(xd - 13, ya - 13, xd + 13, ya + 13, fill="#fafafa", outline=ALLER, width=3)
        c.create_text(xd, ya, text="A", font=MOYEN_GRAS)
        c.create_oval(xd - 13, yr - 13, xd + 13, yr + 13, fill=LAMPE, outline=RETOUR, width=3)
        c.create_text(xd, yr, text="B", font=MOYEN_GRAS)
        c.create_text((xs[1] + xs[4]) / 2 + l / 2, ya - 14, text="aller", fill=ALLER, font=MOYEN_GRAS)
        c.create_text((xs[1] + xs[4]) / 2 + l / 2, yr + 16, text="retour", fill=RETOUR, font=MOYEN_GRAS)

        # Exemple réel calculé par le moteur
        y = y0 + h + 60
        c.create_text(x0, y, anchor="w", font=MOYEN_GRAS,
                      text="Exemple : rotors I-II-III en AAA, on appuie 5 fois sur A")
        m = Enigma()
        lignes = [("Fenêtres", []), ("Touche", []), ("Lampe", [])]
        for _ in range(5):
            sortie, _ = m.appuyer("A")
            lignes[0][1].append(m.positions())
            lignes[1][1].append("A")
            lignes[2][1].append(sortie)
        for n, (nom, valeurs) in enumerate(lignes):
            yy = y + 40 + n * 40
            c.create_text(x0, yy, text=nom, anchor="w", font=MOYEN)
            for k, v in enumerate(valeurs):
                x = x0 + 130 + k * 90
                if n == 0:
                    c.create_text(x, yy, text=v, font=("Courier", 12, "bold"))
                else:
                    boite(c, x, yy, v, fond=LAMPE if n == 2 else PIECE, taille=28)
        c.create_text(x0, y + 175, anchor="w", font=MOYEN, fill="#555",
                      text="Même touche, cinq lettres différentes : les rotors ont tourné entre chaque appui.")


# ======================================================================
class ChapitreTableau(Chapitre):
    titre = "Le tableau de connexions"
    texte = texte("""
        Le **tableau de connexions** (Steckerbrett) se trouve à l'avant de la machine. L'opérateur y branche des **câbles** qui relient deux lettres : ces deux lettres sont alors **échangées**.

        Sur le schéma, les câbles sont : A↔Z, E↔K, Q↔T et B↔J (traits plus foncés). Les lettres sans câble passent tout droit.

        Le courant passe par le tableau **deux fois** : en entrant dans la machine, puis juste avant d'allumer la lampe.

        À l'époque, on utilisait en général **10 câbles**. Seul, le tableau est un chiffrement très faible (une simple substitution), mais c'est la pièce qui ajoute le plus de combinaisons possibles à la clé (chapitre 9).

        ► Cliquez sur une lettre de la colonne « Clavier » pour voir son trajet.
    """)

    def __init__(self):
        self.lettre = "A"
        self.tableau = TableauConnexions("AZ EK QT BJ")

    def dessiner(self, c, rafraichir):
        s = Schema(c, x=260, y=20)
        s.ajouter_tableau("tableau", "Tableau de\nconnexions", self.tableau.cablage)
        s.ajouter_clavier()
        s.dessiner()
        s.quand_on_clique(lambda l: (setattr(self, "lettre", l), rafraichir()))
        entree = ALPHABET.index(self.lettre)
        sortie = self.tableau.echanger(entree)
        s.dessiner_trajet([("tableau", entree, sortie)])
        resultat(c, 200, s.bas() + 30, f"{self.lettre}  →  {ALPHABET[sortie]}", ALLER)


# ======================================================================
class ChapitreRotor(Chapitre):
    titre = "Un rotor : une permutation câblée"
    texte = texte("""
        Un **rotor** est un disque épais avec 26 contacts électriques sur chaque face. À l'intérieur, des fils relient chaque contact de droite à un contact de gauche, dans un ordre mélangé : c'est une **substitution fixe**.

        Les fils gris du schéma représentent ce câblage. La bande de lettres à droite est la **bague** (l'alphabet gravé autour du rotor) ; la case jaune est la lettre visible dans la **fenêtre** de la machine.

        Câblage du rotor I (position A) :
        `Entrée : ABCDEFGHIJKLMNOPQRSTUVWXYZ
        Sortie : EKMFLGDQVZNTOWYHXUSPAIBRCJ`
        A sort en E, B sort en K, etc.

        L'Enigma I était livrée avec **5 rotors différents** (I à V), chacun câblé autrement. On en choisit 3, dans l'ordre de son choix.

        Le courant traverse chaque rotor **deux fois** : de droite à gauche à l'aller, puis de gauche à droite au retour, en suivant un autre fil dans l'autre sens.

        ► Cliquez sur une lettre du clavier.
    """)

    def __init__(self):
        self.lettre = "A"

    def dessiner(self, c, rafraichir):
        rotor = Rotor("I", "A")
        s = Schema(c, x=260, y=20)
        ajouter_rotor_depuis(s, "rotor", "Rotor I", rotor)
        s.ajouter_clavier()
        s.dessiner()
        s.quand_on_clique(lambda l: (setattr(self, "lettre", l), rafraichir()))
        entree = ALPHABET.index(self.lettre)
        sortie = rotor.aller(entree)
        s.dessiner_trajet([("rotor", entree, sortie)])
        resultat(c, 200, s.bas() + 30, f"{self.lettre}  →  {ALPHABET[sortie]}", ALLER)


# ======================================================================
class ChapitreRotation(Chapitre):
    titre = "Le rotor tourne à chaque touche"
    texte = texte("""
        Voici le cœur d'Enigma : **à chaque appui sur une touche, le rotor de droite tourne d'un cran**, et ce **avant** que le courant ne passe.

        Comme le câblage tourne avec le rotor, la même touche emprunte un autre fil et donne une autre lettre. Comparez les deux schémas : toutes les lettres de la bague et tous les fils sont décalés d'une ligne vers le haut.

        Une machine dont la substitution change à chaque lettre fait un chiffrement **polyalphabétique**. L'analyse de fréquences classique ne marche plus : le E, très fréquent en allemand, ne donne pas toujours la même lettre chiffrée.

        Avec un seul rotor, la substitution se répéterait toutes les 26 lettres. C'est pourquoi Enigma en a trois, qui s'entraînent comme un compteur kilométrique (chapitre suivant).

        ► Utilisez les boutons pour tourner le rotor et cliquez sur une lettre du clavier.
    """)

    def __init__(self):
        self.position = 0
        self.lettre = "A"

    def boutons(self):
        return [("◀ Reculer d'un cran", lambda: self.tourner(-1)),
                ("Tourner d'un cran ▶", lambda: self.tourner(+1))]

    def tourner(self, sens):
        self.position = (self.position + sens) % 26

    def dessiner(self, c, rafraichir):
        entree = ALPHABET.index(self.lettre)
        for k, x in enumerate((110, 430)):
            pos = ALPHABET[(self.position + k) % 26]
            rotor = Rotor("I", pos)
            s = Schema(c, x=x, y=20)
            ajouter_rotor_depuis(s, "rotor", f"Rotor I\nfenêtre {pos}", rotor)
            s.ajouter_clavier()
            s.dessiner()
            s.quand_on_clique(lambda l: (setattr(self, "lettre", l), rafraichir()))
            sortie = rotor.aller(entree)
            s.dessiner_trajet([("rotor", entree, sortie)])
            resultat(c, x - 40, s.bas() + 30, f"{self.lettre} → {ALPHABET[sortie]}", ALLER)
        c.create_text(340, 615, anchor="center", font=MOYEN, fill="#555",
                      text="Même touche, rotor décalé d'un cran : la lettre de sortie change.")


# ======================================================================
class ChapitreTroisRotors(Chapitre):
    titre = "Trois rotors : le compteur kilométrique"
    texte = texte("""
        Les trois rotors avancent comme un **compteur kilométrique** :

        • le rotor **droit** avance à **chaque** touche ;
        • chaque rotor a une **encoche** (le triangle orange des schémas). Quand le rotor droit est sur son encoche, il entraîne le rotor du **milieu** d'un cran ;
        • quand le rotor du milieu est sur son encoche, il entraîne le rotor **gauche**.

        Encoches : I → Q, II → E, III → V, IV → J, V → Z.

        **Le double pas.** Particularité mécanique : le cliquet qui fait avancer le rotor gauche s'appuie sur l'encoche du rotor du milieu, et le pousse lui aussi. Le rotor du milieu avance donc **deux fois de suite**.

        Exemple avec I-II-III en ADU : ADU → ADV → **AEW** (le droit passe son encoche V) → **BFX** (double pas : le milieu passe de E à F et le gauche avance).

        Résultat : les rotors reviennent à leur position de départ au bout de 26 × 25 × 26 = **16 900 lettres**.

        ► Appuyez sur les boutons et observez les cases orange (rotors qui ont tourné).
    """)

    def __init__(self):
        self.recommencer()

    def recommencer(self):
        self.machine = Enigma(positions="ADU")
        self.historique = [("Départ", "ADU", [], "")]
        self.numero = 0

    def appuyer(self, fois=1):
        for _ in range(fois):
            self.numero += 1
            _, detail = self.machine.appuyer("A")
            bouges = detail["bouges"]
            if "gauche" in bouges:
                note = "double pas : le milieu re-avance et entraîne le gauche"
            elif "milieu" in bouges:
                note = "le droit était sur son encoche → le milieu avance"
            else:
                note = ""
            self.historique.append((f"Touche {self.numero}", self.machine.positions(), bouges, note))

    def boutons(self):
        return [("Appuyer 1 fois", lambda: self.appuyer()),
                ("Appuyer 10 fois", lambda: self.appuyer(10)),
                ("Recommencer", self.recommencer)]

    def dessiner(self, c, rafraichir):
        x0, y0 = 30, 30
        noms = ("Gauche", "Milieu", "Droit")
        idents = ("gauche", "milieu", "droit")
        for k, rotor in enumerate(self.machine.rotors):
            c.create_text(x0 + 130 + k * 80, y0, justify="center", font=POLICE_TITRE,
                          text=f"{noms[k]} ({rotor.nom})\nencoche {ALPHABET[rotor.encoche]}")
        for n, (nom, positions, bouges, note) in enumerate(self.historique[-12:]):
            y = y0 + 65 + n * 40
            c.create_text(x0, y, text=nom, anchor="w", font=MOYEN)
            for k in range(3):
                fond = BOUGE if idents[k] in bouges else FENETRE
                boite(c, x0 + 130 + k * 80, y, positions[k], fond=fond, taille=32,
                      police=("Courier", 16, "bold"))
            if note:
                c.create_text(x0 + 360, y, text=note, anchor="w", width=280,
                              font=("Helvetica", 10, "bold" if "double" in note else "normal"),
                              fill=ALLER if "double" in note else TEXTE)


# ======================================================================
class ChapitreReflecteur(Chapitre):
    titre = "Le réflecteur"
    texte = texte("""
        Le **réflecteur** (Umkehrwalze) est une pièce fixe placée à gauche des rotors. Il relie les 26 lettres **par paires** (13 fils) et **renvoie le courant** dans les rotors, en sens inverse, par un autre chemin.

        Deux conséquences très importantes :

        1. **Enigma est réciproque.** Si A donne Q, alors, avec les mêmes réglages, Q donne A. Pour déchiffrer, il suffit de remettre la machine dans la même position de départ et de taper le message chiffré. Pas besoin d'un mode « déchiffrement » !

        2. **Une lettre n'est jamais chiffrée en elle-même.** Le courant ne peut pas revenir par le fil d'où il vient. Pratique pour la machine, mais c'est une **faiblesse majeure** exploitée par les cryptanalystes (chapitre 10).

        Ici, le réflecteur B seul : cliquez une lettre, le courant entre, fait demi-tour et allume la lampe de la lettre associée.
    """)

    def __init__(self):
        self.lettre = "A"

    def dessiner(self, c, rafraichir):
        refl = Reflecteur("B")
        s = Schema(c, x=250, y=20)
        s.ajouter_reflecteur("reflecteur", "Réflecteur B", refl.cablage)
        s.ajouter_clavier()
        s.dessiner()
        s.quand_on_clique(lambda l: (setattr(self, "lettre", l), rafraichir()))
        entree = ALPHABET.index(self.lettre)
        sortie = refl.renvoyer(entree)
        s.dessiner_trajet([("reflecteur", entree, sortie)])
        resultat(c, 200, s.bas() + 30, f"{self.lettre}  ↔  {ALPHABET[sortie]}", RETOUR)


# ======================================================================
class ChapitreBague(Chapitre):
    titre = "La bague (Ringstellung)"
    texte = texte("""
        La **bague** est l'anneau qui porte l'alphabet autour du rotor. Avant d'installer le rotor, on peut la faire tourner **par rapport au câblage interne**.

        Résultat : pour une même lettre affichée dans la fenêtre, le câblage n'est pas à la même place. Comparez les deux schémas : même fenêtre A, même touche, mais les fils ont glissé et la lettre de sortie change.

        L'**encoche est fixée sur la bague** : le rotor suivant est donc toujours entraîné quand la même lettre apparaît dans la fenêtre (Q pour le rotor I), quel que soit le réglage de la bague.

        La **clé du jour**, distribuée sur des carnets secrets, comprenait : le choix et l'ordre des rotors, le réglage des bagues et les câbles du tableau. La position de départ des rotors était ensuite choisie pour chaque message.
    """)

    def __init__(self):
        self.bague = 2
        self.lettre = "A"

    def boutons(self):
        return [("Bague −", lambda: self.changer(-1)), ("Bague +", lambda: self.changer(+1))]

    def changer(self, sens):
        self.bague = (self.bague - 1 + sens) % 26 + 1

    def dessiner(self, c, rafraichir):
        entree = ALPHABET.index(self.lettre)
        for x, bague in ((110, 1), (430, self.bague)):
            rotor = Rotor("I", "A", bague)
            s = Schema(c, x=x, y=20)
            ajouter_rotor_depuis(s, "rotor", f"Rotor I\nbague {bague:02d}", rotor)
            s.ajouter_clavier()
            s.dessiner()
            s.quand_on_clique(lambda l: (setattr(self, "lettre", l), rafraichir()))
            sortie = rotor.aller(entree)
            s.dessiner_trajet([("rotor", entree, sortie)])
            resultat(c, x - 40, s.bas() + 30, f"{self.lettre} → {ALPHABET[sortie]}", ALLER)


# ======================================================================
class ChapitreComplet(Chapitre):
    titre = "Le trajet complet"
    texte = texte("""
        Voici la machine complète, comme dans l'onglet Machine (rotors I-II-III, réflecteur B, sans câble).

        Quand on appuie sur une touche :
          1. les rotors tournent (le droit, et parfois les autres) ;
          2. le courant traverse le **tableau** ;
          3. puis les rotors **droit, milieu, gauche** (rouge) ;
          4. le **réflecteur** le renvoie ;
          5. il retraverse les rotors **gauche, milieu, droit** par d'autres fils (bleu) ;
          6. puis le **tableau**, et allume une **lampe**.

        Cela fait **9 substitutions** à la suite, et l'ensemble change à chaque touche.

        ► Essayez : depuis AAA, cliquez cinq fois sur A : vous obtenez B, D, Z, G, O. Cliquez « Recommencer », puis tapez B, D, Z, G, O : vous retrouvez A A A A A. C'est la **réciprocité** en action.
    """)

    def __init__(self):
        self.recommencer()

    def recommencer(self):
        self.machine = Enigma()
        self.detail = None
        self.tape = ""
        self.allume = ""

    def boutons(self):
        return [("Recommencer (AAA)", self.recommencer)]

    def appuyer(self, l):
        sortie, self.detail = self.machine.appuyer(l)
        self.tape += l
        self.allume += sortie

    def dessiner(self, c, rafraichir):
        s = Schema(c, x=14, y=8)
        ajouter_machine(s, self.machine, bouges=self.detail["bouges"] if self.detail else ())
        s.dessiner()
        s.quand_on_clique(lambda l: (self.appuyer(l), rafraichir()))
        if self.detail:
            s.dessiner_trajet(self.detail["trajet"])
        dessiner_legende(c, 14, s.bas() + 20)
        c.create_text(14, s.bas() + 48, anchor="w", font=MOYEN_GRAS,
                      text=f"Tapé : {self.tape or '—'}      Allumé : {self.allume or '—'}")


# ======================================================================
class ChapitreCles(Chapitre):
    titre = "Combien de clés possibles ?"
    texte = texte("""
        Pour lire un message, il faut connaître tous les réglages. Comptons-les, étape par étape (Enigma I, 5 rotors, 10 câbles).

        **1. Ordre des rotors.** 5 choix pour la gauche, puis 4 pour le milieu, puis 3 pour la droite : 5 × 4 × 3 = **60**.

        **2. Positions de départ.** 26 lettres par fenêtre : 26 × 26 × 26 = **17 576**.

        **3. Tableau de connexions (10 câbles).** On relie 20 lettres sur 26 par paires :
          • ranger les 26 lettres dans un ordre : 26! façons ;
          • l'ordre des 6 lettres sans câble ne compte pas : ÷ 6! ;
          • l'ordre des 10 câbles ne compte pas : ÷ 10! ;
          • un câble A–B est le même que B–A : ÷ 2¹⁰.
        Soit 26! ÷ (6! × 10! × 2¹⁰) = **150 738 274 937 250**.

        **4. Total** : on multiplie les trois.

        Si on compte aussi les bagues des rotors droit et milieu (qui changent le moment où les rotors s'entraînent), on multiplie encore par 26² = 676.

        Conclusion : impossible de tout essayer à la main. Il a fallu trouver des **raccourcis** (chapitre 10).
    """)

    def dessiner(self, c, rafraichir):
        def espaces(n):
            return f"{n:,}".replace(",", " ")

        ordre = 5 * 4 * 3
        positions = 26 ** 3
        tableau = math.factorial(26) // (math.factorial(6) * math.factorial(10) * 2 ** 10)
        total = ordre * positions * tableau
        mantisse, exposant = f"{total:.2e}".split("e+")
        exposant = int(exposant)
        exposant_txt = str(exposant).translate(str.maketrans("0123456789", "⁰¹²³⁴⁵⁶⁷⁸⁹"))
        annees = total / 1e6 / (365.25 * 24 * 3600)

        cartes = [("Ordre des 3 rotors (parmi 5)", "5 × 4 × 3", ordre),
                  ("Positions de départ", "26 × 26 × 26", positions),
                  ("Tableau de connexions (10 câbles)", "26! ÷ (6! × 10! × 2¹⁰)", tableau)]
        x0, y = 30, 25
        for k, (titre, formule, valeur) in enumerate(cartes):
            c.create_rectangle(x0, y, x0 + 620, y + 80, fill=PIECE, outline=BORD, width=2)
            c.create_text(x0 + 15, y + 22, text=titre, anchor="w", font=MOYEN_GRAS)
            c.create_text(x0 + 15, y + 55, text=formule, anchor="w", font=("Courier", 12))
            c.create_text(x0 + 605, y + 55, text=espaces(valeur), anchor="e",
                          font=("Courier", 15, "bold"), fill=ALLER)
            y += 80
            if k < len(cartes) - 1:
                c.create_text(x0 + 310, y + 15, text="×", font=("Helvetica", 18, "bold"))
                y += 30

        y += 20
        c.create_text(x0 + 310, y, text="=", font=("Helvetica", 18, "bold"))
        y += 20
        c.create_rectangle(x0, y, x0 + 620, y + 115, fill=FENETRE, outline=BORD, width=3)
        c.create_text(x0 + 15, y + 22, text="Nombre total de clés", anchor="w", font=MOYEN_GRAS)
        c.create_text(x0 + 310, y + 58, text=espaces(total), font=("Courier", 17, "bold"))
        c.create_text(x0 + 310, y + 93, font=GRAND,
                      text=f"≈ {mantisse.replace('.', ',')} × 10{exposant_txt}")

        y += 150
        c.create_text(x0, y, anchor="w", font=MOYEN, width=620,
                      text=f"Avec un ordinateur testant 1 million de clés par seconde, il faudrait "
                           f"environ {annees / 1e6:.0f} millions d'années pour toutes les essayer.")


# ======================================================================
class ChapitreFaiblesses(Chapitre):
    titre = "Comment Enigma a été cassée"
    texte = texte("""
        Enigma a pourtant été cassée : d'abord par les mathématiciens polonais (Marian **Rejewski**, dès 1932), puis à **Bletchley Park** par l'équipe d'Alan **Turing**, avec la **Bombe**, une machine électromécanique qui testait les réglages à grande vitesse.

        Ses principales faiblesses :

        • **Aucune lettre ne se chiffre en elle-même** (à cause du réflecteur).

        • **Les mots probables** (« cribs ») : beaucoup de messages contenaient des mots prévisibles : WETTERBERICHT (bulletin météo), KEINE BESONDEREN EREIGNISSE (rien à signaler), des grades, des noms de lieux…

        En combinant les deux, on fait glisser le mot probable sous le message chiffré : si une lettre tombe **sur la même lettre**, cette position est **impossible**. Le schéma le montre en rouge.

        • **Les erreurs humaines** : clés paresseuses (AAA…), messages répétés, même texte envoyé avec deux clés…

        Une fois le mot probable placé, la Bombe cherchait les réglages compatibles avec lui et éliminait des millions de combinaisons en quelques heures.

        ► Décalez le mot probable pour trouver les positions possibles.
    """)

    CLAIR = "HEUTEWETTERBERICHTXNORDSEEXREGEN"
    MOT = "WETTERBERICHT"

    def __init__(self):
        cle = dict(rotors=("II", "V", "III"), positions="HDX", bagues=(4, 12, 20),
                   connexions="AM FI NV PS TU WZ")
        self.chiffre = Enigma(**cle).chiffrer(self.CLAIR)
        self.decalage = 0
        self.montrer_clair = False

    def boutons(self):
        maxi = len(self.chiffre) - len(self.MOT)
        return [("◀ Décaler", lambda: setattr(self, "decalage", max(0, self.decalage - 1))),
                ("Décaler ▶", lambda: setattr(self, "decalage", min(maxi, self.decalage + 1))),
                ("Voir le clair", lambda: setattr(self, "montrer_clair", not self.montrer_clair))]

    def possible(self, d):
        return all(self.chiffre[d + j] != l for j, l in enumerate(self.MOT))

    def dessiner(self, c, rafraichir):
        x0, w = 20, 20
        c.create_text(x0, 30, anchor="w", font=MOYEN_GRAS, text="Message chiffré intercepté :")
        for i, l in enumerate(self.chiffre):
            boite(c, x0 + 10 + i * w, 60, l)
            c.create_text(x0 + 10 + i * w, 80, text=str(i), font=("Helvetica", 7), fill="#888")

        c.create_text(x0, 115, anchor="w", font=MOYEN_GRAS,
                      text=f"Mot probable « {self.MOT} » placé en position {self.decalage} :")
        conflits = 0
        for j, l in enumerate(self.MOT):
            i = self.decalage + j
            conflit = self.chiffre[i] == l
            conflits += conflit
            boite(c, x0 + 10 + i * w, 145, l, fond="#ff9a9a" if conflit else "#c8f0c0")
            if conflit:
                c.create_line(x0 + 10 + i * w, 70, x0 + 10 + i * w, 135, fill=ALLER, width=2)

        if conflits:
            message, couleur = (f"Impossible : {conflits} lettre(s) tomberaient sur elles-mêmes.", ALLER)
        else:
            message, couleur = ("Position possible ✓ (aucune lettre sur elle-même)", "#2a8a2a")
        c.create_text(x0, 190, anchor="w", font=GRAND, fill=couleur, text=message)

        possibles = [d for d in range(len(self.chiffre) - len(self.MOT) + 1) if self.possible(d)]
        total = len(self.chiffre) - len(self.MOT) + 1
        c.create_text(x0, 235, anchor="w", font=MOYEN, width=640,
                      text=f"Positions encore possibles ({len(possibles)} sur {total}) : "
                           f"{', '.join(map(str, possibles))}. Les autres sont éliminées sans "
                           f"rien connaître des réglages de la machine ! Avec un message plus long "
                           f"et plusieurs mots probables, on en élimine encore davantage.")

        if self.montrer_clair:
            c.create_text(x0, 290, anchor="w", font=MOYEN_GRAS, text="Message clair (secret) :")
            for i, l in enumerate(self.CLAIR):
                dans_mot = self.CLAIR.find(self.MOT) <= i < self.CLAIR.find(self.MOT) + len(self.MOT)
                boite(c, x0 + 10 + i * w, 320, l, fond=FENETRE if dans_mot else PIECE)
            c.create_text(x0, 360, anchor="w", font=MOYEN, fill="#555", width=640,
                          text=f"Le mot était en position {self.CLAIR.find(self.MOT)}. "
                               "Aucune lettre du clair n'est identique à la lettre chiffrée en dessous.")


# ======================================================================
class PageExplications(ttk.Frame):
    """Onglet 2 : chapitres d'explication avec illustrations."""

    def __init__(self, parent):
        super().__init__(parent, padding=8)
        self.chapitres = [VueEnsemble(), ChapitreTableau(), ChapitreRotor(), ChapitreRotation(),
                          ChapitreTroisRotors(), ChapitreReflecteur(), ChapitreBague(),
                          ChapitreComplet(), ChapitreCles(), ChapitreFaiblesses()]
        self.index = 0

        # --- À droite : illustration (placée en premier pour ne jamais être coupée) ---
        self.canvas = tk.Canvas(self, width=680, height=640, bg=FOND, highlightthickness=0)
        self.canvas.pack(side="right", anchor="n")

        # --- À gauche : sommaire ---
        self.sommaire = tk.Listbox(self, width=27, font=("Helvetica", 10), activestyle="none",
                                   exportselection=False, relief="flat", highlightthickness=0)
        for k, ch in enumerate(self.chapitres):
            self.sommaire.insert("end", f" {k + 1}. {ch.titre}")
        self.sommaire.pack(side="left", fill="y")
        self.sommaire.bind("<<ListboxSelect>>",
                           lambda e: self.sommaire.curselection() and
                           self.afficher(self.sommaire.curselection()[0]))

        # --- Au milieu : texte + boutons ---
        milieu = ttk.Frame(self, padding=(12, 0))
        milieu.pack(side="left", fill="both", expand=True)
        self.titre = ttk.Label(milieu, font=("Helvetica", 16, "bold"), wraplength=330)
        self.titre.pack(anchor="w", pady=(0, 6))
        self.texte = tk.Text(milieu, width=40, wrap="word", font=("Helvetica", 10),
                             relief="flat", padx=8, pady=8, spacing2=2, bg="#fffdf7")
        self.texte.tag_config("gras", font=("Helvetica", 10, "bold"))
        self.texte.tag_config("mono", font=("Courier", 9, "bold"))
        self.texte.pack(fill="both", expand=True)
        self.cadre_boutons = ttk.Frame(milieu)
        self.cadre_boutons.pack(fill="x", pady=6)
        nav = ttk.Frame(milieu)
        nav.pack(fill="x")
        ttk.Button(nav, text="◀ Précédent", command=lambda: self.afficher(self.index - 1)).pack(side="left")
        ttk.Button(nav, text="Suivant ▶", command=lambda: self.afficher(self.index + 1)).pack(side="right")

        self.afficher(0)

    def afficher(self, index):
        self.index = index % len(self.chapitres)
        ch = self.chapitres[self.index]
        self.sommaire.selection_clear(0, "end")
        self.sommaire.selection_set(self.index)
        self.titre.config(text=ch.titre)

        # Texte avec **gras** et `police fixe`
        self.texte.config(state="normal")
        self.texte.delete("1.0", "end")
        for morceau in re.split(r"(\*\*.+?\*\*|`[^`]+`)", ch.texte):
            if morceau.startswith("**"):
                self.texte.insert("end", morceau[2:-2], "gras")
            elif morceau.startswith("`"):
                self.texte.insert("end", morceau[1:-1], "mono")
            else:
                self.texte.insert("end", morceau)
        self.texte.config(state="disabled")

        # Boutons propres au chapitre
        for b in self.cadre_boutons.winfo_children():
            b.destroy()
        for libelle, action in ch.boutons():
            ttk.Button(self.cadre_boutons, text=libelle,
                       command=lambda a=action: (a(), self.redessiner())).pack(side="left", padx=(0, 4))
        self.redessiner()

    def redessiner(self):
        self.canvas.delete("all")
        self.canvas.config(cursor="")
        self.chapitres[self.index].dessiner(self.canvas, self.redessiner)
