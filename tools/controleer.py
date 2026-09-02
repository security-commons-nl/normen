#!/usr/bin/env python3
"""Controleert de kaders en herrekent hun vingerafdruk; schrijft kaders.md voor de leesbare versie.

Een dataset zonder bewaking wordt binnen een half jaar een tweede waarheid. Dit script is de bewaking:
elk kaderbestand heeft dezelfde kop, een lijst met records die elk minimaal `id`, `titel` en `thema`
dragen, en een vingerafdruk over de inhoud. Klopt de vingerafdruk niet, dan is er met de hand in de
data gewerkt zonder dit script te draaien, en dat is precies wat opvalt hoort te vallen.

Aanroep:
    python tools/controleer.py            # controleert, herrekent vingerafdrukken, schrijft kaders.md
    python tools/controleer.py --check    # alleen controleren; exit 1 als er iets afwijkt (CI)

Alleen standaardbibliotheek. Het volledige JSON Schema (schema.json) wordt in de tests gevalideerd;
hier staan de controles die ook zonder pip moeten kunnen.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import sys

HIER = pathlib.Path(__file__).resolve().parent
REPO = HIER.parent

# De kaders, in de volgorde van de leesbare versie. `lijst` is de sleutel van de recordlijst; voor de
# beleidsdomeinen van BIO2 is dat geen lijst van maatregelen maar van domeinen.
KADERS = [
    {"bestand": "bio2.json", "lijst": "maatregelen"},
    {"bestand": "bio2-domeinen.json", "lijst": "domeinen"},
    {"bestand": "nist-csf.json", "lijst": "maatregelen"},
    {"bestand": "wpg.json", "lijst": "maatregelen"},
    {"bestand": "avg.json", "lijst": "maatregelen"},
]

KOP_VERPLICHT = ("kader", "titel", "versie", "toelichting", "bron", "vingerafdruk")
BRON_VERPLICHT = ("naam", "versie", "licentie", "opgehaald")
RECORD_VERPLICHT = ("id", "titel")

# Velden die nooit in een kader mogen staan: normtekst van een auteursrechthebbende die niet de
# overheid is. Een test in tests/ bewaakt dit ook; hier staat het zodat --check het zonder pip ziet.
VERBODEN_VELDEN = {"iso_maatregel", "iso_tekst", "iso"}


def vingerafdruk(records: list[dict]) -> str:
    """Sha256 over de inhoud, niet over de bytes: onafhankelijk van platform, regeleindes en volgorde
    van sleutels. Dezelfde regel als in de handelingsperspectief-kopieën van de commons."""
    ruw = json.dumps(records, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(ruw.encode("utf-8")).hexdigest()


def lees(bestand: str) -> dict:
    pad = REPO / bestand
    if not pad.is_file():
        sys.exit(f"{bestand} ontbreekt")
    return json.loads(pad.read_text(encoding="utf-8"))


def controleer_kader(kader: dict, data: dict) -> list[str]:
    fouten: list[str] = []
    naam = kader["bestand"]
    for veld in KOP_VERPLICHT:
        if veld not in data:
            fouten.append(f"{naam}: kopveld '{veld}' ontbreekt")
    bron = data.get("bron")
    if not isinstance(bron, dict):
        fouten.append(f"{naam}: 'bron' moet een object zijn")
    else:
        for veld in BRON_VERPLICHT:
            if not bron.get(veld):
                fouten.append(f"{naam}: bron.{veld} ontbreekt of is leeg")
    records = data.get(kader["lijst"])
    if not isinstance(records, list) or not records:
        fouten.append(f"{naam}: lijst '{kader['lijst']}' ontbreekt of is leeg")
        return fouten
    gezien: set[str] = set()
    for i, record in enumerate(records):
        for veld in RECORD_VERPLICHT:
            if not record.get(veld):
                fouten.append(f"{naam}[{i}]: veld '{veld}' ontbreekt")
        if record.get("id") in gezien:
            fouten.append(f"{naam}: id '{record.get('id')}' komt twee keer voor")
        gezien.add(record.get("id"))
        verboden = VERBODEN_VELDEN & set(record)
        if verboden:
            fouten.append(f"{naam}[{i}]: verboden veld(en) {sorted(verboden)}: normtekst van een "
                          "auteursrechthebbende hoort hier niet")
    if data.get("vingerafdruk") != vingerafdruk(records):
        fouten.append(f"{naam}: vingerafdruk klopt niet met de inhoud; draai tools/controleer.py")
    return fouten


def kaders_md(alles: list[tuple[dict, dict]]) -> str:
    """De leesbare versie: per kader de kop en een tabel met id, titel en thema."""
    regels = ["# Wat er in de kaders zit", "",
              "Gegenereerd door `tools/controleer.py` uit de JSON-bestanden in deze repo; wijzig de JSON, "
              "niet dit bestand. Per kader staat de herkomst erbij; de vingerafdruk is de sha256 over de "
              "inhoud van de lijst.", ""]
    for kader, data in alles:
        records = data[kader["lijst"]]
        bron = data["bron"]
        regels += [f"## {data['titel']} (`{kader['bestand']}`)", "",
                   data["toelichting"], "",
                   f"- **Bron:** {bron['naam']}, {bron['versie']}" +
                   (f", [link]({bron['url']})" if bron.get("url") else ""),
                   f"- **Licentie van de bron:** {bron['licentie']}",
                   f"- **Opgehaald:** {bron['opgehaald']}",
                   f"- **Records:** {len(records)} · **Vingerafdruk:** `{data['vingerafdruk'][:16]}`", ""]
        heeft_thema = any(r.get("thema") for r in records)
        kop = "| Id | Titel | Thema |" if heeft_thema else "| Id | Titel |"
        regels += [kop, "|---|---|---|" if heeft_thema else "|---|---|"]
        for r in records:
            titel = str(r["titel"]).replace("|", "\\|").replace("\n", " ")
            rij = f"| {r['id']} | {titel} |"
            if heeft_thema:
                rij += f" {str(r.get('thema', '')).replace('|', '/')} |"
            regels.append(rij)
        regels.append("")
    return "\n".join(regels).rstrip() + "\n"


def main(argv: list[str]) -> int:
    alleen_check = "--check" in argv
    alles: list[tuple[dict, dict]] = []
    fouten: list[str] = []
    for kader in KADERS:
        data = lees(kader["bestand"])
        if not alleen_check:
            data["vingerafdruk"] = vingerafdruk(data.get(kader["lijst"], []))
            (REPO / kader["bestand"]).write_bytes(
                (json.dumps(data, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))
        fouten += controleer_kader(kader, data)
        alles.append((kader, data))

    if fouten:
        print("\n".join(fouten))
        print(f"\n{len(fouten)} probleem/problemen.")
        return 1

    md = kaders_md(alles)
    doel = REPO / "kaders.md"
    if alleen_check:
        if not doel.is_file() or doel.read_text(encoding="utf-8") != md:
            print("kaders.md loopt achter op de JSON; draai tools/controleer.py")
            return 1
    else:
        doel.write_bytes(md.encode("utf-8"))
    for kader, data in alles:
        print(f"  {kader['bestand']:22} {len(data[kader['lijst']]):4} records  {data['vingerafdruk'][:12]}")
    print("kaders in orde" + (" (check)" if alleen_check else "; kaders.md geschreven"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
