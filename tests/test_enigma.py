"""Tests du moteur (enigma.py) et de sa ligne de commande.

Les cinq vecteurs de référence du test ``test_vecteurs_de_reference`` ont été
produits par une autre implémentation de la machine (py-enigma 1.0.2). Le
moteur a en outre été comparé à cette implémentation sur 300 clés tirées au
hasard (rotors, positions de départ, bagues, réflecteurs et tableaux de
connexions) : 300 résultats identiques. Ces vecteurs figent donc à la fois les
câblages et le mécanisme d'avancement, encoches et double pas compris.
"""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from enigma import (
    ALPHABET,
    REFLECTEURS,
    ROTORS,
    Enigma,
    Rotor,
    TableauConnexions,
    autotest,
    bague_depuis_texte,
    en_groupes,
    lettre,
    nettoyer,
    num,
    principal,
)

RACINE = Path(__file__).resolve().parent.parent

CLES_ALEATOIRES = [
    dict(rotors=("I", "II", "III"), positions="AAA", bagues=(1, 1, 1)),
    dict(rotors=("II", "V", "III"), positions="HDX", bagues=(4, 12, 20),
         reflecteur="C", connexions="AM FI NV PS TU WZ"),
    dict(rotors=("V", "I", "IV"), positions="ZQO", bagues=(26, 13, 7),
         reflecteur="C", connexions="AB CD EF"),
]


def lancer_cli(*arguments, entree=None):
    """Lance « python enigma.py … » et renvoie le résultat du processus."""
    return subprocess.run([sys.executable, str(RACINE / "enigma.py"), *arguments],
                          input=entree, capture_output=True, text=True, cwd=RACINE,
                          timeout=60, check=False)


# ==========================================================================
# Câblages et conversions
# ==========================================================================
def test_cablages_historiques():
    assert list(ROTORS) == ["I", "II", "III", "IV", "V"]
    for nom, (cablage, encoche) in ROTORS.items():
        assert len(cablage) == 26, nom
        assert set(cablage) == set(ALPHABET), nom
        assert encoche in ALPHABET, nom


def test_reflecteurs_sont_reciproques():
    for nom, cablage in REFLECTEURS.items():
        assert len(cablage) == 26, nom
        for i, c in enumerate(cablage):
            assert cablage[num(c)] == ALPHABET[i], nom


def test_num_et_lettre():
    assert num("A") == 0
    assert num("Z") == 25
    assert lettre(0) == "A"
    assert lettre(26) == "A"
    assert lettre(-1) == "Z"


@pytest.mark.parametrize("valeur", ["AB", "", "a", "1", None, 3])
def test_num_refuse_autre_chose_qu_une_lettre(valeur):
    with pytest.raises(ValueError, match="lettre"):
        num(valeur)


def test_nettoyer_accents_ponctuation_chiffres():
    assert nettoyer("Bonjour, l'été ! 123") == "BONJOURLETE"
    assert nettoyer("") == ""
    assert nettoyer("éàü") == "EAU"


def test_nettoyer_refuse_un_non_texte():
    with pytest.raises(ValueError, match="texte"):
        nettoyer(None)


def test_en_groupes():
    assert en_groupes("BONJOUR", 5) == "BONJO UR"
    assert en_groupes("BONJOUR", 0) == "BONJOUR"
    assert en_groupes("BONJOUR", -3) == "BONJOUR"
    assert en_groupes("", 5) == ""


# ==========================================================================
# Fonctionnement de la machine
# ==========================================================================
def test_valeur_de_reference():
    assert Enigma().chiffrer("AAAAA") == "BDZGO"


@pytest.mark.parametrize("cle", CLES_ALEATOIRES)
def test_reciprocite(cle):
    texte = "ATTAQUEALAPLAGEAMINAUBE"
    chiffre = Enigma(**cle).chiffrer(texte)
    assert Enigma(**cle).chiffrer(chiffre) == texte


