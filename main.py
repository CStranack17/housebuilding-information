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
    "Planning Portal": "https://www.planningportal.co.uk/services/professional-portal/professional-news/rss",
    "Housing Today": "https://www.housingtoday.co.uk/rss",
    "The Planner": "https://www.theplanner.co.uk/rss.xml",
    "GOV UK Housing": "https://www.gov.uk/government/organisations/ministry-of-housing-communities-and-local-government.atom",
    "Bank of England": "https://www.bankofengland.co.uk/rss/news",
    "ONS": "https://www.ons.gov.uk/rss"
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
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading {path}: {e}")
        return default

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def generate_id(url):
    return hashlib.sha256(url.encode()).hexdigest()

history = load_json(HISTORY_FILE, [])
buffer_data = load_json(BUFFER_FILE, [])
known_ids = set(history)

# =====================================================
# CLASSIFICATION & SCORING
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
                if not url:
                    continue
                
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
                    "date_found": datetime.now(timezone.utc).isoformat()
                }

                findings.append(item)
                known_ids.add(uid)
        except Exception as e:
            print(f"Error reading {source}: {e}")

    return findings

def simplify_summary(text, max_length=220):
    if not text:
        return ""

    text = re.sub("<.*?>", "", text)
    text = text.replace("\n", " ").replace("\r", " ").strip()

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

    ordered = sorted(unique_items, key=lambda x: x["score"], reverse=True)
    ordered = ordered[:MAX_EMAIL_ARTICLES]

    for item in ordered:
        sections[item["category"]].append(item)

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
    </head>
    <body style="background:{BACKGROUND}; font-family: Arial, sans-serif; padding: 20px;">
        <div style="max-width: 650px; margin: 0 auto; background:{CARD}; padding: 25px; border-radius: 10px;">
            <h1 style="color:{NAVY}; margin-top: 0;">Bell Homes Land Intelligence</h1>
            <div style="
                background:{LIGHT_BLUE};
                padding:18px;
                border-left:6px solid {MAROON};
                border-radius:8px;
                margin-bottom:25px;
            ">
                <b>Weekly Intelligence Summary</b><br><br>
                {len(ordered)} prioritised intelligence items included.
            </div>
    """

    for category, entries in sections.items():
        if not entries:
            continue

        html += f"""
        <h2 style="
            color:{MAROON};
            margin-top:35px;
            border-bottom:2px solid {LIGHT_BLUE};
            padding-bottom:8px;
        ">
            {category}
        </h2>
        """

        for item in entries:
            summary = simplify_summary(item.get("summary", ""))
            html += f"""
            <div style="
                background:white;
                border:1px solid #dce3ea;
                border-left:5px solid {MAROON};
                border-radius:10px;
                padding:18px;
                margin-bottom:16px;
            ">
                <div style="
                    font-size:18px;
                    font-weight:600;
                    color:{NAVY};
                    margin-bottom:8px;
                ">
                    {item['title']}
                </div>
                <div style="
                    color:#64748b;
                    font-size:13px;
                    margin-bottom:12px;
                ">
                    Source: {item['source']}
                </div>
                <div style="
                    color:#334155;
                    line-height:1.6;
                    margin-bottom:14px;
                ">
                    {summary}
                </div>
                <a href="{item['url']}" style="
                    color:{MAROON};
                    font-weight:bold;
                    text-decoration:none;
                ">
                    Read Full Article &rarr;
                </a>
            </div>
            """

    html += """
        </div>
    </body>
    </html>
    """
    return html

# =====================================================
# MAIN EXECUTION
# =====================================================

def main():
    print("Collecting RSS feeds...")
    new_items = collect_rss()
    print(f"Found {len(new_items)} new items.")

    # Append new items to buffer
    buffer_data.extend(new_items)
    save_json(BUFFER_FILE, buffer_data)

    # Save updated history
    history.extend([item["id"] for item in new_items])
    save_json(HISTORY_FILE, history)

    # Send weekly digest if running on Monday (or force send if buffer has items)
    is_monday = datetime.now(timezone.utc).weekday() == 0

    if is_monday and buffer_data:
        print("Generating weekly digest...")
        html_content = build_digest(buffer_data)

        with open(DIGEST_FILE, "w", encoding="utf-8") as f:
            f.write(html_content)

        api_key = os.environ.get("RESEND_API_KEY")
        to_email = os.environ.get("TO_EMAIL")

        if api_key and to_email:
            resend.api_key = api_key
            print(f"Sending email digest via Resend to {to_email}...")
            resend.Emails.send({
                "from": "onboarding@resend.dev",
                "to": to_email,
                "subject": f"Bell Homes Land Intelligence - {datetime.now().strftime('%d %b %Y')}",
                "html": html_content
            })
            print("Email sent successfully!")

            # Clear buffer after sending weekly email
            save_json(BUFFER_FILE, [])
        else:
            print("Missing RESEND_API_KEY or TO_EMAIL environment variables. Skipping email send.")

if __name__ == "__main__":
    main()
