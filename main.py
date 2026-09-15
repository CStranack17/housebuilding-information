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

HOUSEBUILDING_KEYWORDS = [
    "housing",
    "residential",
    "homes",
    "housebuilder",
    "development",
    "planning permission",
    "outline consent",
    "reserved matters",
    "site allocation",
    "housing allocation",
    "development land",
    "strategic land",
    "call for sites",
    "brownfield",
    "greenfield",
    "planning application",
    "local plan",
    "nutrient neutrality",
    "biodiversity net gain",
    "section 106",
    "cil",
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

def is_housebuilding_relevant(title, summary):

    text = f"{title} {summary}".lower()

    matches = 0

    for keyword in HOUSEBUILDING_KEYWORDS:

        if keyword in text:
            matches += 1

    return matches >= 1


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

def simplify_summary(text, max_length=180):

    if not text:
        return ""

    text = (
        text.replace("\n", " ")
        .replace("\r", " ")
        .replace("<p>", "")
        .replace("</p>", "")
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

    total_items = len(items)

    html = f"""
    <html>
    <body style="
        margin:0;
        padding:0;
        background:#eef5fb;
        font-family:'Segoe UI', Arial, sans-serif;
        color:#2c3e50;
    ">

    <div style="
        max-width:900px;
        margin:30px auto;
        background:#ffffff;
        border-radius:16px;
        overflow:hidden;
        box-shadow:0 8px 30px rgba(0,0,0,0.08);
    ">

        <div style="
            background:linear-gradient(
                135deg,
                #6ea8dc,
                #a1345e
            );
            padding:35px;
            color:white;
        ">

            <h1 style="
                margin:0;
                font-size:34px;
            ">
                Bell Homes
            </h1>

            <p style="
                margin-top:10px;
                font-size:18px;
            ">
                Weekly Land Intelligence Digest
            </p>

            <p style="
                margin-top:15px;
                opacity:0.95;
                font-size:14px;
            ">
                Planning • Economics • Development Land • Competitors
            </p>

        </div>

        <div style="padding:35px;">

            <div style="
                background:#f3f8fc;
                border-left:5px solid #6ea8dc;
                padding:18px;
                border-radius:8px;
                margin-bottom:30px;
            ">

                <strong>Week at a Glance</strong>

                <p style="
                    margin-top:10px;
                    margin-bottom:0;
                    color:#556575;
                ">
                    {total_items} intelligence items were
                    captured during the last reporting period.
                    Articles have been prioritised based on
                    regional relevance, planning significance
                    and competitor activity.
                </p>

            </div>
    """

    for category, entries in sections.items():

        colour = "#6ea8dc"

        if category == "Competitor Activity":
            colour = "#a1345e"

        html += f"""
        <h2 style="
            color:{colour};
            border-bottom:2px solid #e2e8f0;
            padding-bottom:8px;
            margin-top:40px;
        ">
            {category}
        </h2>
        """

        if not entries:

            html += """
            <p style="
                color:#94a3b8;
            ">
                No notable updates identified.
            </p>
            """
            continue

        for item in entries:

            summary = simplify_summary(
                item.get("summary", "")
            )

            html += f"""
            <div style="
                background:#fafafa;
                border:1px solid #e5e7eb;
                border-left:5px solid {colour};
                border-radius:10px;
                padding:18px;
                margin-bottom:16px;
            ">

                <div style="
                    font-size:18px;
                    font-weight:600;
                    color:#1e293b;
                    margin-bottom:8px;
                ">
                    {item['title']}
                </div>

                <div style="
                    font-size:13px;
                    color:#7c8a9b;
                    margin-bottom:12px;
                ">
                    Source: {item['source']}
                </div>

                <div style="
                    line-height:1.65;
                    color:#475569;
                    margin-bottom:14px;
                ">
                    {summary}
                </div>

                <a
                    href="{item['url']}"
e →
                </a>

            </div>
            """

    html += f"""
            <div style="
                margin-top:40px;
                padding-top:20px;
                border-top:1px solid #e2e8f0;
                color:#94a3b8;
                font-size:12px;
            ">

                Generated automatically on
                {datetime.now(timezone.utc).strftime('%d %B %Y at %H:%M UTC')}

            </div>

        </div>

    </div>

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
