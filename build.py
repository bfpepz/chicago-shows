#!/usr/bin/env python3
"""Build the Chicago Shows static site from venues.json + events.json.

Usage:  python3 build.py [--today YYYY-MM-DD]
Output: dist/index.html     (standalone page, open or serve it)
        dist/artifact.html  (same page as an HTML fragment for publishing)
"""
import argparse, json, html, sys
from collections import Counter, OrderedDict
from datetime import date, datetime
from zoneinfo import ZoneInfo
from pathlib import Path

ROOT = Path(__file__).parent
esc = html.escape

NOT_CONNECTED = [
    {"key": "emptybottle", "name": "Empty Bottle", "site": "https://www.emptybottle.com/",
     "platform": "Squarespace (needs investigation)"},
]

CSS = """
:root{
  --bg:#f5f2ec; --fg:#1c1b18; --muted:#6b675e; --rule:#dcd6c9; --card:#fbf9f4;
  --accent:#c8102e; --link:#1d5f8f; --chip:#ebe5d8; --chip-on:#1c1b18; --chip-on-fg:#f5f2ec;
  --price:#2a6a3a; --sold:#9a948a;
}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){
  --bg:#141412; --fg:#ece8df; --muted:#9a958a; --rule:#2c2b27; --card:#1b1a17;
  --accent:#ff5a6e; --link:#7fc0ee; --chip:#26251f; --chip-on:#ece8df; --chip-on-fg:#141412;
  --price:#7bd08f; --sold:#6f6a60; color-scheme:dark}}
:root[data-theme="dark"]{
  --bg:#141412; --fg:#ece8df; --muted:#9a958a; --rule:#2c2b27; --card:#1b1a17;
  --accent:#ff5a6e; --link:#7fc0ee; --chip:#26251f; --chip-on:#ece8df; --chip-on-fg:#141412;
  --price:#7bd08f; --sold:#6f6a60; color-scheme:dark}
*{box-sizing:border-box}
[hidden]{display:none!important}
body{background:var(--bg);color:var(--fg);margin:0;
  font:16px/1.45 "Archivo",system-ui,-apple-system,"Segoe UI",sans-serif;
  padding-left:max(16px,env(safe-area-inset-left,0px));
  padding-right:max(16px,env(safe-area-inset-right,0px));
  padding-block:0 3rem}
.wrap{max-width:760px;margin:0 auto}
a{color:inherit}
header.top{padding-top:2rem;display:flex;flex-direction:column;gap:.35rem}
h1{font:800 clamp(2rem,7vw,2.8rem)/1 "Archivo",sans-serif;letter-spacing:-.03em;margin:0;text-wrap:balance}
h1 span{color:var(--accent)}
.sub{color:var(--muted);margin:0;font-size:.95rem;max-width:60ch}
.mono{font-family:"IBM Plex Mono",ui-monospace,Menlo,monospace}
.bar{position:sticky;top:env(safe-area-inset-top,0px);z-index:5;background:var(--bg);
  border-bottom:1px solid var(--rule);margin-top:1.25rem;padding:.7rem 0;display:flex;flex-direction:column;gap:.55rem}
.bar input[type=search]{width:100%;font:inherit;padding:.5rem .7rem;border:1px solid var(--rule);
  background:var(--card);color:var(--fg);border-radius:6px}
.chips{display:flex;flex-wrap:wrap;gap:.35rem}
.chip{font:500 .8rem/1 "IBM Plex Mono",monospace;padding:.45rem .6rem;border-radius:99px;border:1px solid var(--rule);
  background:var(--chip);color:var(--fg);cursor:pointer}
.chip[aria-pressed="true"]{background:var(--chip-on);color:var(--chip-on-fg);border-color:var(--chip-on)}
.count{color:var(--muted);font-size:.8rem}
.day{margin-top:1.75rem}
.day h2{font:600 .8rem/1 "IBM Plex Mono",monospace;text-transform:uppercase;letter-spacing:.12em;
  margin:0 0 .4rem;padding-bottom:.5rem;border-bottom:2px solid var(--fg);display:flex;gap:.6rem;align-items:baseline}
.day h2 .today{color:var(--accent)}
.show{display:grid;grid-template-columns:4.6rem 1fr auto;gap:.2rem .9rem;padding:.8rem 0;border-bottom:1px solid var(--rule);align-items:baseline}
.time{font:500 .9rem/1.3 "IBM Plex Mono",monospace}
.time small{display:block;color:var(--muted);font-size:.7rem}
.main{min-width:0}
.head{font-weight:700;font-size:1.08rem;line-height:1.25;text-decoration:none;text-wrap:balance}
.head:hover{color:var(--link);text-decoration:underline}
.support{color:var(--muted);font-size:.9rem}
.where{font-size:.85rem;margin-top:.15rem}
.where b{font-weight:600}
.where .room{color:var(--muted)}
.meta{text-align:right;display:flex;flex-direction:column;align-items:flex-end;gap:.2rem;font:500 .8rem/1.2 "IBM Plex Mono",monospace}
.price{color:var(--price);font-weight:600}
.age{color:var(--muted)}
.tix{color:var(--link)}
.sold{color:var(--accent);text-transform:uppercase;letter-spacing:.06em}
.show.is-sold .head{color:var(--sold);text-decoration:line-through}
.empty{padding:2rem 0;color:var(--muted)}
footer{margin-top:3rem;border-top:2px solid var(--fg);padding-top:1rem;font-size:.85rem;color:var(--muted)}
footer h3{font:600 .8rem/1 "IBM Plex Mono",monospace;text-transform:uppercase;letter-spacing:.12em;color:var(--fg);margin:0 0 .6rem}
.tbl{overflow-x:auto}
table{border-collapse:collapse;width:100%;min-width:480px}
th,td{text-align:left;padding:.35rem .5rem .35rem 0;border-bottom:1px solid var(--rule);font-size:.82rem;vertical-align:top}
th{font:600 .7rem/1 "IBM Plex Mono",monospace;text-transform:uppercase;letter-spacing:.08em}
td.n{font-family:"IBM Plex Mono",monospace}
footer p{max-width:62ch}
@media (max-width:520px){
  .show{grid-template-columns:3.9rem 1fr}
  .meta{grid-column:2;flex-direction:row;flex-wrap:wrap;justify-content:flex-start;gap:.2rem .8rem;text-align:left}
}
"""

