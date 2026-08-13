# Umsetzungsbericht

## Ausgangslage

Das Ziel-Repository enthielt nur eine README. Die separat gelieferten Module
waren kein startfähiges Projekt: Basismodule fehlten, Guild-/Rollen-/Kanal-IDs
waren hart codiert und Daten wurden parallel in globalen JSON-Dateien und einer
SQLite-Datei gespeichert. Daher wurde eine konsistente, installierbare Basis
erstellt.

## Implementiert

- Zentrale SQLite-Datenbank mit automatischem Schemaaufbau, WAL und Indizes
- Strikte Trennung aller Einstellungen und Daten über `guild_id`
- Rollen- und Berechtigungsauswahl über Discord Role Selects
- Exakte Teamhierarchie: Owner zuerst, Test Supporter zuletzt, kein Media
- Nur die höchste Teamrolle pro Mitglied; Update alle 30 Sekunden und bei
  Rollenänderungen; keine Discord-Bearbeitung ohne Inhaltsänderung
- Team-Leitungs-Panel mit den sechs exakt geforderten Standardbereichen,
  mehreren Rollen/Personen und Mehrfachzuordnung von Personen
- Moderation: Warn, Timeout, Kick, Ban, DM mit Grund, Verlauf und Teamstatistik
- Ticketarten, Kategorien und mehrere Staff-Rollen; persistente Views,
  Duplikatschutz, Transkript und Archiv
- Bewerbungsarten, Archivdaten, Rollenvergabe, Testzeiten und typbezogene DMs
- Test-Supporter-Onboarding mit Platzhaltern und Mentor; ausschließlich für
  Test Supporter und über den Bewerbungsstatus gegen Doppelversand geschützt
- Announcement-Vorschau, Kanal-/Ping-Auswahl und serverseitige Berechtigung
- Giveaways mit persistenter Teilnahme, Gewinnerermittlung und genau einem
  Gewinn-Ticket pro Gewinner/Giveaway; kein Ticketversand per DM
- Minecraft-Status alle 15 Sekunden, Request-Lock und update-on-change
- Willkommen/Verabschiedung, Audit-Logs, Anti-Spam und frei postbare Regeln
- Automatisch aus dem Command Tree erzeugte Command-Übersicht
- Persistente Views werden beim Neustart registriert

## Datenbank

Tabellen: `guild_settings`, `role_bindings`, `panels`,
`moderation_actions`, `tickets`, `applications`,
`leadership_sections`, `giveaways`, `giveaway_entries` und
`giveaway_claims`. Das Schema wird idempotent beim Start angelegt.

## Einrichtung

1. Token und optionalen Datenbankpfad in `.env` setzen.
2. Server Members Intent im Discord Developer Portal aktivieren.
3. Bot mit den benötigten Kanal-, Rollen- und Moderationsrechten einladen.
4. Mit `/config`, `/config-channel`, `/ticket category` und
   `/minecraft configure` die jeweilige Guild konfigurieren.
5. Panels in den gewünschten Kanälen veröffentlichen.

## Tests

- Python-Bytecode-Kompilierung
- Laden aller Extensions und 27 Slash-Commands
- Ruff-Formatierung und statische Prüfung
- Unit-Tests für exakte Hierarchie, höchste Rolle, Standard-Leitungsbereiche
  und vollständige Multi-Guild-Datentrennung

## Bekannte Einschränkungen

- Ein Live-End-to-End-Test gegen einen echten Discord- und Minecraft-Server
  benötigt Token, Guild und Serveradresse und wurde lokal nicht ausgeführt.
- Discords Embed-Grenzen erzwingen bei sehr großen Teamlisten eine spätere
  Pagination/Mehrnachrichten-Darstellung.
- Das Announcement-Command unterstützt aktuell einen Rollen-Ping je Nachricht;
  `@everyone` und `@here` sind ebenfalls verfügbar. Eine Multi-Role-Auswahl
  im Vorschau-Workflow ist eine noch offene Erweiterung.
- Frei erstellbare Bewerbungs- und Tickettypen sowie das Hinzufügen/Bearbeiten
  eigener Leitungsbereiche sind im Datenmodell vorbereitet, im Discord-Panel
  aber noch nicht vollständig als CRUD-Oberfläche umgesetzt.
- Archivsuche und Verlauf liefern aktuell begrenzte Ergebnislisten statt einer
  interaktiven Pagination.
