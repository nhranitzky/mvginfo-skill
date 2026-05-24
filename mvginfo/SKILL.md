---
name: mvginfo
description: Real-time Munich public transport — departures, routes, disruptions and station search via MVG CLI
version: 1.0.0
author: nhranitzky
license: MIT
platforms: [macos, linux]
metadata:
  hermes:
    tags: [Transport, Munich, PublicTransit, Realtime]
---

# MVG Info

## Overview

Provides real-time Munich public transport data via the MVG CLI — station search, departure boards, direct connections, and live disruption alerts. Use this skill whenever the user asks about U-Bahn, S-Bahn, tram, or bus in the Munich MVG network.

The CLI calls the MVG API directly (no API key required) and returns compact TOON-formatted output optimised for LLM consumption.

## When to Use

**Use when the user:**
- Asks for departure times, next trains, or buses at a Munich station
- Names a Munich station or MVG line (U3, S8, Tram 19, …)
- Asks about current disruptions or service alerts on the Munich network
- Asks for a direct connection from station A to station B in Munich

**Do not use for:**
- Connections requiring transfers → direct the user to <https://www.mvg.de/verbindungen.html>
- Cities outside the MVG network
- Multi-day advance timetable planning
- Real-time vehicle positions

## CLI Invocation

All commands follow the pattern:

```bash
${HERMES_SKILL_DIR}/scripts/bin/mvgcli --output llm <command> [options]
```

`uv` must be in `PATH`. On first `disruptions` call, Chromium is installed automatically.

## find-stations

Search for stations by name or GPS coordinates.

```bash
# By name
${HERMES_SKILL_DIR}/scripts/bin/mvgcli --output llm find-stations --name "Marienplatz"

# By coordinates
${HERMES_SKILL_DIR}/scripts/bin/mvgcli --output llm find-stations --lat 48.137 --lng 11.575

# All nearby stations (not just the closest)
${HERMES_SKILL_DIR}/scripts/bin/mvgcli --output llm find-stations --lat 48.137 --lng 11.575 --all
```

**Output:**
```toon
stations:
  - id: de:09162:2
    name: Marienplatz, München
    coords: [48.13726, 11.57549]
    lines: UBAHN:U3, UBAHN:U6
```

Use the `id` field (e.g. `de:09162:2`) as `--station` value when a name is ambiguous.

## departures

Real-time departure board for a station.

```bash
# Basic
${HERMES_SKILL_DIR}/scripts/bin/mvgcli --output llm departures --station "Marienplatz"

# Limit results and add walking offset
${HERMES_SKILL_DIR}/scripts/bin/mvgcli --output llm departures --station "Marienplatz" --limit 10 --offset 3

# Filter by transport type and/or line
${HERMES_SKILL_DIR}/scripts/bin/mvgcli --output llm departures --station "Marienplatz" --transport UBAHN --lines U3,U6
```

**Output:**
```toon
station: Marienplatz, München
time: 09:45
departures:
  - line: U3
    type: U-Bahn
    destination: Moosach
    in_minutes: 3
    delay_seconds: 0
    realtime: true
    cancelled: false
    platform: 1
```

`--offset` shifts the departure window by N minutes (useful for walking time to the station).

## route

Direct connections from one station to another.

```bash
${HERMES_SKILL_DIR}/scripts/bin/mvgcli --output llm route --from "Marienplatz" --to "Hauptbahnhof"

# With filters
${HERMES_SKILL_DIR}/scripts/bin/mvgcli --output llm route --from "Marienplatz" --to "Hauptbahnhof" --transport UBAHN --limit 4
```

**Output:**
```toon
origin: Marienplatz
destination: Hauptbahnhof
time: 09:45
connections:
  - line: U3
    type: U-Bahn
    destination: Hauptbahnhof
    board_at: Marienplatz
    in_minutes: 2
    departs_at: "09:47"
    delay_seconds: 0
    realtime: true
```

**Important:** Only direct services are supported. If no connection is found, the user needs a transfer — refer them to <https://www.mvg.de/verbindungen.html>.

## disruptions

Live service disruptions and alerts. Loads data via Playwright (headless Chromium).

```bash
# All disruptions
${HERMES_SKILL_DIR}/scripts/bin/mvgcli --output llm disruptions

# Filtered by line
${HERMES_SKILL_DIR}/scripts/bin/mvgcli --output llm disruptions --lines U3,U6

# Filtered by transport type
${HERMES_SKILL_DIR}/scripts/bin/mvgcli --output llm disruptions --transport UBAHN
```

**Output:**
```toon
source: https://www.mvg.de/verbindungen/betriebsmeldungen.html
time: 24.05.2026 09:45
disruptions:
  - type: DISRUPTION
    title: U3 service interruption
    lines: [U3]
    transport_types: [UBAHN]
    valid_from: 24.05.2026 10:00
    valid_to: 24.05.2026 14:00
    description: |
      Delays due to a technical fault.
```

An empty `disruptions:` list means no active alerts.

## Transport Types

| Value | Description |
|-------|-------------|
| `UBAHN` | U-Bahn (underground) |
| `SBAHN` | S-Bahn (suburban rail) |
| `TRAM` | Tram / Streetcar |
| `BUS` | Bus |
| `BAHN` | Regional rail |
| `REGIONAL_BUS` | Regional bus |
| `SCHIFF` | Ferry |
| `SEV` | Rail replacement service |

## Common Pitfalls

1. **Station not found by name** — use the global ID instead: `--station de:09162:2`. Run `find-stations` first to get the ID.
2. **`disruptions` hangs or errors** — Chromium must be installed: run `python -m playwright install chromium` inside the scripts directory.
3. **`route` returns no results** — only direct services are supported. For connections with transfers, direct the user to <https://www.mvg.de/verbindungen.html>.
4. **`uv` not found** — install via `brew install uv` (macOS) or `pip install uv` (Linux), then reopen the terminal.

## Verification Checklist

- [ ] `find-stations --name "Marienplatz"` returns at least one station with an `id` field
- [ ] `departures --station "Marienplatz"` returns entries with `in_minutes` values
- [ ] `route --from "Marienplatz" --to "Hauptbahnhof"` returns at least one connection with `departs_at`
- [ ] `disruptions` completes without error (empty list is valid)
