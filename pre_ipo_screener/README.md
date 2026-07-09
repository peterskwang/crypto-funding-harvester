# Pre-IPO Stock Screener

Scans upcoming US IPOs, filters out ETF/SPAC/trust noise, and ranks the best
long (buy-the-pop) and short (fade-the-pop / lockup-expiry) candidates using
a transparent, rules-based score grounded in how similar recent IPOs actually
performed.

> **Not investment advice.** This is a research/alerting tool, not an
> execution bot. It surfaces ranked tickers with rationale for you to act on
> manually — verify everything independently before risking capital.

This currently lives inside `crypto-funding-harvester` as a second, unrelated
project (the GitHub integration doesn't yet have permission to create a new
repo). It's self-contained under `pre_ipo_screener/` so it can be lifted out
into its own repo later without restructuring.

## How it works
1. **Universe** (`screener/universe.py`) — pulls Polygon's IPO calendar for
   the next `LOOKAHEAD_DAYS` (upcoming candidates) and past `LOOKBACK_DAYS`
   (historical reference pool), dropping ETFs, SPAC units/warrants/rights,
   trusts, and bond funds.
2. **Historical pattern reference** (`screener/historical.py`) — computes
   day-1 pop, week-1/month-1 return, and realized volatility for each recent
   IPO, then groups them by sector × deal-size tier to answer "how did
   companies like this actually trade in the last quarter."
3. **Scoring** (`screener/scoring.py`) — upcoming IPOs get a 0-100 long score
   from deal size, matching analog-group performance, and listing proximity.
   Recent IPOs get flagged SHORT for momentum fades (strong day-1 pop now
   decaying) or lockup-expiry watch (~90-180 days post-listing). A suggested
   holding style (day-trade / swing hold / lockup watch) comes from realized
   volatility, so this isn't limited to intraday calls.
4. **Report** (`screener/report.py`) — renders a dated markdown report with
   top long picks, top short/fade picks, and the analog reference table.

## Setup
```bash
# from the repo root
pip install -r requirements.txt
export POLYGON_API_KEY=your_key_here   # or set it in the environment config so it persists
```

## Running
```bash
# from the repo root
python -m pre_ipo_screener.run_screen --mode weekly   # full universe + analog rebuild
python -m pre_ipo_screener.run_screen --mode daily     # cheap refresh using the cached weekly universe
```
Reports are written to `pre_ipo_screener/reports/YYYY-MM-DD.md`. Weekly runs
cache the universe and analog groups to `pre_ipo_screener/state/screener_state.json`
so daily runs stay cheap.

## Configuration
Edit `config.py` to adjust lookahead/lookback windows, deal-size tiers,
scoring weights, fade/lockup thresholds, and volatility cutoffs for the
suggested holding style.

## Tests
```bash
pytest tests/test_pre_ipo_universe.py tests/test_pre_ipo_scoring.py tests/test_pre_ipo_report.py
```
All tests mock `PolygonClient` — no live network calls or API key required.
