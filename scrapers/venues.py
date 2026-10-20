"""One function per venue/source. Each returns a list of events (see common.make_event)."""
import json, re
from datetime import datetime
from zoneinfo import ZoneInfo
from bs4 import BeautifulSoup
from .common import *
from . import rhp

CHI = ZoneInfo("America/Chicago")


def metro(today):
    vm = {"metro": "metro", "sleeping village": "sleepingvillage"}  # Metro also lists Sleeping Village shows
    return rhp.scrape("https://metrochicago.com/events/", vm, today=today)


def buddyguy(today):
    return rhp.scrape("https://www.buddyguy.com/", {"buddy guy's legends": "buddyguy"}, "buddyguy", today)


def gman(today):
    return rhp.scrape("https://gmantavern.com/", {}, "gman", today)


def parse_reggies(html, today):
    soup = BeautifulSoup(html, "html.parser")
    out = []
    for a in soup.select("article.show"):
        cls = " ".join(a.get("class", []))
        t = a.select_one("time[datetime]")
        titles = [h.get_text(" ", strip=True) for h in a.select("hgroup .band-title")]
        if not (t and titles) or "genre-sports" in cls or not is_music(titles[0], a.select_one(".presented-by").get_text() if a.select_one(".presented-by") else ""):
            continue
        d = datetime.strptime(t["datetime"], "%Y-%m-%d").date()
        doors = show = plain = None
        for li in a.select("ul.details li"):
            tx = li.get_text(" ", strip=True)
            if re.search(r"\bdoors\b", tx, re.I): doors = to_24h(tx)
            elif re.search(r"\bshow\b", tx, re.I): show = to_24h(tx)
            elif to_24h(tx) and not li.find("a"): plain = to_24h(tx)
        if plain:
            if show: doors = doors or plain
            else: show = plain
        age = a.select_one("ul.details li a")
        room = a.select_one("aside.sideicons a")
        room = re.sub(r"^View all\s+", "", room.get("title", "")).strip() if room else None
        tix = a.select_one("a.ticketfly") or a.select_one("a.expandshow")
        if not tix: continue
        out.append(make_event(d, "reggies", titles[0], tix["href"], doors, show, titles[1:],
                              room or None, age_norm(age.get_text() if age else ""), None, None))
    return out


def reggies(today):
    return parse_reggies(fetch("https://www.reggieslive.com/"), today)


def parse_rosas(html, today):
    out = []
    for blob in re.findall(r'<script[^>]*ld\+json[^>]*>(.*?)</script>', html, re.S):
        try:
            data = json.loads(blob)
        except ValueError:
            continue
        for e in data.get("Events", []) if isinstance(data, dict) else []:
            sd = e.get("startDate")
            if not (sd and e.get("name") and e.get("url")): continue
            dt = datetime.fromisoformat(sd.replace("Z", "+00:00")).astimezone(CHI)
            if not is_music(e["name"]): continue
            out.append(make_event(dt.date(), "rosas", e["name"], e["url"], None, dt.strftime("%H:%M")))
    return out


def rosas(today):
    return parse_rosas(fetch("https://www.rosaslounge.com/"), today)


def parse_hob(html, today):
    out = []
    for blob in re.findall(r'<script type="application/ld\+json">(\{"@context":"https://schema.org","@type":"MusicEvent".*?)</script>', html, re.S):
        try:
            e = json.loads(blob)
        except ValueError:
            continue
        sd = e.get("startDate", "")
        if not (sd and e.get("name") and e.get("url")): continue
        d, _, tm = sd.partition("T")
        out.append(make_event(d, "hob", e["name"], e["url"], None, tm[:5] or None))
    return out


def hob(today):
    return parse_hob(fetch("https://www.houseofblues.com/chicago"), today)


def parse_fitz(html, today):
    soup = BeautifulSoup(html, "html.parser")
    out = []
    for dspan in soup.select("span.tw-event-date"):
        box = dspan
        while box.parent and len(box.select("span.tw-event-date")) < 1 or (box.parent and len(box.parent.select("span.tw-event-date")) == 1):
            box = box.parent
        title = box.select_one("a[title], .tw-name a") or box.select("a")[-1]
        names = [a.get_text(" ", strip=True) for a in box.select("a") if len(a.get_text(strip=True)) > 12 and "tw-buy" not in " ".join(a.get("class", []))]
        name = names[0] if names else None
        buy = box.select_one("a.tw-buy-tix-btn")
        d = month_day(dspan.get_text(), today)
        if not (name and buy and d) or not is_music(name): continue
        g = lambda c: (box.select_one(c).get_text(" ", strip=True) if box.select_one(c) else "")
        out.append(make_event(d, "fitzgeralds", name, buy["href"], to_24h(g(".tw-event-door-time")),
                              to_24h(g(".tw-event-time")), [], None, age_norm(g(".tw-age-restriction")), price_norm(g(".tw-price"))))
    return out


def fitzgeralds(today):
    return parse_fitz(fetch("https://www.fitzgeraldsnightclub.com/", delay=10), today)


# scraper name -> (function, venue keys it is responsible for)
REGISTRY = {
    "metro": (metro, ["metro"]),
    "buddyguy": (buddyguy, ["buddyguy"]),
    "gman": (gman, ["gman"]),
    "reggies": (reggies, ["reggies"]),
    "rosas": (rosas, ["rosas"]),
    "hob": (hob, ["hob"]),
    "fitzgeralds": (fitzgeralds, ["fitzgeralds"]),
}
