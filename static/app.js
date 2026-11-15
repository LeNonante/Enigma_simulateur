/* ==========================================================
   Enigma — script de la version web
   Le serveur (web.py) fait tout le travail : chiffrement et dessin.
   Ce script envoie les actions et affiche les réponses.
   ========================================================== */

const $ = (selecteur) => document.querySelector(selecteur);
const $$ = (selecteur) => document.querySelectorAll(selecteur);

// ---------------- Outils ----------------

/** Appel à l'API : GET si pas de données, POST JSON sinon. */
async function api(url, donnees) {
  const options = donnees === undefined ? {} : {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(donnees),
  };
  const reponse = await fetch(url, options);
  const json = await reponse.json().catch(() => ({}));
  if (!reponse.ok) throw new Error(json.erreur || "Erreur du serveur.");
  return json;
}

/** Les actions sont exécutées une par une, dans l'ordre (frappe rapide au clavier). */
let file = Promise.resolve();
function enFile(action) {
  file = file.then(action).catch((e) => afficherErreur(e.message));
  return file;
}

function afficherErreur(message) {
  const toast = $("#toast");
  toast.textContent = message;
  toast.hidden = false;
  clearTimeout(afficherErreur.minuteur);
  afficherErreur.minuteur = setTimeout(() => (toast.hidden = true), 4000);
}

function echapper(texte) {
  const div = document.createElement("div");
  div.textContent = texte;
  return div.innerHTML;
}

/** "HELLOWORLD" -> "HELLO WORLD" (présentation historique par groupes de 5) */
function parCinq(texte) {
  return texte.match(/.{1,5}/g)?.join(" ") ?? "";
}

/** Coordonnées d'un clic converties dans le repère du dessin SVG. */
function pointSVG(svg, evenement) {
  const point = svg.createSVGPoint();
  point.x = evenement.clientX;
  point.y = evenement.clientY;
  return point.matrixTransform(svg.getScreenCTM().inverse());
}

/** Rend cliquables les touches dessinées dans un schéma SVG. */
function brancherClics(conteneur, envoyer) {
  conteneur.addEventListener("click", (evenement) => {
    const cible = evenement.target.closest("[data-tag]");
    if (!cible) return;
    const p = pointSVG(conteneur.querySelector("svg"), evenement);
    envoyer(cible.dataset.tag, p.y);
  });
}

// ---------------- Onglets ----------------

$$(".onglet").forEach((bouton) => {
  bouton.addEventListener("click", () => {
    $$(".onglet").forEach((b) => b.classList.toggle("actif", b === bouton));
    $$(".page").forEach((p) => p.classList.toggle("active", p.id === bouton.dataset.onglet));
  });
});

const ongletMachineActif = () => $("#machine").classList.contains("active");

// ==========================================================
// Onglet Machine
// ==========================================================

function afficherMachine(etat) {
  $("#schema-machine").innerHTML = etat.svg;

  // Fenêtres des rotors
  [...etat.positions].forEach((lettre, k) => {
    $(`[data-fenetre="${k}"]`).textContent = lettre;
  });

  // Réglages (resynchronisés avec le serveur, utile après une erreur)
  const r = etat.reglages;
  $("#reflecteur").value = r.reflecteur;
  $$(".modele").forEach((s, k) => (s.value = r.rotors[k]));
  $$(".bague").forEach((s, k) => (s.value = r.bagues[k]));
  if (document.activeElement !== $("#connexions")) $("#connexions").value = r.connexions;

  // Lampes
  $$(".lampe").forEach((l) => l.classList.toggle("allumee", l.dataset.lettre === etat.lampe));

  // Textes
  for (const [id, texte] of [["#texte-entree", etat.entree], ["#texte-sortie", etat.sortie]]) {
    const zone = $(id);
    zone.textContent = parCinq(texte);
    zone.scrollTop = zone.scrollHeight;
  }

  // Détail de la dernière lettre
  $("#detail").innerHTML = etat.detail
    .map(([texte, style]) => `<span class="${style}">${echapper(texte)}</span>`)
    .join("");
}

const anime = () => $("#anime").checked;

function appuyer(lettre) {
  enFile(async () => afficherMachine(await api("/api/machine/touche", { lettre, anime: anime() })));
}