JS = """
(function(){
  var rows=[].slice.call(document.querySelectorAll('.show')),
      days=[].slice.call(document.querySelectorAll('.day')),
      q=document.getElementById('q'), chips=[].slice.call(document.querySelectorAll('.chip[data-v]')),
      hs=document.getElementById('hs'), count=document.getElementById('count'), none=document.getElementById('none');
  var on={}, hideSold=false;
  function apply(){
    var t=(q.value||'').toLowerCase().trim(), any=Object.keys(on).length, n=0;
    rows.forEach(function(r){
      var ok=(!any||on[r.dataset.v])&&(!t||r.dataset.s.indexOf(t)>-1)&&!(hideSold&&r.dataset.sold==='1');
      r.hidden=!ok; if(ok)n++;
    });
    days.forEach(function(d){d.hidden=!d.querySelector('.show:not([hidden])')});
    count.textContent=n+' show'+(n===1?'':'s'); none.hidden=n>0;
  }
  chips.forEach(function(c){c.addEventListener('click',function(){
    var v=c.dataset.v; if(on[v]){delete on[v];c.setAttribute('aria-pressed','false')}
    else{on[v]=1;c.setAttribute('aria-pressed','true')} apply()})});
  hs.addEventListener('click',function(){hideSold=!hideSold;hs.setAttribute('aria-pressed',hideSold);apply()});
  q.addEventListener('input',apply); apply();
})();
"""


def fmt_time(t):
    if not t:
        return ""
    h, m = map(int, t.split(":"))
    suf = "am" if h < 12 else "pm"
    h12 = h % 12 or 12
    return f"{h12}{suf}" if m == 0 else f"{h12}:{m:02d}{suf}"


def render_row(e, venues):
    v = venues.get(e["venue"], {"name": e["venue"]})
    main_t = e.get("show") or e.get("doors")
    sub_t = f"doors {fmt_time(e['doors'])}" if e.get("doors") and e.get("show") else ""
    sold = e.get("status") == "sold_out"
    support = ", ".join(e.get("support") or [])
    age = {"all": "all ages"}.get(e.get("age"), e.get("age") or "")
    search = " ".join([e["headliner"], support, v["name"], e.get("room") or ""]).lower()

    if sold:
        right = '<span class="sold">sold out</span>'
    elif e.get("price"):
        right = f'<span class="price">{esc(e["price"])}</span>'
    else:
        right = f'<a class="tix" href="{esc(e["url"])}" rel="noopener" target="_blank">tickets &rarr;</a>'
    age_html = f'<span class="age">{esc(age)}</span>' if age else ""
    room = f' <span class="room">· {esc(e["room"])}</span>' if e.get("room") else ""
    sup = f'<div class="support">{esc(support)}</div>' if support else ""
    return (
        f'<article class="show{" is-sold" if sold else ""}" data-v="{esc(e["venue"])}" '
        f'data-s="{esc(search)}" data-sold="{1 if sold else 0}">'
        f'<div class="time">{fmt_time(main_t) or "tba"}<small>{sub_t}</small></div>'
        f'<div class="main"><a class="head" href="{esc(e["url"])}" rel="noopener" target="_blank">{esc(e["headliner"])}</a>'
        f'{sup}<div class="where"><b>{esc(v["name"])}</b>{room}</div></div>'
        f'<div class="meta">{right}{age_html}</div></article>'
    )


