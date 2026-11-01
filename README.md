# 🏆 Title Race — EPL Season Simulator

Play out a full Premier League season by hand. Single-file web app — no build
step, no dependencies, no external requests once loaded.

**▶️ Play: https://astki-kr.github.io/title-race/**

Companion app to [Pitch Perfect](https://astki-kr.github.io/fifawc/) (World Cup
trivia & history) — same install pattern, separate app.

## Install on your iPad / iPhone

1. Open the link above in **Safari**.
2. Tap the **Share** button, then **Add to Home Screen**.
3. It launches full-screen with its own icon, like a native app.

On **Android**, open the link in Chrome and tap **Install app** / **Add to Home screen**.

## How it works

### 📅 Fixtures
All 20 current Premier League clubs, drawn into a real **double round-robin**
season — every team plays every other team once at home, once away. That's
38 matchdays and 380 matches in total, exactly mirroring the real competition.

Browse by matchday, enter the score for each match, then tap **+ scorer** to
credit goals to specific players from either squad — searchable, same as
picking a favourite. Once you hit **Save score**, that match **locks for
3 minutes** before it can be edited again — long enough to stop a quick
re-edit, short enough that a genuine correction doesn't mean waiting around.

### 📊 Table
The league table, computed live from every match you've entered — points,
goal difference, goals for/against, all the usual tie-breaks. The top 4
(Champions League) and bottom 3 (relegation) are marked, same as the real
thing.

### Squads
Tap any club — from the fixture list, the table, or search — for its full
squad: **shirt number, position, date of birth (with age computed live),
and country**. Pick one **favourite player per club** with a heart; picking
a new one swaps out the old pick automatically.

## Data

- **Squads** — 670 players across all 20 clubs, from the official
  [Fantasy Premier League API](https://fantasy.premierleague.com/api/bootstrap-static/)
  (name, club, nationality, date of birth) cross-matched against the
  Premier League's own stats API for shirt numbers. Numbers with no
  confident match show as "–" rather than being guessed — about 77% of
  players have one. FPL is a live, actively-updated source (the same data
  the real fantasy game runs on), so club assignment stays current through
  each transfer window; a handful of entries can lag by a few days right
  after deadline day, same as the real game.
- **Fixtures** — a generated double round-robin, not the real published
  2026-27 calendar. The simulator only needs the structure (who plays whom,
  home and away), not real-world dates, since matches are entered as they're
  actually played.

Both are embedded directly in `index.html` as plain data — swappable for a
`fetch()` later without touching anything else.

### Re-syncing after a transfer window

Squad data doesn't call a live API on every page load — it's baked into the
file, same as the companion app. To refresh it (recommended: once, after the
January window):

```
python3 scripts/update_squads.py        # writes a fresh epl_squads.js
# then splice its SQUADS block into index.html, run ./bump.sh, and deploy
```

If the 20-club list itself changes (end-of-season promotion/relegation),
regenerate the fixture list too:

```
python3 scripts/generate_fixtures.py     # writes a fresh epl_fixtures.js
```

## Files

| File | Purpose |
|------|---------|
| `index.html` | The entire app — HTML, CSS and JS in one file |
| `manifest.json` | PWA manifest (Android install, standalone display) |
| `icon-*.png` | Home-screen icons |
| `epl_squads.js` / `epl_fixtures.js` | Source data, spliced into `index.html` |
| `scripts/update_squads.py` | Re-fetch squads after a transfer window |
| `scripts/generate_fixtures.py` | Regenerate fixtures if the club list changes |
| `bump.sh` | Stamps a new version so installed copies notice an update |

## Architecture notes

All persistence goes through a `Store` module behind an async storage
adapter — currently `localStorage`, swappable for a cloud database in one
call without touching anything else:

```js
Store.use({
  async load()      { return (await db.get(uid)).data; },
  async save(state) { await db.set(uid, state); }
});
```

Installed home-screen copies check `version.json` on each launch and offer
a one-tap update when a newer version has been deployed — the same
mechanism as the companion app, needed because iOS caches home-screen web
apps aggressively.
