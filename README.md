# Nexoria Craft Discord Bot

Der vollständige Community-Bot mit Tickets, Bewerbungen, Teamverwaltung,
Moderation, Announcements, Giveaways, Einladungen, Minecraft-Status, Regeln,
Welcome/Leave, Logging und Anti-Spam.

## Voraussetzungen

- Python 3.11 bis 3.13
- Discord-Bot mit aktiviertem **Server Members Intent** und
  **Message Content Intent**
- Discord-Scopes `bot` und `applications.commands`

## Installation

```bash
git clone --branch agent/modular-multi-guild-bot --single-branch \
  https://github.com/nexoria-server/nexoria-bot.git
cd nexoria-bot
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
cp .env.example .env
```

Die IDs eines Discord-Objekts erhältst du nach Aktivierung des Discord-
Entwicklermodus über **Rechtsklick → ID kopieren**. Trage Token, Kanäle,
Kategorien und Rollen in `.env` ein.

Start:

```bash
.venv/bin/python main.py
```

## Vionity aktualisieren

Im bestehenden Verzeichnis:

```bash
cd /root/nexoria-bot
git pull --ff-only origin agent/modular-multi-guild-bot
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python main.py
```

Die vorhandene `.env` und Datenbanken werden von Git nicht verändert. Vor
einem Update empfiehlt sich trotzdem ein Backup des Ordners `data/`.

## Erste Discord-Konfiguration

```text
/config logs:#logs tickets:Ticket-Kategorie applications:#bewerbungen
        ticket_staff:@Support application_staff:@Bewerbungsteam
/ticket channel:#tickets
/bewerbung_panel
/minecraft kanal:#minecraft-status
/invite_panel
/announce-panel
/regeln
```

Die tatsächlich registrierten Commands können je nach konfigurierten Modulen
abweichen. Technische Fehler erscheinen ausschließlich in der Konsole und in
`logs/bot.log`.

## Archiv

Unter `legacy_sources/` bleiben außerdem alle 14 ursprünglich einzeln
bereitgestellten Dateien unverändert erhalten. Sie werden nicht ausgeführt.
Der vollständige und überarbeitete Bot liegt unter `bot/` und startet über
`main.py`.