def build(today):
    venues_list = json.loads((ROOT / "venues.json").read_text())
    venues = {v["key"]: v for v in venues_list}
    events = json.loads((ROOT / "events.json").read_text()) if (ROOT / "events.json").read_text().lstrip().startswith("[") else \
        [json.loads(l) for l in (ROOT / "events.json").read_text().splitlines() if l.strip()]

    events = [e for e in events if e["date"] >= today.isoformat()]
    events.sort(key=lambda e: (e["date"], e.get("show") or e.get("doors") or "99:99", e["headliner"]))

    # dedupe: same date + venue + headliner
    seen, uniq = set(), []
    for e in events:
        k = (e["date"], e["venue"], e["headliner"].lower())
        if k not in seen:
            seen.add(k)
            uniq.append(e)
    events = uniq

    by_day = OrderedDict()
    for e in events:
        by_day.setdefault(e["date"], []).append(e)

    counts = Counter(e["venue"] for e in events)
    priced = Counter(e["venue"] for e in events if e.get("price"))

    parts = []
    for d, evs in by_day.items():
        dt = datetime.strptime(d, "%Y-%m-%d").date()
        label = dt.strftime("%a %b ") + str(dt.day)
        tag = '<span class="today">today</span>' if dt == today else ""
        parts.append(f'<section class="day"><h2><span>{label}</span>{tag}</h2>'
                     + "".join(render_row(e, venues) for e in evs) + "</section>")

    chips = "".join(
        f'<button class="chip" type="button" data-v="{v["key"]}" aria-pressed="false">{esc(v["name"])}</button>'
        for v in venues_list if counts.get(v["key"]))

    rows = []
    for v in venues_list:
        c = counts.get(v["key"], 0)
        p = f'{priced.get(v["key"], 0)}/{c}' if c else "–"
        rows.append(f'<tr><td><a href="{esc(v["site"])}" rel="noopener" target="_blank">{esc(v["name"])}</a></td>'
                    f'<td class="n">{c}</td><td class="n">{p}</td><td>{("not connected yet · " if not c else "")}{esc(v["platform"])}</td></tr>')
    for v in NOT_CONNECTED:
        rows.append(f'<tr><td><a href="{esc(v["site"])}" rel="noopener" target="_blank">{esc(v["name"])}</a></td>'
                    f'<td class="n">–</td><td class="n">–</td><td>not connected yet · {esc(v["platform"])}</td></tr>')

    first = datetime.strptime(next(iter(by_day)), "%Y-%m-%d").date() if by_day else today
    last = datetime.strptime(next(reversed(by_day)), "%Y-%m-%d").date() if by_day else today
    span = f'{first.strftime("%b")} {first.day} – {last.strftime("%b")} {last.day}'

    body = f"""
<div class="wrap">
<header class="top">
  <h1>Chicago <span>Shows</span></h1>
  <p class="sub">Live music in Chicago, one list, soonest first. Prices shown where the venue lists them;
  otherwise tap through to tickets.</p>
</header>
<div class="bar">
  <input id="q" type="search" placeholder="Search bands or venues" aria-label="Search bands or venues">
  <div class="chips">{chips}<button class="chip" id="hs" type="button" aria-pressed="false">hide sold out</button></div>
  <div class="count mono" id="count"></div>
</div>
<main>{''.join(parts)}<p class="empty" id="none" hidden>Nothing matches. Try clearing a filter.</p></main>
<footer>
  <h3>Coverage</h3>
  <div class="tbl"><table><thead><tr><th>Venue</th><th>Shows</th><th>With price</th><th>Source</th></tr></thead>
  <tbody>{''.join(rows)}</tbody></table></div>
  <p>Listings come from each venue's own calendar, whitelisted and refreshed daily in the real version. Every show links
  back to the venue's ticket page. Doors/show times, prices and ages are as the venue lists them. Always confirm with the venue.</p>
</footer>
</div>
<script>{JS}</script>
"""
    return body, len(events), counts, priced


FONTS = ('<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@400;500;600;700;800'
         '&family=IBM+Plex+Mono:wght@400;500;600&display=swap">')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--today", default=None)
    a = ap.parse_args()
    today = date.fromisoformat(a.today) if a.today else datetime.now(ZoneInfo('America/Chicago')).date()

    body, n, counts, priced = build(today)
    dist = ROOT / "dist"
    dist.mkdir(exist_ok=True)

    head = ('<meta name="claude:viewport-fit-sides" content="cover">\n<title>Chicago Shows</title>\n'
            "<meta name='impact-site-verification' value='bb5ea79b-5729-4929-821a-e1705dc3ba7a'>\n"
            f'{FONTS}\n<style>{CSS}</style>\n')
    (dist / "artifact.html").write_text(head + body)

    standalone = ('<!doctype html>\n<html lang="en"><head><meta charset="utf-8">'
                  '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">\n'
                  + head + '</head><body>' + body + '</body></html>')
    (dist / "index.html").write_text(standalone)

    print(f"built {n} shows from {today} -> dist/index.html, dist/artifact.html")
    for k, c in counts.most_common():
        print(f"  {k:16s} {c:3d} shows, {priced.get(k, 0)} priced")


if __name__ == "__main__":
    sys.exit(main())
