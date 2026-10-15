# chicagoshows
## Prototype

    python3 build.py                # renders dist/index.html from venues.json + events.json
    python3 -m http.server -d dist  # open http://localhost:8000

Pass `--today YYYY-MM-DD` to simulate a date; past shows are dropped at build time.
`events.json` is hand-compiled sample data (Oct 14-22, 2026); scrapers will replace it.
