import os
import json
import hashlib
import re
from datetime import datetime, timezone

import feedparser
import resend

# =====================================================
# CONFIG
# =====================================================

HISTORY_FILE = "scraped_history.json"
BUFFER_FILE = "weekly_intelligence_buffer.json"
DIGEST_FILE = "weekly_land_intel_digest.html"

MAX_EMAIL_ARTICLES = 25

# =====================================================
# BRANDING
# =====================================================

MAROON = "#7A2747"
LIGHT_BLUE = "#DCECF7"
NAVY = "#243746"
BACKGROUND = "#F5F7FA"
CARD = "#FFFFFF"

# =====================================================
# REGIONS
# =====================================================

REGION_KEYWORDS = [
    "forest of dean",
    "gloucester",
    "gloucestershire",
    "stroud",
    "cotswold",
    "tewkesbury",
    "herefordshire",
    "wychavon",
    "worcestershire",
    "malvern hills",
    "monmouthshire",
    "south wales",
    "ross-on-wye",
    "chepstow",
    "newent"
]

# =====================================================
# FEEDS
# =====================================================

RSS_FEEDS = {

    "Planning Portal":
        "https://www.planningportal.co.uk/services/professional-portal/professional-news/rss",

    "Housing Today":
        "https://www.housingtoday.co.uk/rss",

    "The Planner":
        "https://www.theplanner.co.uk/rss.xml",

    "GOV UK Housing":
        "https://www.gov.uk/government/organisations/ministry-of-housing-communities-and-local-government.atom",

    "Bank of England":
        "https://www.bankofengland.co.uk/rss/news",

    "ONS":
        "https://www.ons.gov.uk/rss"
}

COMPETITOR_KEYWORDS = [
    "bellway",
    "persimmon",
    "redrow",
    "vistry",
    "bloor homes",
    "bovis",
    "lioncourt",
    "freeman homes",
    "newland homes"
]

POLICY_KEYWORDS = [
    "local plan",
    "housing delivery",
    "section 106",
    "s106",
    "cil",
    "nppf",
    "planning reform",
    "biodiversity net gain",
    "bng",
    "nutrient neutrality"
]

ECONOMIC_KEYWORDS = [
    "base rate",
    "interest rate",
    "inflation",
    "house price",
    "house price index",
    "development finance",
    "construction costs",
    "mortgage"
]

# =====================================================
# FILE UTILITIES
# =====================================================


def load_json(path, default):
    if not os.path.exists(path):
        return default

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def generate_id(url):
    return hashlib.sha256(url.encode()).hexdigest()


history = load_json(HISTORY_FILE, [])
buffer_data = load_json(BUFFER_FILE, [])

known_ids = set(history)


# =====================================================
# CLASSIFICATION
# =====================================================

def classify_item(title, summary):

    text = f"{title} {summary}".lower()

    if any(region in text for region in REGION_KEYWORDS):
        return "🏛 Local Planning Updates"

    if any(word in text for word in POLICY_KEYWORDS):
        return "📜 Planning & Housing Policy"

    if any(word in text for word in ECONOMIC_KEYWORDS):
        return "📈 Housing Market & Economics"

    if any(word in text for word in COMPETITOR_KEYWORDS):
        return "🏗 Housebuilders & Competitors"

    return "📰 Industry & Development News"


def score_item(title, summary):

    text = f"{title} {summary}".lower()

    score = 1

    for region in REGION_KEYWORDS:
        if region in text:
            score += 5

    for keyword in POLICY_KEYWORDS:
        if keyword in text:
            score += 3

    for keyword in ECONOMIC_KEYWORDS:
        if keyword in text:
            score += 2

    for keyword in COMPETITOR_KEYWORDS:
        if keyword in text:
            score += 2

    return score


# =====================================================
# RSS COLLECTION
# =====================================================

def collect_rss():

    findings = []

    for source, feed_url in RSS_FEEDS.items():

        try:

            feed = feedparser.parse(feed_url)

            for entry in feed.entries:

                url = entry.get("link", "")
                uid = generate_id(url)

                if uid in known_ids:
                    continue

                title = entry.get("title", "")

                summary = (
                    entry.get("summary", "")
                    .replace("<p>", "")
                    .replace("</p>", "")
                )
                
                if not is_housebuilding_relevant(
                    title,
                    summary
                ):
                    continue

                item = {

                    "id": uid,
                    "source": source,
                    "title": title,
                    "summary": summary,
                    "url": url,
                    "category": classify_item(title, summary),
                    "score": score_item(title, summary),
                    "date_found": datetime.now(
                        timezone.utc
                    ).isoformat()
                }

                findings.append(item)

                known_ids.add(uid)

        except Exception as e:

            print(f"Error {source}: {e}")

    return findings

def simplify_summary(text, max_length=220):

    if not text:
        return ""

    text = re.sub("<.*?>", "", text)

    text = (
        text.replace("\n", " ")
        .replace("\r", " ")
        .strip()
    )

    while "  " in text:
        text = text.replace("  ", " ")

    if len(text) <= max_length:
        return text

    shortened = text[:max_length]

    last_space = shortened.rfind(" ")

    if last_space > 0:
        shortened = shortened[:last_space]

    return shortened + "..."


# =====================================================
# DIGEST CREATION
# =====================================================

def build_digest(items):

  sections = {

    "🏛 Local Planning Updates": [],
    "📜 Planning & Housing Policy": [],
    "📈 Housing Market & Economics": [],
    "🏗 Housebuilders & Competitors": [],
    "📰 Industry & Development News": []
}

seen_titles = set()

unique_items = []

for item in items:

    title_key = item["title"].strip().lower()

    if title_key in seen_titles:
        continue

    seen_titles.add(title_key)

    unique_items.append(item)

ordered = sorted(
    unique_items,
    key=lambda x: x["score"],
    reverse=True
)

ordered = ordered[:MAX_EMAIL_ARTICLES]

for item in ordered:
    sections[item["category"]].append(item)

html = f"""
<html>

<body style="
    background:{BACKGROUND};
    font-family:'Segoe UI',Arial,sans-serif;
    margin:0;
    padding:25px;
">

<div style="
    max-width:950px;
    margin:auto;
    background:white;
    border-radius:14px;
    overflow:hidden;
">

<div style="
    background:{MAROON};
    padding:35px;
    color:white;
">

<h1 style="margin:0;">
Bell Homes
</h1>

<p style="
    margin-top:10px;
    font-size:18px;
">
Weekly Land Intelligence Digest
</p>

<p style="
    margin-top:12px;
    font-size:13px;
    opacity:0.85;
">
Planning • Policy • Economics • Competitors • Development
</p>

</div>

<div style="padding:30px;">
"""

html += f"""

<div style="
    background:{LIGHT_BLUE};
    padding:18px;
    border-left:6px solid {MAROON};
    border-radius:8px;
    margin-bottom:25px;
">

<b>Weekly Intelligence Summary</b>

<br><br>

{len(ordered)} prioritised intelligence items included.

</div>
"""

<div style="
    background:white;
    border:1px solid #dce3ea;
    border-left:5px solid {MAROON};
    border-radius:10px;
    padding:18px;
    margin-bottom:16px;
">

<a
href="{item['url']}"
style="
color:{MAROON};
text-decoration:none;
font-weight:600;
font-size:13px;
