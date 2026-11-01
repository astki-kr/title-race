#!/usr/bin/env python3
"""
Re-sync EPL squad data for Title Race — run this once after the winter
transfer window (or whenever a squad looks stale), not on every deploy.

What it does:
  1. Fetches the live Fantasy Premier League API for all current players:
     name, club, nationality (via /regions/), date of birth.
     This is the authoritative source — it's the same data the real
     Fantasy Premier League game runs on, so club assignment is kept
     current through every transfer window. A handful of entries can
     lag by a few days right after deadline day; that's normal FPL
     data behaviour, not a bug here.
  2. Fetches the Premier League's own stats API (pulselive), team by
     team, purely to harvest shirt numbers. That API's own "current
     club" field is NOT reliable in bulk (confirmed: it mislabels some
     players), so this script ignores it entirely and instead matches
     each pulselive record back to the trusted FPL roster by
     (normalised name, date of birth) — a near-unique key. Unmatched
     or ambiguous players are left with number = null, rendered as
     "–" in the app rather than guessed.
  3. Writes epl_squads.js in the exact format index.html expects.
     Open index.html afterwards, replace the SQUADS block with the
     new file's contents, then run ./bump.sh and deploy as usual.

Usage:
    python3 scripts/update_squads.py
    # then manually splice the new epl_squads.js into index.html
"""
import json
import re
import time
import unicodedata
import urllib.request

UA = "Mozilla/5.0 (Title Race squad sync)"
POS = {1: "GK", 2: "DF", 3: "MF", 4: "FW"}


def get_json(url, headers=None):
    req = urllib.request.Request(url, headers={"User-Agent": UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def norm(s):
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    s = re.sub(r"[^a-z0-9 ]", "", s.lower())
    return re.sub(r"\s+", " ", s).strip()


def dob_to_label(iso):
    try:
        y, m, d = iso.split("-")
        months = ["January", "February", "March", "April", "May", "June", "July",
                  "August", "September", "October", "November", "December"]
        return f"{int(d)} {months[int(m) - 1]} {y}"
    except Exception:
        return None


def main():
    print("Fetching FPL bootstrap-static (authoritative roster)...")
    boot = get_json("https://fantasy.premierleague.com/api/bootstrap-static/")
    regions = {r["id"]: r["name"] for r in get_json("https://fantasy.premierleague.com/api/regions/")}
    teams = {t["id"]: t["name"] for t in boot["teams"]}
    print(f"  {len(boot['elements'])} players across {len(teams)} clubs")

    fpl_players = []
    for e in boot["elements"]:
        full = f"{e['first_name']} {e['second_name']}".strip()
        fpl_players.append({
            "name": full, "web_name": e["web_name"], "team": teams[e["team"]],
            "country": regions.get(e["region"], "Unknown"), "dob": e["birth_date"],
            "pos": POS.get(e["element_type"], "?"),
            "norm_full": norm(full), "norm_web": norm(e["web_name"]),
        })

    print("Fetching pulselive team IDs for the current competition season...")
    pulse_teams = get_json(
        "https://footballapi.pulselive.com/football/teams?pageSize=100&compSeasons=841&altIds=true",
        {"Origin": "https://www.premierleague.com", "Referer": "https://www.premierleague.com/"},
    )["content"]
    # NOTE: if this script is re-run for a future season, the compSeasons id
    # above must be updated — check https://footballapi.pulselive.com/football/competitions
    # or inspect premierleague.com's network requests for the current id.

    print(f"Fetching shirt numbers for {len(pulse_teams)} clubs (name+DOB match only)...")
    pulse_by_name = {}
    for t in pulse_teams:
        data = get_json(
            f"https://footballapi.pulselive.com/football/players?pageSize=100&compSeasons=841&teams={int(t['id'])}&altIds=true",
            {"Origin": "https://www.premierleague.com", "Referer": "https://www.premierleague.com/"},
        )
        for p in data.get("content", []):
            nm = p.get("name", {}).get("display")
            sn = p.get("info", {}).get("shirtNum")
            dob = p.get("birth", {}).get("date", {}).get("label")
            if not nm or sn is None:
                continue
            pulse_by_name.setdefault(norm(nm), []).append((dob, int(sn)))
        time.sleep(0.3)   # be polite to an undocumented endpoint

    matched = 0
    for p in fpl_players:
        cands = pulse_by_name.get(p["norm_full"]) or pulse_by_name.get(p["norm_web"])
        p["number"] = None
        if not cands:
            continue
        if len(cands) == 1:
            p["number"] = cands[0][1]
            matched += 1
            continue
        target = dob_to_label(p["dob"])
        exact = [c for c in cands if c[0] == target]
        if len(exact) == 1:
            p["number"] = exact[0][1]
            matched += 1

    print(f"  shirt numbers matched: {matched}/{len(fpl_players)} ({100 * matched / len(fpl_players):.0f}%)")

    by_team = {}
    for p in fpl_players:
        by_team.setdefault(p["team"], []).append(p)
    for t in by_team:
        by_team[t].sort(key=lambda p: (p["number"] is None, p["number"] or 999, p["pos"], p["name"]))

    def js(v):
        return json.dumps(v, ensure_ascii=False, separators=(",", ":"))

    lines = []
    for t in sorted(by_team):
        arr = [[p["name"], p["number"], p["pos"], p["dob"], p["country"]] for p in by_team[t]]
        lines.append(f"  {js(t)}: [" + ",".join(js(a) for a in arr) + "]")

    out = ('/* Player: [name, shirtNumber|null, position, dateOfBirth, country]\n'
           '   shirtNumber is null where no reliable source had it — shown as "-" rather than guessed. */\n'
           'const SQUADS = {\n' + ",\n".join(lines) + "\n};\n")

    with open("epl_squads.js", "w", encoding="utf-8") as f:
        f.write(out)
    print(f"\nWrote epl_squads.js — {sum(len(v) for v in by_team.values())} players across {len(by_team)} clubs.")
    print("Next: splice this file's SQUADS block into index.html, run ./bump.sh, then deploy.")


if __name__ == "__main__":
    main()