@pytest.mark.parametrize("cle", CLES_ALEATOIRES)
def test_aucune_lettre_ne_s_chiffre_en_elle_meme(cle):
    machine = Enigma(**cle)
    for _ in range(1000):
        touche = lettre(machine.rotors[2].position)
        assert machine.appuyer(touche)[0] != touche


def test_double_pas():
    """ADU -> ADV -> AEW -> BFX : le rotor du milieu avance deux fois de suite."""
    machine = Enigma(positions="ADU")
    positions = []
    for _ in range(3):
        machine.appuyer("A")
        positions.append(machine.positions())
    assert positions == ["ADV", "AEW", "BFX"]


def test_rotors_qui_bougent():
    machine = Enigma(positions="ADU")
    assert machine.appuyer("A")[1]["bouges"] == ["droit"]
    assert machine.appuyer("A")[1]["bouges"] == ["droit", "milieu"]
    assert machine.appuyer("A")[1]["bouges"] == ["droit", "milieu", "gauche"]


def test_trajet_traverse_neuf_pieces():
    _, detail = Enigma().appuyer("A")
    pieces = [piece for piece, _, _ in detail["trajet"]]
    assert pieces == ["tableau", "droit", "milieu", "gauche", "reflecteur",
                      "gauche", "milieu", "droit", "tableau"]
    # Les contacts se suivent : la sortie d'une pièce entre dans la suivante
    for (_, _, sortie), (_, entree, _) in zip(detail["trajet"], detail["trajet"][1:]):
        assert sortie == entree


def test_detail_de_l_appui():
    sortie, detail = Enigma().appuyer("A")
    assert detail["touche"] == "A"
    assert detail["explications"]
    assert sortie == "B"


def test_la_bague_change_le_chiffrement():
    sans = Enigma().chiffrer("AAAAA")
    avec = Enigma(bagues=(2, 1, 1)).chiffrer("AAAAA")
    assert sans != avec


def test_positions_minuscules_acceptees():
    assert Enigma(positions="aaa").chiffrer("A") == Enigma().chiffrer("A")


def test_position_apres_une_touche():
    machine = Enigma()
    machine.appuyer("A")
    assert machine.positions() == "AAB"


def test_reglages():
    machine = Enigma(rotors=("II", "V", "III"), positions="HDX", bagues=(4, 12, 20),
                     reflecteur="C", connexions="AM FI")
    assert machine.reglages() == {"rotors": ["II", "V", "III"], "positions": "HDX",
                                  "bagues": [4, 12, 20], "reflecteur": "C",
                                  "connexions": "AM FI"}


# ==========================================================================
# Vecteurs de référence (produits par py-enigma 1.0.2)
# ==========================================================================
@pytest.mark.parametrize("reglages, clair, chiffre", [
    (dict(rotors="I II III", positions="AAA", bagues=(1, 1, 1), reflecteur="B",
          connexions=""), "AAAAA", "BDZGO"),
    (dict(rotors="I II III", positions="ADU", bagues=(1, 1, 1), reflecteur="B",
          connexions=""), "AAAAAA", "EQIBMG"),
    (dict(rotors="II V III", positions="HDX", bagues=(4, 12, 20), reflecteur="C",
          connexions="AM FI NV PS TU WZ"), "BONJOURDEPUISTROYES", "SPJRGXNYDFRFVXFPCVX"),
    (dict(rotors="IV V II", positions="QWE", bagues=(26, 1, 13), reflecteur="B",
          connexions="AZ BY CX DW EV"), "LENIGMAAETEINDECHIFFRABLE", "HHKZEXMGWIDCITJUDUROJWXAK"),
    (dict(rotors="III I IV", positions="LWK", bagues=(3, 8, 18), reflecteur="C",
          connexions="QZ WM EN RX"), "ATTAQUEALAPLAGE", "ZQWIMKWKBFOVWHQ"),
])
def test_vecteurs_de_reference(reglages, clair, chiffre):
    assert Enigma(**reglages).chiffrer(clair) == chiffre


# ==========================================================================
# Réglages impossibles : refusés tout de suite, avec un message utile
# ==========================================================================
def test_deux_rotors_refuses():
    with pytest.raises(ValueError, match="trois rotors"):
        Enigma(rotors=("I", "II"))


