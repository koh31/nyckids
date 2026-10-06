#!/usr/bin/env python3
from __future__ import annotations
import json,re,hashlib,html
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
from dateutil import parser as dtparser
ROOT=Path(__file__).resolve().parents[1];DATA=ROOT/"data"/"events.json";TZ=ZoneInfo("America/New_York")
HEADERS={"User-Agent":"NYCKidsGo/1.0 (+family event index)"};ALLOWED_AREAS={"Manhattan","Brooklyn","Queens"}
def clean(v):return re.sub(r"\s+"," ",html.unescape(str(v or ""))).strip()
def get(url):
    r=requests.get(url,headers=HEADERS,timeout=30);r.raise_for_status();return r
def parse_date(text):
    text=clean(text);m=re.search(r"\b(20\d{2})-(\d{2})-(\d{2})\b",text)
    if m:return m.group(0)
    m=re.search(r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2}(?:,\s*20\d{2})?",text,re.I)
    if not m:return ""
    try:
        default=datetime.now(TZ).replace(tzinfo=None);d=dtparser.parse(m.group(0),default=default)
        if not re.search(r"20\d{2}",m.group(0)) and d.date()<datetime.now(TZ).date():d=d.replace(year=d.year+1)
        return d.date().isoformat()
    except:return ""
def date_label(date):
    try:return datetime.fromisoformat(date).strftime("%b %d").replace(" 0"," ")
    except:return date or ""
def infer_age(text,default="Family"):
    t=text.lower();m=re.search(r"ages?\s*(\d{1,2})\s*[–—-]\s*(\d{1,2})",t)
    if m:
        lo,hi=int(m.group(1)),int(m.group(2))
        if hi<=5:return "0-5"
        if lo>=13:return "13+"
        if lo>=6 and hi<=12:return "6-12"
        return "Family"
    if any(k in t for k in ["baby","babies","toddler","preschool"]):return "0-5"
    if "teen" in t:return "13+"
    return default
def infer_genre(text):
    t=text.lower();checks=[(["storytime","story time","read aloud"],"Storytime"),(["music","sing","song","concert"],"Music"),(["dance","theater","theatre","performance","show"],"Performance"),(["science","stem","engineering"],"Science"),(["outdoor","park","garden","nature walk"],"Outdoor"),(["workshop","craft","hands-on"],"Workshop"),(["art","paint","drawing","gallery"],"Art")]
    for keys,g in checks:
        if any(k in t for k in keys):return g
    return "Other"
def infer_price(text,default="paid"):
    t=text.lower();return "free" if "free" in t or "no cost" in t else default
def image_from(node,base):
    img=node.select_one("img")
    if not img:return ""
    src=img.get("src") or img.get("data-src") or img.get("data-lazy-src") or ""
    return "" if not src or src.startswith("data:") else urljoin(base,src)
def candidate_nodes(soup):
    sels=["article","[class*='event-card']","[class*='event_card']","[class*='event-list'] > *","[class*='calendar'] article",".views-row","li[class*='event']"];found=[];seen=set()
    for sel in sels:
        for n in soup.select(sel):
            if id(n) not in seen:seen.add(id(n));found.append(n)
    return found
def generic_events(url,source,area="Manhattan",default_age="Family",default_price="paid",must_terms=None,limit=80):
    soup=BeautifulSoup(get(url).text,"html.parser");out=[]
    for n in candidate_nodes(soup):
        text=clean(n.get_text(" ",strip=True));low=text.lower()
        if len(text)<18 or (must_terms and not any(k in low for k in must_terms)):continue
        a=n.select_one("h1 a,h2 a,h3 a,h4 a,a")
        if not a:continue
        title=clean(a.get_text(" ",strip=True))
        if len(title)<4 or len(title)>180:continue
        d=parse_date(text)
        if not d or d<datetime.now(TZ).date().isoformat():continue
        out.append({"title":title,"date":d,"date_label":date_label(d),"time":"","area":area,"borough":area,"venue":source,"age_group":infer_age(text,default_age),"genre":infer_genre(text),"price_type":infer_price(text,default_price),"description":clean(text[:650]),"source":source,"url":urljoin(url,a.get("href") or url),"image":image_from(n,url)})
        if len(out)>=limit:break
    return out
def nypl():
    url="https://www.nypl.org/events/calendar?audience=children";soup=BeautifulSoup(get(url).text,"html.parser");out=[]
    for n in candidate_nodes(soup)+list(soup.select("table tr")):
        text=clean(n.get_text(" ",strip=True));low=text.lower()
        if len(text)<20 or not any(k in low for k in ["child","kids","family","toddler","baby","storytime","teen"]):continue
        a=n.select_one("h2 a,h3 a,h4 a,a")
        if not a:continue
        title=clean(a.get_text(" ",strip=True));d=parse_date(text)
        if len(title)<4 or not d or d<datetime.now(TZ).date().isoformat():continue
        area="Manhattan"
        if "brooklyn" in low:area="Brooklyn"
        elif "queens" in low:area="Queens"
        elif "bronx" in low or "staten island" in low:continue
        out.append({"title":title,"date":d,"date_label":date_label(d),"time":"","area":area,"borough":area,"venue":"New York Public Library","age_group":infer_age(text),"genre":infer_genre(text),"price_type":"free","description":clean(text[:650]),"source":"NYPL","url":urljoin(url,a.get("href") or url),"image":image_from(n,url)})
    return out[:120]
def cmom():return generic_events("https://cmom.org/events/","Children's Museum of Manhattan","Manhattan","0-5","paid",["event","workshop","family","children","story","art","music","science","play"],80)
def moma():
    out=[]
    for url in ["https://www.moma.org/visit/families/","https://www.moma.org/calendar/"]:
        try:out+=generic_events(url,"MoMA","Manhattan","Family","paid",["family","kids","kid","children","child","teen","gallery talk","workshop"],70)
        except Exception as e:print("[WARN] MoMA",e)
    return out
def met():
    out=[]
    for url in ["https://www.metmuseum.org/events","https://www.metmuseum.org/visit-guides/families/programs-and-resources","https://www.metmuseum.org/visit-guides/families/childrens-classes"]:
        try:out+=generic_events(url,"The Met","Manhattan","Family","paid",["famil","kids","kid","children","child","storytime","ages","art","studio"],80)
        except Exception as e:print("[WARN] The Met",e)
    return out
def dedupe(items):
    out=[];seen=set()
    for e in sorted(items,key=lambda x:(x.get("date","9999"),x.get("title",""))):
        key=hashlib.sha1((e.get("title","").lower()+e.get("date","")+e.get("source","")).encode()).hexdigest()
        if key in seen:continue
        seen.add(key);out.append(e)
    return out
def main():
    old={"events":[]}
    if DATA.exists():
        try:old=json.loads(DATA.read_text(encoding="utf-8"))
        except:pass
    fresh=[]
    for fn in (nypl,cmom,moma,met):
        try:
            rows=fn();print(fn.__name__,len(rows));fresh+=rows
        except Exception as e:print("[WARN]",fn.__name__,e)
    today=datetime.now(TZ).date().isoformat();retained=[e for e in old.get("events",[]) if e.get("date","")>=today]
    items=dedupe(retained+fresh);items=[e for e in items if not (e.get("area") and e.get("area") not in ALLOWED_AREAS)]
    DATA.write_text(json.dumps({"updated_at":datetime.now(TZ).isoformat(timespec="seconds"),"events":items},ensure_ascii=False,indent=2),encoding="utf-8");print("TOTAL",len(items))
if __name__=="__main__":main()
