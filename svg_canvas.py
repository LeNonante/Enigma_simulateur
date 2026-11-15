"""
svg_canvas.py — Un faux Canvas Tkinter qui produit une image SVG.

Il imite les méthodes de tkinter.Canvas utilisées par schema.py et
chapitres.py (create_line, create_text, tag_bind, after...). Ainsi, le MÊME
code de dessin sert à l'interface Tkinter et à la version web.

    canvas = CanvasSVG(680, 640)
    chapitre.dessiner(canvas, lambda: None)
    svg = canvas.rendu()          # chaîne "<svg ...>...</svg>"

Particularités :
  - canvas.after(ms, f) exécute f tout de suite, mais les éléments dessinés
    reçoivent un délai d'apparition CSS : c'est ce qui anime le courant ;
  - canvas.tag_bind(tag, "<Button-1>", f) mémorise f dans self.liaisons.
    Les éléments de ce tag deviennent cliquables dans la page, et le serveur
    rejoue le clic avec cliquer(tag, y).
"""

from html import escape

POLICES = {"Helvetica": "Helvetica, Arial, sans-serif",
           "Courier": "'Courier New', Courier, monospace"}


class Evenement:
    """Imite l'objet event de Tkinter (seuls x et y sont utilisés)."""

    def __init__(self, x=0, y=0):
        self.x, self.y = x, y


