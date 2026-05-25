# mvgcli CLI Reference

Command-line tool for Munich public transport (MVG).

## Global option

| Option | Values | Description |
|--------|--------|-------------|
| `--output` / `-o` | `text`, `json`, `llm` | Output format (default: `text`) |

## Commands

---

### `find-stations`

Search for stations by name or GPS coordinates.

**Options:**

| Option | Type | Description |
|--------|------|-------------|
| `--name` | TEXT | Station name or global ID (e.g. `de:09162:2`) |
| `--lat` | FLOAT | Latitude — requires `--lng` |
| `--lng` | FLOAT | Longitude — requires `--lat` |
| `--all` | Flag | Return all nearby stations (default: closest only) |
| `--no-lines` | Flag | Skip line lookup (faster) |

**`--output json`:**
```json
[
  {
    "id": "de:09162:2",
    "name": "Marienplatz",
    "place": "München",
    "latitude": 48.13726,
    "longitude": 11.57549,
    "lines": [{"label": "U3", "transport_type": "UBAHN"}]
  }
]
```

**`--output llm`:**
````
```toon
stations:
  - id: de:09162:2
    name: Marienplatz, München
    coords: [48.13726, 11.57549]
    lines: UBAHN:U3, UBAHN:U6
```
````

---

### `departures`

Real-time departure board for a station.

**Options:**

| Option | Type | Description |
|--------|------|-------------|
| `--station` | TEXT | Station name or global ID **(required)** |
| `--limit` | INT | Number of departures (default: 20) |
| `--offset` | INT | Walking offset in minutes (default: 0) |
| `--transport` | TEXT | Transport type filter, comma-separated |
| `--lines` | TEXT | Line filter, comma-separated (e.g. `U3,U6`) |

**`--output json`:**
```json
[
  {
    "line": "U3",
    "type": "U-Bahn",
    "destination": "Moosach",
    "time": 1716545400,
    "delay": 0,
    "realtime": true,
    "cancelled": false,
    "platform": "1"
  }
]
```

**`--output llm`:**
````
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
````

---

### `route`

Journey planner from A to B including transfers (via MVG route API).

**Options:**

| Option | Type | Description |
|--------|------|-------------|
| `--from` | TEXT | Origin station **(required)** |
| `--to` | TEXT | Destination station **(required)** |
| `--limit` | INT | Max journeys (default: 6) |
| `--transport` | TEXT | Transport type filter |
| `--lines` | TEXT | Line filter (journeys containing these lines) |

**`--output json`:**
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
        "transfer_at": "Innsbrucker Ring",
        "arrival": "14:19",
        "direction": "Neuperlach Süd",
        "platform": "2"
      },
      {
        "line": "U2",
        "type": "UBAHN",
        "origin": "Innsbrucker Ring",
        "departure": "14:24",
        "departure_rt": null,
        "transfer_at": "Sendlinger Tor",
        "arrival": "14:31",
        "direction": "Messestadt Ost",
        "platform": null
      }
    ]
  }
]
```

**`--output llm`:**
````
```toon
origin: Hauptbahnhof
destination: Sendlinger Tor
time: 14:05
journeys:
  - duration: 22
    transfers: 1
    legs:
      - line: U5
        type: UBAHN
        origin: Hauptbahnhof
        departure: "14:09"
        transfer_at: Innsbrucker Ring
        arrival: "14:19"
        direction: Neuperlach Süd
        platform: "2"
      - line: U2
        type: UBAHN
        origin: Innsbrucker Ring
        departure: "14:24"
        transfer_at: Sendlinger Tor
        arrival: "14:31"
        direction: Messestadt Ost
```
````

---

### `disruptions`

Live service disruptions and alerts (loaded via Playwright).

**Options:**

| Option | Type | Description |
|--------|------|-------------|
| `--transport` | TEXT | Transport type filter |
| `--lines` | TEXT | Line filter |
| `--debug` | Flag | Print all intercepted API URLs |

**`--output json`:**
```json
[
  {
    "type": "DISRUPTION",
    "title": "U3 service interruption",
    "description": "Delays due to a technical fault.",
    "lines": ["U3"],
    "transport_types": ["UBAHN"],
    "valid_from": "24.05.2026 10:00",
    "valid_to": "24.05.2026 14:00",
    "link": ""
  }
]
```

**`--output llm`:**
````
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
````

## Transport types

| Value | Description |
|-------|-------------|
| `UBAHN` | Underground (U-Bahn) |
| `SBAHN` | Suburban rail (S-Bahn) |
| `TRAM` | Tram / Streetcar |
| `BUS` | Bus |
| `BAHN` | Regional rail |
| `REGIONAL_BUS` | Regional bus |
| `SCHIFF` | Ferry |
| `SEV` | Rail replacement service |

## Troubleshooting

- **`disruptions` hangs or fails:** Chromium is installed automatically on first run. If problems persist: `python -m playwright install chromium`.
- **Station not found:** Use the global ID, e.g. `--station de:09162:2`.
- **`route` finds no connection:** Try the station's global ID (e.g. `--from de:09162:2`). Walking-only routes are filtered out automatically.
- **Unknown transport type in output:** Pass `--output json` to see the raw `type` field returned by the MVG API.

## TOON output format

`--output llm` produces **TOON** (Text Object Output Notation) — a compact, YAML-like format optimised for AI agents. Compared to JSON, TOON significantly reduces token consumption while remaining easy for language models to parse.

Each command wraps its output in a fenced code block:

````
```toon
...
````

Errors are emitted as TOON on stderr:

````
```toon
error:
  code: NOT_FOUND
  message: Station "Nirgendwo" not found.
```
````

**Specification:** <https://toonformat.dev>
