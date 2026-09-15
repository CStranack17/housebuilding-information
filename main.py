import os
import json
import hashlib
from datetime import datetime, timezone
import requests
import feedparser
import resend

# =====================================================
# CONFIG
# =====================================================

HISTORY_FILE = "scraped_history.json"
BUFFER_FILE = "weekly_intelligence_buffer.json"
DIGEST_FILE = "weekly_land_intel_digest.html"

REGION_KEYWORDS = [
    "gloucestershire",
    "herefordshire",
    "forest of dean",
    "stroud",
    "cotswold",
    "tewkesbury",
    "monmouthshire",
    "south wales",
    "worcestershire",
    "ross-on-wye",
    "chepstow",
    "newent"
]

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
    "bovis",
    "redrow",
    "persimmon",
    "vistry",
    "bloor homes",
    "cotswold oak",
    "lioncourt",
    "freeman homes",
    "newland homes"
]

POLICY_KEYWORDS = [
    "local plan",
    "section 106",
    "s106",
    "cil",
    "biodiversity net gain",
    "bng",
    "nutrient neutrality",
    "housing delivery",
    "planning reform",
    "nppf"
]

ECONOMIC_KEYWORDS = [
    "base rate",
    "interest rate",
    "construction inflation",
    "house price index",
    "land market",
    "development finance"
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

    combined = f"{title} {summary}".lower()

    if any(k in combined for k in POLICY_KEYWORDS):
        return "Planning & Policy"

    if any(k in combined for k in ECONOMIC_KEYWORDS):
        return "Economic Intelligence"

    if any(k in combined for k in COMPETITOR_KEYWORDS):
        return "Competitor Activity"

    return "Industry News"


def score_item(title, summary):

    combined = f"{title} {summary}".lower()

    score = 0

    for word in REGION_KEYWORDS:
        if word in combined:
            score += 3

    for word in POLICY_KEYWORDS:
        if word in combined:
            score += 2

    for word in ECONOMIC_KEYWORDS:
        if word in combined:
            score += 2

    for word in COMPETITOR_KEYWORDS:
        if word in combined:
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


# =====================================================
# DIGEST CREATION
# =====================================================

def build_digest(items):

    sections = {
        "Planning & Policy": [],
        "Economic Intelligence": [],
        "Industry News": [],
        "Competitor Activity": []
    }

    ordered = sorted(
        items,
        key=lambda x: x["score"],
        reverse=True
    )

    for item in ordered:
        sections[item["category"]].append(item)

    html = """
    <html>
    <body style="font-family:Arial;">
    <h1>Weekly Land Intelligence Digest</h1>

    <p>
    Automatically generated strategic intelligence
    for Bell Homes.
    </p>
    """

    for category, entries in sections.items():

        html += f"<h2>{category}</h2>"

        if not entries:
            html += "<p>No notable items.</p>"
            continue

        html += "<ul>"

        for item in entries:

            html += f"""
            <li>
                <strong>{item['title']}</strong>
                <br>
                {item['summary']}
                <br>
                {item['url']}View Source</a>
            </li>
            <br>
            """

        html += "</ul>"

    html += """
    </body>
    </html>
    """

    return html


# =====================================================
# EMAIL
# =====================================================

def send_digest(html_content):

    api_key = os.getenv("RESEND_API_KEY")
    recipient = os.getenv("TO_EMAIL")

    if not api_key:
        raise ValueError("RESEND_API_KEY missing.")

    if not recipient:
        raise ValueError("TO_EMAIL missing.")

    resend.api_key = api_key

    resend.Emails.send(
        {
            "from": "Land Intelligence <onboarding@resend.dev>",
            "to": [recipient],
            "subject": "Weekly Land Intelligence Digest",
            "html": html_content
        }
    )


# =====================================================
# MAIN
# =====================================================

new_findings = collect_rss()

if new_findings:

    history.extend([x["id"] for x in new_findings])
    buffer_data.extend(new_findings)

save_json(HISTORY_FILE, history)
save_json(BUFFER_FILE, buffer_data)

today = datetime.now(timezone.utc)

# Allow manual testing
force_email = (
    os.getenv("FORCE_EMAIL", "false")
    .lower()
    == "true"
)

# Monday = 0
if (today.weekday() == 0 or force_email) and len(buffer_data) > 0:

    digest_html = build_digest(buffer_data)

    with open(
        DIGEST_FILE,
        "w",
        encoding="utf-8"
    ) as f:
        f.write(digest_html)

    print("Sending weekly digest email...")

    send_digest(digest_html)

    print("Email sent successfully.")

    save_json(BUFFER_FILE, [])
