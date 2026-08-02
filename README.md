# Völk Digital Signage

Lokale Digital-Signage für Raspberry Pi Zero 2 W. Der Flask-Server liefert eine lokal gespeicherte, reveal.js-kompatible Präsentation aus, Chromium zeigt sie im Kiosk-Modus an.

## URLs

| URL | Inhalt |
| --- | --- |
| `/` | Gemischt: Turnierinformationen und Sponsoren |
| `/turnier` | Nur Spielplan und Gruppenranglisten |
| `/sponsoring` | Nur Sponsor-Bilder |

Die Turnierfolien betten die offiziellen Widgets von meinturnierplan.de ein. Aktuelle Ergebnisse erscheinen direkt im Kiosk, solange der Raspberry Pi Internetzugang hat.
Jede Gruppe erhält eine eigene Folie mit ihrer Rangliste und allen Spielen dieser Gruppe. Standardmässig sind die Gruppen `1,2,3` aktiviert; bei Bedarf lässt sich die Liste beim Dienst über `TOURNAMENT_GROUPS` (z. B. `1,2,3,4`) ändern.
Zusätzlich zeigt eine eigene Folie die zehn vergangenen, das laufende sowie zehn kommenden Spiele. Alle offiziellen Widgets erhalten den Parameter `sbr`.

## Lokal entwickeln

```bash
python -m venv .venv
.venv\\Scripts\\pip install -r requirements.txt
.venv\\Scripts\\python app.py
```

Danach `http://127.0.0.1:8000` öffnen. Bilder und Videos im gesamten Ordner `assets/sponsoren/` werden rekursiv erkannt. Unterstützt werden AVIF, GIF, JPEG, JPG, PNG, WebP sowie MP4, OGG und WebM. Das Motiv `assets/SaveTheDate.jpg` wird automatisch als eigene Folie gezeigt. Alle Dateien im Ordner `Heart of Colors` erscheinen als zusammenhängende Sequenz.

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
 