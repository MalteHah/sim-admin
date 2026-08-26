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
- optionaler Service Provider Name (SPN) mit Vergleich und Rückprüfung
- kartentypspezifisches Ki-/OPc-Schreiben für SysmocomSJA5
- optionale IMS- und 5GS-/SUCI-Profildaten in Import und Einzelkartenerfassung
- SUCI-Berechnung im Endgerät oder auf einer S17-USIM sowie bis zu acht
  priorisierte Schutzverfahren
- vorab lesend geprüfte und zurückgelesene IMS-/5GS-Schreibpfade für SysmocomSJA5
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

- [Bedienungsanleitung](docs/user-guide.md)
- [Administrationsanleitung](docs/administration.md)
- [Standalone-Installation](docs/standalone/installation.md)
- [Backup und Wiederherstellung](docs/standalone/backup-restore.md)
- [Roadmap und Abnahmestand](docs/testing-and-roadmap.md)
- [Release Notes 1.0.3](docs/release-notes-1.0.3.md)
- [Release Notes 1.0.2](docs/release-notes-1.0.2.md)
- [Release Notes 1.0.1](docs/release-notes-1.0.1.md)
- [Release Notes 1.0.0](docs/release-notes-1.0.0.md)
- [Architektur](docs/architecture/overview.md)
- [Projektchronik](docs/project-history.md)
- [Änderungsprotokoll](CHANGELOG.md)
- [Sicherheitsrichtlinie](SECURITY.md)
- [Mitwirken](CONTRIBUTING.md)

## Releases

Die Datei `VERSION` bestimmt die Anwendungsversion. Ein Tag mit derselben Version
(`v1.0.3`) startet nach erfolgreichen Tests den GitHub-Releaseprozess. Lokal kann
das reproduzierbare Archiv samt SHA-256-Prüfsumme so gebaut werden:

```bash
./scripts/build-release.sh
```

Für ein signiertes Offline-Paket wird ein außerhalb des Repositorys verwahrter
Ed25519-Schlüssel angegeben. Der öffentliche Schlüssel muss auf dem Zielrechner
bereits als vertrauenswürdiger Release-Schlüssel hinterlegt sein:

```bash
./scripts/build-release.sh --signing-key /sicherer/ort/release-signing-key.pem
./scripts/verify-release.sh dist/sim-admin-1.0.3.tar.gz \
  --public-key /etc/sim-admin/release-signing-key.pub.pem
```

Die dem Download beiliegende öffentliche Schlüsseldatei dient nur zur Verteilung
und darf einen bereits hinterlegten Vertrauensanker nicht unbemerkt ersetzen.
Der automatische GitHub-Release setzt den verschlüsselten privaten Schlüssel
Base64-kodiert als Repository-Secret `RELEASE_SIGNING_KEY_BASE64` und das separat
gespeicherte Passwort als `RELEASE_SIGNING_KEY_PASSWORD` voraus. Ohne beide
Secrets bricht er ab. Der Schlüssel wird niemals in einen Build übernommen.

Ein neuer, direkt am gewählten Sicherungsort verschlüsselter Release-Schlüssel
wird interaktiv erzeugt mit:

```bash
./scripts/create-release-key.sh /pfad/zum/usb-stick
```

Das Skript überschreibt keine vorhandenen Schlüsseldateien. Auf einem
Standalone-Rechner wird ausschließlich der öffentliche Schlüssel nach manuellem
Abgleich des angezeigten Fingerabdrucks installiert.

## Wichtiger Sicherheitshinweis

Dieses Projekt verarbeitet hochsensible Mobilfunk-Zugangsdaten. Reale Ki-,
OPc-, ADM-, PIN-, PUK- oder Teilnehmerdaten dürfen niemals in Git, Issues oder
Testdateien gelangen. Hardware-Schreibtests dürfen ausschließlich mit dafür
vorgesehenen Testkarten und einem vorhandenen Backup erfolgen.

## Projektstatus

`1.0.3` korrigiert zusätzlich die pfadunabhängige Testausführung während der
Neuinstallation. Die Version enthält außerdem den SUCI-Preflight-Fix aus 1.0.2
und die Betriebsdokumentation für PC/SC und benutzerbezogen eingehängte
USB-Datenträger. Die Neuinstallation wird auf einem separaten
Minirechner abgenommen; produktive Offline-Updates sind noch nicht freigegeben. Netzseitige
IMS-Systeme sind nicht Bestandteil dieses Projekts.

## Lizenz

GNU General Public License v3.0 oder später (`GPL-3.0-or-later`) – siehe
[LICENSE](LICENSE).
