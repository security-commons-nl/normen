"""De normwijzer: per maatregel wat de norm vraagt, wat je eraan kunt doen en welk bewijs je dan hebt.

De bouw voegt drie repo's samen. Deze tests toetsen de eigen data (trefwoorden, practices), de regels die
voor de hele commons gelden (geen normtekst, geen taal die compliance belooft) en, als de buur-repo's er zijn,
de gebouwde pagina zelf.
"""
from __future__ import annotations

import importlib.util
import json
import pathlib
import re

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("bouw", ROOT / "tools" / "bouw_normwijzer.py")
bouw = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bouw)

TREFWOORDEN = json.loads((ROOT / "trefwoorden.json").read_text(encoding="utf-8"))
PRACTICES = json.loads((ROOT / "bio-practices.json").read_text(encoding="utf-8"))
# Een trefwoord dat alles vindt, vindt niets. Deze woorden staan in de titel van tientallen stukken.
TE_ALGEMEEN = {"beleid", "informatiebeveiliging", "handreiking", "gemeente", "gemeenten", "bio", "bio2",
               "security", "beveiliging", "privacy officer", "verwerker", "audit", "threat", "classificatie"}


def buren_aanwezig() -> bool:
    try:
        bouw.buur("aanvalspaden")
        bouw.buur("kennisbank")
        return True
    except SystemExit:
        return False


# ----------------------------------------------------------------------------- eigen data
def test_trefwoorden_horen_bij_een_bestaande_maatregel():
    """Een trefwoord bij een nummer dat niet bestaat, doet stil niets."""
    for kader, bestand in (("bio2", None), ("avg", "avg.json"), ("wpg", "wpg.json")):
        if bestand:
            bekend = {m["id"] for m in json.loads((ROOT / bestand).read_text(encoding="utf-8"))["maatregelen"]}
        else:
            # BIO op ISO-niveau: het nummer voor de eerste punt-nul, 5.01.01 wordt 5.1
            bekend = {".".join(str(int(x)) for x in m["id"].split(".")[:2])
                      for m in json.loads((ROOT / "bio2.json").read_text(encoding="utf-8"))["maatregelen"]}
        for nr in TREFWOORDEN[kader]:
            assert nr in bekend, f"{kader} {nr} bestaat niet"


def test_trefwoorden_zijn_niet_te_algemeen():
    for kader in ("bio2", "avg", "wpg"):
        for nr, woorden in TREFWOORDEN[kader].items():
            assert woorden, f"{kader} {nr} heeft een lege lijst"
            for w in woorden:
                assert w.strip().lower() not in TE_ALGEMEEN, f"{kader} {nr}: '{w}' is te algemeen"
                assert len(w.strip()) >= 2


def test_practices_voor_elke_overheidsmaatregel_en_alleen_verwijzingen():
    """Elke overheidsmaatregel uit bio2.json staat erin; per practice alleen code, adres en titel."""
    nummers = {m["id"] for m in json.loads((ROOT / "bio2.json").read_text(encoding="utf-8"))["maatregelen"]}
    assert set(PRACTICES["practices"]) == nummers
    for nr, lijst in PRACTICES["practices"].items():
        for p in lijst:
            assert set(p) == {"code", "url", "titel"}, nr
            assert p["url"].startswith("https://"), nr
    assert sum(1 for v in PRACTICES["practices"].values() if v) >= 90, "BIO Practices gaf eerder 102 maatregelen met practices"


# ----------------------------------------------------------------------------- adressen en trefwoorden
def test_adres_per_maatregel_bij_de_bron():
    assert bouw.norm_url("nist-csf", {"id": "PR.AA-01"}).endswith("element=PR.AA-01")
    assert bouw.norm_url("avg", {"artikel": "AVG art. 32"}).endswith("#art_32")
    assert bouw.norm_url("avg", {"artikel": "AVG art. 5 lid 1 onder f"}).endswith("#art_5")
    assert bouw.norm_url("wpg", {"artikel": "Wpg art. 4a lid 1 t/m 5"}).endswith("artikel=4a")
    assert bouw.norm_url("wpg", {"artikel": "Bijlage 4 bij de handreiking"}) is None
    assert bouw.norm_url("bio2", {"id": "8.5"}) is None


