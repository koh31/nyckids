#!/usr/bin/env python3
"""
Daily updater for NYC Kids Go!
- Pulls selected official event pages.
- Parses upcoming child/family events.
- Merges them with existing data.
- Keeps future events only.

NOTE:
Website markup changes over time. Each source adapter is isolated so it can be
updated independently when a source redesigns its site.
"""
from __future__ import annotations
import json, re, hashlib
from datetime import datetime, date
from pathlib import Path
from zoneinfo import ZoneInfo
import requests
from bs4 import BeautifulSoup
from dateutil import parser as dtparser

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "events.json"
TZ = ZoneInfo("America/New_York")
HEADERS = {"User-Agent": "NYCKidsGo/1.0 (+static family event index; respectful daily fetch)"}

def clean(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "")).strip()

def infer_category(text: str) -> str:
    t = text.lower()
    for keys, cat in [
        (["dance","ballet"],"dance"), (["music","sing","song"],"music"),
        (["art","paint","craft","design"],"art"), (["science","stem","robot"],"science"),
        (["story","book","read"],"story"), (["park","outdoor","nature"],"outdoor"),
        (["cook","food","boba"],"food"),
    ]:
        if any(k in t for k in keys): return cat
    return "general"

def age_group(text: str, default="all-ages"):
    t=text.lower()
    if re.search(r"\b(0|1|2|3|4|5)\b", t) and not re.search(r"\b(6|7|8|9|10|11|12)\b", t):
        return "0-5","0–5歳"
    if re.search(r"\b(6|7|8|9|10|11|12)\b", t):
        return "6-12","6–12歳"
    return default,"Family"

def cmom():
    urls = [
        "https://cmom.org/events/category/sign-up-workshops/",
        "https://cmom.org/events/category/performances-shows/",
        "https://cmom.org/events/category/drop-in-programs/",
    ]
    out=[]
    for url in urls:
        r=requests.get(url,headers=HEADERS,timeout=25); r.raise_for_status()
        soup=BeautifulSoup(r.text,"html.parser")
        # The Events Calendar commonly uses tribe-events structures.
        candidates=soup.select("article, .tribe-events-calendar-list__event, .type-tribe_events")
        for node in candidates:
            title_node=node.select_one("h2 a, h3 a, .tribe-events-calendar-list__event-title-link")
            if not title_node: continue
            title=clean(title_node.get_text(" ",strip=True))
            text=clean(node.get_text(" ",strip=True))
            date_node=node.select_one("time")
            dt=None
            if date_node:
                raw=date_node.get("datetime") or date_node.get_text(" ",strip=True)
                try: dt=dtparser.parse(raw)
                except Exception: pass
            if not dt:
                m=re.search(r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}(?:,\s+\d{4})?",text)
                if m:
                    try: dt=dtparser.parse(m.group(0),default=datetime.now(TZ).replace(tzinfo=None))
                    except Exception: pass
            if not dt: continue
            if dt.date() < datetime.now(TZ).date(): continue
            ag, label=age_group(text,"0-5")
            href=title_node.get("href") or url
            out.append({
                "title":title,"date":dt.date().isoformat(),"time":"",
                "borough":"Manhattan","venue":"Children's Museum of Manhattan",
                "age_group":ag,"age_label":label if label!="Family" else "0–6中心",
                "price_type":"paid","category":infer_category(text),"tags":[],
                "description":clean(text[:280]),"source":"Children's Museum of Manhattan","url":href
            })
    return out




def nypl():
    out = []

    for page in range(0,5):
        url = f"https://www.nypl.org/events/calendar?page={page}&audience=children"

        r = requests.get(url, headers=HEADERS)
        soup = BeautifulSoup(r.text, "html.parser")

        for row in soup.select("table tr"):
            text = row.get_text(" ", strip=True)

    if not any(x in text.lower() for x in ["child", "family", "toddler", "baby"]):
    continue

            out.append({
                "title": text[:80],
                "source": "NYPL",
                "url": url
            })

    return out


def bpl():
    url="https://www.bklynlibrary.org/event-series/events-for-youth-and-family"
    r=requests.get(url,headers=HEADERS,timeout=25); r.raise_for_status()
    soup=BeautifulSoup(r.text,"html.parser")
    out=[]
    # Parse blocks that contain event links + recognizable dates.
    for node in soup.select("article, .event, .views-row, li"):
        a=node.find("a")
        if not a: continue
        title=clean(a.get_text(" ",strip=True))
        text=clean(node.get_text(" ",strip=True))
        if len(title)<4 or not re.search(r"\b(Mon|Tue|Wed|Thu|Fri|Sat|Sun)\b",text,re.I): continue
        m=re.search(r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2}",text,re.I)
        if not m: continue
        try:
            dt=dtparser.parse(m.group(0),default=datetime.now(TZ).replace(tzinfo=None))
            if dt.date() < datetime.now(TZ).date():
                dt=dt.replace(year=dt.year+1)
        except Exception: continue
        href=a.get("href") or url
        if href.startswith("/"): href="https://www.bklynlibrary.org"+href
        out.append({
            "title":title,"date":dt.date().isoformat(),"time":"",
            "borough":"Brooklyn","venue":"Brooklyn Public Library",
            "age_group":"all-ages","age_label":"Family","price_type":"free",
            "category":infer_category(text),"tags":["kids","family"],
            "description":clean(text[:280]),"source":"Brooklyn Public Library","url":href
        })
    return out

def dedupe(items):
    seen=set(); out=[]
    for e in sorted(items,key=lambda x:(x["date"],x["title"])):
        key=hashlib.sha1((e["title"].lower()+e["date"]+e["source"]).encode()).hexdigest()
        if key not in seen:
            seen.add(key); out.append(e)
    return out

def main():
    existing={"events":[]}
    if DATA.exists():
        existing=json.loads(DATA.read_text(encoding="utf-8"))
    fresh=[]
    for fn in (cmom,bpl):
        try: fresh += fn()
        except Exception as exc: print(f"[WARN] {fn.__name__}: {exc}")
    today=datetime.now(TZ).date().isoformat()
    # Keep old future records as fallback, then let new scrape refresh/augment.
    merged=[e for e in existing.get("events",[]) if e.get("date","")>=today] + fresh
    payload={"updated_at":datetime.now(TZ).isoformat(timespec="seconds"),"events":dedupe(merged)}
    DATA.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
    print(f"Wrote {len(payload['events'])} events")

def is_kids_event(text: str) -> bool:
    t = text.lower()

    include = [
        "kids", "children", "family", "toddler",
        "storytime", "story time", "baby",
        "parent", "family friendly"
    ]

    exclude = [
        "21+", "adult", "networking", "business",
        "conference", "crypto", "dating"
    ]

    if any(x in t for x in exclude):
        return False

    return any(x in t for x in include)

if not is_kids_event(text):
    continue

def score_event(e):
    score = 0

    if e["price_type"] == "free":
        score += 2

    if "museum" in e["source"].lower():
        score += 2

    if e["age_group"] in ["0-5", "6-12"]:
        score += 1

    if "story" in e["title"].lower():
        score += 1

    return score

events = sorted(events, key=lambda e: (-score_event(e), e["date"]))

if __name__=="__main__":
    main()
