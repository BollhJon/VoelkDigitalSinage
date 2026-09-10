"""Lokaler Webserver fuer die Digital-Signage."""

import os
import json
import re
import html
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
# Tournament Infos
tournaments = []

def media_entry(path: Path, root: Path):
    return {
        "path": path.relative_to(root).as_posix(),
        "type": "video" if path.suffix.casefold() in VIDEO_EXTENSIONS else "image",
        "mime": VIDEO_MIME_TYPES.get(path.suffix.casefold()),
        "name": path.stem,
    }


def sponsor_profiles():
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


def tournament_request(tournament_id):
    response = requests.get(
        f"https://www.meinturnierplan.ch/showit.php?id={tournament_id}",
        headers={"User-Agent": "VoelkDigitalSignage/1.0"},
        timeout=10,
    )
    response.raise_for_status()
    return response.text

def tournament_name(request_text):
    title_match = re.search(r"<title>(.*?)</title>", request_text, re.IGNORECASE | re.DOTALL)

    if title_match:
        return html.unescape(title_match.group(1)).strip()

    return None

def tournament_groups(request_text):
    groups_match = re.search(r'"groups"\s*:\s*\[(.*?)\]', request_text, re.DOTALL)
    groups_count = 0
    if groups_match:
        groups_count = len(re.findall(r'"name"\s*:\s*"[^"]+"', groups_match.group(1), re.DOTALL))

    final_groups_match = re.search(r'"finalGroups"\s*:\s*\[(.*?)\]', request_text, re.DOTALL)
    final_groups_count = 0
    if final_groups_match:
        final_groups_count = len(re.findall(r'"name"\s*:\s*"[^"]+"', final_groups_match.group(1), re.DOTALL))

    return (groups_count, final_groups_count)

def tournament_matches(request_text):
    # group matches
    groups_match = re.search(r'"groupMatches"\s*:\s*\[(.*?)\]', request_text, re.DOTALL)
    group_result = (-1,0,0)
    if groups_match:
        group_games = re.findall(r'"gameId"\s*:\s*"(\d+)"',groups_match.group(1), re.DOTALL)
        group_result = (
            len(group_games),
            int(group_games[0]),
            int(group_games[-1])
        )
        
    # final matches
    finals_match = re.search(r'"finalMatches"\s*:\s*\[(.*?)\]', request_text, re.DOTALL)
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

def tournament_infos(tournament_id):
    response = tournament_request(tournament_id)
    title = tournament_name(response)
    groups = tournament_groups(response)
    matches = tournament_matches(response)
    return (tournament_id, title, (groups[0], matches[0]), (groups[1], matches[1]))

def group_label(index):
    label = ""
    while True:
        index, remainder = divmod(index, 26)
        label = chr(ord("A") + remainder) + label
        if index == 0:
            return label
        index -= 1

def group_widgets(tournament):
    tournament_id = tournament[0]
    group_count = tournament[2][0]
    if group_count == 0:
        return []
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
    for group in range(group_count):
        base = {"id": tournament_id, "gr": group+1, **style}
        table = {**base, "s[logosize]": 20}
        matches = {**base, "s[ehrsize]": 10, "s[ehrtop]": 9, "s[ehrbottom]": 3}
        widgets.append({
            "group": group,
            "label": group_label(group),
            "table_url": "https://www.meinturnierplan.ch/displayTable.php?" + urlencode(table) + "&sbr",
            "matches_url": "https://www.meinturnierplan.ch/displayMatches.php?" + urlencode(matches) + "&sbr",
        })
    return widgets

def group_allwidgets(tournaments):
    widgets = []
    for tournament in tournaments:
        widget = group_widgets(tournament)
        if widget != []:
            widgets = widget
    return widgets

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
    return "https://www.meinturnierplan.ch/displayMatches.php?" + urlencode(params) + flags


