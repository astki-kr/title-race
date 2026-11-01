#!/usr/bin/env python3
"""
Regenerate epl_fixtures.js — only needed if the 20-club list changes
(promotion/relegation at the end of a season). Takes the club names
straight from SQUADS in epl_squads.js, so run update_squads.py first.

Produces a standard double round-robin: every team plays every other
team once at home, once away — 38 matchdays, 380 matches total,
exactly the real competition's structure. It is NOT the actual
published fixture calendar (dates/order); the simulator only needs
the structure, since matches are entered by hand as they're played.

Usage:
    python3 scripts/generate_fixtures.py
"""
import json
import re


def round_robin(teams):
    n = len(teams)
    arr = teams[:]
    fixed = arr[0]
    rest = arr[1:]
    rounds = []
    for r in range(n - 1):
        pairing = [(fixed, rest[-1])] if r % 2 == 0 else [(rest[-1], fixed)]
        half = len(rest) // 2
        for i in range(half):
            a, b = rest[i], rest[len(rest) - 2 - i]
            pairing.append((a, b) if (i + r) % 2 == 0 else (b, a))
        rounds.append(pairing)
        rest = [rest[-1]] + rest[:-1]
    return rounds


def main():
    squads_js = open("epl_squads.js", encoding="utf-8").read()
    teams = sorted(re.findall(r'^\s*"([^"]+)":\s*\[', squads_js, re.M))
    assert len(teams) == 20, f"expected 20 clubs in epl_squads.js, found {len(teams)}"

    first_half = round_robin(teams)
    second_half = [[(b, a) for (a, b) in rnd] for rnd in first_half]
    season = first_half + second_half

    # Validate before writing: every team 19 home + 19 away, every pairing
    # meets exactly twice, no team scheduled twice in one matchday.
    from collections import Counter
    home, away, pairs = Counter(), Counter(), Counter()
    for rnd in season:
        assert len(rnd) == len(teams) // 2
        seen = set()
        for h, a in rnd:
            assert h not in seen and a not in seen, "a team appears twice in one matchday"
            seen.add(h); seen.add(a)
            home[h] += 1; away[a] += 1
            pairs[frozenset((h, a))] += 1
    assert all(v == len(teams) - 1 for v in home.values())
    assert all(v == len(teams) - 1 for v in away.values())
    assert all(v == 2 for v in pairs.values())

    def js(v):
        return json.dumps(v, ensure_ascii=False, separators=(",", ":"))

    lines = []
    for md, rnd in enumerate(season, start=1):
        for h, a in rnd:
            lines.append(f"  {{md:{md},h:{js(h)},a:{js(a)}}}")

    out = ("/* 380-match double round-robin: every team home and away once. md = matchday 1-38. */\n"
           "const FIXTURES = [\n" + ",\n".join(lines) + "\n];\n")

    with open("epl_fixtures.js", "w", encoding="utf-8") as f:
        f.write(out)
    print(f"Wrote epl_fixtures.js — {sum(len(r) for r in season)} matches across {len(season)} matchdays.")
    print("Next: splice this file's FIXTURES block into index.html, run ./bump.sh, then deploy.")


if __name__ == "__main__":
    main()