def test_positions_tronquees_refusees():
    with pytest.raises(ValueError, match="position"):
        Enigma(positions="AA")


def test_rotors_doubles_refuses():
    with pytest.raises(ValueError, match="un seul exemplaire"):
        Enigma(rotors=("I", "I", "III"))


def test_rotor_inconnu_refuse():
    with pytest.raises(ValueError, match="Rotor inconnu"):
        Enigma(rotors=("I", "II", "IX"))


def test_reflecteur_inconnu_refuse():
    with pytest.raises(ValueError, match="Réflecteur inconnu"):
        Enigma(reflecteur="D")


@pytest.mark.parametrize("positions", ["", "AAAA", "AA1", "A A", None])
def test_positions_invalides_refusees(positions):
    with pytest.raises(ValueError, match="position"):
        Enigma(positions=positions)


@pytest.mark.parametrize("bague", [0, 27, -1, 1.5, "1", True])
def test_bagues_invalides_refusees(bague):
    with pytest.raises(ValueError, match="bague"):
        Enigma(bagues=(bague, 1, 1))


def test_deux_bagues_refusees():
    with pytest.raises(ValueError, match="trois bagues"):
        Enigma(bagues=(1, 1))


def test_rotors_en_texte_acceptes():
    assert Enigma(rotors="I II III").chiffrer("A") == Enigma().chiffrer("A")


# ==========================================================================
# Rotor et tableau de connexions, pris séparément
# ==========================================================================
def test_rotor_valide_ses_reglages():
    with pytest.raises(ValueError, match="Rotor inconnu"):
        Rotor("IX")
    with pytest.raises(ValueError, match="Position"):
        Rotor("I", position="AB")
    with pytest.raises(ValueError, match="bague"):
        Rotor("I", bague=0)


def test_rotor_aller_retour_sont_inverses():
    rotor = Rotor("I", "K", 7)
    for contact in range(26):
        assert rotor.retour(rotor.aller(contact)) == contact


def test_tableau_sans_cable():
    tableau = TableauConnexions()
    assert tableau.paires == []
    assert all(tableau.echanger(i) == i for i in range(26))


def test_tableau_none_ou_vide():
    assert TableauConnexions(None).paires == []
    assert TableauConnexions("   ").paires == []


def test_tableau_echange_les_paires():
    tableau = TableauConnexions("am fi")
    assert tableau.paires == ["AM", "FI"]
    assert tableau.echanger(num("A")) == num("M")
    assert tableau.echanger(num("M")) == num("A")


@pytest.mark.parametrize("paires, message", [
    ("ABC", "paire de deux lettres"),
    ("A1", "paire de deux lettres"),
    ("AA", "elle-même"),
    ("AM AM", "déjà un câble"),
    ("AM MA", "déjà un câble"),
])
def test_tableau_refuse_les_cables_impossibles(paires, message):
    with pytest.raises(ValueError, match=message):
        TableauConnexions(paires)


def test_tableau_refuse_un_non_texte():
    with pytest.raises(ValueError, match="texte"):
        TableauConnexions(["AM"])


# ==========================================================================
# Touches
# ==========================================================================
def test_touche_minuscule_acceptee():
    assert Enigma().appuyer("a")[0] == Enigma().appuyer("A")[0]


@pytest.mark.parametrize("touche", ["AB", "", "1", None, 3, ["A"]])
def test_touches_invalides_refusees(touche):
    with pytest.raises(ValueError, match="touche"):
        Enigma().appuyer(touche)


def test_autotest():
    assert autotest()


# ==========================================================================
# Ligne de commande
# ==========================================================================
class Terminal:
    """Faux terminal : isatty() vrai, donc l'autotest doit se lancer."""

    def isatty(self):
        return True

    def read(self):     # pragma: no cover - ne doit jamais être appelé
        raise AssertionError("l'entrée standard ne doit pas être lue")