def matches_pages(tournament):
    tournament_id = tournament[0]
    group_matches = tournament[2][1]
    final_matches = tournament[3][1]

    group_pages = []
    #groupmatches
    if group_matches[0] != -1:
        for start in range(group_matches[1], group_matches[2]-1, MATCHES_PER_PAGE):
            end = min(start + MATCHES_PER_PAGE - 1, group_matches[2])
            group_pages.append({
                "start": start, 
                "end": end, 
                "url": matches_widget_url(start, end, tournament_id, False),
            })
    
    final_pages = []
    #finalmatches
    if final_matches[0] != -1:
        for start in range(final_matches[1], final_matches[2]-1, FINAL_MATCHES_PER_PAGE):
            end = min(start + FINAL_MATCHES_PER_PAGE - 1, final_matches[2])
            final_pages.append({
                "start": start, 
                "end": end, 
                "url": matches_widget_url(start, end, tournament_id, True),
            })
    
    return group_pages, final_pages

def matches_allpages(tournaments):
    pages = [[],[]]
    for tournament in tournaments:
        group_pages, final_pages = matches_pages(tournament)
        if group_pages != []:
            pages[0] = group_pages
        if final_pages != []:
            pages[1] = final_pages
    return pages


@app.get("/")
def presentation_index():
    # Startup Mode
    #SINAGE_MODE = os.environ.get("SINAGE_MODE", "SPONSORING")
    SINAGE_MODE = os.environ.get("SINAGE_MODE", "TURNIER")

    if SINAGE_MODE == "TURNIER":
        return redirect("/turnier")
    elif SINAGE_MODE == "SPONSORING":
        return redirect("/sponsoring")


@app.get("/turnier")
def tournament_presentation():
    for id in SINAGE_TOURNAMENT_IDS:
        tournaments.append(tournament_infos(id))
    widgets = group_allwidgets(tournaments)
    match_pages = matches_allpages(tournaments)
    return render_template(
        "tournament.j2", 
        mode="tournament",
        match_pages=match_pages[0],
        final_match_pages=match_pages[1], 
        widgets=widgets,
        tournament_display_duration=tournament_display_duration(),
    )


@app.get("/group")
def group_presentation():
    for id in SINAGE_TOURNAMENT_IDS:
        tournaments.append(tournament_infos(id))
    widgets = group_allwidgets(tournaments)
    match_pages = matches_allpages(tournaments)
    return render_template(
        "tournament.j2",
        mode="group", 
        match_pages=match_pages[0],
        final_match_pages=[], 
        widgets=widgets,
        tournament_display_duration=tournament_display_duration(),
    )


@app.get("/finale")
def final_presentation():
    for id in SINAGE_TOURNAMENT_IDS:
        tournaments.append(tournament_infos(id))
    widgets = group_allwidgets(tournaments)
    match_pages = matches_allpages(tournaments)
    return render_template(
        "tournament.j2", 
        mode="finale", 
        match_pages=[],
        final_match_pages=match_pages[1], 
        widgets=[],
        tournament_display_duration=tournament_display_duration(),
    )


@app.get("/sponsoring")
def sponsoring_presentation():
    gold_sponsors, other_sponsors = sponsor_profiles()
    return render_template(
        "sponsors.j2",
        gold_sponsors=gold_sponsors,
        other_sponsors=other_sponsors,
        save_the_date=save_the_date_media(),
        sponsoring_durations=sponsoring_durations(),
        other_sponsors_per_cycle=OTHER_SPONSORS_PER_CYCLE,
    )


@app.get("/health")
def health():
    for id in SINAGE_TOURNAMENT_IDS:
        tournaments.append(tournament_infos(id))
    mode = os.environ.get("SINAGE_MODE", "TURNIER"), 
    return [mode, tournaments, sponsor_profiles()]


if __name__ == "__main__":
    # Spielplan Infos
    SINAGE_TOURNAMENT_IDS = os.environ.get("SINAGE_TOURNAMENT_IDS", "0jj2i6bso4").split(';')
    #SINAGE_TOURNAMENT_IDS = os.environ.get("SINAGE_TOURNAMENT_IDS", "1757255205;1757569613").split(';')

    app.run(host="127.0.0.1", port=8000)