def test_korte_trefwoorden_alleen_als_heel_woord():
    """'soc' mag 'Datawarehouse Sociaal Domein' niet vinden; 'SOC' als woord wel."""
    assert not bouw.raakt(bouw.norm("Datawarehouse Sociaal Domein"), "soc")
    assert bouw.raakt(bouw.norm("Deel een SOC met andere organisaties"), "soc")
    assert bouw.raakt(bouw.norm("Handreiking Logging BIO"), "logging")
    assert bouw.raakt(bouw.norm("Handreiking Bedrijfscontinuïteitsbeheer"), "bedrijfscontinuiteit")
    assert bouw.raakt(bouw.norm("Back-up Plan"), "back-up")
    assert bouw.raakt(bouw.norm("Back-up Plan"), "backup")


# ----------------------------------------------------------------------------- de pagina
SJABLOON = (ROOT / "site" / "normwijzer-sjabloon.html").read_text(encoding="utf-8")


def test_sjabloon_laadt_niets_van_buiten():
    assert "default-src 'none'" in SJABLOON
    assert not re.search(r'<(script|link|img)[^>]+(src|href)="https?://', SJABLOON)


def test_geen_taal_die_compliance_belooft():
    """De relatie is 'levert bewijs voor'; de pagina zegt nooit dat je voldoet of dat iets dekt."""
    tekst = re.sub(r"<[^>]+>", " ", SJABLOON).lower()
    for verboden in ("voldoet aan", "dekt af", "afgedekt", "compliant", "u voldoet", "je voldoet"):
        assert verboden not in tekst, verboden
    assert "levert bewijs voor" in tekst
    assert "beoordeelt de auditor" in tekst


@pytest.fixture(scope="module")
def data():
    if not buren_aanwezig():
        pytest.skip("aanvalspaden en kennisbank staan niet naast normen of in _aanvalspaden/_kennisbank")
    return bouw.verzamel()


def test_alle_maatregelen_van_de_vier_kaders(data):
    tel = {}
    for m in data["maatregelen"]:
        tel[m["k"]] = tel.get(m["k"], 0) + 1
    assert tel == {"bio2": 89, "nist-csf": 106, "avg": 32, "wpg": 36}


def test_elke_bio_maatregel_draagt_zijn_overheidsmaatregelen_met_practices(data):
    bio = [m for m in data["maatregelen"] if m["k"] == "bio2"]
    ids = {o["id"] for m in bio for o in m["overheid"]}
    assert ids == set(PRACTICES["practices"])
    m85 = next(m for m in bio if m["id"] == "8.5")
    assert any(p["url"].startswith("https://www.noraonline.nl/") for o in m85["overheid"] for p in o["practices"])


def test_bewijs_komt_uit_de_mappingen_met_bekende_barrieres(data):
    for m in data["maatregelen"]:
        for r in m["bewijs"]:
            assert r["b"] in data["barrieres"], (m["k"], m["id"], r["b"])
            assert r["sterkte"] in bouw.STERKTE
    assert sum(len(m["bewijs"]) for m in data["maatregelen"]) >= 300, "de mappingen hadden 333 regels"


def test_een_raakvlak_levert_geen_handleiding_op(data):
    """Een raakvlak telt niet als bewijs, dus ook niet als route naar wat je eraan kunt doen."""
    for m in data["maatregelen"]:
        sterk = {r["b"] for r in m["bewijs"] if r["sterkte"] != "raakvlak"}
        for d in m["doen"]:
            assert d["via"] in sterk, (m["k"], m["id"], d["via"])


def test_treffers_op_trefwoord_zijn_gemarkeerd_en_begrensd(data):
    for m in data["maatregelen"]:
        assert len(m["trefwoord"]) <= bouw.MAX_TREFWOORD
        for t in m["trefwoord"]:
            assert t["trefwoord"] is True


def test_andersom_levert_elke_barriere_zijn_normen(data):
    """'Ik doe passkeys': de barriere pr moet naar BIO 8.5 wijzen."""
    pr = data["barrieres"]["pr"]
    assert {"k": "bio2", "id": "8.5", "sterkte": "volledig"} in pr["normen"]


def test_geen_normtekst_in_de_data(data):
    blob = json.dumps(data, ensure_ascii=False)
    for veld in ('"iso_tekst"', '"tekst"', '"overheidsmaatregel_tekst"'):
        assert veld not in blob


def test_de_gebouwde_pagina_is_actueel(data):
    """Wie de bouw aanpast, bouwt de pagina mee; in CI loopt de dagelijkse bouw dit na."""
    uit = ROOT / "normwijzer.html"
    assert uit.exists()
    gebouwd = uit.read_text(encoding="utf-8")
    assert "/*NORMWIJZER_DATA*/" not in gebouwd
    assert '"maatregelen":' in gebouwd
