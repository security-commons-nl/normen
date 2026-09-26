# normen

De normbronnen van Security Commons NL als dataset: BIO 2.0, NIST CSF 2.0, het Wpg-toetsingskader voor
boa-organisaties en de AVG, elk als één JSON-bestand in één schema, met herkomst en een vingerafdruk.
Voor iedereen die een norm in een tool wil laden zonder hem eerst uit een PDF te moeten halen.

Status: in gebruik. De aanvalspaden en applicatiecheck lezen hieruit; tests en CI bewaken de inhoud.

> **Zoek je wat een norm vraagt en wat je eraan kunt doen?** Open de
> [normwijzer](https://security-commons-nl.github.io/normen/normwijzer.html): per maatregel uit BIO 2.0,
> NIST CSF 2.0, de AVG en de Wpg de link naar de bron, de practices van het CIP, handleidingen en stukken
> van anderen, en het bewijs dat de zelfcheck oplevert. Andersom: typ wat je doet en zie de normen.

## Voor wie

Wie een instrument bouwt dat naar een norm verwijst, en wie een norm wil doorzoeken of hergebruiken
zonder de opmaak van de uitgever. CISO's, ISO's, privacy officers en bouwers bij publieke organisaties.

## Snel starten

1. Kies een kader: [`bio2.json`](bio2.json), [`bio2-domeinen.json`](bio2-domeinen.json),
   [`nist-csf.json`](nist-csf.json), [`wpg.json`](wpg.json) of [`avg.json`](avg.json). Wat erin zit staat
   in [kaders.md](kaders.md), of leesbaar op
   [security-commons-nl.github.io/normen](https://security-commons-nl.github.io/normen/).
2. Elk bestand heeft dezelfde kop: `kader`, `titel`, `versie`, `toelichting`, `bron` (naam, versie,
   url, licentie, datum van ophalen) en `vingerafdruk`, en daaronder de lijst `maatregelen` (of
   `domeinen`). Het schema staat in [`schema.json`](schema.json).
3. Gebruik je een kader in een eigen repo, kopieer het dan en bewaar de `vingerafdruk` erbij. Zo zie
   je wanneer je kopie achterloopt; de repo's van de commons doen dat met een `tools/haal_normen.py`
   dat in CI `--check` draait.

## Bijdragen

Zie de [CONTRIBUTING](https://github.com/security-commons-nl/.github/blob/main/CONTRIBUTING.md) van
de organisatie: daar staat per project een formulier, ook zonder Git-ervaring. Een issue of discussion
is een volwaardige bijdrage. Voor deze repo: zie [CONTRIBUTING.md](CONTRIBUTING.md), vooral over wat
we wel en niet opnemen.

## Licentie

EUPL-1.2, zie [LICENSE](LICENSE), voor wat in deze repo zelf is gemaakt: het schema, de indeling, de
scripts, de samenvattingen bij Wpg en AVG en de beleidsdomeinen. **Per kader staat de licentie van de
bron in het bestand zelf**, onder `bron.licentie`. BIO 2.0 is een publicatie van het CIP onder
CC BY-NC-SA 4.0, en daarom staan hier alleen de nummers, titels en thema's; NIST CSF 2.0 staat in het publieke domein; de AVG is wettekst; het
Wpg-toetsingskader is van NOREA en staat hier alleen als eigen samenvatting.

**Wat hier bewust niet in staat: normtekst.** BIO 2.0 volgt de nummering van ISO 27002:2022, en de bron
waaruit deze dataset is overgenomen droeg per maatregel de ISO-tekst en de tekst van de overheidsmaatregel.
De eerste is van NEN/ISO, de tweede van het CIP onder CC BY-NC-SA 4.0; geen van beide laat herdistributie
onder EUPL toe. Een test blokkeert als een van die velden ooit terugkomt. Wie de tekst nodig heeft, gaat
naar de bron; het nummer hier is ook het nummer daar.

## Wat erin zit

| Bestand | Kader | Records | Wat een record draagt |
|---|---|---|---|
| `bio2.json` | BIO 2.0 (CIP, v1.3 definitief) | 148 overheidsmaatregelen | nummer (ook het ISO-nummer), titel, thema; geen tekst |
| `bio2-domeinen.json` | BIO 2.0, beleidsdomeinen | 15 domeinen | id, titel, omschrijving, de maatregelen die in dat beleidsdocument horen |
| `nist-csf.json` | NIST CSF 2.0 | 106 subcategorieën | id, uitkomst (Engels, zoals NIST hem formuleert), functie en categorie |
| `wpg.json` | Wpg-toetsingskader (NOREA) | 36 maatregelen | id, titel, artikel, thema, kern in eigen woorden |
| `avg.json` | AVG | 32 artikelen | id, titel, artikel, thema, kern in eigen woorden |

Wat er **niet** in zit: de mappingen tussen kaders en de aanvalspaden. Die horen bij de barrières en
staan in [`aanvalspaden/mappingen/`](https://github.com/security-commons-nl/aanvalspaden). Deze repo
levert de bronnen; de aanvalspaden leggen de verbanden.

## De normwijzer

[`normwijzer.html`](https://security-commons-nl.github.io/normen/normwijzer.html) brengt de kaders, de
mappingen en de kennisbank samen op één pagina. Elke maatregel heeft een eigen adres
(`normwijzer.html#bio2/8.5`, `#avg/A35`, `#nist-csf/PR.AA-01`) met vier blokken: wat de norm vraagt, wat je
eraan kunt doen, hoe je het aantoont, en wat er nog ontbreekt.

| Bestand | Wat |
|---|---|
| [`bio-practices.json`](bio-practices.json) | Per BIO-overheidsmaatregel de practices die het CIP op BIO Practices noemt (102 van de 148, 248 verwijzingen op 26-09-2026). Alleen code en adres, geen tekst |
| [`trefwoorden.json`](trefwoorden.json) | Per maatregel de woorden waarmee de normwijzer stukken uit de kennisbank en het bronnenregister vindt. Een treffer staat als voorstel op de pagina |
| `site/normwijzer-sjabloon.html` | De pagina zelf; de data wordt er bij het bouwen in gezet |

Een barriere **levert bewijs voor** een maatregel, zoals in de mappingen. De normwijzer zegt nooit dat je
aan een norm voldoet.

## Onderhoud

- `python tools/controleer.py` valideert alle kaders, herrekent de vingerafdrukken en schrijft
  `kaders.md`. In CI draait hij met `--check` en wordt rood als iemand in de JSON heeft gewerkt zonder
  hem te draaien.
- `python -m pytest tests/` toetst het schema, de aantallen, de unieke ids, de afwezigheid van
  ISO-tekst en of `bio2.json` nog gelijk is aan de overname.
- Een nieuwe versie van een kader komt binnen via de generator van dat kader in `tools/`
  (`genereer_nist.py` leest de CSF-export van NIST). Voor BIO 2.0 is de eerste versie eenmalig
  overgenomen uit `cisochat` met `tools/overname.py`; dat script documenteert de herkomst en hoeft niet
  opnieuw te draaien.
- `python tools/bouw_normwijzer.py` bouwt de normwijzer. Hij leest `aanvalspaden` en `kennisbank` als
  buurmap (of uit `_aanvalspaden` en `_kennisbank`). De workflow *Normwijzer bijwerken* doet dat elke
  nacht en commit alleen als er iets is veranderd, zodat een nieuwe handleiding in de kennisbank vanzelf
  in de normwijzer komt.
- `python tools/haal_bio_practices.py --schrijf` haalt de practices van het CIP opnieuw op. Het formulier
  van BIO Practices kent geen adres per maatregel, vandaar het script; het wacht even tussen de vragen.
