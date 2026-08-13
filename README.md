# Nexoria Craft Discord Bot

Professioneller, persistenter Multi-Guild-Bot für Tickets, Bewerbungen,
Teamverwaltung, Moderation, Giveaways, Minecraft-Status, Announcements,
Einladungen, Regeln, Welcome/Leave, Logging und Sicherheit.

## Voraussetzungen

- Python 3.11 bis 3.13
- Discord-Bot mit aktiviertem **Server Members Intent** und
  **Message Content Intent**
- Discord-Scopes `bot` und `applications.commands`

Die privilegierten Intents werden im
[Discord Developer Portal](https://discord.com/developers/applications) unter
**Bot → Privileged Gateway Intents** aktiviert.

## Installation auf Vionity/Linux

```bash
cd /root
git clone --branch agent/modular-multi-guild-bot --single-branch https://github.com/nexoria-server/nexoria-bot.git
cd nexoria-bot
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
nano .env
.venv/bin/python main.py
```

In `nano`: Werte eintragen, mit `Strg+O`, Enter speichern und mit `Strg+X`
schließen. Der Discord-Token gehört ausschließlich in `.env` und niemals in
GitHub oder einen Discord-Chat.

## Update auf Vionity

Bot im Panel stoppen und danach nacheinander ausführen:

```bash
cd /root/nexoria-bot
git pull --ff-only origin agent/modular-multi-guild-bot
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python main.py
```

Die `.env` und SQLite-Datenbanken werden von Git nicht verändert. Vor einem
Update sollte der Ordner `data/` gesichert werden.

## Einrichtung in Discord

Ein Administrator beginnt mit `/settings`. Dort werden ohne manuelle IDs
mehrere Rollen je Zuständigkeit, Teamstufen und Systemkanäle ausgewählt.

Empfohlene Reihenfolge:

1. `/settings` – Teamrollen, Berechtigungen, Ticket-/Bewerbungsrollen und Kanäle
2. `/ticket category` – Kategorie für jede Ticketart festlegen
3. `/ticket open kanal` und `/ticket archive kanal`
4. `/application panel kanal` und `/application archive kanal`
5. `/team-list kanal`, `/team-panel kanal`, `/minecraft channel`
6. `/commands-panel kanal` – permanente, kategorisierte Command-Hilfe

Die Botrolle muss in der Discord-Rollenliste über allen Rollen stehen, die der
Bot automatisch vergeben oder moderieren soll.

## Wichtige Funktionen

- Teamliste alle 30 Sekunden und zusätzlich sofort nach Rollenänderungen;
  jedes Mitglied erscheint nur unter seiner höchsten konfigurierten Rolle.
- Minecraft-Panel alle 15 Sekunden; Online-Namen sind über einen geschützten
  Admin-Button abrufbar.
- Bewerbungen: Test Supporter 30 Tage, Test Developer 14 Tage, Media 14 Tage,
  Partner 7 Tage; kompakte Formulare, passende Entscheidungs-DMs und Archiv.
- Tickets: getrennte Kategorien und Zuständigkeitsrollen, vollständige
  HTML-Transkripte und Suchpanel.
- Giveaway-Gewinner erhalten keine Ticket-DM. Im Ergebniskanal kann nur ein
  tatsächlicher Gewinner genau einmal sein Gewinn-Ticket erzeugen.
- Moderationsaktionen werden gespeichert, per DM erklärt und sind im
  Team-Statistikpanel samt Verlauf auswertbar.

## Originalstand

Unter `legacy_sources/` bleiben alle ursprünglich bereitgestellten Dateien
unverändert erhalten. Sie werden nicht ausgeführt; der produktive Bot liegt
unter `bot/` und startet über `main.py`.
