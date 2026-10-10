
#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import html
import json
import re
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup
from dateutil import parser as dtparser

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "events.json"
TZ = ZoneInfo("America/New_York")

ALLOWED_AREAS = {"Manhattan", "Brooklyn", "Queens"}
HEADERS = {
    "User-Agent": "NYCKidsGo/1.0 (family event directory)"
}

TODAY = datetime.now(TZ).date().isoformat()


def clean(value):
    return re.sub(
        r"\s+", " ", html.unescape(str(value or ""))
    ).strip()


def get(url):
    """公式ページを通常のHTTPリクエストで取得する。"""
    response = requests.get(
        url, headers=HEADERS, timeout=30
    )

    if response.status_code in (403, 429):
        raise requests.HTTPError(
            f"HTTP {response.status_code}: {url}",
            response=response,
        )

    response.raise_for_status()
    return response


def parse_date(value):
    """ISO形式または英語の日付をYYYY-MM-DDに変換。"""
    text = clean(value)

    iso = re.search(
        r"\b(20\d{2}-\d{2}-\d{2})\b", text
    )
    if iso:
        try:
            return datetime.fromisoformat(
                iso.group(1)
            ).date().isoformat()
        except ValueError:
            pass

    pattern = (
        r"\b(?:January|February|March|April|May|June|"
        r"July|August|September|October|November|December)"
        r"\s+\d{1,2}(?:st|nd|rd|th)?"
        r"(?:,\s*20\d{2})?\b"
    )
    match = re.search(pattern, text, re.I)
    if not match:
        return ""

    try:
        now = datetime.now(TZ).replace(tzinfo=None)
        d = dtparser.parse(match.group(0), default=now)

        if not re.search(r"20\d{2}", match.group(0)):
            if d.date().isoformat() < TODAY:
                d = d.replace(year=d.year + 1)

        return d.date().isoformat()
    except (ValueError, OverflowError):
        return ""


def date_label(date):
    try:
        return datetime.fromisoformat(date).strftime(
            "%b %d"
        ).replace(" 0", " ")
    except (ValueError, TypeError):
        return date or ""


def extract_time(text):
    """イベントカードから開始時刻を探す。"""
    match = re.search(
        r"\b\d{1,2}(?::\d{2})?\s*[ap]\.?m\.?\b",
        clean(text),
        re.I,
    )
    return clean(match.group(0)) if match else ""


def infer_age(text, default="Family"):
    t = text.lower()
    match = re.search(
        r"ages?\s*(\d{1,2})\s*[–—-]\s*(\d{1,2})",
        t,
    )

    if match:
        low, high = map(int, match.groups())
        if high <= 5:
            return "0-5"
        if low >= 13:
            return "13+"
        if low >= 6 and high <= 12:
            return "6-12"

    if any(k in t for k in (
        "baby", "babies", "toddler", "preschool"
    )):
        return "0-5"

    if "teen" in t:
        return "13+"

    return default


def infer_genre(text):
    t = text.lower()
    checks = [
        (["storytime", "story time", "read aloud"],
         "Storytime"),
        (["music", "sing", "song", "concert"], "Music"),
        (["dance", "theater", "theatre", "performance"],
         "Performance"),
        (["science", "stem", "engineering"], "Science"),
        (["outdoor", "park", "garden", "nature walk"],
         "Outdoor"),
        (["workshop", "craft", "hands-on"], "Workshop"),
        (["art", "paint", "drawing", "gallery"], "Art"),
    ]

    for keywords, genre in checks:
        if any(word in t for word in keywords):
            return genre

    return "Other"


def infer_price(text, default="paid"):
    t = text.lower()
    if "free" in t or "no cost" in t:
        return "free"
    return default


def image_from(node, base):
    img = node.select_one("img")
    if not img:
        return ""

    src = (
        img.get("src")
        or img.get("data-src")
        or img.get("data-lazy-src")
        or ""
    )

    if not src or src.startswith("data:"):
        return ""

    return urljoin(base, src)


