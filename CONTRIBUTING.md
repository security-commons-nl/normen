# Bijdragen

Dit project hoort bij [security-commons-nl](https://github.com/security-commons-nl). De
organisatiebrede regels staan in
[CONTRIBUTING.md](https://github.com/security-commons-nl/.github/blob/main/CONTRIBUTING.md) en het
[redactiestatuut](https://github.com/security-commons-nl/.github/blob/main/REDACTIESTATUUT.md).

## Wat helpt

- **Een nummer, titel of thema dat afwijkt van de bron.** Noem het kader, het id en wat er in de bron
  staat. Tekstgetrouwheid is de kern van deze dataset; elke afwijking is een bug.
- **Een nieuwe versie van een kader.** Als het CIP een nieuwe BIO publiceert of NIST het CSF bijwerkt,
  is een issue met de link genoeg; het bijwerken doen we met de generator in `tools/`.
- **Een kader dat ontbreekt.** Zeg welk, wie het uitgeeft en onder welke licentie. Normtekst van een
  auteursrechthebbende die niet de overheid is (ISO, NEN) nemen we niet op; nummers, titels en
  thema's wel.

Een [issue](../../issues/new/choose) of
[discussion](https://github.com/security-commons-nl/.github/discussions) is een volwaardige bijdrage.
"Maak maar een pull request" is nooit het antwoord.

## Werkwijze

1. Wijzig de JSON, nooit `kaders.md` (dat wordt gegenereerd).
2. Draai `python tools/controleer.py`; dat herrekent de vingerafdruk en schrijft `kaders.md`.
3. Draai `python -m pytest tests/`.
4. Afnemers halen de nieuwe versie op met hun `tools/haal_normen.py`; hun CI wordt rood tot ze dat doen.
