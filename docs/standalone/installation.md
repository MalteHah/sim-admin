# Installation auf einem Standalone-System

Die Installation wird schrittweise automatisiert. Der erste, nicht verändernde
Prüfmodus kontrolliert die Systemvoraussetzungen. Die eigentliche Installation
und signierte Offline-Updates folgen in den nächsten Bereitstellungsstufen.

## Installationsprüfung

Im Wurzelverzeichnis des entpackten Release-Pakets:

```bash
./scripts/install.sh --check
```

Der Prüfmodus benötigt keine Administratorrechte und nimmt keinerlei Änderungen
am Rechner vor. Er kontrolliert Betriebssystem, Python-Version, systemd, OpenSSL
und die PC/SC-Voraussetzungen. Eine bestehende Installation wird nur erkannt,
nicht verändert.

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
