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
IMAGE_EXTENSIONS = {".avif", ".gif", ".jpeg", ".jpg", ".png", ".webp", ".svg"}
VIDEO_EXTENSIONS = {".mp4", ".ogg", ".webm"}
VIDEO_MIME_TYPES = {".mp4": "video/mp4", ".ogg": "video/ogg", ".webm": "video/webm"}
# Anzeigedauern fuer die Sponsoring-Folien in Sekunden.
SAVE_THE_DATE_DURATION_SECONDS = 5
GOLD_SPONSOR_DURATION_SECONDS = 5
OTHER_SPONSOR_DURATION_SECONDS = 5
OTHER_SPONSORS_PER_CYCLE = 4
TOURNAMENT_DISPLAY_DURATION_SECONDS = 3
MATCHES_PER_PAGE = 20
FINAL_MATCHES_PER_PAGE = 10
# Spielplan IDs
SINAGE_TOURNAMENT_IDS = os.environ.get("SINAGE_TOURNAMENT_IDS", "0jj2i6bso4")
TOURNAMENT_ID = "1757255205"
FINAL_TOURNAMENT_ID = "1757569613"
# Startup Mode
#SINAGE_MODE = os.environ.get("SINAGE_MODE", "SPONSORING")
SINAGE_MODE = os.environ.get("SINAGE_MODE", "TURNIER")



def media_entry(path: Path, root: Path):
    """Bereitet eine lokale Bild- oder Video-Datei fuer das Template vor."""
    return {
        "path": path.relative_to(root).as_posix(),
        "type": "video" if path.suffix.casefold() in VIDEO_EXTENSIONS else "image",
        "mime": VIDEO_MIME_TYPES.get(path.suffix.casefold()),
        "name": path.stem,
    }


def group_label(index):
    """Erzeugt Gruppenbezeichnungen A, B, ..., Z, AA, AB, ... ."""
    label = ""
    while True:
        index, remainder = divmod(index, 26)
        label = chr(ord("A") + remainder) + label
        if index == 0:
            return label
        index -= 1


def sponsor_profiles():
    """Liest Sponsor-Ordner und ihre Beitraege inklusive optionaler Logos ein."""
    if not SPONSOR_DIRECTORY.is_dir():
        return [], []

    gold_sponsors, other_sponsors = [], []
    for category in sorted(SPONSOR_DIRECTORY.iterdir(), key=lambda entry: entry.name.casefold()):
        if not category.is_dir():
            continue
        category_name = category.name.casefold()
        target = gold_sponsors if "gold" in category_name else other_sponsors
        if not any(level in category_name for level in ("gold", "silber", "bronze")):
            continue

        for sponsor_directory in sorted(category.iterdir(), key=lambda entry: entry.name.casefold()):
            if not sponsor_directory.is_dir():
                continue
            files = [
                file for file in sorted(sponsor_directory.rglob("*"), key=lambda entry: str(entry).casefold())
                if file.is_file() and file.suffix.casefold() in IMAGE_EXTENSIONS | VIDEO_EXTENSIONS
            ]
            small_logo = next((file for file in files if file.stem.casefold() == "logo_small"), None)
            media = []
            for file in files:
                # LOGO_small ist eine Einblendung, kein eigenstaendiger Beitrag.
                if file == small_logo:
                    continue
                item = media_entry(file, Path(app.static_folder))
                item["is_big_logo"] = file.stem.casefold() == "logo_big"
                media.append(item)
            if not media:
                continue
            target.append({
                "id": f"{category.name}/{sponsor_directory.name}",
                "name": sponsor_directory.name,
                "media": media,
                "small_logo": media_entry(small_logo, Path(app.static_folder)) if small_logo else None,
            })
    return gold_sponsors, other_sponsors


def sponsoring_durations():
    """Liefert die in der Vorlage benoetigten Dauern in Millisekunden."""
    return {
        "save_the_date": SAVE_THE_DATE_DURATION_SECONDS * 1000,
        "gold": GOLD_SPONSOR_DURATION_SECONDS * 1000,
        "other": OTHER_SPONSOR_DURATION_SECONDS * 1000,
    }


def tournament_display_duration():
    """Liefert die Anzeigedauer der Turnierfolien in Millisekunden."""
    return TOURNAMENT_DISPLAY_DURATION_SECONDS * 1000


def save_the_date_media():
    """Liefert das Save-the-Date-Motiv, falls es im Asset-Ordner vorhanden ist."""
    image = Path(app.static_folder) / "assets" / "SaveTheDate.jpg"
    return media_entry(image, Path(app.static_folder)) if image.is_file() else None


def tournament_widgets(tournament_id):
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
    for index, group in enumerate(tournament_groups(tournament_id)):
        base = {"id": tournament_id, "gr": group, **style}
        table = {**base, "s[logosize]": 20}
        matches = {**base, "s[ehrsize]": 10, "s[ehrtop]": 9, "s[ehrbottom]": 3}
        widgets.append({
            "group": group,
            "label": group_label(index),
            "table_url": "https://www.meinturnierplan.ch/displayTable.php?" + urlencode(table) + "&sbr",
            # Ohne mn-Parameter zeigt das Widget alle Spiele dieser Gruppe.
            "matches_url": "https://www.meinturnierplan.ch/displayMatches.php?" + urlencode(matches) + "&sbr",
        })
    return widgets

