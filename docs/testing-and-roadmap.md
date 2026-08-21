# Offene Punkte und Abnahmetests

Stand: 21. August 2026, Zielversion 0.2.0 (Vorabstand).

## Erfolgreich geprüft

- SysmocomSJA5: Routing Indicator `0000`, Profile A (X25519), HN-Key-ID 1,
  öffentlicher Schlüssel sowie UST-Service 124 aktiv und 125 inaktiv wurden
  geschrieben und unmittelbar zurückgelesen.
- Open5GS hat die verschlüsselte SUCI mit Scheme 1 und Key ID 1 verarbeitet,
  zur erwarteten IMSI aufgelöst und die 5G-Registrierung abgeschlossen.
- Der Profiltresor-Kartenabgleich liest diese SUCI-Werte künftig ohne
  Schreibzugriff zurück und vergleicht sie mit der aktiven Revision.

## Vor einem ersten stabilen Release zwingend zu testen

- IMS-Schreiben auf einer vorgesehenen SysmocomSJA5: IMPI, IMPU, Domain und IST.
- Verbleibende 5GS-/SUCI-Varianten: Null Scheme und Profile B mit geeignetem
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

- Feldweiser Kartenabgleich für auslesbare IMS-Werte sowie eine spätere
  selektive Übernahme. Der 5GS-/SUCI-Abgleich ist bereits lesend umgesetzt;
  Ki, OPc und ADM1 bleiben ausgeschlossen.
- Mehrere Home-Network-Schlüssel und mehrere Protection-Scheme-Einträge mit
  Prioritätsverwaltung.
- S17-spezifische SUCI-Berechnung auf der USIM über `DF.SAIP` und Profile B mit
  unkomprimiertem öffentlichen Schlüssel.
- Produktiver Offline-Updatepfad mit Sicherung, atomarem Austausch,
  Datenbankschema-Prüfung und Rollback.
- Bedienoberfläche und Fehlermeldungen nach den Hardwaretests nachschärfen.
- Finales Release-Paket, signierter Tag und abschließende Release Notes.

## Zurückgestellte Integrationstests

Die Open5GS-Netzregistrierung mit verschlüsselter SUCI wurde erfolgreich
geprüft. Kamailio-IMS ist derzeit ein eigenständiger, größerer Integrationsblock und wird separat
analysiert. Erst nach funktionsfähigem P-/I-/S-CSCF-Aufbau folgen:

- IMS-Registrierung der vorgesehenen Teilnehmer,
- Zuordnung von IMPI, IMPU und Nebenstelle,
- Gespräche in beide Richtungen,
- Prüfung, dass programmierte IMS-/SUCI-Werte tatsächlich verwendet werden.

Kamailio-IMS blockiert nicht die lokale Weiterentwicklung oder Dokumentation von
SIM-Admin, wohl aber die Ende-zu-Ende-Abnahme der IMS-Funktionen.
