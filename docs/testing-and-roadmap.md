# Offene Punkte und Abnahmetests

Stand: 23. August 2026, Zielversion 0.2.0 (Vorabstand).

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
- Der Abbruch für einen nicht unterstützten Kartentyp wurde mit simuliertem
  Adapter ohne realen ADM-Versuch geprüft: Revision und Entwurf bleiben erhalten.
- Eine unpassende IST-Dateigröße wurde simuliert und eindeutig abgebrochen;
  Revision und Entwurf bleiben ebenfalls unverändert.
- Die selektive Kartenübernahme wurde mit einer ausschließlich auf der Karte
  abweichenden IMS-Domain praktisch geprüft: Nur das betroffene Feld wurde nach
  erneuter Karten- und Passwortprüfung als Revision 2 übernommen; die SIM blieb
  beim Übernahmevorgang unverändert.
- ACC und MSISDN werden zusätzlich rein lesend aus der Karte ermittelt, einzeln
  mit dem Tresorprofil verglichen und können bei einer Abweichung selektiv als
  neue Tresorrevision übernommen werden. Der automatisierte Stand ist geprüft;
  die Abnahme mit einer realen Karte steht noch aus.
- Mehrere Protection-Scheme-Einträge und zugehörige HN-Schlüssel werden aus
  `EF.SUCI_Calc_Info` vollständig aufgelöst und nach Kartenpriorität angezeigt.
  Die Bearbeitung, Validierung und der gemeinsame Schreibpfad für bis zu acht
  priorisierte Einträge sind implementiert; der reale Mehrfacheintrag-Kartentest
  steht noch aus.

## Vor einem ersten stabilen Release zwingend zu testen

- Neuinstallation aus einem vollständig offline gebauten Release-Paket auf der
  vorbereiteten Test-VM.
- Signatur-, Prüfsummen-, Versions- und Speicherplatzprüfung eines Updatepakets
  vom USB-Stick.
- Vollständige Updateausführung einschließlich automatischem Vorab-Backup und
  Rückkehr zur vorherigen Version. Dieser Teil ist noch nicht implementiert.
- Backup und Restore eines realistischen Profiltresors auf einem zweiten
  Datenträger; danach Anmeldung, Historie und Entschlüsselung stichprobenartig
  prüfen.

## Karten-Roadmap

### Revision 1 – implementiert

- SUCI-Berechnung direkt auf der USIM ist auf S17 mit Profile B und UST 124/125
  Ende-zu-Ende gegen Open5GS geprüft.
- Mehrere Home-Network-Schlüssel und Protection-Scheme-Einträge einschließlich
  Prioritätsverwaltung sind implementiert und auf Karte 900001 abgenommen. Das
  Endgerät wählte Profile B mit HN-Key-ID 2; Open5GS schloss die Registrierung
  erfolgreich ab.
- ACC und MSISDN werden rein lesend verglichen und können einzeln in eine neue
  Tresorrevision übernommen werden.

Damit ist der geplante Funktionsumfang der Karten-Revision 1 einschließlich der
Hardware-Abnahme umgesetzt.

### Revision 2 – spätere Kartenfunktionen

- Weitere Kartentypen und Hersteller unterstützen.
- S17-spezifische Dateien und Parameter sowie weitere kartenspezifische
  SUCI-Varianten.
- Erweiterte IMS-Kartenstrukturen, darunter zusätzliche Dateien und mehrere
  Datensätze.
- Geführte Stapelverarbeitung mehrerer Karten.
- Erkennung, Bestandsaufnahme und geführte Wiederaufnahme nach Unterbrechung
  eines Schreibvorgangs.

### Verbindliche ADM1-Grenze

- ADM1 wird nur zur Autorisierung eines ausdrücklich freigegebenen
  Schreibvorgangs geprüft.
- SIM-Admin liest ADM1 nicht von der Karte, übernimmt es nicht von der Karte und
  ändert, entsperrt oder schreibt ADM1 niemals.

## Noch zu entwickeln – Betrieb und Veröffentlichung

- Produktiver Offline-Updatepfad mit Sicherung, atomarem Austausch,
  Datenbankschema-Prüfung und Rollback.
- Bedienoberfläche und Fehlermeldungen nach den Hardwaretests nachschärfen.
- Finales Release-Paket, signierter Tag und abschließende Release Notes.

Netzseitige IMS-Systeme sind ausdrücklich nicht Bestandteil dieser Karten-
Roadmap und werden in einem getrennten Projektblock behandelt.