def make_event(
    title, date, text, url, source,
    area="Manhattan", default_age="Family",
    default_price="paid", image="",
):
    title = clean(title)
    date = clean(date)

    if not title or not date or date < TODAY:
        return None

    if area not in ALLOWED_AREAS:
        return None

    return {
        "title": title,
        "date": date,
        "date_label": date_label(date),
        "time": extract_time(text),
        "area": area,
        "borough": area,
        "venue": source,
        "age_group": infer_age(text, default_age),
        "genre": infer_genre(title + " " + text),
        "price_type": infer_price(text, default_price),
        "description": clean(text)[:650],
        "source": source,
        "url": url,
        "image": image,
    }


def jsonld_events(soup, base, source, area="Manhattan",
                  default_age="Family", default_price="paid"):
    """ページ内にEvent構造化データがあれば優先して使う。"""
    out = []

    def visit(obj):
        if isinstance(obj, list):
            for item in obj:
                visit(item)
            return

        if not isinstance(obj, dict):
            return

        kind = obj.get("@type", "")
        kinds = kind if isinstance(kind, list) else [kind]

        if any(
            "event" in str(k).lower()
            for k in kinds
        ):
            title = clean(obj.get("name", ""))
            start = clean(obj.get("startDate", ""))
            date = parse_date(start)

            description = clean(
                obj.get("description", "")
            )

            event_url = obj.get("url", base)
            if isinstance(event_url, dict):
                event_url = event_url.get("@id", base)
            event_url = urljoin(base, str(event_url))

            image = obj.get("image", "")
            if isinstance(image, list):
                image = image[0] if image else ""
            if isinstance(image, dict):
                image = image.get("url", "")
            if isinstance(image, str):
                image = urljoin(base, image)

            text = title + " " + description + " " + start
            event = make_event(
                title, date, text, event_url, source,
                area, default_age, default_price, image,
            )

            if event:
                out.append(event)

        for key, value in obj.items():
            if key in ("@context",):
                continue
            if isinstance(value, (dict, list)):
                visit(value)

    for script in soup.select(
        'script[type="application/ld+json"]'
    ):
        try:
            visit(json.loads(script.string or script.get_text()))
        except (json.JSONDecodeError, TypeError):
            continue

    return out


def html_events(soup, base, source, area="Manhattan",
                default_age="Family", default_price="paid",
                limit=100):
    """HTMLカードを解析。サイト構造が変わると取得できない場合がある。"""
    selectors = [
        "article.tribe_events",
        ".tribe-events-calendar-list__event",
        ".tribe-events-pro-photo__event",
        "article",
        "[class*='event-card']",
        "[class*='event_card']",
        "[class*='event-list'] > *",
        "[class*='calendar'] article",
        ".views-row",
        "li[class*='event']",
        "table tr",
    ]

    nodes = []
    seen_nodes = set()

    for selector in selectors:
        for node in soup.select(selector):
            identity = id(node)
            if identity not in seen_nodes:
                seen_nodes.add(identity)
                nodes.append(node)

    out = []

    for node in nodes:
        text = clean(node.get_text(" ", strip=True))
        if len(text) < 18:
            continue

        # イベント見出しへのリンクを優先
        link = node.select_one(
            "h1 a, h2 a, h3 a, h4 a"
        )

        if not link:
            link = node.select_one("a[href]")

        if not link:
            continue

        title = clean(link.get_text(" ", strip=True))
        if len(title) < 4 or len(title) > 180:
            continue

        date = parse_date(text)
        if not date or date < TODAY:
            continue

        event_area = area
        lower = text.lower()

        if source == "NYPL":
            if "brooklyn" in lower:
                event_area = "Brooklyn"
            elif "queens" in lower:
                event_area = "Queens"
            elif "bronx" in lower or "staten island" in lower:
                continue

        event = make_event(
            title,
            date,
            text,
            urljoin(base, link.get("href") or base),
            source,
            event_area,
            default_age,
            default_price,
            image_from(node, base),
        )

        if event:
            out.append(event)

        if len(out) >= limit:
            break

    return out


def scrape_page(url, source, area="Manhattan",
                default_age="Family", default_price="paid"):
    response = get(url)
    soup = BeautifulSoup(response.text, "html.parser")

    # 構造化データとHTMLカードの両方を試す
    structured = jsonld_events(
        soup, url, source, area, default_age, default_price
    )
    cards = html_events(
        soup, url, source, area, default_age, default_price
    )

    return structured + cards


def nypl():
    url = "https://www.nypl.org/events/calendar?audience=children"
    return scrape_page(
        url, "NYPL", "Manhattan", "Family", "free"
    )