function envoyerReglages() {
  enFile(async () => {
    const reglages = {
      reflecteur: $("#reflecteur").value,
      rotors: [...$$(".modele")].map((s) => s.value),
      bagues: [...$$(".bague")].map((s) => Number(s.value)),
      connexions: $("#connexions").value,
    };
    try {
      afficherMachine(await api("/api/machine/reglages", reglages));
    } catch (e) {
      afficherErreur(e.message);
      afficherMachine(await api("/api/machine"));   // on remet les réglages valides
    }
  });
}

// Réglages
$$(".reglage").forEach((s) => s.addEventListener("change", envoyerReglages));
$("#appliquer").addEventListener("click", envoyerReglages);
$("#connexions").addEventListener("keydown", (e) => {
  if (e.key === "Enter") {
    e.preventDefault();
    envoyerReglages();
  }
});

// Boutons ◀ ▶ des fenêtres
$$(".tourner").forEach((b) => b.addEventListener("click", () => {
  enFile(async () => afficherMachine(await api("/api/machine/tourner", {
    rotor: Number(b.dataset.rotor), sens: Number(b.dataset.sens),
  })));
}));

$("#nouveau").addEventListener("click", () => {
  enFile(async () => afficherMachine(await api("/api/machine/nouveau", {})));
});

// Clavier à l'écran
$$(".touche").forEach((b) => b.addEventListener("click", () => appuyer(b.dataset.lettre)));

// Vrai clavier (sauf quand on écrit dans un champ)
document.addEventListener("keydown", (e) => {
  if (!ongletMachineActif() || e.ctrlKey || e.metaKey || e.altKey) return;
  if (["INPUT", "SELECT", "TEXTAREA"].includes(e.target.tagName)) return;
  if (/^[a-z]$/i.test(e.key)) {
    e.preventDefault();
    appuyer(e.key.toUpperCase());
  }
});

// Clic sur la colonne « Clavier » du schéma
brancherClics($("#schema-machine"), (tag, y) => {
  enFile(async () => afficherMachine(await api("/api/machine/clic", { tag, y, anime: anime() })));
});

// Taper un texte entier
$("#form-texte").addEventListener("submit", (e) => {
  e.preventDefault();
  const texte = $("#texte").value;
  if (!texte.trim()) return;
  enFile(async () => {
    afficherMachine(await api("/api/machine/texte", { texte }));
    $("#texte").value = "";
  });
});

// ==========================================================
// Onglet « Comment ça marche ? »
// ==========================================================

const NB_CHAPITRES = $$(".chapitre-lien").length;
let chapitreCourant = 0;

function afficherChapitre(n, etat) {
  chapitreCourant = n;
  $$(".chapitre-lien").forEach((l) => l.classList.toggle("actif", Number(l.dataset.chapitre) === n));
  $("#chapitre-titre").textContent = etat.titre;
  $("#chapitre-texte").innerHTML = etat.texte;   // HTML déjà échappé par le serveur
  $("#schema-chapitre").innerHTML = etat.svg;

  const boutons = $("#chapitre-boutons");
  boutons.innerHTML = "";
  etat.boutons.forEach((libelle, index) => {
    const b = document.createElement("button");
    b.textContent = libelle;
    b.addEventListener("click", () => {
      enFile(async () => afficherChapitre(n, await api(`/api/chapitres/${n}/bouton`, { index })));
    });
    boutons.appendChild(b);
  });
}

function ouvrirChapitre(n) {
  n = (n + NB_CHAPITRES) % NB_CHAPITRES;
  enFile(async () => afficherChapitre(n, await api(`/api/chapitres/${n}`)));
}

$$(".chapitre-lien").forEach((l) => l.addEventListener("click", () => ouvrirChapitre(Number(l.dataset.chapitre))));
$("#precedent").addEventListener("click", () => ouvrirChapitre(chapitreCourant - 1));
$("#suivant").addEventListener("click", () => ouvrirChapitre(chapitreCourant + 1));

brancherClics($("#schema-chapitre"), (tag, y) => {
  const n = chapitreCourant;
  enFile(async () => afficherChapitre(n, await api(`/api/chapitres/${n}/clic`, { tag, y })));
});

// ---------------- Démarrage ----------------
enFile(async () => afficherMachine(await api("/api/machine")));
ouvrirChapitre(0);
