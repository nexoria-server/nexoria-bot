# Nexoria Bot

Ein modularer Discord-Management-Bot für mehrere Guilds. Konfigurationen, Rollen,
Panels und Verlaufsdaten werden pro Guild in SQLite gespeichert; Discord-IDs sind
nicht im Code hinterlegt.

## Start

```bash
python -m venv .venv
.venv/Scripts/pip install -e .
copy .env.example .env
python -m nexoria
```

Benötigt Python 3.11+, den aktivierten **Server Members Intent** und einen
Bot-Token. Mit `/config` wird die Guild eingerichtet. `/commands` zeigt alle
verfügbaren Befehle und deren Parameter automatisch an.

## Wichtige Befehle

- `/config` – zentrales Administrationspanel
- `/team panel` und `/team-leitungs-panel` – automatisch aktualisierte Panels
- `/moderation …` – Warn, Timeout, Kick, Ban und Verlauf mit DM/Logging
- `/ticket panel` – Ticket-Auswahl; geschlossene Tickets werden archiviert
- `/application panel` – konfigurierbare Bewerbungsarten und Testphasen
- `/announce` – Vorschau und kontrollierter Versand
- `/minecraft configure` – gecachter Serverstatus im 15-Sekunden-Takt

## Tests

```bash
pytest
ruff check .
```

Die Datenbank wird beim Start automatisch migriert. `data/` und `.env` werden
nicht versioniert.

## Ursprüngliche Dateien

Alle vom Auftraggeber bereitgestellten Dateien liegen vollständig und mit ihren
ursprünglichen Dateinamen unter `legacy_sources/`. Sie werden nicht automatisch
geladen, da sie feste Discord-IDs und nicht vorhandene `bot.*`-Abhängigkeiten
enthalten. Die startfähige Überarbeitung befindet sich unter `nexoria/`.
