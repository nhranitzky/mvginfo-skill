---
name: mvginfo
description: Real-time Munich public transport — departures, connections, disruptions and station search via MVG CLI
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

Provides real-time Munich public transport data via the MVG CLI — station search, departure boards, connections, and live disruption alerts. Use this skill whenever the user asks about U-Bahn, S-Bahn, tram, or bus in the Munich MVG network.

The CLI calls the MVG API directly (no API key required) and returns JSON output optimised for LLM consumption.

## When to Use

**Use when the user:**
- Asks for departure times, next trains, or buses at a Munich station
- Names a Munich station or MVG line (U3, S8, Tram 19, …)
- Asks about current disruptions or service alerts on the Munich network
- Asks for a connection from station A to station B in Munich

**Do not use for:**
- Cities outside the MVG network
- Multi-day advance timetable planning
- Real-time vehicle positions

## CLI Invocation

All commands follow the pattern:

```bash
${HERMES_SKILL_DIR}/scripts/mvgcli <command> --json [options]
```

`uv` must be in `PATH`.

## stations

Search for stations by name or GPS coordinates.

```bash
# By name
${HERMES_SKILL_DIR}/scripts/mvgcli stations --json "Marienplatz"

# By GPS coordinates
${HERMES_SKILL_DIR}/scripts/mvgcli stations --json --lat 48.137 --lng 11.575

# With line details
${HERMES_SKILL_DIR}/scripts/mvgcli stations --json --with-lines "Marienplatz"
```

**Output:**
```json
[
  {
    "id": "de:09162:2",
    "name": "Marienplatz",
    "place": "München",
    "latitude": 48.13726,
    "longitude": 11.57549,
    "lines": []
  }
]
```

Use the `id` field (e.g. `de:09162:2`) as station argument when a name is ambiguous.

## departures

Real-time departure board for a station.

```bash
# Basic
${HERMES_SKILL_DIR}/scripts/mvgcli departures --json "Marienplatz"

# Limit results and add walking offset
${HERMES_SKILL_DIR}/scripts/mvgcli departures --json --limit 10 --offset 3 "Marienplatz"

# Filter by transport type and/or line
${HERMES_SKILL_DIR}/scripts/mvgcli departures --json --transport UBAHN --lines U3,U6 "Marienplatz"
```

**Output:**
```json
[
  {
    "line": "U3",
    "type": "UBAHN",
    "destination": "Moosach",
    "planned_time": 1748000000000,
    "realtime_time": 1748000180000,
    "delay_minutes": 3,
    "realtime": true,
    "cancelled": false,
    "platform": 1
  }
]
```

`--offset` shifts the departure window by N minutes (useful for walking time to the station).

## connections

Journey planner from one station to another, including transfers.

```bash
${HERMES_SKILL_DIR}/scripts/mvgcli connections --json --from "Marienplatz" --to "Hauptbahnhof"

# With filters
${HERMES_SKILL_DIR}/scripts/mvgcli connections --json --from "Marienplatz" --to "Hauptbahnhof" --transport UBAHN --limit 4
```

**Output:**
```json
[
  {
    "duration": 22,
    "transfers": 1,
    "legs": [
      {
        "line": "U5",
        "type": "UBAHN",
        "origin": "Hauptbahnhof",
        "departure": "14:09",
        "departure_rt": null,
        "destination": "Innsbrucker Ring",
        "arrival": "14:19",
        "direction": "Neuperlach Süd",
        "platform": 2
      }
    ]
  }
]
```

`departure_rt` is set when the realtime departure differs from the planned one.

## disruptions

Live service disruptions and alerts.

```bash
# All disruptions
${HERMES_SKILL_DIR}/scripts/mvgcli disruptions --json

# Filtered by line
${HERMES_SKILL_DIR}/scripts/mvgcli disruptions --json --lines U3,U6

# Filtered by transport type
${HERMES_SKILL_DIR}/scripts/mvgcli disruptions --json --transport UBAHN
```

**Output:**
```json
[
  {
    "type": "INCIDENT",
    "title": "U3 service interruption",
    "description": "Delays due to a technical fault.",
    "lines": ["U3"],
    "transport_types": ["UBAHN"],
    "valid_from": "24.05.2026 10:00",
    "valid_to": "24.05.2026 14:00"
  }
]
```

An empty array `[]` means no active alerts.

## Error Output

On failure the CLI exits with a non-zero status and writes a JSON object to **stderr**:

```json
{
  "error": "NOT_FOUND",
  "message": "Station \"Foo\" not found.",
  "suggestion": "mvginfo stations <name> to search"
}
```

| Field | Description |
|-------|-------------|
| `error` | Machine-readable error code (see below) |
| `message` | Human-readable description |
| `suggestion` | Optional hint for the next step (may be absent) |

**Error codes:**

| Code | Meaning |
|------|---------|
| `NOT_FOUND` | Station or resource not found |
| `MISSING_ARG` | Required argument missing |
| `ARG_CONFLICT` | Mutually exclusive arguments used together |
| `INVALID_ARG` | Argument has an invalid value (e.g. unknown transport type) |
| `API_ERROR` | MVG API returned an error |

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

1. **Station not found by name** — use the global ID instead: `mvgcli departures --json "de:09162:2"`. Run `stations` first to get the ID.
2. **`connections` returns no results** — use the station's global ID (e.g. `--from de:09162:2`). Walking-only routes are filtered out automatically.
3. **`uv` not found** — install via `brew install uv` (macOS) or `pip install uv` (Linux), then reopen the terminal.

## Verification Checklist

- [ ] `stations --json "Marienplatz"` returns at least one station with an `id` field
- [ ] `departures --json "Marienplatz"` returns entries with `delay_minutes` values
- [ ] `connections --json --from "Marienplatz" --to "Hauptbahnhof"` returns at least one connection with `legs`
- [ ] `disruptions --json` completes without error (empty array is valid)
