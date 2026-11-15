"""
schema.py — Dessin des pièces d'Enigma et du trajet du courant sur un Canvas Tkinter.

Le même code sert pour l'onglet « Machine » et pour les illustrations de
l'onglet « Comment ça marche ? », pour que les visuels soient identiques.

Principe du schéma :
  - les pièces sont posées côte à côte, de gauche à droite
    (réflecteur, rotors, tableau, clavier) ;
  - chaque pièce a 26 contacts, un par ligne (ligne 0 en haut) ;
  - entre deux pièces, le contact n°i est relié au contact n°i (fils droits) ;
  - à l'intérieur d'une pièce, les fils gris montrent son câblage.
"""

from enigma import ALPHABET

# ---------- Couleurs (partagées par toute l'application) ----------
FOND = "#f5f2eb"
PIECE = "#ffffff"
BANDE_FOND = "#ece5d6"
BORD = "#444444"
FIL = "#d9d4c7"
FIL_FORT = "#8f8877"
ALLER = "#d62828"      # courant aller (rouge)
RETOUR = "#1f6fd1"     # courant retour (bleu)
FENETRE = "#ffd966"    # lettre visible dans la fenêtre
BOUGE = "#f08a24"      # rotor qui vient de tourner / encoche
LAMPE = "#ffd23f"
TEXTE = "#222222"

POLICE = ("Courier", 9, "bold")
POLICE_TITRE = ("Helvetica", 9, "bold")

# ---------- Dimensions ----------
LARGEURS = {"reflecteur": 100, "rotor": 84, "tableau": 84, "clavier": 34}
BANDE = 18        # bande de lettres sur le côté droit des pièces
ESPACE = 28       # espace entre deux pièces
HAUT_TITRE = 34   # place pour le titre au-dessus des pièces


