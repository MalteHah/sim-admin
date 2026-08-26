# Installation auf einem Standalone-System

Das Installationsskript unterstützt Prüfung, Vorschau und eine geschützte
Neuinstallation. Version 1.0.1 ergänzt den vollständigen Offline-pySim-Pfad; die
Neuinstallation wird auf einem separaten Debian-13-Minirechner abgenommen. Für
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
die Anwendung nach `/opt/sim-admin/application`, pySim nach
`/opt/sim-admin/pysim`, erstellt beide getrennten Python-Umgebungen, Zugangsdaten
und ein lokales TLS-Zertifikat und richtet die beiden systemd-Dienste ein. Vor
deren Aktivierung werden pySim-Importtests und die komplette Anwendungstestsuite
ausgeführt. Ein fehlgeschlagener Erstlauf entfernt seine unvollständigen Dateien.

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
./scripts/offline-update.sh /pfad/zum/sim-admin-1.0.1.tar.gz
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

### Reader unter Debian 13 nicht sichtbar

Wenn `pcscd` den Prozess des Dienstkontos mit `Rejected unauthorized PC/SC
client` beziehungsweise `NOT authorized for action: access_pcsc` ablehnt,
blockiert Polkit den nicht interaktiv angemeldeten Benutzer `sim-admin`. In
diesem Fall wird folgende, ausschließlich auf dieses Dienstkonto und die beiden
PC/SC-Aktionen begrenzte Regel benötigt:

```javascript
polkit.addRule(function(action, subject) {
    if (
        subject.user === "sim-admin" &&
        (
            action.id === "org.debian.pcsc-lite.access_pcsc" ||
            action.id === "org.debian.pcsc-lite.access_card"
        )
    ) {
        return polkit.Result.YES;
    }

    return polkit.Result.NOT_HANDLED;
});
```

Die Datei wird als
`/etc/polkit-1/rules.d/60-sim-admin-pcsc.rules` mit Modus `0644` gespeichert.
Polkit erkennt neue beziehungsweise geänderte Regeln normalerweise automatisch;
auf dem Debian-13-Testrechner war kein Dienstneustart erforderlich. Danach kann
der Zugriff unter dem tatsächlichen Dienstkonto geprüft werden:

```bash
runuser -u sim-admin -- /opt/sim-admin/venv/bin/python -c \
  'from smartcard.System import readers; print(readers())'
```

Ein Neustart von `pcscd` oder SIM-Admin ist nur nötig, wenn die Regel nicht
automatisch wirksam wird.

## Voraussetzungen

- Debian-basiertes Linux
- Python 3.11 oder neuer
- `python3`, `python3-venv`, `openssl`, `tar` und systemd
- `pcscd`, `libpcsclite1` und `libccid`
- kompatibler USB-Kartenleser
- lokales TLS-Zertifikat

Das offizielle Release-Asset enthält die Python-Wheels sowie den getesteten
pySim-Commit aus `PYSIM_REVISION`. Daher werden `build-essential`, `swig`,
`pkg-config` und `libpcsclite-dev` nur benötigt, wenn bewusst ohne das
Offline-Wheelpaket aus einem Quellbaum installiert wird. `install.sh --check`
nennt jedes fehlende Debian-Paket einzeln und nimmt keine Änderungen vor.
Direkte Git-Abhängigkeiten des festgelegten pySim-Stands werden ausschließlich
beim signierten Release-Bau aufgelöst. Das Zielsystem installiert danach nur die
mitgelieferten Wheels anhand einer eingefrorenen Offline-Anforderungsliste.

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

Seit Version 1.0.1 installiert das Standalone-Skript den im Release enthaltenen,
auf der Referenz-VM getesteten pySim-Stand automatisch nach
`/opt/sim-admin/pysim`. Seine getrennte Python-Umgebung liegt unter
`/opt/sim-admin/venv`. Die Installation endet nur erfolgreich, wenn sich die
benötigten pySim-, PC/SC- und Smartcard-Module importieren lassen.
