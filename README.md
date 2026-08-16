# Völk Digital Signage

Lokale Digital-Signage für Raspberry Pi Zero 2 W. Der Flask-Server liefert eine lokal gespeicherte, reveal.js-kompatible Präsentation aus, Chromium zeigt sie im Kiosk-Modus an.

## URLs

| URL | Inhalt |
| --- | --- |
| `/` | Weiterleitung auf `/turnier` |
| `/turnier` | Gruppenphase und Finalspiele |
| `/group` | Nur Gruppenphase |
| `/finale` | Nur Finalspiele |
| `/sponsoring` | Nur Sponsor-Bilder |

Die Turnierfolien betten die offiziellen Widgets von meinturnierplan.de ein. Aktuelle Ergebnisse erscheinen direkt im Kiosk, solange der Raspberry Pi Internetzugang hat.
Jede Gruppe erhält eine eigene Folie mit ihrer Rangliste und allen Spielen dieser Gruppe. Die Gruppenphase wird oben in `app.py` über `TOURNAMENT_ID` und `TOURNAMENT_DISPLAY_DURATION_SECONDS` konfiguriert. Die technischen IDs werden automatisch als `1` bis zur Gruppenanzahl abgefragt und auf den Folien als `A`, `B`, `C` usw. angezeigt.
Zusätzlich werden alle Spiele in mehreren Folien angezeigt. Die Anzahl Spiele pro Folie wird in `app.py` über `MATCHES_PER_PAGE` gesteuert. Alle offiziellen Widgets erhalten den Parameter `sbr`.

Die Finalspiele werden als eigene Folien angezeigt. Dafür stehen in `app.py` die separaten Parameter `FINAL_TOURNAMENT_ID` und `FINAL_MATCHES_PER_PAGE` bereit. Die Seitenbereiche werden automatisch aus den Display-IDs der Finalspiele ermittelt. Die Anzeigedauer übernimmt `TOURNAMENT_DISPLAY_DURATION_SECONDS` aus der Gruppenphase.

## Lokal entwickeln

```bash
python -m venv .venv
.venv\\Scripts\\pip install -r requirements.txt
.venv\\Scripts\\python app.py
```

Danach `http://127.0.0.1:8000` öffnen. Unterstützt werden AVIF, GIF, JPEG, JPG, PNG, WebP sowie MP4, OGG und WebM. Das Motiv `assets/SaveTheDate.jpg` wird automatisch als eigene Folie gezeigt.

Sponsoren werden nach `assets/sponsoren/01_Goldsponsoren`, `02_Silbersponsoren` und `03_Bronzesponsoren` gruppiert. Jeder Unterordner entspricht einem Sponsor. Eine Sponsoring-Sequenz zeigt Save the Date, anschliessend jeden Goldsponsor mit einem wechselnden Beitrag und danach vier wechselnde Silber- oder Bronzesponsoren. `LOGO_small` wird bei Beiträgen desselben Sponsors links oben eingeblendet; `LOGO_big` wird als eigenständiger Beitrag ohne kleine Logo-Einblendung behandelt. Die Anzeigedauern stehen oben in `app.py` als `*_DURATION_SECONDS` und sind in Sekunden angegeben; die Anzahl weiterer Sponsoren über `OTHER_SPONSORS_PER_CYCLE`.

## Raspberry Pi installieren

Raspberry Pi OS **mit Desktop** installieren, Netzwerk und GitHub-Zugriff einrichten, dann einmalig ausführen:

```bash
git clone https://github.com/BollhJon/VoelkDigitalSignage.git
cd REPOSITORY
bash scripts/install-raspi.sh https://github.com/BollhJon/VoelkDigitalSignage.git main
```

Das Skript installiert Chromium und Python-Abhängigkeiten, erstellt den `signage`-Dienst und richtet Chromium für den Desktop-Autostart ein. Der Dienst holt beim Booten den aktuellen Stand des Branches von GitHub, installiert bei Bedarf Python-Abhängigkeiten und startet den Server. Änderungen direkt auf dem Pi in versionierten Dateien werden dabei absichtlich durch den GitHub-Stand ersetzt.

Für eine andere Anzeige-URL die Datei `~/.config/autostart/signage-kiosk.desktop` anpassen, z. B. auf `http://127.0.0.1:8000/turnier`.

## Betrieb prüfen

```bash
systemctl status signage
journalctl -u signage -f
curl http://127.0.0.1:8000/health
```
