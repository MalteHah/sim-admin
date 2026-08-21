# Offene Punkte und Abnahmetests

Stand: 20. August 2026, Zielversion 0.2.0 (Vorabstand).

## Vor einem ersten stabilen Release zwingend zu testen

- IMS-Schreiben auf einer vorgesehenen SysmocomSJA5: IMPI, IMPU, Domain und IST.
- 5GS-/SUCI-Schreiben im Endgerät: Routing Indicator, UST-Service 124 aktiv,
  Service 125 inaktiv sowie Null Scheme und Profile A/B mit geeignetem
  öffentlichen Testschlüssel.
- Readback, Revisionierung und Abbruchverhalten bei falscher ICCID, falschem ADM1,
  nicht unterstützter Karte, unpassender Dateigröße und entferntem Kartenleser.
- Neuinstallation aus einem vollständig offline gebauten Release-Paket auf der
  vorbereiteten Test-VM.
- Signatur-, Prüfsummen-, Versions- und Speicherplatzprüfung eines Updatepakets
  vom USB-Stick.
- Vollständige Updateausführung einschließlich automatischem Vorab-Backup und
  Rückkehr zur vorherigen Version. Dieser Teil ist noch nicht implementiert.
- Backup und Restore eines realistischen Profiltresors auf einem zweiten
  Datenträger; danach Anmeldung, Historie und Entschlüsselung stichprobenartig
  prüfen.

## Noch zu entwickeln

- Feldweiser Kartenabgleich für auslesbare IMS- und 5GS-Werte mit selektiver
  Übernahme in den Profiltresor. Ki, OPc und ADM1 bleiben ausgeschlossen.
- Mehrere Home-Network-Schlüssel und mehrere Protection-Scheme-Einträge mit
  Prioritätsverwaltung.
- S17-spezifische SUCI-Berechnung auf der USIM über `DF.SAIP` und Profile B mit
  unkomprimiertem öffentlichen Schlüssel.
- Produktiver Offline-Updatepfad mit Sicherung, atomarem Austausch,
  Datenbankschema-Prüfung und Rollback.
- Bedienoberfläche und Fehlermeldungen nach den Hardwaretests nachschärfen.
- Finales Release-Paket, signierter Tag und abschließende Release Notes.

## Zurückgestellte Integrationstests

Die Open5GS-Netzregistrierung wird nach den Kartentests geprüft. Kamailio-IMS ist
derzeit ein eigenständiger, größerer Integrationsblock und wird separat
analysiert. Erst nach funktionsfähigem P-/I-/S-CSCF-Aufbau folgen:

- IMS-Registrierung der vorgesehenen Teilnehmer,
- Zuordnung von IMPI, IMPU und Nebenstelle,
- Gespräche in beide Richtungen,
- Prüfung, dass programmierte IMS-/SUCI-Werte tatsächlich verwendet werden.

Kamailio-IMS blockiert nicht die lokale Weiterentwicklung oder Dokumentation von
SIM-Admin, wohl aber die Ende-zu-Ende-Abnahme der IMS-Funktionen.
