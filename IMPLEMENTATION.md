# Umsetzungsbericht

## Grundlage

Der vollständige vom Auftraggeber gelieferte ZIP-Stand ist die kanonische
Anwendung. Produktive Dateien wie `.env`, Logs, JSON-Nutzerdaten und SQLite-
Datenbanken werden aus Sicherheits- und Datenschutzgründen nicht versioniert.

## Überarbeitet

- alle 13 vorhandenen Cogs in die startfähige Paketstruktur übernommen
- fehlerhaften Announcement-Modulnamen und fehlendes Invite-Modul korrigiert
- Modulfehler brechen den Start sichtbar ab, statt unbemerkt Features auszulassen
- fehlerhafte Unicode-/Emoji-Kodierung im gesamten Python-Code repariert
- sämtliche Discord-IDs aus dem Code in `.env`-Konfiguration verschoben
- Daten-, Log- und Datenbankpfade absolut und unabhängig vom Startverzeichnis
- SQLite-Verzeichnisse und Tabellen werden idempotent angelegt; WAL und Indizes
- Minecraft-Panel multi-guild-persistent, 15-Sekunden-Takt, Request-Lock,
  Online-Spieler und Bearbeitung nur bei Inhaltsänderung
- Teamhierarchie korrigiert: Owner zuerst, Test Supporter zuletzt, kein Media;
  Mitglieder erscheinen nur unter ihrer höchsten konfigurierten Rolle
- Moderations-Hierarchieprüfung, DMs, dauerhafte Aktionen und Verlauf ergänzt
- Anti-Spam robuster gemacht und Raid-Logmeldungen gedrosselt
- Secrets, virtuelle Umgebung, Logs und produktive Daten zuverlässig ignoriert
- Vionity-Installations- und Updateanleitung ergänzt

## Datenmigration

Vorhandene `data/bot.db` bleibt kompatibel und wird beim Start erweitert.
Die ursprüngliche `team_panel.db` kann nach `data/team_panel.db` verschoben
oder über `TEAM_DB_PATH` referenziert werden. Vor der ersten Aktualisierung
sollte ein Backup beider Datenbanken angelegt werden.

## Prüfung

- Kompilierung aller Python-Dateien
- Import sämtlicher Module
- isolierter SQLite-Schema- und Multi-Guild-Test
- statische Prüfung auf Syntax-/Namensfehler
- Secret- und Hardcoding-Suche

Ein vollständiger Discord-End-to-End-Test benötigt den produktiven Token und
die konfigurierte Guild und wird deshalb erst nach dem Deployment ausgeführt.
