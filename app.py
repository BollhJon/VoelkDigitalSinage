"""Lokaler Webserver fuer die Digital-Signage."""

import os
import json
import re
from pathlib import Path
from urllib.parse import urlencode

import requests
from flask import Flask, redirect, render_template

# reveal.js und die Bilder bleiben im Repository-Root.
app = Flask(__name__, static_folder=".", static_url_path="/static")

SPONSOR_DIRECTORY = Path(app.static_folder) / "assets" / "sponsoren"
IMAGE_EXTENSIONS = {".avif", ".gif", ".jpeg", ".jpg", ".png", ".webp"}
VIDEO_EXTENSIONS = {".mp4", ".ogg", ".webm"}
VIDEO_MIME_TYPES = {".mp4": "video/mp4", ".ogg": "video/ogg", ".webm": "video/webm"}
TOURNAMENT_ID = os.environ.get("TOURNAMENT_ID", "1757255205")
TOURNAMENT_SOURCE_URL = f"https://www.meinturnierplan.de/showit.php?id={TOURNAMENT_ID}"
TOURNAMENT_GROUPS = tuple(
    group.strip()
    for group in os.environ.get("TOURNAMENT_GROUPS", "1,2,3").split(",")
    if group.strip()
)


def media_entry(path: Path, root: Path):
    """Bereitet eine lokale Bild- oder Video-Datei fuer das Template vor."""
    return {
        "path": path.relative_to(root).as_posix(),
        "type": "video" if path.suffix.casefold() in VIDEO_EXTENSIONS else "image",
        "mime": VIDEO_MIME_TYPES.get(path.suffix.casefold()),
        "name": path.stem,
    }


def sponsor_media():
    """Findet Bilder und Videos rekursiv; Heart of Colors bleibt als Block zusammen."""
    if not SPONSOR_DIRECTORY.is_dir():
        return [], []

    media = [
        media_entry(file, SPONSOR_DIRECTORY)
        for file in sorted(SPONSOR_DIRECTORY.rglob("*"), key=lambda entry: str(entry).casefold())
        if file.is_file() and file.suffix.casefold() in IMAGE_EXTENSIONS | VIDEO_EXTENSIONS
    ]
    hearts, sponsors = [], []
    for item in media:
        (hearts if "heart of colors" in item["path"].casefold() else sponsors).append(item)
    return sponsors, hearts


def save_the_date_media():
    """Liefert das Save-the-Date-Motiv, falls es im Asset-Ordner vorhanden ist."""
    image = Path(app.static_folder) / "assets" / "SaveTheDate.jpg"
    return media_entry(image, Path(app.static_folder)) if image.is_file() else None


def tournament_widgets():
    """Erzeugt je Gruppe die offiziellen Ranglisten- und Spielplan-Widgets."""
    style = {
        "s[size]": 9,
        "s[sizeheader]": 10,
        "s[color]": "000000",
        "s[maincolor]": "173f75",
        "s[padding]": 2,
        "s[innerpadding]": 5,
        "s[bgcolor]": "00000000",
        "s[bcolor]": "bbbbbb",
        "s[bsizeh]": 1,
        "s[bsizev]": 1,
        "s[bsizeoh]": 1,
        "s[bsizeov]": 1,
        "s[bbcolor]": "bbbbbb",
        "s[bbsize]": 2,
        "s[bgeven]": "f0f8ffb0",
        "s[bgodd]": "ffffffb0",
        "s[bgover]": "eeeeffb0",
        "s[bghead]": "eeeeffff",
        "s[wrap]": "false",
    }
    widgets = []
    for group in TOURNAMENT_GROUPS:
        base = {"id": TOURNAMENT_ID, "gr": group, **style}
        table = {**base, "s[logosize]": 20}
        matches = {**base, "s[ehrsize]": 10, "s[ehrtop]": 9, "s[ehrbottom]": 3}
        widgets.append({
            "group": group,
            "table_url": "https://www.meinturnierplan.de/displayTable.php?" + urlencode(table) + "&sbr",
            # Ohne mn-Parameter zeigt das Widget alle Spiele dieser Gruppe.
            "matches_url": "https://www.meinturnierplan.de/displayMatches.php?" + urlencode(matches) + "&sbr",
        })
    return widgets


def current_match_number():
    """Ermittelt die Nummer des laufenden Spiels fuer das Uebersichtsfenster."""
    response = requests.get(
        TOURNAMENT_SOURCE_URL,
        headers={"User-Agent": "VoelkDigitalSignage/1.0"},
        timeout=10,
    )
    response.raise_for_status()
    state = re.search(r"window\.preloadedState\s*=\s*(.*?);", response.text, re.DOTALL)
    if not state:
        raise ValueError("Turnierdaten nicht gefunden")

    tournaments = json.loads(state.group(1)).get("tournaments", {})
    tournament = next(iter(tournaments.values()))["data"]
    matches = tournament.get("groupMatches", [])
    if not matches:
        raise ValueError("Keine Gruppenspiele gefunden")

    active_index = next((i for i, match in enumerate(matches) if match.get("isActive")), None)
    if active_index is None:
        # Vor dem Start: erstes Spiel; in einer Pause: erstes noch nicht gespieltes Spiel.
        active_index = next(
            (i for i, match in enumerate(matches) if match.get("score1") is None),
            len(matches) - 1,
        )
    current = matches[active_index]
    return int(current.get("displayId") or current.get("matchNumber") or active_index + 1)


@app.get("/api/current-matches-widget")
def current_matches_widget():
    """Leitet auf ein Widget mit 10 vergangenen, dem aktuellen und 10 kommenden Spielen."""
    try:
        current = current_match_number()
    except (requests.RequestException, ValueError, KeyError, IndexError, StopIteration):
        current = 11

    start = max(1, current - 10)
    end = current + 10
    params = {
        "id": TOURNAMENT_ID,
        "mn": f"{start}-{end}",
        "s[size]": 9,
        "s[sizeheader]": 10,
        "s[color]": "000000",
        "s[maincolor]": "173f75",
        "s[padding]": 2,
        "s[innerpadding]": 5,
        "s[bgcolor]": "00000000",
        "s[bcolor]": "bbbbbb",
        "s[bsizeh]": 1,
        "s[bsizev]": 1,
        "s[bsizeoh]": 1,
        "s[bsizeov]": 1,
        "s[bbcolor]": "bbbbbb",
        "s[bbsize]": 2,
        "s[bgeven]": "f0f8ffb0",
        "s[bgodd]": "ffffffb0",
        "s[bgover]": "eeeeffb0",
        "s[bghead]": "eeeeffff",
        "s[ehrsize]": 10,
        "s[ehrtop]": 9,
        "s[ehrbottom]": 3,
        "s[wrap]": "false",
    }
    return redirect("https://www.meinturnierplan.de/displayMatches.php?" + urlencode(params) + "&sbr")


@app.get("/")
def mixed_presentation():
    sponsors, hearts = sponsor_media()
    return render_template(
        "presentation.html",
        mode="mixed",
        sponsors=sponsors,
        hearts=hearts,
        save_the_date=save_the_date_media(),
        widgets=tournament_widgets(),
    )


@app.get("/turnier")
def tournament_presentation():
    return render_template(
        "presentation.html", mode="tournament", sponsors=[], widgets=tournament_widgets()
    )


@app.get("/sponsoring")
def sponsoring_presentation():
    sponsors, hearts = sponsor_media()
    return render_template(
        "presentation.html",
        mode="sponsors",
        sponsors=sponsors,
        hearts=hearts,
        save_the_date=save_the_date_media(),
        widgets=[],
    )


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=8000)