def tournament_groups(tournament_id):
    response = requests.get(
        f"https://www.meinturnierplan.ch/showit.php?id={tournament_id}",
        headers={"User-Agent": "VoelkDigitalSignage/1.0"},
        timeout=10,
    )
    response.raise_for_status()
    groups_match = re.search(r'"groups"\s*:\s*\[(.*?)\]', response.text, re.DOTALL)
    if not groups_match:
        return tuple()
    groups_count = len(re.findall(r'"name"\s*:\s*"[^"]+"', groups_match.group(1), re.DOTALL))
    return tuple(str(group) for group in range(1, groups_count + 1))

def tournament_matches(tournament_id):
    response = requests.get(
        f"https://www.meinturnierplan.ch/showit.php?id={tournament_id}",
        headers={"User-Agent": "VoelkDigitalSignage/1.0"},
        timeout=10,
    )
    response.raise_for_status()
    # group matches
    groups_match = re.search(r'"groupMatches"\s*:\s*\[(.*?)\]', response.text, re.DOTALL)
    group_result = (-1,0,0)
    if groups_match:
        group_games = re.findall(r'"gameId"\s*:\s*"(\d+)"',groups_match.group(1), re.DOTALL)
        group_result = (
            len(group_games),
            int(group_games[0]),
            int(group_games[-1])
        )
        
    # final matches
    finals_match = re.search(r'"finalMatches"\s*:\s*\[(.*?)\]', response.text, re.DOTALL)
    final_result = (-1,0,0)
    if finals_match:
        final_games = re.findall(r'"gameId"\s*:\s*"(\d+)"',finals_match.group(1), re.DOTALL)
        final_result = (
            len(final_games),
            int(final_games[0]),
            int(final_games[-1])
        )
    # out ((count, first id, last id) seperate for final and group games)
    return (group_result, final_result)

def matches_widget_url(start, end, tournament_id, final_round):
    params = {
        "id": tournament_id,
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
    flags = "&se&sp&sbr" if final_round else "&sbr"
    return "https://www.meinturnierplan.de/displayMatches.php?" + urlencode(params) + flags


def matches_pages(tournament_id, final_round):
    if final_round:
        matches_per_page = FINAL_MATCHES_PER_PAGE
    else:
        matches_per_page = MATCHES_PER_PAGE
    
    try:
        matches = tournament_matches(tournament_id)
        numbers = [
            int(match.get("displayId") or match.get("matchNumber") or index + 1)
            for index, match in enumerate(matches)
        ]
        first, last = min(numbers), max(numbers)
    except (requests.RequestException, ValueError, KeyError, IndexError, StopIteration) as e:
        first, last = 1, matches_per_page


    pages = []
    for start in range(first, last + 1, matches_per_page):
        end = min(start + matches_per_page - 1, last)
        pages.append({
            "start": start, 
            "end": end, 
            "url": matches_widget_url(start, end, tournament_id, final_round),
        })
    return pages


@app.get("/")
def presentation_index():
    if SINAGE_MODE == "TURNIER":
        return redirect("/turnier")
    elif SINAGE_MODE == "SPONSORING":
        return redirect("/sponsoring")


@app.get("/turnier")
def tournament_presentation():
    return render_template(
        "presentation.html", mode="tournament", gold_sponsors=[], other_sponsors=[],
        other_sponsors_per_cycle=OTHER_SPONSORS_PER_CYCLE,
        match_pages=matches_pages(TOURNAMENT_ID, False), final_match_pages=matches_pages(FINAL_TOURNAMENT_ID, True), widgets=tournament_widgets(TOURNAMENT_ID),
        tournament_display_duration=tournament_display_duration(),
        show_group_phase=True, show_final_phase=True,
    )


@app.get("/group")
def group_presentation():
    return render_template(
        "presentation.html", mode="group", gold_sponsors=[], other_sponsors=[],
        other_sponsors_per_cycle=OTHER_SPONSORS_PER_CYCLE,
        match_pages=matches_pages(TOURNAMENT_ID, False), final_match_pages=[], widgets=tournament_widgets(TOURNAMENT_ID),
        tournament_display_duration=tournament_display_duration(),
        show_group_phase=True, show_final_phase=False,
    )


@app.get("/finale")
def final_presentation():
    return render_template(
        "presentation.html", mode="finale", gold_sponsors=[], other_sponsors=[],
        other_sponsors_per_cycle=OTHER_SPONSORS_PER_CYCLE,
        match_pages=[], final_match_pages=matches_pages(FINAL_TOURNAMENT_ID, True), widgets=[],
        tournament_display_duration=tournament_display_duration(),
        show_group_phase=False, show_final_phase=True,
    )


@app.get("/sponsoring")
def sponsoring_presentation():
    gold_sponsors, other_sponsors = sponsor_profiles()
    return render_template(
        "presentation.html",
        mode="sponsors",
        gold_sponsors=gold_sponsors,
        other_sponsors=other_sponsors,
        save_the_date=save_the_date_media(),
        sponsoring_durations=sponsoring_durations(),
        other_sponsors_per_cycle=OTHER_SPONSORS_PER_CYCLE,
        match_pages=[],
        final_match_pages=[],
        tournament_display_duration=tournament_display_duration(),
        show_group_phase=False,
        show_final_phase=False,
        widgets=[],
    )


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    #app.run(host="127.0.0.1", port=8000)
    print(tournament_matches(TOURNAMENT_ID))
    print(tournament_matches(SINAGE_TOURNAMENT_IDS))
    print(tournament_matches(FINAL_TOURNAMENT_ID))