from __future__ import annotations

from typing import Annotated, Optional

import typer

from .core import (
    ClientError,
    find_nearby,
    find_station,
    get_connections,
    get_departures,
    get_disruptions,
    get_station_lines,
    parse_line_filter,
    parse_transport_types,
)
from .output import (
    OutputFormat,
    render_connections,
    render_departures,
    render_disruptions,
    render_error,
    render_stations,
)

app = typer.Typer(no_args_is_help=True)


def _err(message: str, code: str, json_out: bool, exit_code: int = 1, suggestion: str = "") -> None:
    render_error(message, code, OutputFormat.json if json_out else OutputFormat.text, suggestion)
    raise typer.Exit(exit_code)


# ── stations ──────────────────────────────────────────────────────────────────


@app.command("stations")
def stations_cmd(
    query: Annotated[Optional[str], typer.Argument(help="Station name or global ID")] = None,
    lat: Annotated[Optional[float], typer.Option("--lat", metavar="LAT", help="Latitude (GPS search)")] = None,
    lng: Annotated[Optional[float], typer.Option("--lng", metavar="LNG", help="Longitude (GPS search)")] = None,
    with_lines: Annotated[bool, typer.Option("--lines", help="Fetch line details (extra API call)")] = False,
    limit: Annotated[int, typer.Option("--limit", help="Max number of stations for GPS search")] = 10,
    json_out: Annotated[bool, typer.Option("--json", help="Output as JSON.")] = False,
) -> None:
    """Search MVG stations by name, global ID, or GPS coordinates."""
    if query is None and lat is None:
        _err(
            "Either QUERY or --lat/--lng is required.",
            "MISSING_ARG",
            json_out,
            exit_code=2,
            suggestion="mvginfo stations Marienplatz  or  mvginfo stations --lat 48.137 --lng 11.575",
        )
    if query is not None and lat is not None:
        _err("QUERY and --lat are mutually exclusive.", "ARG_CONFLICT", json_out, exit_code=2)
    if lat is not None and lng is None:
        _err("--lat requires --lng.", "MISSING_ARG", json_out, exit_code=2)

    try:
        if query is not None:
            station = find_station(query)
            if station is None:
                _err(
                    f'Station "{query}" not found.',
                    "NOT_FOUND",
                    json_out,
                    suggestion="mvginfo stations <partial name> to search",
                )
                return
            stations = [station]
        else:
            stations = find_nearby(lat, lng)  # type: ignore[arg-type]
            if not stations:
                _err("No stations found near the given coordinates.", "NOT_FOUND", json_out)
                return
            stations = stations[:limit]

        if with_lines:
            for s in stations:
                s.lines = get_station_lines(s.id)

    except ClientError as exc:
        _err(str(exc), "API_ERROR", json_out)
        return

    render_stations(stations, OutputFormat.json if json_out else OutputFormat.text)


# ── departures ────────────────────────────────────────────────────────────────


@app.command("departures")
def departures_cmd(
    station: Annotated[str, typer.Argument(help="Station name or global ID")],
    limit: Annotated[int, typer.Option("--limit", help="Number of departures")] = 20,
    offset: Annotated[int, typer.Option("--offset", help="Walking offset in minutes")] = 0,
    transport: Annotated[
        Optional[str],
        typer.Option("--transport", metavar="TYPE,TYPE", help="Transport type filter (UBAHN,SBAHN,TRAM,BUS,...)"),
    ] = None,
    lines: Annotated[
        Optional[str], typer.Option("--lines", metavar="LINE,LINE", help="Line filter (U3,S1,...)")
    ] = None,
    json_out: Annotated[bool, typer.Option("--json", help="Output as JSON.")] = False,
) -> None:
    """Real-time departure board for a station."""
    try:
        tt = parse_transport_types(transport) if transport else None
    except ValueError as exc:
        _err(str(exc), "INVALID_ARG", json_out, exit_code=2)
        return

    try:
        resolved = find_station(station)
        if resolved is None:
            _err(
                f'Station "{station}" not found.',
                "NOT_FOUND",
                json_out,
                suggestion="mvginfo stations <name> to search",
            )
            return
        deps = get_departures(resolved.id, limit=limit, offset=offset, transport_types=tt)
    except ClientError as exc:
        _err(str(exc), "API_ERROR", json_out)
        return

    if lines:
        wanted = parse_line_filter(lines)
        deps = [d for d in deps if d.line.upper() in wanted]

    render_departures(resolved, deps, offset, OutputFormat.json if json_out else OutputFormat.text)


# ── connections ───────────────────────────────────────────────────────────────


@app.command("connections")
def connections_cmd(
    origin: Annotated[str, typer.Option("--from", metavar="STATION", help="Origin station")],
    destination: Annotated[str, typer.Option("--to", metavar="STATION", help="Destination station")],
    limit: Annotated[int, typer.Option("--limit", help="Max number of connections")] = 6,
    transport: Annotated[
        Optional[str], typer.Option("--transport", metavar="TYPE,TYPE", help="Transport type filter")
    ] = None,
    json_out: Annotated[bool, typer.Option("--json", help="Output as JSON.")] = False,
) -> None:
    """Find connections with transfers between two stations."""
    try:
        tt = parse_transport_types(transport) if transport else None
    except ValueError as exc:
        _err(str(exc), "INVALID_ARG", json_out, exit_code=2)
        return

    try:
        origin_station = find_station(origin)
        if origin_station is None:
            _err(f'Origin station "{origin}" not found.', "NOT_FOUND", json_out)
            return
        dest_station = find_station(destination)
        if dest_station is None:
            _err(f'Destination station "{destination}" not found.', "NOT_FOUND", json_out)
            return
        conns = get_connections(origin_station.id, dest_station.id, limit=limit, transport_types=tt)
    except ClientError as exc:
        _err(str(exc), "API_ERROR", json_out)
        return

    render_connections(origin, destination, conns, OutputFormat.json if json_out else OutputFormat.text)


# ── disruptions ───────────────────────────────────────────────────────────────


@app.command("disruptions")
def disruptions_cmd(
    transport: Annotated[
        Optional[str], typer.Option("--transport", metavar="TYPE,TYPE", help="Transport type filter")
    ] = None,
    lines: Annotated[Optional[str], typer.Option("--lines", metavar="LINE,LINE", help="Line filter")] = None,
    json_out: Annotated[bool, typer.Option("--json", help="Output as JSON.")] = False,
) -> None:
    """Show current MVG service alerts and disruptions."""
    try:
        tt = parse_transport_types(transport) if transport else None
    except ValueError as exc:
        _err(str(exc), "INVALID_ARG", json_out, exit_code=2)
        return

    line_filter = parse_line_filter(lines) if lines else None

    try:
        disruptions = get_disruptions(transport_types=tt, line_filter=line_filter)
    except ClientError as exc:
        _err(str(exc), "API_ERROR", json_out)
        return

    disruptions.sort(key=lambda d: 0 if d.type == "INCIDENT" else 1)
    render_disruptions(disruptions, OutputFormat.json if json_out else OutputFormat.text)


def main() -> None:
    app(prog_name="mvginfo")
