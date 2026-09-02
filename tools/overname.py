#!/usr/bin/env python3
"""De eenmalige overname van de kaders uit cisochat en aanvalspaden, 02-09-2026.

Dit script bestaat om de herkomst reproduceerbaar te maken: draai het opnieuw op dezelfde commits en je
krijgt dezelfde bestanden. Na de overname is `normen` de bron; een latere versie van een kader komt
binnen via de generator van dat kader (tools/genereer_*.py), niet via dit script.

Wat het doet:
- `bio2.json`: de 148 overheidsmaatregelen uit `cisochat/data/bio2.json`, alleen nummer, titel en thema
  (`iv_standaard`). De ISO-tekst (NEN/ISO) en de tekst van de overheidsmaatregel en het risico (CIP,
  CC BY-NC-SA 4.0) gaan er allebei uit.
- `bio2-domeinen.json`: de vijftien beleidsdomeinen uit `cisochat/data/domeinen.json`.
- `nist-csf.json`, `wpg.json`, `avg.json`: uit `aanvalspaden/mappingen/bronnen/`, in het schema van
  hier gezet (`versie` in de kop, `bron.opgehaald` in plaats van `peildatum`, `bron.licentie` ingevuld
  waar die ontbrak).
- `tests/fixtures/cisochat-bio2-<commit>.json`: de overname zonder ISO-veld, zodat een test kan bewijzen
  dat de dataset niet stil is veranderd tussen overname en nu.

Aanroep, vanuit de werkmap met de andere repo's ernaast:
    python tools/overname.py
Daarna:
    python tools/controleer.py     (vingerafdrukken en kaders.md)

Alleen standaardbibliotheek.
"""
from __future__ import annotations

import datetime as dt
import json
import pathlib
import subprocess
import sys

HIER = pathlib.Path(__file__).resolve().parent
REPO = HIER.parent
WERKMAP = REPO.parent
CISOCHAT = WERKMAP / "cisochat"
BRONNEN = WERKMAP / "aanvalspaden" / "mappingen" / "bronnen"
VANDAAG = dt.date.today().isoformat()

LICENTIE_ALS_ONBEKEND = {
    "nist-csf": "Publiek domein (werk van de Amerikaanse federale overheid); de Engelse formuleringen "
                "zijn die van NIST",
    "wpg": "Eigen samenvattingen onder EUPL-1.2; het toetsingskader zelf staat in de NOREA Handreiking "
           "Privacy audit Wpg en is van NOREA",
    "avg": "Wettekst, Verordening (EU) 2016/679, vrij te gebruiken; de selectie en de samenvattingen "
           "onder EUPL-1.2",
}


def commit_van(repo: pathlib.Path, bestand: str) -> str:
    """De laatste commit waarin het bestand in die repo is gewijzigd; 'onbekend' zonder git."""
    try:
        uit = subprocess.run(["git", "log", "-1", "--format=%H", "--", bestand],
                             cwd=repo, capture_output=True, text=True, check=True)
        return uit.stdout.strip() or "onbekend"
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "onbekend"


