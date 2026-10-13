# Wijzigingen

Nieuwste bovenaan. De datasets zelf dragen hun eigen versie en vingerafdruk; hier staat wat er aan de repo en
de pagina's verandert.

## 2026-10

- 13-10: `bio2.json` volgt nu BIO 2.0 versie 1.3. De eerste versie kwam uit cisochat en had de nummering van
  versie 1.2: tien nummers die in 1.3 vervallen of verplaatst zijn stonden erin, zestien die in 1.3 gelden
  ontbraken (onder meer 6.01.01 screening en 8.24.02, 8.24.04 en 8.24.05 cryptografie). Nieuw:
  `tools/genereer_bio2.py` leest deel 2 rechtstreeks uit de pdf van het CIP, en elk record heeft een veld
  `soort` (`overheid` of `alleen-iso`). Telling: 157 nummers, waarvan 117 overheidsmaatregelen. De
  beleidsdomeinen en de practices zijn mee omgezet.

## 2026-09

- 28-09: de normwijzer wijst naar "van aanvalspad naar norm" in `aanvalspaden`, de weergave per barriere.
  Op de voorpagina van de commons opent de kaart "Wat toon ik aan?" nu de normwijzer.
- 28-09: `zoekindex.json` naast de normwijzer: alle stukken (kennisbank en bronnenregister) en maatregelen,
  voor het zoekvak op de voorpagina. De nachtelijke bouw houdt het bestand bij.
- 28-09: trefwoorden per maatregel vastgesteld; een maatregel is ook vindbaar op zijn trefwoorden.
- 26-09: de normwijzer (`normwijzer.html`): per maatregel wat de norm vraagt, wat je eraan kunt doen en welk
  bewijs je dan hebt, met een adres per maatregel (`#bio2/8.5`). `bio-practices.json` met de practices van
  het CIP per BIO-overheidsmaatregel.