class Schema:
    def __init__(self, canvas, x=10, y=10, ligne=19):
        self.canvas = canvas
        self.x0, self.y0, self.ligne = x, y, ligne
        self.pieces = {}        # identifiant -> dictionnaire décrivant la pièce
        self.ordre = []         # identifiants de gauche à droite
        self.curseur = x        # abscisse de la prochaine pièce
        self.animations = []    # identifiants des after() en cours
        self.tag = f"schema{id(self)}"   # étiquette unique pour ce schéma

    # ================== Géométrie ==================
    def y(self, contact):
        """Ordonnée du centre de la ligne n°contact."""
        return self.y0 + HAUT_TITRE + contact * self.ligne + self.ligne / 2

    def haut(self):
        return self.y0 + HAUT_TITRE

    def bas(self):
        return self.y0 + HAUT_TITRE + 26 * self.ligne

    # ================== Ajout des pièces (de gauche à droite) ==================
    def _ajouter(self, ident, type_, titre, **options):
        largeur = LARGEURS[type_]
        piece = dict(id=ident, type=type_, titre=titre,
                     xg=self.curseur, xd=self.curseur + largeur, **options)
        self.pieces[ident] = piece
        self.ordre.append(ident)
        self.curseur += largeur + ESPACE
        return piece

    def ajouter_reflecteur(self, ident, titre, cablage):
        # On range les 13 fils du plus court au plus long pour limiter les croisements
        paires = {tuple(sorted((i, j))) for i, j in enumerate(cablage)}
        paires = sorted(paires, key=lambda p: p[1] - p[0])
        piece = self._ajouter(ident, "reflecteur", titre, liens=list(cablage), paires=paires)
        # Chaque paire a son « couloir » vertical
        xb = piece["xd"] - BANDE
        pas = (xb - piece["xg"] - 8) / len(paires)
        piece["couloirs"] = {}
        for k, (i, j) in enumerate(paires):
            piece["couloirs"][i] = piece["couloirs"][j] = xb - 5 - k * pas

    def ajouter_rotor(self, ident, titre, liens, etiquettes, encoche=None, bouge=False):
        """liens[i] = contact de gauche relié au contact de droite i."""
        self._ajouter(ident, "rotor", titre, liens=liens, etiquettes=etiquettes,
                      encoche=encoche, bouge=bouge)

    def ajouter_tableau(self, ident, titre, cablage):
        self._ajouter(ident, "tableau", titre, liens=list(cablage))

    def ajouter_clavier(self, titre="Clavier\nLampes"):
        self._ajouter("clavier", "clavier", titre)

    # ================== Dessin des pièces ==================
    def dessiner(self):
        c = self.canvas
        # 1) Fils fixes entre deux pièces voisines
        for gauche, droite in zip(self.ordre, self.ordre[1:]):
            xa, xb = self.pieces[gauche]["xd"], self.pieces[droite]["xg"]
            for i in range(26):
                c.create_line(xa, self.y(i), xb, self.y(i), fill=FIL)
        # 2) Chaque pièce selon son type
        for ident in self.ordre:
            piece = self.pieces[ident]
            self._titre(piece)
            getattr(self, "_dessiner_" + piece["type"])(piece)

    def _titre(self, p):
        titre = p["titre"] + (" ↻" if p.get("bouge") else "")
        self.canvas.create_text((p["xg"] + p["xd"]) / 2, self.y0 + HAUT_TITRE / 2,
                                text=titre, font=POLICE_TITRE, justify="center",
                                fill=BOUGE if p.get("bouge") else TEXTE)

    def _corps(self, p):
        """Rectangle de la pièce + bande de lettres à droite."""
        c = self.canvas
        xb = p["xd"] - BANDE
        c.create_rectangle(p["xg"], self.haut(), p["xd"], self.bas(),
                           fill=PIECE, outline=BORD, width=2)
        c.create_rectangle(xb, self.haut(), p["xd"], self.bas(), fill=BANDE_FOND, outline=BORD)
        return xb

    def _lettres(self, p, etiquettes):
        xb = p["xd"] - BANDE
        for i, l in enumerate(etiquettes):
            self.canvas.create_text((xb + p["xd"]) / 2, self.y(i), text=l,
                                    font=POLICE, tags=(self.tag + "lettre",))

    def _dessiner_rotor(self, p):
        c = self.canvas
        xb = self._corps(p)
        # Câblage interne
        for i, j in enumerate(p["liens"]):
            c.create_line(xb, self.y(i), p["xg"], self.y(j), fill=FIL)
        # Case de la fenêtre (ligne 0)
        demi = self.ligne / 2
        c.create_rectangle(xb, self.y(0) - demi, p["xd"], self.y(0) + demi, fill=FENETRE,
                           outline=BOUGE if p["bouge"] else BORD, width=3 if p["bouge"] else 1)
        self._lettres(p, p["etiquettes"])
        # Encoche : petit triangle orange à droite de la lettre concernée
        if p["encoche"] is not None:
            yy = self.y(p["encoche"])
            c.create_polygon(p["xd"] + 1, yy, p["xd"] + 8, yy - 5, p["xd"] + 8, yy + 5,
                             fill=BOUGE, outline=BORD)

    def _dessiner_tableau(self, p):
        c = self.canvas
        xb = self._corps(p)
        for i, j in enumerate(p["liens"]):
            if i == j:
                c.create_line(xb, self.y(i), p["xg"], self.y(j), fill=FIL)
            else:   # lettre reliée par un câble
                c.create_line(xb, self.y(i), p["xg"], self.y(j), fill=FIL_FORT, width=2)
        self._lettres(p, ALPHABET)

    def _dessiner_reflecteur(self, p):
        c = self.canvas
        xb = self._corps(p)
        for i, j in p["paires"]:
            x = p["couloirs"][i]
            c.create_line(xb, self.y(i), x, self.y(i), x, self.y(j), xb, self.y(j), fill=FIL)
        self._lettres(p, ALPHABET)

    def _dessiner_clavier(self, p):
        c = self.canvas
        cx = (p["xg"] + p["xd"]) / 2
        r = self.ligne / 2 - 1
        for i, l in enumerate(ALPHABET):
            y = self.y(i)
            c.create_oval(cx - r, y - r, cx + r, y + r, fill="#fafafa", outline=BORD,
                          tags=(self.tag + "touche",))
            c.create_text(cx, y, text=l, font=POLICE, tags=(self.tag + "touche",))

    # ================== Clic sur une touche du clavier ==================
    def quand_on_clique(self, fonction):
        """Appelle fonction('A'...'Z') quand on clique une lettre du clavier du schéma."""
        tag = self.tag + "touche"

        def clic(event):
            contact = int((self.canvas.canvasy(event.y) - self.haut()) // self.ligne)
            if 0 <= contact < 26:
                fonction(ALPHABET[contact])

        self.canvas.tag_bind(tag, "<Button-1>", clic)
        self.canvas.tag_bind(tag, "<Enter>", lambda e: self.canvas.config(cursor="hand2"))
        self.canvas.tag_bind(tag, "<Leave>", lambda e: self.canvas.config(cursor=""))

    # ================== Trajet du courant ==================
    def segments(self, etapes):
        """
        Transforme les étapes [(pièce, entrée, sortie), ...] en segments à tracer :
        [(x1, y1, x2, y2, couleur), ...]
        """
        segs = []
        couleur = ALLER
        sens = "gauche"            # le courant part du clavier vers la gauche
        point = None               # dernier point atteint
        clavier = self.pieces.get("clavier")
        if clavier:
            point = (clavier["xg"], self.y(etapes[0][1]))

        def aller_a(*points):
            nonlocal point
            for p in points:
                if point is not None and p != point:
                    segs.append((*point, *p, couleur))
                point = p

        for ident, entree, sortie in etapes:
            p = self.pieces[ident]
            xg, xd, xb = p["xg"], p["xd"], p["xd"] - BANDE
            if p["type"] == "reflecteur":
                x = p["couloirs"][entree]
                aller_a((xd, self.y(entree)), (x, self.y(entree)),
                        (x, self.y(sortie)), (xd, self.y(sortie)))
                sens, couleur = "droite", RETOUR      # le courant repart vers la droite
            elif sens == "gauche":
                aller_a((xd, self.y(entree)), (xb, self.y(entree)), (xg, self.y(sortie)))
            else:
                aller_a((xg, self.y(entree)), (xb, self.y(sortie)), (xd, self.y(sortie)))

        if sens == "droite" and clavier:
            aller_a((clavier["xg"], point[1]))        # retour jusqu'à la lampe
        elif sens == "gauche":
            aller_a((point[0] - 20, point[1]))        # petit bout de fil qui sort
        return segs, sens

    def dessiner_trajet(self, etapes, anime=False, vitesse=22):
        """Trace le trajet du courant, d'un coup ou progressivement (anime=True)."""
        segs, sens = self.segments(etapes)
        entree, sortie = etapes[0][1], etapes[-1][2]
        self._marquer_touche(entree)

        def tracer(k):
            x1, y1, x2, y2, couleur = segs[k]
            self.canvas.create_line(x1, y1, x2, y2, fill=couleur, width=3, capstyle="round")
            self.canvas.tag_raise(self.tag + "lettre")   # garder les lettres lisibles

        def terminer():
            if sens == "droite":
                self._allumer_lampe(sortie)
            else:   # pas de réflecteur : on écrit la lettre de sortie au bout du fil
                x, y = segs[-1][2], segs[-1][3]
                self.canvas.create_text(x - 4, y, text=ALPHABET[sortie], anchor="e",
                                        fill=ALLER, font=("Helvetica", 12, "bold"))

        if not anime:
            for k in range(len(segs)):
                tracer(k)
            terminer()
        else:
            for k in range(len(segs)):
                self.animations.append(self.canvas.after(k * vitesse, tracer, k))
            self.animations.append(self.canvas.after(len(segs) * vitesse, terminer))

    def arreter(self):
        """Annule une animation en cours (avant de redessiner)."""
        for a in self.animations:
            self.canvas.after_cancel(a)
        self.animations.clear()

    def _marquer_touche(self, contact):
        clavier = self.pieces.get("clavier")
        if not clavier:
            return
        cx, y, r = (clavier["xg"] + clavier["xd"]) / 2, self.y(contact), self.ligne / 2 + 1
        self.canvas.create_oval(cx - r, y - r, cx + r, y + r, outline=ALLER, width=3)

    def _allumer_lampe(self, contact):
        clavier = self.pieces["clavier"]
        cx, y, r = (clavier["xg"] + clavier["xd"]) / 2, self.y(contact), self.ligne / 2 + 1
        self.canvas.create_oval(cx - r, y - r, cx + r, y + r, fill=LAMPE, outline=RETOUR, width=3)
        self.canvas.create_text(cx, y, text=ALPHABET[contact], font=POLICE)


# ======================================================================
# Fonctions pratiques pour construire un schéma à partir du moteur
# ======================================================================
def ajouter_rotor_depuis(schema, ident, titre, rotor, bouge=False):
    """Ajoute au schéma un rotor du moteur (enigma.Rotor) dans son état actuel."""
    liens = [rotor.aller(i) for i in range(26)]
    # Lettre de la bague en face de chaque ligne (la ligne 0 = fenêtre)
    etiquettes = [ALPHABET[(rotor.position + i) % 26] for i in range(26)]
    encoche = (rotor.encoche - rotor.position) % 26
    schema.ajouter_rotor(ident, titre, liens, etiquettes, encoche, bouge)


def ajouter_machine(schema, machine, bouges=()):
    """Ajoute toutes les pièces d'une machine enigma.Enigma au schéma."""
    gauche, milieu, droit = machine.rotors
    schema.ajouter_reflecteur("reflecteur", f"Réflecteur\n{machine.reflecteur.nom}",
                              machine.reflecteur.cablage)
    for ident, nom, rotor in (("gauche", "Rotor gauche", gauche),
                              ("milieu", "Rotor milieu", milieu),
                              ("droit", "Rotor droit", droit)):
        ajouter_rotor_depuis(schema, ident, f"{nom}\n{rotor.nom}", rotor, bouge=ident in bouges)
    schema.ajouter_tableau("tableau", "Tableau de\nconnexions", machine.tableau.cablage)
    schema.ajouter_clavier()


def dessiner_legende(canvas, x, y):
    """Petite légende des couleurs, sur une ligne."""
    c = canvas
    c.create_line(x, y, x + 22, y, fill=ALLER, width=3)
    c.create_text(x + 27, y, text="aller", anchor="w", font=POLICE_TITRE)
    x += 70
    c.create_line(x, y, x + 22, y, fill=RETOUR, width=3)
    c.create_text(x + 27, y, text="retour", anchor="w", font=POLICE_TITRE)
    x += 80
    c.create_rectangle(x, y - 7, x + 16, y + 7, fill=FENETRE, outline=BORD)
    c.create_text(x + 21, y, text="lettre dans la fenêtre", anchor="w", font=POLICE_TITRE)
    x += 160
    c.create_polygon(x, y, x + 8, y - 5, x + 8, y + 5, fill=BOUGE, outline=BORD)
    c.create_text(x + 13, y, text="encoche", anchor="w", font=POLICE_TITRE)
    x += 75
    c.create_text(x, y, text="↻ = vient de tourner", anchor="w", font=POLICE_TITRE, fill=BOUGE)
