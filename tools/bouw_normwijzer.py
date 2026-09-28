#!/usr/bin/env python3
"""Bouwt normwijzer.html: per maatregel wat de norm vraagt, wat je eraan kunt doen en welk bewijs je dan hebt.

Aanroep:
    python tools/bouw_normwijzer.py          # bouwt normwijzer.html
    python tools/bouw_normwijzer.py --check  # exit 1 als normwijzer.html niet overeenkomt met de bronnen

De pagina voegt drie repo's samen, en maakt geen eigen oordeel:
- `normen` (deze repo): de kaders, de practices van het CIP per BIO-overheidsmaatregel
  (bio-practices.json) en de trefwoorden per maatregel (trefwoorden.json).
- `aanvalspaden`: de barrieres (paden.json), de mappingen van barriere naar maatregel met sterkte en reden
  (mappingen/*.json), de BIO op ISO-niveau met de overheidsmaatregelen erbij (mappingen/bronnen/bio2.json) en
  de meetitems per chokepoint (meting/regels.json).
- `kennisbank`: de handleidingen per barriere (handelingsperspectief.json), alle items, het bronnenregister
  (bronnen.json) en de partijen uit de stelselkaart.

Lokaal staan de andere repo's als buurmap; in CI worden ze uitgecheckt in _aanvalspaden en _kennisbank.

De relatie blijft die van de mappingen: een barriere levert bewijs voor een maatregel. Een treffer op
trefwoord is automatisch gevonden met vastgestelde trefwoorden en staat zo op de pagina. Normtekst van ISO, NEN of het CIP komt er niet in.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys
import unicodedata

ROOT = pathlib.Path(__file__).resolve().parent.parent
SJABLOON = ROOT / "site" / "normwijzer-sjabloon.html"
UIT = ROOT / "normwijzer.html"
KB_SITE = "https://security-commons-nl.github.io/kennisbank"
ZELFCHECK = "https://security-commons-nl.github.io/aanvalspaden/"
METING = "https://security-commons-nl.github.io/aanvalspaden/meting/"
BIO_PRACTICES = "https://www.bio-overheid.nl/bio-practices/"

KADERS = [
    {"id": "bio2", "naam": "BIO 2.0", "sub": "en daarmee ISO 27001:2022",
     "bron": {"naam": "BIO 2.0 bij het CIP", "url": "https://www.bio-overheid.nl/bio2/"}},
    {"id": "nist-csf", "naam": "NIST CSF 2.0", "sub": "Cybersecurity Framework",
     "bron": {"naam": "CSF 2.0 in de referentietool van NIST",
              "url": "https://csrc.nist.gov/projects/cprt/catalog#/cprt/framework/version/CSF_2_0_0/home"}},
    {"id": "avg", "naam": "AVG", "sub": "Algemene verordening gegevensbescherming",
     "bron": {"naam": "De AVG op EUR-Lex",
              "url": "https://eur-lex.europa.eu/legal-content/NL/TXT/HTML/?uri=CELEX:32016R0679"}},
    {"id": "wpg", "naam": "Wpg", "sub": "toetsingskader voor boa-organisaties",
     "bron": {"naam": "De Wet politiegegevens op wetten.nl", "url": "https://wetten.overheid.nl/BWBR0022463/"}},
]
STERKTE = ("volledig", "gedeeltelijk", "raakvlak")
MAX_TREFWOORD = 12


# ----------------------------------------------------------------------------- bronnen vinden
def buur(naam: str) -> pathlib.Path:
    for kandidaat in (ROOT.parent / naam, ROOT / f"_{naam}"):
        if kandidaat.is_dir():
            return kandidaat
    raise SystemExit(f"Repo '{naam}' niet gevonden: zet hem naast normen of in _{naam}")


def lees(pad: pathlib.Path) -> dict:
    return json.loads(pad.read_text(encoding="utf-8"))


# ----------------------------------------------------------------------------- adressen
def norm_url(kader: str, rec: dict) -> str | None:
    """Het adres van de maatregel bij de bron zelf, of None als de bron er geen per maatregel heeft."""
    if kader == "nist-csf":
        return ("https://csrc.nist.gov/projects/cprt/catalog#/cprt/framework/version/CSF_2_0_0/home?element="
                + rec["id"])
    art = re.search(r"art\.\s*(\d+[a-z]?)", rec.get("artikel", ""))
    if kader == "avg" and art:
        return f"https://eur-lex.europa.eu/legal-content/NL/TXT/HTML/?uri=CELEX:32016R0679#art_{art.group(1)}"
    if kader == "wpg" and art and rec.get("artikel", "").startswith("Wpg"):
        return f"https://wetten.overheid.nl/jci1.3:c:BWBR0022463&artikel={art.group(1)}"
    return None


# ----------------------------------------------------------------------------- trefwoorden
def norm(tekst: str) -> str:
    """Kleine letters, zonder accenten, koppeltekens weg, leestekens als spatie, met spaties eromheen."""
    t = unicodedata.normalize("NFD", str(tekst).lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn").replace("-", "")
    return " " + re.sub(r"[^a-z0-9]+", " ", t).strip() + " "


def raakt(tekst_norm: str, woord: str) -> bool:
    """Korte woorden (drie tekens of minder) alleen als heel woord: 'soc' mag 'sociaal' niet vinden."""
    w = norm(woord).strip()
    if not w:
        return False
    return f" {w} " in tekst_norm if len(w) <= 3 else w in tekst_norm


# ----------------------------------------------------------------------------- bouwen
def verzamel() -> dict:
    ap, kb = buur("aanvalspaden"), buur("kennisbank")
    paden = lees(ap / "paden.json")
    meting = lees(ap / "meting" / "regels.json")
    hp = lees(kb / "handelingsperspectief.json")
    register = lees(kb / "bronnen.json")
    ptn = {p["id"]: p for p in lees(kb / "security" / "stelselkaart-security-gremia" / "data" / "partijen.json")["partijen"]}
    practices = lees(ROOT / "bio-practices.json")["practices"]
    trefwoorden = lees(ROOT / "trefwoorden.json")

    # Barrieres: de sleutel van de hele keten. Een barriere komt bij meerdere paden voor.
    barrieres: dict[str, dict] = {}
    cp_naar_b: dict[str, str] = {}
    for blad in paden["bladeren"]:
        for cp in blad["chokepoints"]:
            b = barrieres.setdefault(cp["vraag_id"], {"titel": cp["titel"], "claim": cp["vraag"]["claim"],
                                                      "bewijs": cp.get("bewijs", ""), "paden": [], "meting": []})
            if blad["id"] not in b["paden"]:
                b["paden"].append(blad["id"])
            cp_naar_b[cp["id"]] = cp["vraag_id"]
    for rv in paden.get("randvoorwaarden", []):
        barrieres.setdefault(rv["vraag_id"], {"titel": rv["titel"], "claim": rv.get("vraag", {}).get("claim", ""),
                                              "bewijs": rv.get("bewijs", ""), "paden": [], "meting": []})
    for item in meting["items"]:
        b = cp_naar_b.get(item.get("chokepoint", ""))
        if b and b in barrieres:
            barrieres[b]["meting"].append({"id": item["id"], "label": item["label"]})

    handleidingen: dict[str, list[dict]] = {}
    for h in hp["handleidingen"]:
        handleidingen.setdefault(h["barriere"], []).append({"titel": h["titel"], "url": h["url"], "rol": h["rol"]})

    # Alles wat op trefwoord gevonden kan worden: de items van de kennisbank en het bronnenregister.
    stukken: list[dict] = []
    for readme in sorted(kb.glob("*/*/README.md")):
        vak, item = readme.parent.parent.name, readme.parent.name
        if vak.startswith((".", "_", "tools")):
            continue
        kop = readme.read_text(encoding="utf-8").split("\n---", 1)[0]
        titel = re.search(r"^titel:\s*(.+)$", kop, re.M)
        samenvatting = re.search(r"^samenvatting:\s*(.+)$", kop, re.M)
        if titel:
            stukken.append({"titel": titel.group(1).strip(), "url": f"{KB_SITE}/{vak}/{item}/", "wie": "kennisbank",
                            "_zoek": norm(titel.group(1) + " " + (samenvatting.group(1) if samenvatting else ""))})
    for bid, b in register["bronnen"].items():
        if b.get("vervallen"):
            continue
        p = ptn.get(b["partij"])
        stukken.append({"titel": b["titel"], "url": b["url"], "wie": p["naam"] if p else b["partij"],
                        "slot": b.get("kring") if b.get("toegang") == "inlog" else None, "_zoek": norm(b["titel"])})

    maatregelen: list[dict] = []
    for kader in KADERS:
        k = kader["id"]
        bron = lees(ap / "mappingen" / "bronnen" / f"{k}.json")["maatregelen"]
        mapping = lees(ap / "mappingen" / f"{k}.json")
        per_norm: dict[str, list[dict]] = {}
        for r in mapping["regels"]:
            per_norm.setdefault(r["norm"], []).append({"b": r["barriere"], "sterkte": r["sterkte"], "reden": r["reden"]})
        tw_kader = trefwoorden.get(k, {})
        for rec in bron:
            regels = sorted(per_norm.get(rec["id"], []), key=lambda r: STERKTE.index(r["sterkte"]))
            doen, gezien = [], set()
            for r in regels:
                if r["sterkte"] == "raakvlak":
                    continue
                for h in handleidingen.get(r["b"], []):
                    if h["url"] not in gezien:
                        gezien.add(h["url"])
                        doen.append({"titel": h["titel"], "url": h["url"], "wie": "kennisbank", "via": r["b"]})
            woorden = tw_kader.get(rec["id"], [])
            treffers = []
            for s in stukken:
                if s["url"] in gezien:
                    continue
                n = sum(1 for w in woorden if raakt(s["_zoek"], w))
                if n:
                    treffers.append((n, s))
            treffers.sort(key=lambda x: (-x[0], x[1]["wie"] != "kennisbank", x[1]["titel"].lower()))
            op_trefwoord = [{k2: v for k2, v in s.items() if not k2.startswith("_")} | {"trefwoord": True}
                            for _, s in treffers[:MAX_TREFWOORD]]
            m = {"k": k, "id": rec["id"], "titel": rec["titel"], "thema": rec.get("thema", ""),
                 "url": norm_url(k, rec), "bewijs": regels, "doen": doen, "trefwoord": op_trefwoord,
                 "meer_trefwoord": max(0, len(treffers) - MAX_TREFWOORD),
                 # Ook de maatregel zelf is vindbaar op zijn trefwoorden: wie "verwerkingsregister" typt,
                 # moet AVG artikel 30 vinden, ook al heet dat "Register van verwerkingsactiviteiten".
                 "zoek": " ".join(woorden)}
            if rec.get("artikel"):
                m["artikel"] = rec["artikel"]
            if rec.get("kern"):
                m["kern"] = rec["kern"]
            if k == "bio2":
                m["overheid"] = [{"id": o, "practices": practices.get(o, [])} for o in rec.get("overheidsmaatregelen", [])]
            maatregelen.append(m)

    # De omgekeerde kant: per stuk en per barriere de maatregelen erachter.
    normen_per_b: dict[str, list[dict]] = {}
    for m in maatregelen:
        for r in m["bewijs"]:
            normen_per_b.setdefault(r["b"], []).append({"k": m["k"], "id": m["id"], "sterkte": r["sterkte"]})
    for bid, b in barrieres.items():
        b["normen"] = normen_per_b.get(bid, [])
        b["handleidingen"] = handleidingen.get(bid, [])
    stuk_normen: dict[str, list[dict]] = {}
    for m in maatregelen:
        for d in m["doen"]:
            stuk_normen.setdefault(d["url"], []).append({"k": m["k"], "id": m["id"], "via": "barriere"})
        for d in m["trefwoord"]:
            stuk_normen.setdefault(d["url"], []).append({"k": m["k"], "id": m["id"], "via": "trefwoord"})
    stukken_uit = [{k2: v for k2, v in s.items() if not k2.startswith("_")} | {"normen": stuk_normen.get(s["url"], [])}
                   for s in stukken]

    return {"kaders": KADERS, "maatregelen": maatregelen, "barrieres": barrieres, "stukken": stukken_uit,
            "adressen": {"zelfcheck": ZELFCHECK, "meting": METING, "bio_practices": BIO_PRACTICES}}


def pagina(data: dict) -> str:
    sjabloon = SJABLOON.read_text(encoding="utf-8")
    blob = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    if "/*NORMWIJZER_DATA*/" not in sjabloon:
        raise SystemExit("Het sjabloon mist /*NORMWIJZER_DATA*/")
    return sjabloon.replace("/*NORMWIJZER_DATA*/", blob)


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    data = verzamel()
    html = pagina(data)
    per_k = {}
    for m in data["maatregelen"]:
        per_k.setdefault(m["k"], [0, 0, 0])
        per_k[m["k"]][0] += 1
        per_k[m["k"]][1] += bool([r for r in m["bewijs"] if r["sterkte"] != "raakvlak"])
        per_k[m["k"]][2] += bool(m["doen"] or m["trefwoord"] or any(o["practices"] for o in m.get("overheid", [])))
    for k, (n, bewijs, doen) in per_k.items():
        print(f"{k:9} {n:3} maatregelen, {bewijs:3} met bewijs uit de zelfcheck, {doen:3} met iets om te doen")
    if "--check" in sys.argv:
        if not UIT.exists() or UIT.read_text(encoding="utf-8") != html:
            print("normwijzer.html loopt achter; draai python tools/bouw_normwijzer.py")
            return 1
        return 0
    UIT.write_bytes(html.encode("utf-8"))
    print(f"Geschreven: {UIT.name} ({len(html) // 1024} kB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
