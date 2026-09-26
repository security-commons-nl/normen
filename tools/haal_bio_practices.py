#!/usr/bin/env python3
"""Haalt per BIO-overheidsmaatregel de practices op die het CIP op BIO Practices noemt.

Draaien:  python tools/haal_bio_practices.py            (laat zien wat er is, schrijft niets)
          python tools/haal_bio_practices.py --schrijf  (schrijft bio-practices.json)

BIO Practices (https://www.bio-overheid.nl/bio-practices/) is de zoekpagina van het CIP die per
overheidsmaatregel verwijst naar practices, vooral pagina's op NORA Online. De pagina is een formulier dat
per nummer een POST doet; er is geen adres per maatregel. Dit script doet die vraag voor elk nummer in
bio2.json en bewaart alleen de verwijzingen: code en adres. Geen tekst van het CIP (die staat onder
CC BY-NC-SA 4.0); de normwijzer maakt van de verwijzingen links.

Alleen standaardbibliotheek. Een pauze tussen de vragen, zodat de site er niets van merkt.
"""
from __future__ import annotations

import argparse
import html
import http.cookiejar
import json
import pathlib
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import date

ROOT = pathlib.Path(__file__).resolve().parent.parent
PAGINA = "https://www.bio-overheid.nl/bio-practices/"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128 Safari/537.36"
UIT = ROOT / "bio-practices.json"


def opener() -> urllib.request.OpenerDirector:
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))


def formulier(op: urllib.request.OpenerDirector) -> dict[str, str]:
    """De verborgen velden van het practices-formulier (token en ufprt), uit een verse GET."""
    tekst = op.open(urllib.request.Request(PAGINA, headers={"User-Agent": UA}), timeout=30).read().decode("utf-8")
    blok = tekst[tekst.find('id="bio-onderdeel"') - 3000:tekst.find('id="bio-onderdeel"') + 3000]
    velden = dict(re.findall(r'<input[^>]*name="(__RequestVerificationToken|ufprt)"[^>]*value="([^"]*)"', blok))
    if len(velden) != 2:
        raise SystemExit("Formulier van BIO Practices niet herkend; is de pagina veranderd?")
    return velden


def practices(op: urllib.request.OpenerDirector, velden: dict[str, str], nummer: str) -> list[dict[str, str]]:
    data = urllib.parse.urlencode({**velden, "BioNumber": nummer}).encode()
    req = urllib.request.Request(PAGINA, data=data, headers={"User-Agent": UA,
                                                              "Content-Type": "application/x-www-form-urlencoded"})
    tekst = op.open(req, timeout=30).read().decode("utf-8")
    uit = []
    for rij in re.findall(r"<tr[^>]*>(.*?)</tr>", tekst, re.S):
        if nummer not in rij:
            continue
        for href, code in re.findall(r'<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>', rij, re.S):
            code = html.unescape(re.sub(r"<[^>]+>", "", code)).strip()
            href = html.unescape(href)
            if code and href.startswith("http"):
                uit.append({"code": code, "url": href, "titel": titel_uit_url(href)})
    return uit


def titel_uit_url(url: str) -> str:
    """NORA-pagina's heten ISOR:Beveiligde_inlogprocedure; dat is ook een leesbare titel."""
    laatste = urllib.parse.unquote(url.rstrip("/").rsplit("/", 1)[-1])
    laatste = laatste.split(":", 1)[-1]
    return laatste.replace("_", " ")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--schrijf", action="store_true")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    nummers = [m["id"] for m in json.loads((ROOT / "bio2.json").read_text(encoding="utf-8"))["maatregelen"]]
    op = opener()
    velden = formulier(op)
    per: dict[str, list[dict[str, str]]] = {}
    for nr in nummers:
        per[nr] = practices(op, velden, nr)
        time.sleep(0.35)
    met = sum(1 for v in per.values() if v)
    print(f"{len(nummers)} overheidsmaatregelen, {met} met practices, {sum(len(v) for v in per.values())} verwijzingen.")
    if args.schrijf:
        data = {
            "titel": "BIO Practices: verwijzingen per BIO-overheidsmaatregel",
            "toelichting": "Per overheidsmaatregel de practices die het CIP op BIO Practices noemt, vooral pagina's op "
                           "NORA Online. Alleen code, adres en een titel uit het adres; geen tekst van het CIP. "
                           "Opgehaald met tools/haal_bio_practices.py.",
            "bron": {"naam": "CIP, BIO Practices", "url": PAGINA, "opgehaald": date.today().isoformat(),
                     "licentie": "Verwijzingen; de inhoud van BIO Practices is van het CIP (CC BY-NC-SA 4.0) en van NORA Online"},
            "practices": per,
        }
        UIT.write_bytes((json.dumps(data, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))
        print(f"Geschreven: {UIT.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
