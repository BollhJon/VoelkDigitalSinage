from flask_cors import CORS
from flask import Flask
import requests
import re
import json

app = Flask(__name__)

CORS(app)

@app.route("/turnier-live")
def turnier_live():

    url = (
        "https://www.meinturnierplan.de/showit.php?id=1757255205&filter=4-0~4-1~4-2"
    )

    html = requests.get(
        url,
        headers={
            "User-Agent": "Mozilla/5.0"
        },
        timeout=10
    ).text

    match = re.search(
        r"window\.preloadedState = (.*?);",
        html,
        re.DOTALL
    )

    data = json.loads(match.group(1))


    tournament = list(
        data["tournaments"].values()
    )[0]["data"]

    print(tournament["groups"])

    print(tournament["groupMatches"])

    return data




app.run(
    host="127.0.0.1",
    port=5000
)