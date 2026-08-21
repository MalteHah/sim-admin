# Vorläufige Bedienungsanleitung

Diese Anleitung beschreibt den Funktionsstand der Vorabversion 0.2.0. Für reale
SIM-Daten sollte vor jedem Schreibtest ein aktuelles USB-Backup vorhanden sein.

## Anmeldung und Übersicht

SIM-Admin wird im Browser über `https://<rechner>:8443` geöffnet. Nach der
Anmeldung zeigt die Übersicht Kartenleser, Kartenstatus und die wichtigsten
Arbeitsbereiche. Eine Sitzung läuft automatisch ab; das Anzeigen von
Geheimnissen und gefährliche Vorgänge verlangen das Passwort erneut.

## CSV-Datei importieren

1. **CSV-Import** öffnen und eine vorbereitete CSV-Datei auswählen.
2. Die Vorschau vollständig prüfen. Fehler werden zeilen- und feldbezogen, aber
   ohne Ausgabe geheimer Werte angezeigt.
3. Nur eine vollständig gültige Datei kann verschlüsselt gespeichert werden.

Pflichtfelder sind ICCID, IMSI, Ki, OPc und ADM1. Optional sind unter anderem
MSISDN, ACC, IMPI, IMPU, IMS-Domain, IST, Routing Indicator, Protection Scheme,
HN Public Key ID und HN Public Key. Profile A benötigt einen 32-Byte-Schlüssel;
Profile B einen 33- oder 65-Byte-Schlüssel.

## Einzelkarte erfassen

Unter **Einzelkarte** gibt es zwei Arbeitsweisen:

- **Karte zuerst:** Die Anwendung liest ICCID und IMSI und verhindert eine
  Dublette im Profiltresor.
- **Daten zuerst:** Das Profil wird vorbereitet und als noch nicht
  kartengeprüft gekennzeichnet.

Nach Eingabe der übrigen Daten wird zuerst ein Dry Run erzeugt. Erst danach kann
das Profil verschlüsselt als Revision 1 gespeichert werden. Dieser Vorgang
schreibt nichts auf die SIM.

## Profiltresor

Der Profiltresor bietet Suche nach ICCID/IMSI, Sortierung, Filter,
Seitennavigation, Revisionshistorie und folgende Aktionen:

- **Dry Run:** zeigt den geplanten Zielzustand ohne Kartenänderung.
- **Karte abgleichen/zuordnen:** liest ICCID und IMSI und vergleicht sie.
- **Geheimnisse anzeigen:** verlangt das Passwort erneut und verdeckt die Werte
  automatisch nach 30 Sekunden.
- **Änderung vorbereiten:** speichert einen verschlüsselten Entwurf, ohne die
  aktive Revision oder Karte zu ändern.
- **Profil löschen:** löscht Profil, Revisionen und Entwurf erst nach Passwort-
  und ICCID-Bestätigung.
- **Verwaltung:** markiert eine Karte als „Im Bestand“ oder „Ausgegeben“. Bei
  Ausgabe werden Name und Datum erfasst; eine optionale Bemerkung ist auf 500
  Zeichen begrenzt. Diese Angaben ändern weder SIM-Daten noch Profilrevision.

Die Liste kann zusätzlich nach Bestandsstatus gefiltert werden. Der
Inventarexport enthält Status, Ausgabeangaben und Bemerkung, aber weiterhin keine
SIM-Geheimnisse.

## Auf eine SIM schreiben

Ein Schreibvorgang ist nur über einen gespeicherten Änderungsentwurf möglich.
Vor der Freigabe sollten Dry Run und Kartenabgleich ausgeführt werden. Danach
sind das aktuelle Passwort und exakt `SIM SCHREIBEN` einzugeben.

Die Anwendung prüft ICCID und ADM1. Ki/OPc, IMS- sowie 5GS-/SUCI-Felder werden
nur auf einer eindeutig erkannten SysmocomSJA5 geschrieben. Betroffene Dateien
werden vorab geprüft und nach dem Schreiben unmittelbar zurückgelesen. Eine neue
Tresorrevision entsteht erst nach vollständigem Erfolg.

ICCID und ADM1 sind in Änderungsentwürfen absichtlich nicht veränderbar.

## Aktivitätsprotokoll

Das Aktivitätsprotokoll enthält Vorgangsart, Ergebnis, Zeitpunkt und redigierte
Statusangaben. Ki, OPc, ADM1, Passwörter und vollständige Formulardaten werden
nicht protokolliert.

## Datensicherung

Die Bedienung von Backup und Wiederherstellung beschreibt die
[Backup- und Wiederherstellungsanleitung](standalone/backup-restore.md).
