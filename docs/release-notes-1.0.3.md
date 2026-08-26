# Release Notes – SIM-Admin 1.0.3

## Schwerpunkt

Version 1.0.3 korrigiert die abschließende Testsuite der Neuinstallation.

## Korrigiert

- Der Installer wechselt für die Abnahme ausdrücklich nach
  `/opt/sim-admin/application`, bevor er die Tests startet.
- Der POSIX-Syntaxtest bestimmt `scripts/install.sh` ausgehend vom Speicherort
  der Testdatei und funktioniert damit unabhängig vom Aufrufverzeichnis.

Dadurch tritt der irreführende Fehler `cannot open scripts/install.sh` nach 99
erfolgreichen Tests nicht mehr auf.

## Enthalten

Version 1.0.3 enthält ebenfalls den SUCI-Preflight-Fix aus Version 1.0.2 und den
vollständigen Offline-pySim-Installationspfad aus Version 1.0.1. Der
Kartenfunktionsumfang und die verbindliche ADM1-Grenze bleiben unverändert.
