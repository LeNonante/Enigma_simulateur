# Enigma I — simulateur pédagogique en Python

Simulateur graphique de la machine à chiffrer **Enigma I** (armée allemande, 3 rotors), pensé pour **voir** ce qui se passe à chaque touche : rotation des rotors, trajet du courant à travers chaque pièce, lampe qui s'allume. Un second onglet explique le fonctionnement de la machine, chapitre par chapitre, avec les mêmes schémas.

Deux interfaces partagent exactement le même moteur et les mêmes dessins :

- **Application de bureau** (Tkinter) : aucune dépendance, un seul `python app.py` suffit.
- **Application web** (Flask) : déployable en ligne avec Docker.

## Lancer l'application de bureau (Tkinter)

Seul Python 3 est nécessaire : Tkinter est fourni avec Python.

```bash
python app.py
```

> Sous Linux, si Tkinter manque : `sudo apt install python3-tk`.

## Lancer la version web

### En local (développement)

```bash
pip install -r requirements.txt
python web.py
```

Puis ouvrir <http://localhost:8000>.

### Avec Docker (production)

```bash
docker compose up -d --build
```

Le site est alors disponible sur <http://localhost:8000>.

Les réglages se font avec un fichier `.env`, à créer à partir de `.env.example` :

| Variable | Rôle | Défaut |
|---|---|---|
| `PORT` | Port exposé sur la machine hôte | `8000` |
| `SECRET_KEY` | Clé qui signe les cookies de session | aléatoire à chaque démarrage |

Une route de santé, `GET /sante`, renvoie `ok`. Docker l'utilise pour son `HEALTHCHECK`.

Pour une mise en ligne, placez le conteneur derrière un reverse proxy (Nginx, Caddy, Traefik…) qui gère le HTTPS, et redirigez-le vers le port 8000.

> ⚠️ **Gardez un seul worker Gunicorn.** La machine et les chapitres de chaque visiteur sont gardés **en mémoire** dans le processus (un cookie permet de retrouver chaque visiteur). Plusieurs workers ne partageraient pas ces données. Pour encaisser plus de visiteurs simultanés, augmentez plutôt `--threads` dans le `Dockerfile`. Un redémarrage remet toutes les machines à zéro.

## Vérifier le moteur

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

## Structure du projet

```
enigma/
├── enigma.py           Moteur de la machine (aucune interface) + tests
├── schema.py           Dessin des pièces et du trajet du courant
├── chapitres.py        Contenu des 10 chapitres d'explication (sans Tkinter)
│
├── app.py              Interface de bureau : fenêtre + onglet « Machine »
├── explications.py     Interface de bureau : onglet « Comment ça marche ? »
│
├── web.py              Serveur Flask (pages + API JSON)
├── svg_canvas.py       Faux Canvas Tkinter qui produit du SVG
├── templates/
│   └── index.html      Page web
├── static/
│   ├── style.css       Styles (CSS classique)
│   └── app.js          Interactions (JavaScript sans framework)
│
├── requirements.txt    Dépendances de la version web (Flask, Gunicorn)
├── Dockerfile
├── docker-compose.yml
└── .env.example
```

### Comment le code est partagé

Le moteur (`enigma.py`) et tous les dessins (`schema.py`, `chapitres.py`) sont écrits **une seule fois**. Ils dessinent sur un objet qui possède les méthodes d'un `Canvas` Tkinter (`create_line`, `create_text`, `tag_bind`…).

- **Tkinter** : cet objet est un vrai `tkinter.Canvas`.
- **Web** : c'est un `CanvasSVG` (`svg_canvas.py`), qui imite ces méthodes et produit une image **SVG**. Le serveur envoie cette image au navigateur, ce qui garantit des visuels identiques dans les deux versions.

Deux astuces dans `CanvasSVG` :

- **Animation** : `canvas.after(délai, fonction)` exécute la fonction immédiatement, mais les éléments dessinés reçoivent un `animation-delay` CSS. Le courant apparaît donc progressivement dans le navigateur.
- **Clics** : `tag_bind(tag, "<Button-1>", fonction)` rend les éléments cliquables. Le navigateur renvoie le tag et la coordonnée du clic, et le serveur rejoue le clic sur le même dessin (`canvas.cliquer(tag, y)`).

### API de la version web

| Méthode | Route | Rôle |
|---|---|---|
| GET | `/api/machine` | État de la machine (SVG, positions, textes, détail) |
| POST | `/api/machine/touche` | Appuyer sur une touche `{lettre, anime}` |
| POST | `/api/machine/clic` | Clic dans le schéma `{tag, y, anime}` |
| POST | `/api/machine/texte` | Taper un texte entier `{texte}` |
| POST | `/api/machine/reglages` | `{reflecteur, rotors[3], bagues[3], connexions}` |
| POST | `/api/machine/tourner` | Tourner un rotor `{rotor: 0-2, sens: -1/1}` |
| POST | `/api/machine/nouveau` | Revenir aux positions de départ |
| GET | `/api/chapitres/<n>` | Titre, texte HTML, boutons et SVG d'un chapitre |
| POST | `/api/chapitres/<n>/bouton` | Bouton d'un chapitre `{index}` |
| POST | `/api/chapitres/<n>/clic` | Clic dans le schéma d'un chapitre `{tag, y}` |

### Points clés du moteur

- **Lettres et nombres** : les lettres sont manipulées comme des nombres de 0 (A) à 25 (Z), et tous les décalages se font avec `% 26`.
- **Rotor** : à l'aller, `(cablage[(c + d) % 26] - d) % 26`, avec `d = position - bague`. Au retour, on applique la même formule avec le câblage inverse, qui est précalculé.
- **Avancement des rotors** : il a lieu **avant** le passage du courant. On applique d'abord le double pas (le rotor du milieu est sur son encoche, donc il avance et entraîne le rotor gauche), sinon l'entraînement par le rotor droit, puis le rotor droit avance.
- **Trajet** : `Enigma.appuyer()` renvoie la lettre allumée ainsi que la liste `(pièce, contact d'entrée, contact de sortie)`. Les interfaces utilisent cette liste pour tracer le schéma.

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
- Version web sans état côté serveur (réglages gardés dans le navigateur), pour pouvoir utiliser plusieurs workers.
