# Installation auf einem Standalone-System

Die aktuelle Installation wird noch manuell verwaltet. Ein reproduzierbares
Installationsskript und signierte Offline-Updates sind als nächste
Bereitstellungsstufe vorgesehen.

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
