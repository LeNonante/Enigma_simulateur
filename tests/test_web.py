"""Tests de l'API web (web.py), sans navigateur ni serveur : client de test Flask."""

import pytest

flask = pytest.importorskip("flask")

import web  # noqa: E402  (importé après importorskip : Flask est une dépendance optionnelle)


@pytest.fixture()
def client():
    """Un visiteur neuf. Les sessions vivent en mémoire : on repart de zéro."""
    web._sessions.clear()
    return web.app.test_client()


def reglages(**champs):
    """Réglages valides, surchargeables champ par champ."""
    base = {"reflecteur": "B", "rotors": ["I", "II", "III"], "bagues": [1, 1, 1], "connexions": ""}
    base.update(champs)
    return base


# ==========================================================================
# Pages
# ==========================================================================
def test_accueil(client):
    reponse = client.get("/")
    assert reponse.status_code == 200
    assert "Enigma" in reponse.get_data(as_text=True)


def test_sante(client):
    assert client.get("/sante").data == b"ok"


def test_etat_initial(client):
    donnees = client.get("/api/machine").get_json()
    assert donnees["positions"] == "AAA"
    assert donnees["depart"] == "AAA"
    assert donnees["entree"] == donnees["sortie"] == ""
    assert donnees["reglages"] == {"reflecteur": "B", "rotors": ["I", "II", "III"],
                                   "bagues": [1, 1, 1], "connexions": ""}
    assert donnees["svg"].startswith("<svg")
    assert donnees["detail"]


# ==========================================================================
# Touches et textes
# ==========================================================================
def test_touche_avance_les_rotors(client):
    donnees = client.post("/api/machine/touche", json={"lettre": "A"}).get_json()
    assert donnees["positions"] == "AAB"
    assert donnees["lampe"] == "B"
    assert donnees["entree"] == "A"
    assert donnees["sortie"] == "B"


@pytest.mark.parametrize("lettre", ["", "AB", "1", None, 7, ["A"]])
def test_touche_invalide(client, lettre):
    reponse = client.post("/api/machine/touche", json={"lettre": lettre})
    assert reponse.status_code == 400
    assert "Touche invalide" in reponse.get_json()["erreur"]


def test_texte_nettoie_les_accents(client):
    donnees = client.post("/api/machine/texte", json={"texte": "Bonjour, l'été !"}).get_json()
    assert donnees["entree"] == "BONJOURLETE"
    assert len(donnees["sortie"]) == len(donnees["entree"])


def test_texte_null_ne_tape_rien(client):
    donnees = client.post("/api/machine/texte", json={"texte": None}).get_json()
    assert donnees["entree"] == ""
    assert donnees["positions"] == "AAA"


@pytest.mark.parametrize("texte", [12, ["A"], {"a": 1}])
def test_texte_mauvais_type_refuse(client, texte):
    reponse = client.post("/api/machine/texte", json={"texte": texte})
    assert reponse.status_code == 400
    assert "chaîne" in reponse.get_json()["erreur"]


def test_corps_json_qui_n_est_pas_un_objet(client):
    """Un corps [1] levait une AttributeError, donc une erreur 500."""
    reponse = client.post("/api/machine/reglages", data="[1]", content_type="application/json")
    assert reponse.status_code == 400
    assert reponse.is_json
    assert "objet JSON" in reponse.get_json()["erreur"]


def test_corps_vide_accepte(client):
    assert client.post("/api/machine/nouveau", json={}).status_code == 200


# ==========================================================================
# Réglages
# ==========================================================================
def test_reglages_valides(client):
    donnees = client.post("/api/machine/reglages", json=reglages(
        reflecteur="C", rotors=["IV", "V", "II"], bagues=[4, 12, 20],
        connexions="AM FI NV")).get_json()
    assert donnees["reglages"] == {"reflecteur": "C", "rotors": ["IV", "V", "II"],
                                   "bagues": [4, 12, 20], "connexions": "AM FI NV"}
    assert donnees["depart"] == "AAA"


def test_reglages_conservent_la_position(client):
    client.post("/api/machine/touche", json={"lettre": "A"})
    donnees = client.post("/api/machine/reglages", json=reglages(bagues=[2, 2, 2])).get_json()
    assert donnees["positions"] == "AAB"
    assert donnees["depart"] == "AAB"


def test_connexions_null_veut_dire_aucun_cable(client):
    donnees = client.post("/api/machine/reglages", json=reglages(connexions=None)).get_json()
    assert donnees["reglages"]["connexions"] == ""


@pytest.mark.parametrize("champs", [
    dict(rotors=["I", "I", "III"]),
    dict(rotors=["I", "II"]),
    dict(rotors=[]),
    dict(rotors="III"),
    dict(rotors=["I", "II", "IX"]),
    dict(reflecteur="Z"),
    dict(reflecteur=None),
    dict(bagues=[0, 1, 1]),
    dict(bagues=[27, 1, 1]),
    dict(bagues=[1.9, 2, 3]),
    dict(bagues=["1", 2, 3]),
    dict(bagues=[1, 1]),
    dict(connexions="AM AM"),
    dict(connexions="ABC"),
    dict(connexions=12),
])
def test_reglages_impossibles_refuses(client, champs):
    reponse = client.post("/api/machine/reglages", json=reglages(**champs))
    assert reponse.status_code == 400, reponse.get_json()
    assert reponse.get_json()["erreur"]


