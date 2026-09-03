"""De gebouwde pagina: wat de leesversie belooft, moet er ook staan.

Aanleiding (03-09-2026): op https://security-commons-nl.github.io/normen/ gaven zeven links een 404,
waaronder alle vijf de normbronnen en het schema. De README verwijst ernaar als bestand naast zich, en
de build zette die verwijzing om naar een pad op Pages zonder het bestand mee te kopieren. Juist hier
pijnlijk: die JSON-bestanden zijn het product dat de pagina aanbiedt.

Deze test dekt beide kanten: de datasets staan als download in dist, en een relatieve link naar iets
dat niet meegaat, wijst naar GitHub in plaats van naar het niets.
"""
from __future__ import annotations

import json
import pathlib
import re
import subprocess

import pytest

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATASETS = ["bio2.json", "bio2-domeinen.json", "nist-csf.json", "wpg.json", "avg.json",
            "schema.json"]


@pytest.fixture(scope="module")
def gebouwd() -> str:
    subprocess.run(["node", "site/build.mjs"], cwd=ROOT, check=True, capture_output=True)
    return (ROOT / "dist" / "index.html").read_text(encoding="utf-8")


def test_datasets_gaan_mee_als_download(gebouwd):
    """Elke normbron staat als bestand in dist; anders is de downloadknop een dood eind."""
    for naam in DATASETS:
        assert (ROOT / "dist" / naam).exists(), f"{naam} niet gekopieerd naar dist"
        assert f'href="{naam}"' in gebouwd, f"{naam} wordt niet aangeboden op de pagina"
        json.loads((ROOT / "dist" / naam).read_text(encoding="utf-8"))


def test_datasets_staan_in_de_config():
    """De lijst in site/config.json is de bron; loopt hij achter, dan mist er een download."""
    config = json.loads((ROOT / "site" / "config.json").read_text(encoding="utf-8"))
    assert sorted(config.get("assets", [])) == sorted(DATASETS)


def test_geen_relatieve_link_zonder_bestand(gebouwd):
    """Een relatieve link mag alleen blijven staan als het bestand in dist ligt.

    Alles wat niet meegaat, hoort naar GitHub te wijzen. Deze regel is de sluitregel in
    site/build.mjs; zonder hem lopen verwijzingen naar bestanden in de repo dood op Pages.
    """
    relatief = [h for h in re.findall(r'href="([^"]+)"', gebouwd)
                if not h.startswith(("http://", "https://", "#", "/", "mailto:"))]
    for pad in sorted(set(relatief)):
        assert (ROOT / "dist" / pad).exists(), f"dode link op de pagina: {pad}"


def test_bestanden_in_de_repo_wijzen_naar_github(gebouwd):
    """CONTRIBUTING.md en LICENSE horen op GitHub, niet op Pages."""
    for naam in ("CONTRIBUTING.md", "LICENSE"):
        assert f'href="{naam}"' not in gebouwd, f"{naam} wijst naar Pages en bestaat daar niet"
        assert f"/blob/main/{naam}" in gebouwd, f"{naam} wijst niet naar GitHub"
