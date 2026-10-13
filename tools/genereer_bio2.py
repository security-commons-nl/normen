#!/usr/bin/env python3
"""Genereert bio2.json uit de pdf van BIO 2.0 versie 1.3 van het CIP.

Draaien:  python tools/genereer_bio2.py <pad-naar-bio2-pdf>            (laat de telling zien, schrijft niets)
          python tools/genereer_bio2.py <pad-naar-bio2-pdf> --schrijf  (schrijft bio2.json)
Daarna:   python tools/controleer.py

Waarom: de eerste versie van bio2.json (02-09-2026) kwam uit cisochat en volgde de nummering van versie 1.2.
Versie 1.3 (9 januari 2026) heeft maatregelen verplaatst, laten vervallen en toegevoegd. Dit script leest
deel 2 van de pdf zelf en neemt elk nummer over dat in 1.3 geldt:

- `soort: overheid`: een nummer met een eigen overheidsmaatregel (117 in versie 1.3);
- `soort: alleen-iso`: "Geen overheidsmaatregel"; dan geldt de ISO-beheersmaatregel zelf (40).

Nummers met "Vervallen", "Verplaatst naar" of "Zie overheidsmaatregel" gaan er niet in; welke dat zijn staat
in `bron.let_op`. Van de pdf neemt het script alleen de nummers en hun soort. De tekst van de
overheidsmaatregel (CIP, CC BY-NC-SA 4.0) gaat er niet in; de titel is die van de ISO-beheersmaatregel en
het thema de IV-standaard, beide uit de vorige bio2.json per ISO-nummer, met NIEUWE_ISO voor de vier
ISO-maatregelen die daar nog geen nummer hadden.

Vraagt pypdf (pip install pypdf); de rest is standaardbibliotheek. De pdf zit niet in de repo: hij staat
op de site van het CIP en in de bijlagen van aanbestedingen; de sha256 staat in `bron.herkomst`.
"""
from __future__ import annotations

import collections
import hashlib
import json
import pathlib
import re
import sys
from datetime import date

ROOT = pathlib.Path(__file__).resolve().parent.parent
UIT = ROOT / "bio2.json"
VERSIE = "BIO2 v1.3 definitief - 9 januari 2026"

# ISO-beheersmaatregelen die in de vorige dataset geen nummer hadden: titel en thema.
NIEUWE_ISO = {
    "5.37": ("Gedocumenteerde bedieningsprocedures", "Wijzigingsbeheer"),
    "6.1": ("Screening", "Screening, bewustzijn & opleiding"),
    "7.3": ("Beveiligen van kantoren, ruimten en faciliteiten", "Fysieke toegang & beveiliging"),
    "7.4": ("Monitoren van de fysieke beveiliging", "Fysieke toegang & beveiliging"),
}


def iso(nummer: str) -> str:
    """5.01.02 -> 5.1"""
    a, b, _ = nummer.split(".")
    return f"{int(a)}.{int(b)}"


def lees_deel2(pdf: pathlib.Path) -> dict[str, str]:
    import pypdf
    tekst = "\n".join(p.extract_text() for p in pypdf.PdfReader(pdf).pages)
    deel2 = tekst[tekst.index("DEEL 2"):]
    stukken = re.split(r"(?m)^\s*([5-8]\.\d{2}\.\d{2})\b", deel2)
    nummers: dict[str, str] = {}
    for i in range(1, len(stukken), 2):
        # Een maatregel die over een paginagrens loopt, komt twee keer langs; de eerste is het begin.
        nummers.setdefault(stukken[i], " ".join(stukken[i + 1].split()))
    return nummers


