# sim-admin

`sim-admin` ist eine lokale, offline betriebene Webanwendung zur Verwaltung und
kontrollierten Personalisierung von SIM-Karten. Sie wurde für einen dedizierten
Standalone-Rechner mit PC/SC-Kartenleser und separat installierter pySim-Umgebung
entwickelt.

## Funktionsumfang

- passwortgeschützte HTTPS-Weboberfläche
- PC/SC-Lesererkennung und read-only Kartenidentifikation
- sysmocom-CSV-Prüfung und verschlüsselter Profiltresor
- Einzelkartenerfassung: „Karte zuerst“ oder „Daten zuerst“
- Suche, Sortierung, Statusfilter und Seitennavigation
- zeitlich begrenzte Geheimnisanzeige nach erneuter Anmeldung
- verschlüsselte Änderungsentwürfe und append-only Revisionen
- Dry Run und read-only Kartenabgleich
- kontrolliertes Schreiben von IMSI, ACC und MSISDN
- kartentypspezifisches Ki-/OPc-Schreiben für SysmocomSJA5
- metadatenbasiertes Aktivitätsprotokoll ohne SIM-Geheimnisse
- AES-256-GCM-verschlüsselte USB-Backups und Wiederherstellung

SIM-Schreibzugriffe erfordern eine passende ICCID, ADM1, erneute
Passwortbestätigung, eine ausdrückliche Schreibfreigabe und anschließendes
Zurücklesen. Erst nach vollständiger Prüfung wird eine Profilrevision übernommen.

## Architektur

```text
Weboberfläche / REST API
          |
    Anwendungsdienste
          |
      Fachmodelle
          |
 Adapter: pySim, PC/SC, SQLite, Backup
```

pySim läuft in getrennten Bridge-Prozessen. Dadurch importiert der Webserver die
Hardwarebibliothek nicht direkt. Details stehen in der
[Architekturübersicht](docs/architecture/overview.md).

## Entwicklung

Voraussetzung ist Python 3.11 oder neuer.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pytest -q
```

Für einen lokalen Start müssen mindestens `SIM_ADMIN_USERNAME`,
`SIM_ADMIN_PASSWORD_HASH` und `SIM_ADMIN_SESSION_SECRET` gesetzt sein. Die
[Beispielkonfiguration](.env.example) enthält keine echten Geheimnisse.

```bash
uvicorn app.main:app --reload
```

## Dokumentation

- [Standalone-Installation](docs/standalone/installation.md)
- [Architektur](docs/architecture/overview.md)
- [Projektchronik](docs/project-history.md)
- [Änderungsprotokoll](CHANGELOG.md)
- [Sicherheitsrichtlinie](SECURITY.md)
- [Mitwirken](CONTRIBUTING.md)

## Releases

Die Datei `VERSION` bestimmt die Anwendungsversion. Ein Tag mit derselben Version
(`v0.1.0`) startet nach erfolgreichen Tests den GitHub-Releaseprozess. Lokal kann
das reproduzierbare Archiv samt SHA-256-Prüfsumme so gebaut werden:

```bash
./scripts/build-release.sh
```

## Wichtiger Sicherheitshinweis

Dieses Projekt verarbeitet hochsensible Mobilfunk-Zugangsdaten. Reale Ki-,
OPc-, ADM-, PIN-, PUK- oder Teilnehmerdaten dürfen niemals in Git, Issues oder
Testdateien gelangen. Hardware-Schreibtests dürfen ausschließlich mit dafür
vorgesehenen Testkarten und einem vorhandenen Backup erfolgen.

## Lizenz

GNU General Public License v3.0 oder später (`GPL-3.0-or-later`) – siehe
[LICENSE](LICENSE).
