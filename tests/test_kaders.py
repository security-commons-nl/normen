"""De kaders: kloppen ze, en zijn ze nog wat er is overgenomen.

Een dataset is alleen bruikbaar als hij klopt en als een wijziging opvalt. Deze tests bewaken drie
dingen: de vorm (het schema), de inhoud (aantallen, unieke ids, geen normtekst van een
auteursrechthebbende buiten de overheid) en de herkomst (BIO2 volgt
de telling van versie 1.3). Faalt hier iets, repareer dan de JSON en draai
tools/controleer.py; nooit de test.
"""
from __future__ import annotations

import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import controleer  # noqa: E402

VERWACHT = {
    "bio2.json": ("maatregelen", 157),
    "bio2-domeinen.json": ("domeinen", 15),
    "nist-csf.json": ("maatregelen", 106),
    "wpg.json": ("maatregelen", 36),
    "avg.json": ("maatregelen", 32),
}

# Per kader de velden die een record mag dragen. Alles daarbuiten is een fout, en `iso_maatregel`
# in het bijzonder: ISO-tekst (NEN/ISO) en de tekst van de overheidsmaatregel (CIP, CC BY-NC-SA)
# publiceren wij niet.
VELDEN = {
    "bio2.json": {"id", "titel", "thema", "soort"},
    "nist-csf.json": {"id", "titel", "thema"},
    "wpg.json": {"id", "titel", "artikel", "thema", "kern"},
    "avg.json": {"id", "titel", "artikel", "thema", "kern"},
}


def lees(naam: str) -> dict:
    return json.loads((ROOT / naam).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def kaders() -> dict[str, dict]:
    return {naam: lees(naam) for naam in VERWACHT}


@pytest.fixture(scope="module")
def schema() -> dict:
    return json.loads((ROOT / "schema.json").read_text(encoding="utf-8"))


def test_elk_kader_voldoet_aan_het_schema(kaders, schema):
    jsonschema = pytest.importorskip("jsonschema", reason="jsonschema niet beschikbaar")
    validator = jsonschema.Draft202012Validator(schema)
    for naam, data in kaders.items():
        fouten = sorted(validator.iter_errors(data), key=lambda e: list(e.path))
        assert not fouten, f"{naam}: " + "; ".join(
            f"{'/'.join(str(p) for p in e.path) or 'wortel'}: {e.message[:120]}" for e in fouten[:5])


def test_aantallen(kaders):
    for naam, (lijst, aantal) in VERWACHT.items():
        assert len(kaders[naam][lijst]) == aantal, naam


def test_ids_uniek(kaders):
    for naam, (lijst, _) in VERWACHT.items():
        ids = [r["id"] for r in kaders[naam][lijst]]
        dubbel = {i for i in ids if ids.count(i) > 1}
        assert not dubbel, f"{naam}: dubbele ids {sorted(dubbel)}"


def test_geen_iso_tekst(kaders):
    """Nummers, titels en thema's mogen; normtekst van NEN/ISO niet. Ook niet onder een andere naam."""
    for naam, toegestaan in VELDEN.items():
        for record in kaders[naam]["maatregelen"]:
            extra = set(record) - toegestaan
            assert not extra, f"{naam} {record['id']}: onverwachte velden {sorted(extra)}"
    # Het woord dat de ISO-tekst in de cisochat-dataset markeerde mag nergens meer voorkomen.
    for naam in VERWACHT:
        tekst = (ROOT / naam).read_text(encoding="utf-8")
        for verboden in ("iso_maatregel", "overheidsmaatregel", "risico"):
            assert f'"{verboden}"' not in tekst, f"{naam}: veld {verboden}"


def test_vingerafdruk_klopt(kaders):
    for naam, (lijst, _) in VERWACHT.items():
        assert kaders[naam]["vingerafdruk"] == controleer.vingerafdruk(kaders[naam][lijst]), naam


def test_bron_compleet(kaders):
    for naam, data in kaders.items():
        for veld in ("naam", "versie", "licentie", "opgehaald"):
            assert data["bron"].get(veld), f"{naam}: bron.{veld} ontbreekt"
        assert data["versie"], f"{naam}: versie ontbreekt"


def test_bio2_domeinen_verwijzen_naar_bestaande_ids(kaders):
    bekend = {m["id"] for m in kaders["bio2.json"]["maatregelen"]}
    for domein in kaders["bio2-domeinen.json"]["domeinen"]:
        onbekend = [c for c in domein["controls"] if c not in bekend]
        assert not onbekend, f"{domein['id']}: onbekende controls {onbekend}"


def test_elke_overheidsmaatregel_in_precies_een_domein(kaders):
    """Wie beleid per domein schrijft, moet erop kunnen rekenen dat geen overheidsmaatregel tussen de domeinen
    door valt. Maatregelen met alleen ISO 27002 mogen in een domein staan, maar hoeven niet."""
    overheid = {m["id"] for m in kaders["bio2.json"]["maatregelen"] if m["soort"] == "overheid"}
    alle = [c for d in kaders["bio2-domeinen.json"]["domeinen"] for c in d["controls"]]
    dubbel = {c for c in alle if alle.count(c) > 1}
    assert not dubbel, f"in meer dan een domein: {sorted(dubbel)}"
    assert not overheid - set(alle), f"in geen domein: {sorted(overheid - set(alle))}"


def test_bio2_volgt_versie_1_3(kaders):
    """BIO 2.0 versie 1.3 telt in deel 2 117 overheidsmaatregelen en 40 ISO-beheersmaatregelen zonder
    overheidsmaatregel. Wat in 1.3 vervallen of verplaatst is, staat er niet meer in. Wijkt dit af, dan is
    de dataset opnieuw gegenereerd uit een andere versie: pas dan deze test aan, met de reden in de commit."""
    bio2 = kaders["bio2.json"]
    assert "v1.3" in bio2["versie"]
    soorten = [m["soort"] for m in bio2["maatregelen"]]
    assert soorten.count("overheid") == 117 and soorten.count("alleen-iso") == 40
    ids = {m["id"] for m in bio2["maatregelen"]}
    for weg in ("5.04.02", "5.04.03", "5.21.01", "5.24.06", "5.25.01", "5.26.01", "5.35.01", "7.01.01",
                "8.08.06", "8.24.03"):
        assert weg not in ids, f"{weg} is in versie 1.3 vervallen of verplaatst"
    assert len({i.rsplit(".", 1)[0] for i in ids}) == 93, "elke ISO 27002-beheersmaatregel heeft een nummer"


def test_kaders_md_is_actueel():
    """De leesbare versie wordt gegenereerd; loopt hij achter, dan liegt de site."""
    alles = [(k, lees(k["bestand"])) for k in controleer.KADERS]
    verwacht = controleer.kaders_md(alles)
    assert (ROOT / "kaders.md").read_text(encoding="utf-8") == verwacht


def test_controleer_check_slaagt():
    import subprocess
    uit = subprocess.run([sys.executable, "tools/controleer.py", "--check"], cwd=ROOT,
                         capture_output=True, text=True, encoding="utf-8")
    assert uit.returncode == 0, uit.stdout + uit.stderr
