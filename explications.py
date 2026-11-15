"""
explications.py — L'onglet « Comment ça marche ? » de l'interface Tkinter.

Le contenu des chapitres (textes et dessins) est dans chapitres.py,
partagé avec la version web.
"""

import re
import tkinter as tk
from tkinter import ttk

from chapitres import creer_chapitres
from schema import FOND


# ======================================================================
class PageExplications(ttk.Frame):
    """Onglet 2 : chapitres d'explication avec illustrations."""

    def __init__(self, parent):
        super().__init__(parent, padding=8)
        self.chapitres = creer_chapitres()
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
