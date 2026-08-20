# Vorläufige Release Notes – SIM-Admin 0.2.0

Status: **Vorabstand – noch kein freigegebenes Produktionsrelease**.

## Schwerpunkt

Version 0.2.0 bildet erstmals den vollständigen lokalen Arbeitsablauf vom
CSV-Import oder der Einzelkartenerfassung über den verschlüsselten Profiltresor
bis zum kontrollierten, zurückgelesenen SIM-Schreibvorgang ab.

## Enthalten

- Offline-fähige, passwortgeschützte HTTPS-Webanwendung.
- PC/SC-Lesererkennung und ausschließlich lesende Kartenidentifikation.
- Validierter sysmocom-CSV-Import und Einzelkartenerfassung.
- Gerätegebunden verschlüsselter Profiltresor mit Revisionen und Entwürfen.
- Suche, Sortierung, Filterung, Seitennavigation und redigierter Inventarexport.
- Kontrolliertes Schreiben von IMSI, ACC, MSISDN sowie auf SysmocomSJA5 Ki/OPc,
  IMS- und 5GS-/SUCI-Feldern.
- AES-256-GCM-verschlüsselte USB-Backups einschließlich Profiltresorschlüssel und
  geprüfter Wiederherstellung.
- Installationsprüfung, Neuinstallationsskript, reproduzierbare Releasepakete,
  Ed25519-Signaturen und rein lesende Offline-Updateprüfung.

## Bekannte Einschränkungen

- Die neuen IMS- und 5GS-/SUCI-Schreibpfade benötigen noch Hardware-Abnahmetests.
- Der produktive Updateaustausch und Rollback sind noch nicht implementiert.
- Es wird derzeit ein einzelner SUCI-Schutzmechanismus mit einem öffentlichen
  Home-Network-Schlüssel verwaltet.
- Der feldweise erweiterte Kartenabgleich ist noch offen.
- Kamailio-IMS ist nicht betriebsbereit; Ende-zu-Ende-IMS-Tests sind daher
  zurückgestellt.

## Freigabebedingung

Ein GitHub-Tag und ein als stabil bezeichnetes Release sollen erst nach den in
[Offene Punkte und Abnahmetests](testing-and-roadmap.md) dokumentierten
Hardware-, Installations-, Update- und Wiederherstellungstests erstellt werden.