def cmom():
    base = "https://cmom.org/events/"
    out = []

    # 公開されているイベント一覧のページネーションを確認
    urls = [base] + [
        urljoin(base, f"list/page/{page}/")
        for page in range(2, 6)
    ]

    for index, url in enumerate(urls):
        try:
            rows = scrape_page(
                url,
                "Children's Museum of Manhattan",
                "Manhattan",
                "0-5",
                "paid",
            )
            print(f"CMOM page {index + 1}: {len(rows)} candidates")
            out.extend(rows)
        except requests.HTTPError as error:
            print(f"[WARN] CMOM page {index + 1}: {error}")
            if getattr(error.response, "status_code", None) == 429:
                break
        except Exception as error:
            print(f"[WARN] CMOM page {index + 1}: {error}")

        if index < len(urls) - 1:
            time.sleep(1)

    return out


def moma():
    urls = [
        "https://www.moma.org/visit/families/",
        "https://www.moma.org/calendar/",
    ]
    out = []

    for url in urls:
        try:
            rows = scrape_page(
                url, "MoMA", "Manhattan", "Family", "paid"
            )
            print(f"MoMA page candidates: {len(rows)}")
            out.extend(rows)
        except Exception as error:
            print(f"[WARN] MoMA: {error}")

    return out


def met():
    # 429が返った場合は連続アクセスせず、そこで停止する
    urls = [
        "https://www.metmuseum.org/events",
        "https://www.metmuseum.org/visit-guides/families/programs-and-resources",
        "https://www.metmuseum.org/visit-guides/families/childrens-classes",
    ]
    out = []

    for url in urls:
        try:
            rows = scrape_page(
                url, "The Met", "Manhattan", "Family", "paid"
            )
            print(f"The Met page candidates: {len(rows)}")
            out.extend(rows)
        except requests.HTTPError as error:
            print(f"[WARN] The Met: {error}")
            if getattr(error.response, "status_code", None) == 429:
                break
        except Exception as error:
            print(f"[WARN] The Met: {error}")

        time.sleep(2)

    return out


def event_key(event):
    """タイトル・日付・時刻・施設が同じイベントだけを重複扱いにする。"""
    parts = [
        clean(event.get("source", "")).lower(),
        clean(event.get("title", "")).lower(),
        clean(event.get("date", "")),
        clean(event.get("time", "")).lower(),
    ]
    raw = "|".join(parts)
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def dedupe(items):
    result = []
    seen = set()

    for event in sorted(
        items,
        key=lambda item: (
            item.get("date", "9999"),
            item.get("time", ""),
            item.get("title", "").lower(),
        ),
    ):
        key = event_key(event)
        if key in seen:
            continue
        seen.add(key)
        result.append(event)

    return result


def main():
    old_events = []

    if DATA.exists():
        try:
            old_data = json.loads(
                DATA.read_text(encoding="utf-8")
            )
            old_events = old_data.get("events", [])
        except (json.JSONDecodeError, OSError) as error:
            print("[WARN] Cannot read old events:", error)

    # 取得に失敗した施設の既存の未来イベントは保持する
    retained = [
        event for event in old_events
        if event.get("date", "") >= TODAY
        and event.get("area", "Manhattan") in ALLOWED_AREAS
    ]

    fresh = []

    for function in (nypl, cmom, moma, met):
        try:
            rows = function()
            print(f"{function.__name__}: {len(rows)} candidates")
            fresh.extend(rows)
        except Exception as error:
            print(f"[WARN] {function.__name__}: {error}")

    print("OLD FUTURE EVENTS:", len(retained))
    print("FRESH CANDIDATES:", len(fresh))

    items = dedupe(retained + fresh)
    items = [
        event for event in items
        if event.get("area", "Manhattan") in ALLOWED_AREAS
        and event.get("date", "") >= TODAY
    ]

    print("TOTAL AFTER DEDUPE:", len(items))

    counts = {}
    for event in items:
        source = event.get("source", "Unknown")
        counts[source] = counts.get(source, 0) + 1

    print("FINAL COUNTS BY SOURCE:", json.dumps(counts))

    DATA.parent.mkdir(parents=True, exist_ok=True)
    DATA.write_text(
        json.dumps(
            {
                "updated_at": datetime.now(TZ).isoformat(
                    timespec="seconds"
                ),
                "events": items,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
