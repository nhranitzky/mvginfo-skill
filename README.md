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
 
### Custom directory (skills.external_dirs)

```bash
git clone https://github.com/nhranitzky/mvginfo-skill.git
cp -R  mvginfo-skill/mvginfo /path/to/skills
 
```

## Requirements

 
- Chromium for the `disruptions` command — installed automatically on first run via `python -m playwright install chromium`

## Configuration

No API key required. The MVG API is publicly accessible.

## CLI Usage Examples

See [mvginfo/scripts/README.md](mvginfo/scripts/README.md) for the full CLI reference.

## License

MIT

## Creation

Created with the help of AI coding tool, but human reviewed and tested