class CanvasSVG:
    def __init__(self, largeur, hauteur, fond=None):
        self.largeur, self.hauteur, self.fond = largeur, hauteur, fond
        self.elements = []     # dicts : balise, attributs, contenu, tags, délai
        self.liaisons = {}     # tag -> fonction appelée lors d'un clic
        self.marqueurs = {}    # flèches : identifiant -> définition SVG
        self._cles_marqueurs = {}   # (couleur, forme) -> identifiant
        self._delai = None
        self._compteur = 0

    # ================== Méthodes imitant tkinter.Canvas ==================
    def delete(self, quoi="all"):
        self.elements.clear()
        self.liaisons.clear()

    def config(self, **options):
        pass            # (le curseur est géré en CSS)

    configure = config

    def canvasy(self, y):
        return y

    def after(self, ms, fonction, *args):
        ancien, self._delai = self._delai, ms
        try:
            fonction(*args)
        finally:
            self._delai = ancien
        self._compteur += 1
        return self._compteur

    def after_cancel(self, identifiant):
        pass

    def tag_bind(self, tag, sequence, fonction):
        if sequence == "<Button-1>":
            self.liaisons[tag] = fonction

    def tag_raise(self, tag):
        """Passe les éléments de ce tag au premier plan (= en fin de document SVG)."""
        dessous = [e for e in self.elements if tag not in e["tags"]]
        dessus = [e for e in self.elements if tag in e["tags"]]
        self.elements = dessous + dessus

    def create_line(self, *coords, fill="black", width=1, arrow=None, arrowshape=(8, 10, 3),
                    capstyle=None, tags=()):
        points = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(coords[::2], coords[1::2]))
        attributs = {"points": points, "fill": "none", "stroke": fill or "none",
                     "stroke-width": width}
        if capstyle == "round":
            attributs["stroke-linecap"] = "round"
        if arrow == "last":
            attributs["marker-end"] = f"url(#{self._marqueur(fill, arrowshape)})"
        self._ajouter("polyline", attributs, tags=tags)

    def create_rectangle(self, x1, y1, x2, y2, fill="", outline="black", width=1, tags=()):
        self._ajouter("rect", {"x": min(x1, x2), "y": min(y1, y2),
                               "width": abs(x2 - x1), "height": abs(y2 - y1),
                               "fill": fill or "none", "stroke": outline or "none",
                               "stroke-width": width}, tags=tags)

    def create_oval(self, x1, y1, x2, y2, fill="", outline="black", width=1, tags=()):
        self._ajouter("ellipse", {"cx": (x1 + x2) / 2, "cy": (y1 + y2) / 2,
                                  "rx": abs(x2 - x1) / 2, "ry": abs(y2 - y1) / 2,
                                  "fill": fill or "none", "stroke": outline or "none",
                                  "stroke-width": width}, tags=tags)

    def create_polygon(self, *coords, fill="black", outline="", width=1, tags=()):
        points = " ".join(f"{x:.1f},{y:.1f}" for x, y in zip(coords[::2], coords[1::2]))
        self._ajouter("polygon", {"points": points, "fill": fill or "none",
                                  "stroke": outline or "none", "stroke-width": width}, tags=tags)

    def create_text(self, x, y, text="", anchor="center", font=("Helvetica", 10), fill="black",
                    justify="left", width=None, tags=()):
        famille, taille, *style = font
        px = taille * 4 / 3                   # points Tk -> pixels
        hauteur_ligne = px * 1.25

        lignes = []
        for paragraphe in str(text).split("\n"):
            lignes += self._couper(paragraphe, width, px) if width else [paragraphe]

        # Position horizontale (ancre Tk -> text-anchor SVG)
        if anchor in ("w", "nw", "sw"):
            ancre = "start"
        elif anchor in ("e", "ne", "se"):
            ancre = "end"
        else:
            ancre = "middle"
        # Position verticale du haut du bloc de texte
        total = hauteur_ligne * len(lignes)
        if anchor in ("n", "nw", "ne"):
            haut = y
        elif anchor in ("s", "sw", "se"):
            haut = y - total
        else:
            haut = y - total / 2

        tspans = "".join(
            f'<tspan x="{x:.1f}" y="{haut + hauteur_ligne * (k + 0.5):.1f}">{escape(l)}</tspan>'
            for k, l in enumerate(lignes))
        self._ajouter("text", {"text-anchor": ancre, "dominant-baseline": "central",
                               "font-family": POLICES.get(famille, famille),
                               "font-size": f"{px:.1f}",
                               "font-weight": "bold" if "bold" in style else "normal",
                               "fill": fill}, contenu=tspans, tags=tags)

    # ================== Spécifique à la version web ==================
    def cliquer(self, tag, y, x=0):
        """Rejoue un clic de la page web sur un élément du tag donné."""
        fonction = self.liaisons.get(tag)
        if fonction:
            fonction(Evenement(x, y))
        return fonction is not None

    def rendu(self):
        """Renvoie l'image SVG complète."""
        morceaux = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.largeur} '
                    f'{self.hauteur}" width="{self.largeur}" height="{self.hauteur}">']
        if self.marqueurs:
            morceaux.append("<defs>" + "".join(self.marqueurs.values()) + "</defs>")
        if self.fond:
            morceaux.append(f'<rect width="100%" height="100%" fill="{self.fond}"/>')
        for e in self.elements:
            attributs = dict(e["attributs"])
            cliquable = next((t for t in e["tags"] if t in self.liaisons), None)
            if cliquable:
                attributs["class"] = "cliquable"
                attributs["data-tag"] = cliquable
            if e["delai"] is not None:
                attributs["class"] = (attributs.get("class", "") + " anim").strip()
                attributs["style"] = f"animation-delay:{e['delai']}ms"
            texte_attributs = " ".join(f'{k}="{escape(str(v))}"' for k, v in attributs.items())
            morceaux.append(f'<{e["balise"]} {texte_attributs}>{e["contenu"]}</{e["balise"]}>')
        morceaux.append("</svg>")
        return "".join(morceaux)

    # ================== Outils internes ==================
    def _ajouter(self, balise, attributs, contenu="", tags=()):
        if isinstance(tags, str):
            tags = (tags,)
        self.elements.append({"balise": balise, "attributs": attributs, "contenu": contenu,
                              "tags": tuple(tags), "delai": self._delai})

    def _marqueur(self, couleur, forme):
        """Identifiant d'une pointe de flèche (créée au besoin) pour cette couleur et forme."""
        cle = (couleur, forme)
        if cle not in self._cles_marqueurs:
            d1, d2, d3 = forme
            ident = f"fleche{len(self.marqueurs)}"
            self._cles_marqueurs[cle] = ident
            self.marqueurs[ident] = (
                f'<marker id="{ident}" markerUnits="userSpaceOnUse" markerWidth="{d2}" '
                f'markerHeight="{2 * d3 + 2}" refX="{d2 - 1}" refY="{d3 + 1}" orient="auto">'
                f'<path d="M0,1 L{d2},{d3 + 1} L0,{2 * d3 + 1} z" fill="{couleur}"/></marker>')
        return self._cles_marqueurs[cle]

    @staticmethod
    def _couper(texte, largeur, px):
        """Coupe un paragraphe en lignes d'environ `largeur` pixels."""
        max_car = max(10, int(largeur / (px * 0.55)))
        lignes, courante = [], ""
        for mot in texte.split(" "):
            essai = (courante + " " + mot).strip()
            if len(essai) > max_car and courante:
                lignes.append(courante)
                courante = mot
            else:
                courante = essai
        lignes.append(courante)
        return lignes