def test_sans_argument_dans_un_terminal_lance_l_autotest(monkeypatch, capsys):
    monkeypatch.setattr(sys, "stdin", Terminal())
    assert principal([]) == 0
    assert "Tous les tests passent." in capsys.readouterr().out


def test_cli_selftest_explicite():
    resultat = lancer_cli("--selftest")
    assert resultat.returncode == 0
    assert "Tous les tests passent." in resultat.stdout


def test_cli_chiffre_avec_la_cle_par_defaut():
    resultat = lancer_cli("AAAAA")
    assert resultat.returncode == 0
    assert resultat.stdout.strip() == "BDZGO"


def test_cli_est_reciproque():
    chiffre = lancer_cli("--positions", "HDX", "Bonjour depuis Troyes").stdout.strip()
    clair = lancer_cli("--positions", "HDX", chiffre).stdout.strip()
    assert clair == "BONJOURDEPUISTROYES"


def test_cli_avec_tous_les_reglages():
    resultat = lancer_cli("--rotors", "II", "V", "III", "--positions", "HDX",
                          "--bagues", "4", "12", "20", "--reflecteur", "C",
                          "--plugs", "AM FI NV PS TU WZ", "BONJOURDEPUISTROYES")
    assert resultat.returncode == 0
    assert resultat.stdout.strip() == "SPJRGXNYDFRFVXFPCVX"


def test_cli_bagues_en_lettres():
    chiffres = lancer_cli("--bagues", "D", "L", "T", "AAAAA").stdout
    nombres = lancer_cli("--bagues", "4", "12", "20", "AAAAA").stdout
    assert chiffres == nombres


def test_grouper():
    resultat = lancer_cli("--grouper", "5", "BONJOUR")
    groupes = resultat.stdout.strip().split()
    assert max(len(g) for g in groupes) <= 5
    assert "".join(groupes) == lancer_cli("BONJOUR").stdout.strip()


def test_cli_detail():
    resultat = lancer_cli("--detail", "AB")
    lignes = [l for l in resultat.stdout.splitlines() if "->" in l and "rotors" in l]
    assert len(lignes) == 2
    assert lignes[0].startswith("A -> ")


def test_cli_json():
    resultat = lancer_cli("--json", "--positions", "HDX", "Ab")
    donnees = json.loads(resultat.stdout)
    assert donnees["clair"] == "AB"
    assert donnees["chiffre"] == lancer_cli("--positions", "HDX", "AB").stdout.strip()
    assert donnees["reglages"]["positions"] == "HDX"
    assert [l["entree"] for l in donnees["lettres"]] == ["A", "B"]
    assert all(len(l["trajet"].split()) == 10 for l in donnees["lettres"])
    assert donnees["lettres"][0]["avant"] == "HDX"
    assert donnees["lettres"][0]["apres"] == "HDY"


def test_cli_lit_l_entree_standard():
    resultat = lancer_cli(entree="attaque a l'aube\n")
    assert resultat.returncode == 0
    assert resultat.stdout.strip() == lancer_cli("ATTAQUEALAUBE").stdout.strip()


@pytest.mark.parametrize("arguments", [
    ["--rotors", "I", "I", "III", "A"],
    ["--rotors", "I", "II", "IX", "A"],
    ["--positions", "AA", "A"],
    ["--reflecteur", "D", "A"],
    ["--bagues", "0", "1", "1", "A"],
])
def test_cli_refuse_les_reglages_invalides(arguments):
    resultat = lancer_cli(*arguments)
    assert resultat.returncode == 2
    assert resultat.stdout == ""


def test_bague_depuis_texte():
    assert bague_depuis_texte("1") == 1
    assert bague_depuis_texte("26") == 26
    assert bague_depuis_texte("01") == 1
    assert bague_depuis_texte("a") == 1
    assert bague_depuis_texte("Z") == 26
    for invalide in ("0", "27", "AB", ""):
        with pytest.raises(Exception):
            bague_depuis_texte(invalide)


def test_principal_renvoie_zero():
    assert principal(["AAAAA"]) == 0
