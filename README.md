# mvginfo for Hermes

Real-time Munich public transport data — departure boards, direct connections, disruption alerts and station search via the MVG CLI.

## Features

- **find-stations** — search stations by name or GPS coordinates
- **departures** — live departure board with delay and platform info
- **route** — next direct connections from A to B
- **disruptions** — live service alerts loaded via Playwright

## Installation

### Managed skill directory (via Hermes CLI)

```bash
hermes skills install nhranitzky/mvginfo-skill/mvginfo
```

> **Note:** The installation will be blocked by default:
> ```
> Installation blocked: Blocked (community source + caution verdict, 2 findings).
> Use --force to override.
> ```
> Review the source code, then install with:

```bash
hermes skills install nhranitzky/mvginfo-skill/mvginfo --force
```

### Custom directory (skills.external_dirs)

```bash
git clone https://github.com/nhranitzky/mvginfo-skill.git
cd mvginfo-skill
./install.sh /path/to/target   # installs into /path/to/target/mvginfo/
```

## Requirements

- `uv` in `PATH` — install via `brew install uv` (macOS) or `pip install uv` (Linux)
- Python ≥ 3.11 (managed automatically by `uv`)
- Chromium for the `disruptions` command — installed automatically on first run via `python -m playwright install chromium`

## Configuration

No API key required. The MVG API is publicly accessible.

## Usage Examples

```bash
# Find a station
scripts/bin/mvgcli --output llm find-stations --name "Marienplatz"

# Departure board (next 10 U-Bahn departures)
scripts/bin/mvgcli --output llm departures --station "Marienplatz" --limit 10 --transport UBAHN

# Direct connection
scripts/bin/mvgcli --output llm route --from "Marienplatz" --to "Hauptbahnhof"

# Live disruptions for U3 and U6
scripts/bin/mvgcli --output llm disruptions --lines U3,U6
```

## License

MIT

## Creation

Created with the help of AI coding tool, but human reviewed and tested