def schrijf(naam: str, data: dict) -> None:
    data.setdefault("vingerafdruk", "0" * 64)   # controleer.py rekent hem uit
    (REPO / naam).write_bytes((json.dumps(data, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))
    lijst = data.get("maatregelen") or data.get("domeinen")
    print(f"  {naam:22} {len(lijst):4} records")


def bio2() -> None:
    pad = CISOCHAT / "data" / "bio2.json"
    if not pad.is_file():
        sys.exit(f"bron ontbreekt: {pad}")
    oud = json.loads(pad.read_text(encoding="utf-8"))
    commit = commit_van(CISOCHAT, "data/bio2.json")
    maatregelen = []
    for c in oud["controls"]:
        # Alleen nummer, titel en thema. De tekst van de overheidsmaatregel en het risico zijn van het
        # CIP (CC BY-NC-SA 4.0) en gaan niet mee; wie de tekst wil, gaat naar de bron.
        maatregelen.append({
            "id": c["id"],
            "titel": c["titel"].strip(),
            "thema": c.get("iv_standaard", "").strip(),
        })

    data = {
        "kader": "bio2",
        "titel": "BIO 2.0",
        "versie": oud.get("versie", "onbekend"),
        "toelichting": (
            "De 148 overheidsmaatregelen van de Baseline Informatiebeveiliging Overheid 2.0, genummerd "
            "volgens de structuur van ISO 27002:2022 (5.01.01 hoort bij ISO-maatregel 5.1). Per maatregel "
            "het nummer, de titel en het thema (de IV-standaard). De tekst van de overheidsmaatregel staat er "
            "niet bij: het CIP publiceert onder CC BY-NC-SA 4.0, en de ISO-tekst eronder is van NEN/ISO. "
            "Wie de tekst nodig heeft, gaat naar de bron; het nummer hier is ook het nummer daar."),
        "bron": {
            "naam": oud.get("bron", "Centrum Informatiebeveiliging en Privacybescherming (CIP)"),
            "versie": oud.get("versie", "onbekend"),
            "url": "https://www.cip-overheid.nl/",
            "licentie": "CC BY-NC-SA 4.0 (CIP). Daarom staan hier alleen nummers, titels en thema's; de "
                        "tekst van de overheidsmaatregelen en de ISO-tekst zijn niet opgenomen",
            "opgehaald": VANDAAG,
            "herkomst": f"eenmalig overgenomen uit security-commons-nl/cisochat, data/bio2.json "
                        f"(toelichting daar: {oud.get('toelichting', '').strip()})",
            "commit": commit,
        },
        "tweede_etiket": {
            "kader": "ISO 27001:2022",
            "toelichting": "BIO 2.0 volgt de nummering van ISO 27002:2022, bijlage A van ISO 27001:2022. "
                           "Het nummer van een maatregel hier is dus ook het ISO-nummer. De ISO-tekst "
                           "staat er niet bij.",
        },
        "maatregelen": maatregelen,
    }
    schrijf("bio2.json", data)

    fixture_map = REPO / "tests" / "fixtures"
    fixture_map.mkdir(parents=True, exist_ok=True)
    fixture = {"herkomst": "security-commons-nl/cisochat, data/bio2.json", "commit": commit,
               "maatregelen": maatregelen}
    (fixture_map / f"cisochat-bio2-{commit[:12]}.json").write_bytes(
        (json.dumps(fixture, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))
    print(f"  fixture geschreven voor commit {commit[:12]}")


def bio2_domeinen() -> None:
    pad = CISOCHAT / "data" / "domeinen.json"
    if not pad.is_file():
        sys.exit(f"bron ontbreekt: {pad}")
    oud = json.loads(pad.read_text(encoding="utf-8"))
    data = {
        "kader": "bio2-domeinen",
        "titel": "BIO 2.0, beleidsdomeinen",
        "versie": oud.get("versie", "1.0"),
        "toelichting": (
            "Vijftien beleidsdomeinen die de overheidsmaatregelen van BIO 2.0 groeperen naar het "
            "beleidsdocument waarin ze thuishoren, van informatiebeveiligingsbeleid tot leveranciersbeheer. "
            "Een afgeleide van bio2.json, bedoeld voor wie beleid schrijft of toetst; elk control-id "
            "verwijst naar een maatregel daar. " + oud.get("toelichting", "").strip()),
        "bron": {
            "naam": "Security Commons NL, afgeleid van BIO 2.0 (CIP)",
            "versie": oud.get("versie", "1.0"),
            "licentie": "EUPL-1.2 (de indeling); de maatregelen zelf zijn van het CIP",
            "opgehaald": VANDAAG,
            "herkomst": "eenmalig overgenomen uit security-commons-nl/cisochat, data/domeinen.json",
            "commit": commit_van(CISOCHAT, "data/domeinen.json"),
        },
        "domeinen": [{"id": d["id"], "titel": d["titel"].strip(), "omschrijving": d["omschrijving"].strip(),
                      "controls": list(d["controls"])} for d in oud["domeinen"]],
    }
    schrijf("bio2-domeinen.json", data)


def uit_aanvalspaden(kader: str) -> None:
    pad = BRONNEN / f"{kader}.json"
    if not pad.is_file():
        sys.exit(f"bron ontbreekt: {pad}")
    oud = json.loads(pad.read_text(encoding="utf-8"))
    bron = dict(oud.get("bron") or {})
    if "peildatum" in bron:
        bron["opgehaald"] = bron.pop("peildatum")
    bron.setdefault("opgehaald", VANDAAG)
    if not bron.get("licentie"):
        bron["licentie"] = LICENTIE_ALS_ONBEKEND[kader]
        print(f"  {kader}: licentie ingevuld (ontbrak in de bron)")
    bron["herkomst"] = f"eenmalig overgenomen uit security-commons-nl/aanvalspaden, mappingen/bronnen/{kader}.json"
    bron["commit"] = commit_van(WERKMAP / "aanvalspaden", f"mappingen/bronnen/{kader}.json")
    data = {
        "kader": oud["kader"],
        "titel": oud["titel"],
        "versie": oud.get("versie") or bron.get("versie") or "onbekend",
        "toelichting": oud["toelichting"].strip(),
        "bron": bron,
    }
    if oud.get("tweede_etiket"):
        data["tweede_etiket"] = oud["tweede_etiket"]
    data["maatregelen"] = oud["maatregelen"]
    schrijf(f"{kader}.json", data)


def main() -> int:
    print("overname:")
    bio2()
    bio2_domeinen()
    for kader in ("nist-csf", "wpg", "avg"):
        uit_aanvalspaden(kader)
    print("klaar; draai nu python tools/controleer.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