def soort(tekst: str) -> str | None:
    if tekst.startswith("Geen overheidsmaatregel"):
        return "alleen-iso"
    if re.match(r"(Vervallen|Verplaatst naar|Zie overheidsmaatregel)", tekst):
        return None
    return "overheid"


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        sys.exit(__doc__)
    pdf = pathlib.Path(argv[1])
    deel2 = lees_deel2(pdf)
    vorige = json.loads(UIT.read_text(encoding="utf-8"))
    per_iso: dict[str, list[dict]] = collections.defaultdict(list)
    for r in vorige["maatregelen"]:
        per_iso[iso(r["id"])].append(r)

    maatregelen, weg = [], []
    for nummer, tekst in deel2.items():
        s = soort(tekst)
        if s is None:
            naar = re.search(r"\d\.\d{2}\.\d{2}", tekst)
            weg.append(f"{nummer} ({'vervallen' if tekst.startswith('Vervallen') else 'nu ' + naar.group(0)})")
            continue
        broers = per_iso.get(iso(nummer))
        if broers:
            titel = broers[0]["titel"]
            eigen = next((r for r in broers if r["id"] == nummer and r.get("thema")), None)
            thema = eigen["thema"] if eigen else collections.Counter(
                r["thema"] for r in broers if r.get("thema")).most_common(1)[0][0]
        else:
            titel, thema = NIEUWE_ISO[iso(nummer)]
        maatregelen.append({"id": nummer, "titel": titel, "thema": thema, "soort": s})

    telling = collections.Counter(r["soort"] for r in maatregelen)
    print(f"{len(maatregelen)} nummers: {telling['overheid']} overheidsmaatregelen, "
          f"{telling['alleen-iso']} alleen ISO; {len(weg)} weg: {', '.join(weg)}")
    if "--schrijf" not in argv:
        return 0

    sha = hashlib.sha256(pdf.read_bytes()).hexdigest()
    data = {
        "kader": "bio2",
        "titel": "BIO 2.0",
        "versie": VERSIE,
        "toelichting": (
            f"De {len(maatregelen)} nummers die in deel 2 van de Baseline Informatiebeveiliging Overheid 2.0 "
            f"gelden: {telling['overheid']} overheidsmaatregelen en {telling['alleen-iso']} "
            "ISO-beheersmaatregelen zonder overheidsmaatregel (veld soort: overheid of alleen-iso). "
            "Genummerd volgens ISO 27002:2022 (5.01.01 hoort bij ISO-maatregel 5.1). Per nummer de titel van "
            "de ISO-beheersmaatregel en het thema (de IV-standaard). De tekst van de overheidsmaatregel staat "
            "er niet bij: het CIP publiceert onder CC BY-NC-SA 4.0, en de ISO-tekst eronder is van NEN/ISO. "
            "Wie de tekst nodig heeft, gaat naar de bron; het nummer hier is ook het nummer daar."),
        "bron": {
            "naam": "Centrum Informatiebeveiliging en Privacybescherming (CIP)",
            "versie": VERSIE,
            "url": "https://www.bio-overheid.nl/bio2/",
            "licentie": "CC BY-NC-SA 4.0 (CIP). Daarom staan hier alleen nummers, titels en thema's; de "
                        "tekst van de overheidsmaatregelen en de ISO-tekst zijn niet opgenomen",
            "opgehaald": date.today().isoformat(),
            "herkomst": f"gegenereerd met tools/genereer_bio2.py uit deel 2 van de pdf van versie 1.3 "
                        f"(sha256 {sha})",
            "let_op": "In versie 1.3 vervallen of verplaatst, en daarom niet in deze lijst: "
                      + ", ".join(weg) + ". De vorige versie van deze dataset (tot 13-10-2026) volgde de "
                      "nummering van versie 1.2 en telde 148 nummers.",
        },
        "tweede_etiket": vorige["tweede_etiket"],
        "maatregelen": maatregelen,
        "vingerafdruk": vorige["vingerafdruk"],
    }
    UIT.write_bytes((json.dumps(data, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))
    print(f"geschreven: {UIT.name}; draai nu tools/controleer.py")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
