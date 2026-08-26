# Release Notes – SIM-Admin 1.0.2

## Schwerpunkt

Version 1.0.2 korrigiert den Vorabtest beim Wechsel von SUCI-Berechnung auf der
USIM zu Null Scheme im Endgerät.

## Korrigiert

- Die für Null Scheme vorgesehene `EF.SUCI_Calc_Info` wird vor dem Schreiben roh
  auf Lesbarkeit geprüft. Ein leerer oder veralteter Inhalt einer zuvor
  inaktiven Datei blockiert den Wechsel nicht mehr durch einen unnötigen
  Decodierversuch.
- Die Vorabprüfung der SUCI-Zieldatei und die Prüfung der UST-Dienste melden
  getrennte Fehlerstufen.

## Dokumentation

- Die unter Debian 13 benötigte, auf das Dienstkonto `sim-admin` begrenzte
  PC/SC-Polkit-Freigabe ist dokumentiert.
- Für benutzerbezogen unter `/media` eingehängte USB-Datenträger ist die Diagnose
  der Pfadrechte sowie eine gezielte ACL-Lösung beschrieben. Der Datenträgername
  ist nicht fest vorgegeben.

## Unverändert

Der Kartenfunktionsumfang entspricht Version 1.0.1. ADM1 wird weiterhin nur zur
Autorisierung verwendet und niemals gelesen, geändert, entsperrt oder auf eine
Karte geschrieben. Produktive Offline-Updates sind weiterhin nicht freigegeben.

## Empfohlener Test

Mit einer vorgesehenen Testkarte einen Änderungsentwurf von SUCI-Berechnung auf
der USIM zu Null Scheme erstellen, zuerst den Dry Run und Kartenabgleich
ausführen und anschließend den kontrollierten Schreibvorgang samt Rückprüfung
abschließen. Bei einem Fehler keine wiederholten Schreibversuche starten,
sondern die gemeldete Stufe und das Aktivitätsprotokoll prüfen.
