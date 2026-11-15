"""
app.py — Simulateur Enigma I avec interface graphique.

Lancer :   python app.py
(Tkinter est inclus avec Python, aucune installation nécessaire.)

Fichiers :
  enigma.py        la logique de la machine (aucune interface)
  schema.py        le dessin des pièces et du trajet du courant
  chapitres.py     le contenu des chapitres d'explication (sans Tkinter)
  explications.py  l'onglet « Comment ça marche ? »
  app.py           la fenêtre principale et l'onglet « Machine »

Une version web de la même application est dans web.py (Flask).
"""

import tkinter as tk
from tkinter import ttk, messagebox

from enigma import Enigma, ROTORS, REFLECTEURS, ALPHABET, nettoyer
from schema import (Schema, ajouter_machine, dessiner_legende, decrire_appui,
                    ALLER, RETOUR, LAMPE, FOND, FENETRE)
from explications import PageExplications

CLAVIER_ALLEMAND = ["QWERTZUIO", "ASDFGHJK", "PYXCVBNML"]   # disposition d'origine


class PageMachine(ttk.Frame):
    """Onglet 1 : la machine, ses réglages et le schéma du courant."""

    def __init__(self, parent):
        super().__init__(parent, padding=8)
        self.machine = Enigma()
        self.positions_depart = "AAA"
        self.texte_entree = ""      # lettres tapées
        self.texte_sortie = ""      # lettres allumées
        self.schema = None
        self.var_anime = tk.BooleanVar(value=True)

        self.construire_reglages()
        self.construire_centre()
        self.redessiner()
        self.dessiner_lampes()

    # ==================================================================
    # Construction de l'interface
    # ==================================================================
    def construire_reglages(self):
        cadre = ttk.LabelFrame(self, text=" Réglages de la machine (la « clé du jour ») ", padding=6)
        cadre.pack(fill="x")

        # --- Réflecteur ---
        f = ttk.LabelFrame(cadre, text="Réflecteur", padding=4)
        f.grid(row=0, column=0, padx=4, sticky="ns")
        self.var_reflecteur = tk.StringVar(value="B")
        cb = ttk.Combobox(f, textvariable=self.var_reflecteur, values=list(REFLECTEURS),
                          width=4, state="readonly")
        cb.pack(pady=8)
        cb.bind("<<ComboboxSelected>>", lambda e: self.appliquer())

        # --- Les trois rotors ---
        self.var_rotors, self.var_bagues, self.var_fenetres = [], [], []
        for k, (titre, defaut) in enumerate(zip(["Rotor gauche", "Rotor milieu", "Rotor droit"],
                                                ["I", "II", "III"])):
            f = ttk.LabelFrame(cadre, text=titre, padding=4)
            f.grid(row=0, column=k + 1, padx=3)

            ttk.Label(f, text="Modèle").grid(row=0, column=0)
            v_rotor = tk.StringVar(value=defaut)
            cb = ttk.Combobox(f, textvariable=v_rotor, values=list(ROTORS), width=3, state="readonly")
            cb.grid(row=1, column=0, padx=3)
            cb.bind("<<ComboboxSelected>>", lambda e: self.appliquer())

            ttk.Label(f, text="Bague").grid(row=0, column=1)
            v_bague = tk.StringVar(value="01")
            cb = ttk.Combobox(f, textvariable=v_bague, values=[f"{n:02d}" for n in range(1, 27)],
                              width=3, state="readonly")
            cb.grid(row=1, column=1, padx=3)
            cb.bind("<<ComboboxSelected>>", lambda e: self.appliquer())

            ttk.Label(f, text="Fenêtre").grid(row=0, column=2)
            fen = ttk.Frame(f)
            fen.grid(row=1, column=2, padx=3)
            v_fenetre = tk.StringVar(value="A")
            ttk.Button(fen, text="◀", width=2, command=lambda k=k: self.tourner(k, -1)).pack(side="left")
            tk.Label(fen, textvariable=v_fenetre, width=2, font=("Courier", 14, "bold"),
                     bg=FENETRE, relief="sunken").pack(side="left", padx=2)
            ttk.Button(fen, text="▶", width=2, command=lambda k=k: self.tourner(k, +1)).pack(side="left")

            self.var_rotors.append(v_rotor)
            self.var_bagues.append(v_bague)
            self.var_fenetres.append(v_fenetre)

        # --- Tableau de connexions ---
        f = ttk.LabelFrame(cadre, text="Tableau de connexions (paires)", padding=4)
        f.grid(row=0, column=4, padx=4, sticky="ns")
        self.var_connexions = tk.StringVar()
        e = ttk.Entry(f, textvariable=self.var_connexions, width=22)
        e.pack()
        e.bind("<Return>", lambda ev: self.appliquer())
        ttk.Label(f, text="ex : AB CD EF (Entrée)", foreground="#777").pack(anchor="w")

        # --- Boutons ---
        f = ttk.Frame(cadre)
        f.grid(row=0, column=5, padx=6)
        ttk.Button(f, text="Appliquer", command=self.appliquer).pack(fill="x", pady=1)
        ttk.Button(f, text="↺ Nouveau message", command=self.nouveau_message).pack(fill="x", pady=1)
        ttk.Checkbutton(f, text="Animer le courant", variable=self.var_anime).pack(anchor="w")

    def construire_centre(self):
        centre = ttk.Frame(self)
        centre.pack(fill="both", expand=True, pady=(8, 0))

        # --- À gauche : le schéma ---
        self.canvas = tk.Canvas(centre, width=660, height=600, bg=FOND, highlightthickness=0)
        self.canvas.pack(side="left", anchor="n")

        # --- À droite : lampes, clavier, textes, détail ---
        droite = ttk.Frame(centre, padding=(12, 0, 0, 0))
        droite.pack(side="left", fill="both", expand=True)

        ttk.Label(droite, text="Tableau lumineux", font=("Helvetica", 10, "bold")).pack(anchor="w")
        self.lampes = tk.Canvas(droite, width=420, height=126, bg="#2b2b2b", highlightthickness=0)
        self.lampes.pack(anchor="w")

        ttk.Label(droite, text="Clavier : cliquez, ou tapez sur votre vrai clavier",
                  font=("Helvetica", 10, "bold")).pack(anchor="w", pady=(6, 0))
        clavier = ttk.Frame(droite)
        clavier.pack(anchor="w")
        for r, rangee in enumerate(CLAVIER_ALLEMAND):
            ligne = ttk.Frame(clavier)
            ligne.pack(anchor="w", padx=(r * 18, 0))
            for l in rangee:
                ttk.Button(ligne, text=l, width=3, style="Touche.TButton",
                           command=lambda l=l: self.appuyer(l)).pack(side="left", padx=1, pady=1)

        self.zone_entree = self.zone_texte(droite, "Lettres tapées")
        self.zone_sortie = self.zone_texte(droite, "Lettres allumées (résultat)")

        f = ttk.Frame(droite)
        f.pack(fill="x", pady=(6, 0))
        self.var_texte = tk.StringVar()
        e = ttk.Entry(f, textvariable=self.var_texte)
        e.pack(side="left", fill="x", expand=True)
        e.bind("<Return>", lambda ev: self.taper_texte())
        ttk.Button(f, text="Taper ce texte", command=self.taper_texte).pack(side="left", padx=(4, 0))

        ttk.Label(droite, text="Que s'est-il passé pour la dernière lettre ?",
                  font=("Helvetica", 10, "bold")).pack(anchor="w", pady=(6, 0))
        self.detail = tk.Text(droite, height=12, width=56, font=("Courier", 9),
                              wrap="word", bg="#fffdf7", relief="solid", borderwidth=1)
        self.detail.pack(fill="both", expand=True)
        self.detail.tag_config("gras", font=("Courier", 9, "bold"))
        self.detail.tag_config("aller", foreground=ALLER)
        self.detail.tag_config("retour", foreground=RETOUR)
        self.ecrire_detail([("Appuyez sur une touche pour voir le courant traverser la machine.", "")])

    def zone_texte(self, parent, titre):
        ttk.Label(parent, text=titre, font=("Helvetica", 10, "bold")).pack(anchor="w", pady=(6, 0))
        zone = tk.Text(parent, height=2, width=56, font=("Courier", 11), wrap="word",
                       relief="solid", borderwidth=1, state="disabled")
        zone.pack(fill="x")
        return zone

    # ==================================================================
    # Actions
    # ==================================================================
    def appuyer(self, touche):
        """Une touche est enfoncée : les rotors tournent, le courant passe, une lampe s'allume."""
        avant = self.machine.positions()
        sortie, detail = self.machine.appuyer(touche)
        self.texte_entree += touche
        self.texte_sortie += sortie
        self.mettre_a_jour(detail, avant, sortie, anime=self.var_anime.get())

    def taper_texte(self):
        """Tape tout le texte du champ, lettre par lettre."""
        lettres = nettoyer(self.var_texte.get())
        if not lettres:
            return
        for touche in lettres:
            avant = self.machine.positions()
            sortie, detail = self.machine.appuyer(touche)
            self.texte_entree += touche
            self.texte_sortie += sortie
        self.var_texte.set("")
        self.mettre_a_jour(detail, avant, sortie, anime=False)

    def mettre_a_jour(self, detail, avant, sortie, anime):
        self.redessiner(detail, anime)
        self.dessiner_lampes(sortie)
        self.afficher_textes()
        self.afficher_detail(detail, avant, sortie)
        self.afficher_fenetres()

    def appliquer(self):
        """Reconstruit la machine avec les réglages choisis."""
        rotors = [v.get() for v in self.var_rotors]
        if len(set(rotors)) < 3:
            messagebox.showerror("Réglage impossible",
                                 "Chaque rotor n'existe qu'en un seul exemplaire :\n"
                                 "choisissez trois rotors différents.")
            return
        try:
            self.machine = Enigma(rotors=rotors,
                                  positions=self.machine.positions(),
                                  bagues=[int(v.get()) for v in self.var_bagues],
                                  reflecteur=self.var_reflecteur.get(),
                                  connexions=self.var_connexions.get())
        except ValueError as erreur:
            messagebox.showerror("Tableau de connexions", str(erreur))
            return
        self.var_connexions.set(" ".join(self.machine.tableau.paires))
        self.positions_depart = self.machine.positions()
        self.redessiner()

    def tourner(self, k, sens):
        """Bouton ◀ / ▶ : tourne un rotor à la main (choix de la position de départ)."""
        rotor = self.machine.rotors[k]
        rotor.position = (rotor.position + sens) % 26
        self.positions_depart = self.machine.positions()
        self.afficher_fenetres()
        self.redessiner()

    def nouveau_message(self):
        """Remet les rotors à la position de départ et efface les textes."""
        for rotor, l in zip(self.machine.rotors, self.positions_depart):
            rotor.position = ALPHABET.index(l)
        self.texte_entree = self.texte_sortie = ""
        self.afficher_fenetres()
        self.afficher_textes()
        self.dessiner_lampes()
        self.redessiner()
        self.ecrire_detail([(f"Rotors remis en {self.positions_depart}. "
                             "Pour déchiffrer, tapez maintenant le message chiffré.", "")])

    # ==================================================================
    # Affichage
    # ==================================================================
    def redessiner(self, detail=None, anime=False):
        if self.schema:
            self.schema.arreter()
        self.canvas.delete("all")
        self.schema = Schema(self.canvas, x=14, y=8)
        ajouter_machine(self.schema, self.machine, bouges=detail["bouges"] if detail else ())
        self.schema.dessiner()
        self.schema.quand_on_clique(self.appuyer)
        if detail:
            self.schema.dessiner_trajet(detail["trajet"], anime=anime)
        dessiner_legende(self.canvas, 14, self.schema.bas() + 22)
        self.canvas.create_text(14, self.schema.bas() + 48, anchor="w", fill="#666",
                                font=("Helvetica", 9),
                                text="Astuce : on peut aussi cliquer sur les lettres de la colonne « Clavier ».")

    def dessiner_lampes(self, allumee=None):
        c = self.lampes
        c.delete("all")
        for r, rangee in enumerate(CLAVIER_ALLEMAND):
            for k, l in enumerate(rangee):
                x, y = 30 + r * 20 + k * 40, 25 + r * 40
                eclairee = (l == allumee)
                if eclairee:   # halo
                    c.create_oval(x - 21, y - 21, x + 21, y + 21, fill="#7a6414", outline="")
                c.create_oval(x - 16, y - 16, x + 16, y + 16, outline="#111", width=2,
                              fill=LAMPE if eclairee else "#4a4a4a")
                c.create_text(x, y, text=l, font=("Helvetica", 12, "bold"),
                              fill="#222" if eclairee else "#bbbbbb")

    def afficher_fenetres(self):
        for v, rotor in zip(self.var_fenetres, self.machine.rotors):
            v.set(rotor.fenetre())

    def afficher_textes(self):
        def par_cinq(s):    # présentation historique : groupes de 5 lettres
            return " ".join(s[i:i + 5] for i in range(0, len(s), 5))
        for zone, texte in ((self.zone_entree, self.texte_entree), (self.zone_sortie, self.texte_sortie)):
            zone.config(state="normal")
            zone.delete("1.0", "end")
            zone.insert("end", par_cinq(texte))
            zone.see("end")
            zone.config(state="disabled")

    def ecrire_detail(self, morceaux):
        """morceaux = liste de (texte, tag)"""
        self.detail.config(state="normal")
        self.detail.delete("1.0", "end")
        for texte, tag in morceaux:
            self.detail.insert("end", texte, tag)
        self.detail.config(state="disabled")

    def afficher_detail(self, detail, avant, sortie):
        self.ecrire_detail(decrire_appui(self.machine, detail, avant, sortie))


class FenetreEnigma(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Enigma I — simulateur pédagogique")
        self.geometry("1280x800")
        self.minsize(1180, 760)
        style = ttk.Style(self)
        if "clam" in style.theme_names():
            style.theme_use("clam")
        style.configure("Touche.TButton", padding=(2, 1))

        self.onglets = ttk.Notebook(self)
        self.onglets.pack(fill="both", expand=True)
        self.page_machine = PageMachine(self.onglets)
        self.onglets.add(self.page_machine, text="  Machine  ")
        self.onglets.add(PageExplications(self.onglets), text="  Comment ça marche ?  ")

        self.bind("<KeyPress>", self.touche_clavier)

    def touche_clavier(self, event):
        """Les touches du vrai clavier actionnent la machine (onglet Machine seulement)."""
        if self.onglets.index("current") != 0:
            return
        if isinstance(event.widget, tk.Entry):    # on écrit dans un champ de saisie
            return
        touche = event.char.upper()
        if len(touche) == 1 and touche in ALPHABET:
            self.page_machine.appuyer(touche)


if __name__ == "__main__":
    FenetreEnigma().mainloop()
