# Umsetzungsbericht

## Architektur

Der ursprüngliche Bot bleibt unter `legacy_sources/` vollständig erhalten.
Die produktiven Module arbeiten servergetrennt mit SQLite und persistenten
Discord-Komponenten. `.env`, Logs, Datenbanken und Nutzerdaten werden nicht
versioniert.

## Umgesetzt

- zentrale `/settings`-Oberfläche für Rollen, Zuständigkeiten, Rechte und Kanäle
- neue Teamhierarchie ohne Media, mit Test Developer und ausschließlicher
  Anzeige der höchsten Rolle
- Teamliste im 30-Sekunden-Takt sowie sofortige Aktualisierung bei Rollenwechsel
- Team-Statistikpanel mit Aktionszahlen und klickbarem Moderationsverlauf
- Moderations-DMs mit Aktion, Grund und gegebenenfalls Dauer
- Minecraft-Panel im 15-Sekunden-Takt; geschützte Online-Spielerliste
- kurze, relevante Formulare für Test Supporter, Test Developer, Media und Partner
- individuelle Testzeiten von 30/14/14/7 Tagen und thematische Annahme-/Absage-DMs
- dauerhaftes Bewerbungsarchiv mit Spieler- und Typauswahl
- frei platzierbare Ticketpanels, Ticketarten, Kategorien und mehrere Staffrollen
- vollständige HTML-Tickettranskripte und durchsuchbares Archiv
- atomarer Giveaway-Abschluss und genau einmal einlösbares Gewinner-Ticket
- permanentes Command-Panel mit unverändertem Hauptpanel und privaten Detailseiten
- Datenbankindizes und Eindeutigkeitsregeln gegen doppelte offene Vorgänge

## Kompatibilität

Vorhandene `data/bot.db` wird beim Start idempotent um neue Tabellen und Indizes
erweitert. Bestehende `.env`-Standardrollen werden bei der ersten Verwendung als
Fallback übernommen; danach kann die Verwaltung vollständig über `/settings`
erfolgen.

## Prüfung

- Kompilierung aller Python-Dateien
- Ruff-Prüfung
- acht automatisierte Tests für Module, Schema, Guild-Isolation, Teamhierarchie
  und Bewerbungsfristen
- Ladeprüfung aller 15 produktiven Extensions und 13 persistenten Views
- `git diff --check` und Secret-Suche vor Veröffentlichung

Ein echter Discord-End-to-End-Test benötigt den produktiven Token und die Guild
und muss nach dem Pull auf dem Server erfolgen.
