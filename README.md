# mvginfo for Hermes

Real-time Munich public transport data — departure boards, connections, disruption alerts and station search via the MVG CLI.

## Features

- **stations** — search stations by name or GPS coordinates
- **departures** — live departure board with delay and platform info
- **connections** — next connections from A to B, including transfers
- **disruptions** — live service alerts from the MVG network

## Installation

### Managed skill directory (via Hermes CLI)

```bash
hermes skills install nhranitzky/mvginfo-skill/mvginfo
```

### Custom directory (skills.external_dirs)

```bash
git clone https://github.com/nhranitzky/mvginfo-skill.git
cp -R mvginfo-skill/mvginfo /path/to/skills
```
or

```bash
npx degit nhranitzky/mvginfo-skill/mvginfo /path/to/skills/mvginfo
```


## Requirements

- [`uv`](https://github.com/astral-sh/uv) must be in `PATH` — install via `brew install uv` (macOS) or `pip install uv`

## Configuration

No API key required. The MVG API is publicly accessible.

## Developer Guide

The CLI source is a separate project: https://github.com/nhranitzky/mvginfo-cli

### Makefile targets

| Target | Description |
|--------|-------------|
| `make dl-cli` | Download the latest CLI scripts from `nhranitzky/mvginfo-cli` into `mvginfo/scripts/mvginfo/` |
| `make commit MSG="…"` | Stage all changes and commit with the given message |
| `make push` | Push the current branch to the remote |

**Typical workflow after a CLI update:**

```bash
make dl-cli
make commit MSG="chore: update mvginfo CLI"
make push
```

## License

MIT

## Creation

Created with the help of AI coding tool, but human reviewed and tested
