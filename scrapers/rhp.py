"""Rockhouse Partners (RHP) events plugin. Used by Metro, Buddy Guy's Legends, Gman Tavern."""
import re
from bs4 import BeautifulSoup
from .common import *


def _text(el):
    return " ".join(el.get_text(" ", strip=True).split()) if el else ""


def parse(html, today, venue_map, default_key=None):
    soup = BeautifulSoup(html, "html.parser")
    out, seen = [], set()
    for w in soup.select("div.eventWrapper"):
        title_el = w.select_one("h2[class*=rhp-event__title]")
        date_el = w.select_one(".singleEventDate")
        if not (title_el and date_el):
            continue
        vl = w.select_one("a.venueLink")
        if vl:
            key = venue_map.get(_text(vl).lower().replace("’", "'"))
        else:
            key = default_key
        d = month_day(_text(date_el), today)
        title = _text(title_el)
        if not (key and d and title) or not is_music(title, _text(w.select_one("[class*=tagline]"))):
            continue
        more = w.select_one("a.url") or w.select_one("a[rel=bookmark]")
        cta = w.select_one("a.btn-primary")
        url = (cta or more or {}).get("href") if (cta or more) else None
        if not url:
            continue
        doors, show = doors_show(_text(w))
        sub = _text(w.select_one("h4[class*=subheader]"))
        sold = bool(w.select_one(".sold-out")) or "sold out" in _text(cta).lower()
        ev = make_event(d, key, title, url, doors, show,
                        support=[s.strip() for s in re.split(r",| / ", sub) if s.strip()] if sub else [],
                        age=age_norm(_text(w.select_one("[class*=age-restriction]"))),
                        price=price_norm(_text(w.select_one("[class*=cost-text]"))),
                        status="sold_out" if sold else None)
        k = (ev["date"], key, ev["headliner"].lower(), show)
        if k not in seen:
            seen.add(k)
            out.append(ev)
    return out


def next_url(html, current):
    soup = BeautifulSoup(html, "html.parser")
    a = soup.select_one("link[rel=next], a[rel=next], a.next")
    return a.get("href") if a and a.get("href") and a.get("href") != current else None


def scrape(base_url, venue_map, default_key=None, today=None, max_pages=8, delay=2.0):
    from datetime import date
    today = today or date.today()
    out, url, n = [], base_url, 0
    while url and n < max_pages:
        html = fetch(url, delay)
        out += parse(html, today, venue_map, default_key)
        url, n = next_url(html, url), n + 1
    return out
