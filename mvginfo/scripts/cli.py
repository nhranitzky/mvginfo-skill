from __future__ import annotations

import sys
from typing import Annotated, Optional

import typer

from .core import (
    ClientError,
    ensure_chromium,
    fetch_disruptions,
    find_journeys,
    find_nearby,
    find_station,
    get_departures,
    get_lines,
    parse_line_filter,
    parse_transport_types,
)
from .output import (
    OutputFormat,
    SEVERITY_ORDER,
    render_departures,
    render_disruptions,
    render_error,
    render_journeys,
    render_stations,
)

app = typer.Typer(no_args_is_help=True)

_OPT = Annotated[OutputFormat, typer.Option("--output", "-o", help="Ausgabeformat: text, json, llm")]


def _err(message: str, code: str, fmt: OutputFormat) -> None:
    render_error(message, code, fmt)
    raise typer.Exit(1)


# ── find-stations ──────────────────────────────────────────────────────────────

@app.command("find-stations")
def find_stations_cmd(
    name: Annotated[Optional[str], typer.Option("--name", metavar="QUERY", help="Stationsname oder globale ID")] = None,
    lat: Annotated[Optional[float], typer.Option("--lat", metavar="LAT", help="Breitengrad")] = None,
    lng: Annotated[Optional[float], typer.Option("--lng", metavar="LNG", help="Längengrad")] = None,
    all_nearby: Annotated[bool, typer.Option("--all", help="Alle nahegelegenen Stationen")] = False,
    no_lines: Annotated[bool, typer.Option("--no-lines", help="Linienabfrage überspringen")] = False,
    output: _OPT = OutputFormat.text,
) -> None:
    """MVG Stationssuche – nach Name oder GPS-Koordinaten."""
    if name is None and lat is None:
        _err("Entweder --name oder --lat/--lng muss angegeben werden.", "MISSING_ARG", output)
    if name is not None and lat is not None:
        _err("--name und --lat schließen sich gegenseitig aus.", "ARG_CONFLICT", output)
    if lat is not None and lng is None:
        _err("--lat erfordert --lng.", "MISSING_ARG", output)

    try:
        if name:
            station = find_station(name)
            if station is None:
                _err(f'Station "{name}" nicht gefunden.', "NOT_FOUND", output)
                return
            if not no_lines:
                station.lines = get_lines(station.id)
            stations = [station]
        else:
            stations = find_nearby(lat, lng, all_stations=all_nearby)  # type: ignore[arg-type]
            if not stations:
                _err("Keine Station in der Nähe der angegebenen Koordinaten.", "NOT_FOUND", output)
                return
            if not no_lines:
                for s in stations:
                    s.lines = get_lines(s.id)
    except ClientError as exc:
        _err(str(exc), "error", output)
        return

    render_stations(stations, output)


# ── departures ─────────────────────────────────────────────────────────────────

@app.command("departures")
def departures_cmd(
    station: Annotated[str, typer.Option("--station", metavar="QUERY", help="Stationsname oder globale ID")],
    limit: Annotated[int, typer.Option("--limit", help="Anzahl der Abfahrten")] = 20,
    offset: Annotated[int, typer.Option("--offset", help="Walking-Offset in Minuten")] = 0,
    transport: Annotated[Optional[str], typer.Option("--transport", metavar="TYPE[,TYPE]", help="Verkehrsmittel-Filter")] = None,
    lines: Annotated[Optional[str], typer.Option("--lines", metavar="LINE[,LINE]", help="Linien-Filter")] = None,
    output: _OPT = OutputFormat.text,
) -> None:
    """MVG Echtzeit-Abfahrtstafel – Live-Board für jede Station."""
    try:
        resolved = find_station(station)
        if resolved is None:
            _err(f'Station "{station}" nicht gefunden.', "NOT_FOUND", output)
            return

        tt = parse_transport_types(transport) if transport else None
        deps = get_departures(resolved.id, limit=limit, offset=offset, transport_types=tt)

        if lines:
            wanted = parse_line_filter(lines)
            deps = [d for d in deps if d.line.upper() in wanted]

    except ClientError as exc:
        _err(str(exc), "error", output)
        return

    render_departures(resolved, deps, offset, output)


# ── route ──────────────────────────────────────────────────────────────────────

@app.command("route")
def route_cmd(
    origin: Annotated[str, typer.Option("--from", metavar="STATION", help="Startstation")],
    destination: Annotated[str, typer.Option("--to", metavar="STATION", help="Zielstation")],
    limit: Annotated[int, typer.Option("--limit", help="Maximale Anzahl Verbindungen")] = 6,
    transport: Annotated[Optional[str], typer.Option("--transport", metavar="TYPE[,TYPE]", help="Verkehrsmittel-Filter")] = None,
    lines: Annotated[Optional[str], typer.Option("--lines", metavar="LINE[,LINE]", help="Linien-Filter")] = None,
    output: _OPT = OutputFormat.text,
) -> None:
    """MVG Routenplaner – Verbindungssuche mit Umstiegen via MVG-Routenplaner-API."""
    try:
        if output == OutputFormat.text:
            sys.stderr.write("  🔍 Stationen werden gesucht …\r")
            sys.stderr.flush()
        origin_station = find_station(origin)
        if origin_station is None:
            _err(f'Startstation "{origin}" nicht gefunden.', "NOT_FOUND", output)
            return

        dest = find_station(destination)
        if dest is None:
            _err(f'Zielstation "{destination}" nicht gefunden.', "NOT_FOUND", output)
            return

        tt = parse_transport_types(transport) if transport else None

        if output == OutputFormat.text:
            sys.stderr.write("  📡 Verbindungen werden geladen …\r")
            sys.stderr.flush()
        journeys = find_journeys(origin_station.id, dest.id, limit=limit, transport_types=tt)

        if lines:
            wanted = parse_line_filter(lines)
            journeys = [j for j in journeys if any(leg.line.upper() in wanted for leg in j.legs)]

    except ClientError as exc:
        _err(str(exc), "error", output)
        return

    render_journeys(origin, destination, journeys, output)


# ── disruptions ────────────────────────────────────────────────────────────────

@app.command("disruptions")
def disruptions_cmd(
    transport: Annotated[Optional[str], typer.Option("--transport", metavar="TYPE[,TYPE]", help="Verkehrsmittel-Filter")] = None,
    lines: Annotated[Optional[str], typer.Option("--lines", metavar="LINE[,LINE]", help="Linien-Filter")] = None,
    debug: Annotated[bool, typer.Option("--debug", help="API-URLs ausgeben")] = False,
    output: _OPT = OutputFormat.text,
) -> None:
    """MVG Störungen & Meldungen – Live-Interception der Betriebsmeldungen."""
    ensure_chromium()

    try:
        if output == OutputFormat.text:
            sys.stderr.write("  📡 betriebsmeldungen.html wird geladen …\r")
            sys.stderr.flush()
        messages = fetch_disruptions(debug=debug)
    except Exception as exc:
        _err(str(exc), "error", output)
        return

    if transport:
        wanted_tt = {t.upper() for t in parse_transport_types(transport)}
        messages = [m for m in messages if not m.transport_types or set(m.transport_types) & wanted_tt]

    if lines:
        wanted_l = parse_line_filter(lines)
        messages = [m for m in messages if not m.lines or {ln.upper() for ln in m.lines} & wanted_l]

    messages.sort(key=lambda m: SEVERITY_ORDER.get(m.type, 9))

    render_disruptions(messages, output)


def main() -> None:
    app(prog_name="mvgcli")
