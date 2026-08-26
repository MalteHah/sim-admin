# Release Notes – SIM-Admin 1.0.1

## Schwerpunkt

Version 1.0.1 korrigiert den auf einem separaten Debian-13-Minirechner
aufgedeckten unvollständigen Installationspfad von Version 1.0.0.

## Geändert

- Das signierte Offline-Release enthält den auf der Referenz-VM getesteten
  pySim-Commit `9c77e4ed948e97584680a0b1c1a630bc7fa6bfcd`.
- pySim und seine Python-Abhängigkeiten werden automatisch in einer vom
  Webserver getrennten Umgebung installiert.
- Fehlende Debian-Pakete werden mit ihrem exakten Paketnamen gemeldet.
- Bei Verwendung des vollständigen Offline-Release-Assets sind keine lokalen
  Python-Buildwerkzeuge erforderlich.
- Nach einem Installationsfehler werden ausschließlich die in diesem Lauf neu
  angelegten, unvollständigen Installationsdateien entfernt.

## Unverändert

Der Kartenfunktionsumfang entspricht Version 1.0.0. ADM1 wird weiterhin nur zur
Autorisierung verwendet und niemals gelesen, geändert, entsperrt oder auf eine
Karte geschrieben.

## Abnahme

Der Installer wird mit dem signierten Release-Asset auf einem separaten
Debian-13-Minirechner geprüft. Produktive Offline-Updates bleiben außerhalb
dieses Patch-Releases.
