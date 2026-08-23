# Installation auf einem Standalone-System

Das Installationsskript unterstützt Prüfung, Vorschau und eine geschützte
Neuinstallation. Die Neuinstallation ist implementiert, für Version 1.0.0 aber
noch nicht auf der vorbereiteten Test-VM abgenommen. Für
bestehende Installationen ist derzeit nur die signierte, nicht verändernde
Offline-Updateprüfung freigegeben.

## Installationsprüfung

Im Wurzelverzeichnis des entpackten Release-Pakets:

```bash
./scripts/install.sh --check
```

Der Prüfmodus benötigt keine Administratorrechte und nimmt keinerlei Änderungen
am Rechner vor. Er kontrolliert Betriebssystem, Python-Version, systemd, OpenSSL
und die PC/SC-Voraussetzungen. Eine bestehende Installation wird nur erkannt,
nicht verändert.

## Installationsvorschau

```bash
./scripts/install.sh --install --dry-run
```

Die Vorschau führt erneut die Voraussetzungenprüfung aus und zeigt anschließend
die geplanten Installationsschritte. Sie benötigt keine Administratorrechte und
verändert ebenfalls nichts.

## Neuinstallation

```bash
sudo ./scripts/install.sh --install
```

Die Neuinstallation fragt verdeckt nach einem mindestens zwölf Zeichen langen
Anmeldepasswort. Sie legt ein eigenes, nicht interaktives Systemkonto an, kopiert
die Anwendung nach `/opt/sim-admin/application`, erstellt die Python-Umgebung,
Zugangsdaten und ein lokales TLS-Zertifikat und richtet die beiden systemd-Dienste
ein. Vor deren Aktivierung wird die komplette Testsuite ausgeführt.

Eine vorhandene Installation wird ausdrücklich nicht überschrieben. Dafür ist
später ausschließlich der gesicherte Offline-Updatepfad vorgesehen.

Offizielle Release-Pakete enthalten ein unter Linux gebautes Wheel-Verzeichnis
mit allen Python-Abhängigkeiten. Die Installation verwendet dieses ohne Zugriff
auf eine externe Paketquelle. Fehlt es in einem lokalen Entwicklungsarchiv, wird
dies deutlich gemeldet und nur die Erstinstallation darf auf die konfigurierte
Paketquelle zurückgreifen.

## Offline-Update prüfen

Ein signiertes Release-Paket wird zunächst ausschließlich geprüft:

```bash
./scripts/offline-update.sh /pfad/zum/sim-admin-1.0.0.tar.gz
```

Neben dem Archiv müssen dessen `.sha256`- und `.sig`-Dateien liegen. Der Prüfer
verwendet ausschließlich den bereits unter `/etc/sim-admin` hinterlegten
öffentlichen Vertrauensanker. Er kontrolliert Signatur, Prüfsumme, jede Datei des
internen Manifests, Versionsfolge, sichere Archivpfade und freien Speicher. In
dieser Stufe werden weder Dateien ersetzt noch Dienste angehalten. Ein
produktiver Updateaustausch mit automatischem Backup und Rollback ist noch offen
und darf nicht durch manuelles Überschreiben der Installation ersetzt werden.

## Nach einer Neuinstallation prüfen

```bash
sudo systemctl status sim-admin sim-admin-redirect pcscd.socket
curl -k https://127.0.0.1:8443/health
```

Danach im Browser anmelden, Kartenleserstatus prüfen, ein Testbackup erstellen
und ausschließlich mit einer vorgesehenen Testkarte einen Read-only-Abgleich
durchführen. Schreibtests sind ein separater Abnahmeschritt.

## Voraussetzungen

- Debian-basiertes Linux
- Python 3.11 oder neuer
- PC/SC-Dienst und kompatibler USB-Kartenleser
- separat installierte pySim-Umgebung
- lokales TLS-Zertifikat

## Anwendung

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m pytest -q
```

Die Anwendung läuft hinter einem systemd-Dienst mit Uvicorn und HTTPS. Lokale
Konfiguration und Geheimnisse werden über eine geschützte Environment-Datei
bereitgestellt. `.env.example` dokumentiert ausschließlich die Variablennamen;
echte Werte gehören nicht in das Repository.

## pySim

pySim wird nicht in den Webprozess importiert. Kartenoperationen laufen über
separate Bridge-Prozesse in einer eigenen Python-Umgebung. Pfade werden über
`SIM_ADMIN_PYSIM_PYTHON` und `SIM_ADMIN_PYSIM_SOURCE` konfiguriert.
