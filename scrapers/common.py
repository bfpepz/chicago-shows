"""Shared helpers: polite fetching (robots.txt aware), time/date parsing, event schema."""
import re, time, urllib.request, urllib.parse, urllib.robotparser
from datetime import date, timedelta

UA = "ChicagoShowsBot/0.1 (+https://github.com/bfpepz/chicago-shows)"
_robots = {}
_last = {}


def _get(url, timeout=40):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html,*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode(r.headers.get_content_charset() or "utf-8", errors="replace")


def allowed(url):
    p = urllib.parse.urlparse(url)
    root = f"{p.scheme}://{p.netloc}"
    if root not in _robots:
        rp = urllib.robotparser.RobotFileParser()
        try:
            rp.parse(_get(root + "/robots.txt", 20).splitlines())
        except Exception:
            rp.parse([])  # robots unreachable -> allow
        _robots[root] = rp
    return _robots[root].can_fetch(UA, url)


def fetch(url, delay=2.0):
    """GET a page, honoring robots.txt and spacing requests to the same host."""
    if not allowed(url):
        raise PermissionError(f"robots.txt disallows {url}")
    host = urllib.parse.urlparse(url).netloc
    wait = delay - (time.time() - _last.get(host, 0))
    if wait > 0:
        time.sleep(wait)
    try:
        return _get(url)
    finally:
        _last[host] = time.time()


TIME_RE = re.compile(r"(\d{1,2})(?::(\d{2}))?\s*([ap])\.?m", re.I)


def to_24h(text):
    m = TIME_RE.search(text or "")
    if not m:
        return None
    h, mi, ap = int(m.group(1)), int(m.group(2) or 0), m.group(3).lower()
    h = h % 12 + (12 if ap == "p" else 0)
    return f"{h:02d}:{mi:02d}"


def doors_show(text):
    """'Doors: 6:30 pm // Show: 7:30 pm' -> ('18:30','19:30'); 'Show: 9 pm' -> (None,'21:00')."""
    t = text or ""
    d = re.search(r"doors?\s*:?\s*(\d{1,2}(?::\d{2})?\s*[ap]\.?m)", t, re.I)
    s = re.search(r"(?:show|music)\s*:?\s*(\d{1,2}(?::\d{2})?\s*[ap]\.?m)", t, re.I)
    doors = to_24h(d.group(1)) if d else None
    show = to_24h(s.group(1)) if s else None
    if not show and not doors:
        show = to_24h(t)
    return doors, show


MONTHS = {m: i for i, m in enumerate("jan feb mar apr may jun jul aug sep oct nov dec".split(), 1)}


def month_day(text, today):
    """'Thu, Oct 22' (no year) -> date, rolling into next year if it is long past."""
    m = re.search(r"([A-Za-z]{3})[a-z]*\.?\s+(\d{1,2})", text or "")
    if not m or m.group(1).lower() not in MONTHS:
        return None
    mo, d = MONTHS[m.group(1).lower()], int(m.group(2))
    try:
        c = date(today.year, mo, d)
    except ValueError:
        return None
    if c < today - timedelta(days=60):
        c = date(today.year + 1, mo, d)
    return c


def age_norm(text):
    t = (text or "").lower()
    if "all ages" in t or "all-ages" in t:
        return "all"
    for a in ("21", "18", "17"):
        if a in t:
            return a + "+"
    return None


def price_norm(text):
    m = re.findall(r"\$\s?\d[\d,]*(?:\.\d{2})?", text or "")
    if not m:
        return None
    vals = [x.replace(" ", "") for x in m]
    if all(float(v[1:].replace(",", "")) == 0 for v in vals):
        return "Free"
    vals = [v[:-3] if v.endswith(".00") else v for v in vals]
    return vals[0] if len(vals) == 1 or vals[0] == vals[-1] else f"{vals[0]}–{vals[-1]}"


NOT_MUSIC = re.compile(
    r"storyslam|story slam|comedy|stand-?up|trivia|bingo|karaoke|tailgate|bus to|\bbus\b|brunch|"
    r"burlesque|\bdj\b|dance party|wrestling|poetry slam|watch party|private event|closed", re.I)


def is_music(title, extra=""):
    return not NOT_MUSIC.search(f"{title} {extra}")


def make_event(d, venue, headliner, url, doors=None, show=None, support=None,
               room=None, age=None, price=None, status=None):
    return {"date": d.isoformat() if hasattr(d, "isoformat") else d, "doors": doors, "show": show,
            "headliner": " ".join((headliner or "").split()), "support": support or [],
            "venue": venue, "room": room, "age": age, "price": price, "status": status, "url": url}
