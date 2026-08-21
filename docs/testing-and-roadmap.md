# Offene Punkte und Abnahmetests

Stand: 21. August 2026, Zielversion 0.2.0 (Vorabstand).

## Erfolgreich geprüft

- SysmocomSJA5: Routing Indicator `0000`, Null Scheme, Profile A (X25519) mit
  HN-Key-ID 1 und Profile B (P-256) mit HN-Key-ID 2 wurden geschrieben und
  unmittelbar zurückgelesen. UST-Service 124 war aktiv und 125 inaktiv.
- Open5GS hat sowohl die unverschlüsselte Null-Scheme-SUCI als auch die mit
  Profile A beziehungsweise Profile B geschützten SUCIs verarbeitet, jeweils
  zur erwarteten IMSI aufgelöst und die 5G-Registrierung abgeschlossen.
- Der Profiltresor-Kartenabgleich liest diese SUCI-Werte künftig ohne
  Schreibzugriff zurück und vergleicht sie mit der aktiven Revision.
- SysmocomSJA5: IMPI, IMPU, IMS-Domain und IST wurden als Änderungsentwurf
  geschrieben, unmittelbar zurückgelesen und erst nach erfolgreicher Prüfung
  als neue Tresorrevision übernommen.
- Das anschließende Löschen aller IMS-Werte wurde ebenfalls geschrieben und
  zurückgelesen. Ein erster fehlgeschlagener Versuch ließ aktive Revision und
  Änderungsentwurf unverändert; nach der Korrektur entstand regulär Revision 4.
- Der rein lesende IMS-Kartenabgleich erkennt sowohl belegte als auch vollständig
  geleerte ISIM-Felder und vergleicht IMPI, IMPU, Domain und IST einzeln.
- Sicherheitsabbruch bei entfernter Karte und bei abweichender ICCID wurde ohne
  Revision und unter Erhalt des Änderungsentwurfs geprüft. Eine absichtlich
  falsche ADM1 wurde genau einmal abgelehnt; weitere reale Fehlversuche wurden
  zum Schutz des ADM-Zählers ausgeschlossen.

## Vor einem ersten stabilen Release zwingend zu testen

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

- Spätere selektive Übernahme abweichender, auslesbarer IMS-/5GS-Werte. Der
  lesende Feldvergleich ist umgesetzt; Ki, OPc und ADM1 bleiben ausgeschlossen.
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
