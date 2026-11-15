# Enigma I : simulateur pédagogique en Python

Simulateur graphique de la machine à chiffrer **Enigma I** (armée allemande, 3 rotors), pensé pour **voir** ce qui se passe à chaque touche : rotation des rotors, trajet du courant à travers chaque pièce, lampe qui s'allume. Un second onglet explique le fonctionnement de la machine, chapitre par chapitre, avec les mêmes schémas.

## Lancer

Seul Python 3 est nécessaire : Tkinter est fourni avec Python, et il n'y a aucune dépendance à installer.

```bash
python app.py
```

> Sous Linux, si Tkinter manque : `sudo apt install python3-tk`.

Pour vérifier que le moteur fonctionne :

```bash
python enigma.py
# → Tous les tests passent.
```

## Fonctionnalités

### Onglet « Machine »

- **Réglages (clé du jour)** : choix du réflecteur (B ou C), modèle des 3 rotors (I à V), réglage des bagues (01 à 26), position de départ (boutons ◀ ▶) et câbles du tableau de connexions (`AB CD EF…`).
- **Schéma du courant** : réflecteur, rotors, tableau et clavier côte à côte, avec leur câblage interne. Le courant aller est tracé en **rouge** et le retour en **bleu**, avec une animation optionnelle.
- **Indicateurs** : la lettre visible dans la fenêtre (jaune), les encoches (triangle orange) et les rotors qui viennent de tourner (↻).
- **Tableau lumineux et clavier** en disposition allemande QWERTZ. On peut taper avec le vrai clavier ou cliquer sur les touches (y compris dans le schéma).
- **Détail de la dernière lettre** : l'avancement des rotors, puis les 9 substitutions successives.
- **Taper un texte entier** d'un coup. Les accents et la ponctuation sont nettoyés automatiquement.
- **Nouveau message** : remet les rotors à leur position de départ, ce qui permet de déchiffrer.

### Onglet « Comment ça marche ? »

Il compte 10 chapitres, chacun illustré par un schéma sur lequel on peut cliquer :

1. Enigma en bref
2. Le tableau de connexions
3. Un rotor : une permutation câblée
4. Le rotor tourne à chaque touche
5. Trois rotors : le compteur kilométrique (et le double pas)
6. Le réflecteur (réciprocité, aucune lettre chiffrée en elle-même)
7. La bague (Ringstellung)
8. Le trajet complet
9. Combien de clés possibles ? (calcul détaillé, ≈ 1,6 × 10²⁰)
10. Comment Enigma a été cassée (démo d'élimination avec un mot probable)

## Essai rapide

1. Laisser les réglages par défaut : I-II-III, réflecteur B, bagues 01, position AAA, sans câble.
2. Taper `AAAAA` : on obtient `BDZGO`, la valeur de référence connue.
3. Cliquer sur **↺ Nouveau message**, puis taper `BDZGO` : on retrouve `AAAAA`.

Ce dernier essai montre qu'Enigma est réciproque : chiffrer et déchiffrer sont la même opération.

## Structure du code

| Fichier | Rôle |
|---|---|
| `enigma.py` | Logique de la machine, sans interface : `Rotor`, `Reflecteur`, `TableauConnexions`, `Enigma`. Contient aussi des tests. |
| `schema.py` | Dessin des pièces et du trajet du courant sur un `Canvas`. Les deux onglets s'en servent. |
| `app.py` | Fenêtre principale et onglet « Machine ». |
| `explications.py` | Onglet « Comment ça marche ? ». Chaque chapitre est une petite classe (`titre`, `texte`, `boutons()`, `dessiner()`). |

### Points clés de l'implémentation

- **Lettres et nombres** : les lettres sont manipulées comme des nombres de 0 (A) à 25 (Z), et tous les décalages se font avec `% 26`.
- **Rotor** : à l'aller, `(cablage[(c + d) % 26] - d) % 26`, avec `d = position - bague`. Au retour, on applique la même formule avec le câblage inverse, qui est précalculé.
- **Avancement des rotors** : il a lieu **avant** le passage du courant. On applique d'abord le double pas (le rotor du milieu est sur son encoche, donc il avance et entraîne le rotor gauche), sinon l'entraînement par le rotor droit, puis le rotor droit avance.
- **Trajet** : `Enigma.appuyer()` renvoie la lettre allumée ainsi que la liste `(pièce, contact d'entrée, contact de sortie)`. L'interface utilise cette liste pour tracer le schéma.

## Câblages utilisés

Ce sont les câblages historiques de l'Enigma I :

| Rotor | Câblage | Encoche |
|---|---|---|
| I | `EKMFLGDQVZNTOWYHXUSPAIBRCJ` | Q |
| II | `AJDKSIRUXBLHWTMCQGZNPYFVOE` | E |
| III | `BDFHJLCPRTXVZNYEIWGAKMUSQO` | V |
| IV | `ESOVPZJAYQUIRHXLNFTGKDCMWB` | J |
| V | `VZBRGITYUPSDNHLXAWMJQOFECK` | Z |
| Réflecteur B | `YRUHQSLDPXNGOKMIEBFZCWVJAT` | – |
| Réflecteur C | `FVPJIAOYEDRZXWGCTKUQSBNMHL` | – |

## Pistes d'extension

- Ajouter la machine navale **M4** (4 rotors, réflecteurs fins B/C, rotor Beta/Gamma).
- **Casser** un message : recherche des positions des rotors par indice de coïncidence, puis du tableau par n-grammes.
- Simuler une **Bombe** de Turing simplifiée à partir d'un mot probable.
