from __future__ import annotations

import enum
import json as _json
import time
from datetime import datetime

from rich.console import Console
from rich.table import Table

from .models import Connection, Departure, Disruption, Station

console = Console()
err_console = Console(stderr=True)

TRANSPORT_ICONS: dict[str, str] = {
    "UBAHN": "🟦",
    "SBAHN": "🟩",
    "TRAM": "🟥",
    "BUS": "🟨",
    "BAHN": "🚂",
    "REGIONAL_BUS": "🚌",
    "SCHIFF": "⛴",
    "SEV": "🔄",
}


class OutputFormat(str, enum.Enum):
    text = "text"
    json = "json"


def _minutes_until(ms: int) -> int:
    return max(0, int((ms / 1000 - time.time()) / 60))


def _fmt_hhmm(ms: int) -> str:
    try:
        return datetime.fromtimestamp(ms / 1000).strftime("%H:%M")
    except Exception:
        return "–"


def _dump_json(data: object) -> None:
    print(_json.dumps(data, ensure_ascii=False, indent=2))


def _print_header(line1: str, line2: str = "") -> None:
    console.print(f"\n{'═' * 60}")
    console.print(f"  {line1}")
    if line2:
        console.print(f"  {line2}")
    console.print(f"{'═' * 60}")


# ── stations ──────────────────────────────────────────────────────────────────


def render_stations(stations: list[Station], fmt: OutputFormat) -> None:
    if fmt == OutputFormat.json:
        _dump_json([s.model_dump() for s in stations])
        return

    table = Table(show_header=True, header_style="bold")
    table.add_column("Name")
    table.add_column("Place")
    table.add_column("ID")
    table.add_column("Coordinates")
    table.add_column("Lines")
    for s in stations:
        lines_str = "  ".join(f"{TRANSPORT_ICONS.get(ln.transport_type, '')} {ln.label}" for ln in s.lines)
        table.add_row(s.name, s.place, s.id, f"{s.latitude:.5f}, {s.longitude:.5f}", lines_str)
    console.print(table)


# ── departures ────────────────────────────────────────────────────────────────


def render_departures(station: Station, departures: list[Departure], offset: int, fmt: OutputFormat) -> None:
    if fmt == OutputFormat.json:
        _dump_json([d.model_dump() for d in departures])
        return

    now_str = datetime.now().strftime("%H:%M")
    offset_hint = f"(showing departures in ≥{offset} min, walking offset)" if offset else ""
    _print_header(f"🚏 {station.name}, {station.place}  –  {now_str}", offset_hint)

    if not departures:
        console.print("\n  No departures for the selected filters.\n")
        return

    for d in departures:
        icon = TRANSPORT_ICONS.get(d.type.upper(), "")
        mins = _minutes_until(d.realtime_time)
        time_str = "Now" if mins == 0 else f"{mins} min"
        delay_str = f" ⚠️ +{d.delay_minutes}m" if d.delay_minutes > 0 else ""
        rt_badge = "📡" if d.realtime else "  "
        status = "❌ Cancelled" if d.cancelled else time_str + delay_str
        plat_str = f"  Platform {d.platform}" if d.platform is not None else ""
        console.print(f"  {icon}{d.line:<5}  {d.destination:<32} {status:<20}{rt_badge}{plat_str}")

    console.print()


# ── connections ───────────────────────────────────────────────────────────────


def render_connections(origin: str, destination: str, connections: list[Connection], fmt: OutputFormat) -> None:
    if fmt == OutputFormat.json:
        _dump_json([c.model_dump() for c in connections])
        return

    now_str = datetime.now().strftime("%H:%M")
    _print_header(f"🗺  {origin}  →  {destination}  –  {now_str}")

    if not connections:
        console.print("\n  No connections found.\n")
        return

    for i, conn in enumerate(connections, 1):
        suffix = "s" if conn.transfers > 1 else ""
        transfers_str = "direct" if conn.transfers == 0 else f"{conn.transfers} transfer{suffix}"
        console.print(f"\n  ┌─ [{i}]  {conn.duration} min  |  {transfers_str}")
        for leg in conn.legs:
            icon = TRANSPORT_ICONS.get(leg.type.upper(), "")
            dep = f"{leg.departure_rt}*" if leg.departure_rt else leg.departure
            plat_str = f"  Platform {leg.platform}" if leg.platform is not None else ""
            console.print(
                f"  │   {icon}{leg.line:<5}  {dep} → {leg.arrival}  "
                f"{leg.destination:<28}  Dir: {leg.direction}{plat_str}"
            )
        console.print(f"  └{'─' * 55}")

    console.print()


# ── disruptions ───────────────────────────────────────────────────────────────


def render_disruptions(disruptions: list[Disruption], fmt: OutputFormat) -> None:
    if fmt == OutputFormat.json:
        _dump_json([d.model_dump() for d in disruptions])
        return

    now_str = datetime.now().strftime("%d.%m.%Y %H:%M")
    _print_header(f"⚠️  MVG Service Alerts  –  {now_str}")

    if not disruptions:
        console.print("\n  ✅ No current disruptions.\n")
        return

    for d in disruptions:
        icon = "🔴" if d.type == "INCIDENT" else "🟡"
        console.print(f"\n  {icon} {d.title}")
        if d.transport_types or d.lines:
            tt_str = "  ".join(f"{TRANSPORT_ICONS.get(t, '')} {t}" for t in d.transport_types)
            line_str = "  ".join(d.lines)
            console.print(f"     {tt_str}  {line_str}".rstrip())
        if d.valid_from:
            period = f"From {d.valid_from}"
            if d.valid_to:
                period += f" until {d.valid_to}"
            console.print(f"     🕐 {period}")
        if d.description and d.description != d.title:
            console.print(f"     {d.description[:400]}")

    console.print()


# ── errors ────────────────────────────────────────────────────────────────────


def render_error(message: str, code: str, fmt: OutputFormat, suggestion: str = "") -> None:
    if fmt == OutputFormat.json:
        payload: dict = {"error": code, "message": message}
        if suggestion:
            payload["suggestion"] = suggestion
        print(_json.dumps(payload, ensure_ascii=False))
    else:
        err_console.print(f"[red]Error:[/red] {message}")
        if suggestion:
            err_console.print(f"[dim]Hint: {suggestion}[/dim]")