def test_reglages_refuses_ne_cassent_pas_la_machine(client):
    client.post("/api/machine/reglages", json=reglages(bagues=[0, 1, 1]))
    assert client.get("/api/machine").status_code == 200
    assert client.get("/api/machine").get_json()["reglages"]["bagues"] == [1, 1, 1]


# ==========================================================================
# Rotors à la main
# ==========================================================================
def test_tourner_un_rotor(client):
    donnees = client.post("/api/machine/tourner", json={"rotor": 0, "sens": -1}).get_json()
    assert donnees["positions"] == "ZAA"
    assert donnees["depart"] == "ZAA"


@pytest.mark.parametrize("corps", [
    {"rotor": 3, "sens": 1},
    {"rotor": -1, "sens": 1},
    {"rotor": 0, "sens": 0},
    {"rotor": 0, "sens": 2},
    {"rotor": 0, "sens": 1.0},
    {"rotor": 0, "sens": "1"},
    {"rotor": True, "sens": True},
    {"rotor": False, "sens": -1},
    {"sens": 1},
    {},
])
def test_tourner_refuse_les_parametres_invalides(client, corps):
    assert client.post("/api/machine/tourner", json=corps).status_code == 400


def test_un_flottant_ne_brique_pas_la_session(client):
    """« sens »: 1.0 laissait la position du rotor en flottant : 500 à vie."""
    assert client.post("/api/machine/tourner", json={"rotor": 0, "sens": 1.0}).status_code == 400
    assert client.get("/api/machine").status_code == 200
    assert client.post("/api/machine/touche", json={"lettre": "A"}).status_code == 200
    assert client.get("/api/machine").get_json()["positions"] == "AAB"


def test_nouveau_message(client):
    client.post("/api/machine/tourner", json={"rotor": 0, "sens": 1})
    client.post("/api/machine/texte", json={"texte": "ABC"})
    donnees = client.post("/api/machine/nouveau", json={}).get_json()
    assert donnees["positions"] == "BAA"
    assert donnees["entree"] == donnees["sortie"] == ""


# ==========================================================================
# Clics dans le schéma
# ==========================================================================
def test_clic_sur_le_clavier_du_schema(client):
    """Le clic est rejoué côté serveur sur le même dessin (tag + ordonnée)."""
    donnees = client.post("/api/machine/clic",
                          json={"tag": "schema14_8touche", "y": 45}).get_json()
    assert donnees["entree"] == "A"
    assert donnees["positions"] == "AAB"


@pytest.mark.parametrize("corps", [{"tag": "inconnu", "y": 45}, {"y": 45}, {"tag": ""},
                                   {"tag": 12, "y": 45}])
def test_clic_hors_touche(client, corps):
    assert client.post("/api/machine/clic", json=corps).status_code == 400


# ==========================================================================
# Chapitres
# ==========================================================================
def test_chapitres(client):
    for n in range(10):
        reponse = client.get(f"/api/chapitres/{n}")
        assert reponse.status_code == 200, n
        donnees = reponse.get_json()
        assert donnees["titre"]
        assert donnees["svg"].startswith("<svg")
        assert isinstance(donnees["boutons"], list)


def test_chapitre_inconnu(client):
    assert client.get("/api/chapitres/10").status_code == 404
    assert client.get("/api/chapitres/999").status_code == 404


def test_bouton_de_chapitre(client):
    """Le premier chapitre qui a des boutons les fait tous fonctionner."""
    for n in range(10):
        nombres = client.get(f"/api/chapitres/{n}").get_json()["boutons"]
        if nombres:
            for k in range(len(nombres)):
                assert client.post(f"/api/chapitres/{n}/bouton", json={"index": k}).status_code == 200
            break
    else:                                   # pragma: no cover - les chapitres en ont
        pytest.fail("aucun chapitre avec des boutons")


@pytest.mark.parametrize("index", [-1, 99, "0", 1.0, True, None])
def test_bouton_invalide(client, index):
    for n in range(10):
        if client.get(f"/api/chapitres/{n}").get_json()["boutons"]:
            reponse = client.post(f"/api/chapitres/{n}/bouton", json={"index": index})
            assert reponse.status_code == 400
            return


def test_bouton_de_chapitre_inconnu(client):
    assert client.post("/api/chapitres/99/bouton", json={"index": 0}).status_code == 404


# ==========================================================================
# Sessions
# ==========================================================================
def test_deux_visiteurs_ne_partagent_pas_leur_machine(client):
    autre = web.app.test_client()
    client.post("/api/machine/texte", json={"texte": "AAAAA"})
    assert client.get("/api/machine").get_json()["entree"] == "AAAAA"
    assert autre.get("/api/machine").get_json()["entree"] == ""
    assert autre.get("/api/machine").get_json()["positions"] == "AAA"
