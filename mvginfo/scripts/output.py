import enum
import json
import sys
from datetime import datetime

from rich.console import Console
from rich.table import Table

from .models import Connection, Departure, Disruption, Journey, Station

console = Console()
err_console = Console(stderr=True)

TRANSPORT_LABELS: dict[str, str] = {
    "U-Bahn": "🚇",
    "S-Bahn": "🚈",
    "Tram": "🚋",
    "Bus": "🚌",
    "StadtBus": "🚌",
    "Regional Bus": "🚌",
    "Regionalbus": "🚌",
    "Bahn": "🚆",
    "Schiff": "⛴",
    "SEV": "🔄",
}

TRANSPORT_LABELS_BY_TYPE: dict[str, str] = {
    "UBAHN": "🟦 U-Bahn",
    "SBAHN": "🟩 S-Bahn",
    "TRAM": "🟥 Tram",
    "BUS": "🟨 Bus",
    "BAHN": "🚂 Bahn",
    "REGIONAL_BUS": "🚌 Reg.-Bus",
    "SCHIFF": "⛴ Schiff",
    "SEV": "🔄 SEV",
}

SEVERITY_ICONS: dict[str, str] = {
    "DISRUPTION": "🔴",
    "INCIDENT": "🔴",
    "WARNING": "🟡",
    "SCHEDULE_CHANGES": "🟡",
    "MESSAGE": "🔵",
    "INFO": "ℹ️ ",
}

SEVERITY_ORDER: dict[str, int] = {
    "DISRUPTION": 0, "INCIDENT": 0,
    "WARNING": 1, "SCHEDULE_CHANGES": 1,
    "MESSAGE": 2, "INFO": 3,
}


class OutputFormat(str, enum.Enum):
    text = "text"
    json = "json"
    llm = "llm"


def _minutes_until(unix_timestamp: int) -> int:
    return max(0, int((unix_timestamp - datetime.now().timestamp()) / 60))


def _fmt_hhmm(unix_timestamp: int) -> str:
    try:
        return datetime.fromtimestamp(unix_timestamp).strftime("%H:%M")
    except Exception:
        return "–"


# ── stations ──────────────────────────────────────────────────────────────────

def render_stations(stations: list[Station], fmt: OutputFormat) -> None:
    if fmt == OutputFormat.json:
        print(json.dumps([s.model_dump() for s in stations], ensure_ascii=False, indent=2))
        return

    if fmt == OutputFormat.llm:
        rows = []
        for s in stations:
            lines_str = ", ".join(
                f"{ln.transport_type}:{ln.label}" for ln in s.lines
            ) if s.lines else ""
            rows.append(
                f"  - id: {s.id}\n    name: {s.name}, {s.place}\n"
                f"    coords: [{s.latitude:.5f}, {s.longitude:.5f}]\n"
                + (f"    lines: {lines_str}\n" if lines_str else "")
            )
        toon = "stations:\n" + "".join(rows)
        print(f"```toon\n{toon}```")
        return

    table = Table(show_header=True, header_style="bold")
    table.add_column("Name")
    table.add_column("Ort")
    table.add_column("ID")
    table.add_column("Koordinaten")
    table.add_column("Linien")
    for s in stations:
        lines_str = "  ".join(
            f"{TRANSPORT_LABELS_BY_TYPE.get(ln.transport_type, ln.transport_type)} {ln.label}"
            for ln in s.lines
        )
        table.add_row(
            s.name, s.place, s.id,
            f"{s.latitude:.5f}, {s.longitude:.5f}",
            lines_str,
        )
    console.print(table)


# ── departures ────────────────────────────────────────────────────────────────

def render_departures(
    station: Station,
    departures: list[Departure],
    offset: int,
    fmt: OutputFormat,
) -> None:
    if fmt == OutputFormat.json:
        print(json.dumps([d.model_dump() for d in departures], ensure_ascii=False, indent=2))
        return

    if fmt == OutputFormat.llm:
        rows = []
        for d in departures:
            mins = _minutes_until(d.time)
            rows.append(
                f"  - line: {d.line}\n    type: {d.type}\n"
                f"    destination: {d.destination}\n"
                f"    in_minutes: {mins}\n"
                f"    delay_seconds: {d.delay}\n"
                f"    realtime: {str(d.realtime).lower()}\n"
                f"    cancelled: {str(d.cancelled).lower()}\n"
                + (f"    platform: {d.platform}\n" if d.platform else "")
            )
        toon = (
            f"station: {station.name}, {station.place}\n"
            f"time: {datetime.now().strftime('%H:%M')}\n"
            "departures:\n" + "".join(rows)
        )
        print(f"```toon\n{toon}```")
        return

    now_str = datetime.now().strftime("%H:%M")
    console.print(f"\n{'═' * 60}")
    console.print(f"  🚏 {station.name}, {station.place}  –  {now_str}")
    if offset:
        console.print(f"  (zeigt Abfahrten in ≥{offset} min, Walking-Offset)")
    console.print(f"{'═' * 60}")

    if not departures:
        console.print("\n  Keine Abfahrten für die gewählten Filter.\n")
        return

    for d in departures:
        icon = TRANSPORT_LABELS.get(d.type, "")
        mins = _minutes_until(d.time)
        time_str = "⏱  Now" if mins == 0 else f"⏱  {mins} min"
        delay_str = f" ⚠️ +{d.delay // 60}m" if d.delay and d.delay > 0 else ""
        rt_badge = "📡" if d.realtime else "📋"
        cancelled_str = "❌ Cancelled" if d.cancelled else time_str + delay_str
        plat_str = f"  Gleis {d.platform}" if d.platform else ""
        col_line = f"{icon}{d.line}"
        console.print(f"  {col_line:<12} {d.destination:<32} {cancelled_str:<22}{rt_badge}{plat_str}")

    console.print()


# ── connections ───────────────────────────────────────────────────────────────

def render_connections(
    origin: str,
    destination: str,
    connections: list[Connection],
    fmt: OutputFormat,
) -> None:
    if fmt == OutputFormat.json:
        print(json.dumps([c.model_dump() for c in connections], ensure_ascii=False, indent=2))
        return

    if fmt == OutputFormat.llm:
        rows = []
        for c in connections:
            mins = _minutes_until(c.time)
            rows.append(
                f"  - line: {c.line}\n    type: {c.type}\n"
                f"    destination: {c.destination}\n"
                f"    board_at: {c.origin_name}\n"
                f"    in_minutes: {mins}\n"
                f"    departs_at: {_fmt_hhmm(c.time)}\n"
                f"    delay_seconds: {c.delay}\n"
                f"    realtime: {str(c.realtime).lower()}\n"
                + (f"    platform: {c.platform}\n" if c.platform else "")
            )
        toon = (
            f"origin: {origin}\ndestination: {destination}\n"
            f"time: {datetime.now().strftime('%H:%M')}\n"
            "connections:\n" + ("".join(rows) if rows else "  []\n")
        )
        print(f"```toon\n{toon}```")
        return

    now_str = datetime.now().strftime("%H:%M")
    console.print(f"\n{'═' * 60}")
    console.print(f"  🗺  {origin}  →  {destination}")
    console.print(f"  📡 Live-Abfahrten um {now_str}  (nur Direkt)")
    console.print(f"{'═' * 60}")

    if not connections:
        console.print(
            "\n  Keine Direktverbindungen gefunden.\n"
            "  ℹ️  Dieses Tool findet nur Direktfahrten. Für Umstiegsverbindungen:\n"
            "      https://www.mvg.de/verbindungen.html\n"
        )
        return

    for i, c in enumerate(connections, 1):
        icon = TRANSPORT_LABELS.get(c.type, "")
        mins = _minutes_until(c.time)
        time_str = "Now" if mins == 0 else f"in {mins} min  ({_fmt_hhmm(c.time)})"
        delay_str = f"  ⚠️ +{c.delay // 60}m" if c.delay and c.delay > 0 else ""
        rt_badge = "📡" if c.realtime else "📋"
        plat_str = f"  Platform {c.platform}" if c.platform else ""
        console.print(
            f"\n  ┌─ [{i}]  {icon}{c.line}  →  {c.destination}\n"
            f"  │   🟢 Departs {time_str}{delay_str}  {rt_badge}{plat_str}\n"
            f"  │   🚏 Board at: {c.origin_name}  │  Alight at: {destination}\n"
            f"  └{'─' * 55}"
        )

    console.print()


# ── journeys ──────────────────────────────────────────────────────────────────

def render_journeys(
    origin: str,
    destination: str,
    journeys: list[Journey],
    fmt: OutputFormat,
) -> None:
    if fmt == OutputFormat.json:
        print(json.dumps([j.model_dump() for j in journeys], ensure_ascii=False, indent=2))
        return

    if fmt == OutputFormat.llm:
        rows = []
        for j in journeys:
            legs_str = "".join(
                f"      - line: {leg.line}\n        type: {leg.type}\n"
                f"        origin: {leg.origin}\n"
                f"        departure: {leg.departure_rt or leg.departure}\n"
                f"        transfer_at: {leg.transfer_at}\n"
                f"        arrival: {leg.arrival}\n"
                f"        direction: {leg.direction}\n"
                + (f"        platform: {leg.platform}\n" if leg.platform else "")
                for leg in j.legs
            )
            rows.append(
                f"  - duration: {j.duration}\n"
                f"    transfers: {j.transfers}\n"
                f"    legs:\n{legs_str}"
            )
        toon = (
            f"origin: {origin}\ndestination: {destination}\n"
            f"time: {datetime.now().strftime('%H:%M')}\n"
            "journeys:\n" + ("".join(rows) if rows else "  []\n")
        )
        print(f"```toon\n{toon}```")
        return

    now_str = datetime.now().strftime("%H:%M")
    console.print(f"\n{'═' * 60}")
    console.print(f"  🗺  {origin}  →  {destination}  –  {now_str}")
    console.print(f"{'═' * 60}")

    if not journeys:
        console.print("\n  Keine Verbindungen gefunden.\n")
        return

    for i, j in enumerate(journeys, 1):
        transfers_str = "ohne Umstieg" if j.transfers == 0 else f"{j.transfers} Umstieg{'e' if j.transfers > 1 else ''}"
        console.print(f"\n  ┌─ [{i}]  {j.duration} min  |  {transfers_str}")
        for leg in j.legs:
            icon = TRANSPORT_LABELS_BY_TYPE.get(leg.type, "").split()[0] if leg.type in TRANSPORT_LABELS_BY_TYPE else ""
            dep = f"{leg.departure_rt}*" if leg.departure_rt else leg.departure
            plat_str = f"  Gleis {leg.platform}" if leg.platform else ""
            console.print(
                f"  │   {icon}{leg.line:<5}  {dep} → {leg.arrival}  "
                f"{leg.transfer_at:<28}  Ri: {leg.direction}{plat_str}"
            )
        console.print(f"  └{'─' * 55}")

    console.print()


# ── disruptions ───────────────────────────────────────────────────────────────

def render_disruptions(disruptions: list[Disruption], fmt: OutputFormat) -> None:
    if fmt == OutputFormat.json:
        print(json.dumps([d.model_dump() for d in disruptions], ensure_ascii=False, indent=2))
        return

    if fmt == OutputFormat.llm:
        rows = []
        for d in disruptions:
            rows.append(
                f"  - type: {d.type}\n    title: {d.title}\n"
                + (f"    lines: [{', '.join(d.lines)}]\n" if d.lines else "")
                + (f"    transport_types: [{', '.join(d.transport_types)}]\n" if d.transport_types else "")
                + (f"    valid_from: {d.valid_from}\n" if d.valid_from else "")
                + (f"    valid_to: {d.valid_to}\n" if d.valid_to else "")
                + (f"    description: |\n      {d.description[:300]}\n" if d.description else "")
                + (f"    link: {d.link}\n" if d.link else "")
            )
        now_str = datetime.now().strftime("%d.%m.%Y %H:%M")
        toon = (
            f"source: {SOURCE_URL}\ntime: {now_str}\n"
            "disruptions:\n" + ("".join(rows) if rows else "  []\n")
        )
        print(f"```toon\n{toon}```")
        return

    now_str = datetime.now().strftime("%d.%m.%Y %H:%M")
    console.print(f"\n{'═' * 60}")
    console.print(f"  ⚠️  MVG Störungen & Meldungen  –  {now_str}")
    console.print(f"  Quelle: {SOURCE_URL}")
    console.print(f"{'═' * 60}")

    if not disruptions:
        console.print("\n  ✅ Keine aktuellen Störungen oder Meldungen.\n")
        return

    for d in disruptions:
        icon = SEVERITY_ICONS.get(d.type, "🔵")
        console.print(f"\n  {icon} {d.title}")
        if d.transport_types or d.lines:
            tt_str = "  ".join(TRANSPORT_LABELS_BY_TYPE.get(t, t) for t in d.transport_types)
            line_str = "  ".join(d.lines)
            console.print(f"     {tt_str}  {line_str}".rstrip())
        if d.valid_from:
            period = f"Von {d.valid_from}"
            if d.valid_to:
                period += f" bis {d.valid_to}"
            console.print(f"     🕐 {period}")
        if d.description and d.description != d.title:
            console.print(f"     {d.description[:400]}")
        if d.link:
            console.print(f"     🔗 {d.link}")

    console.print()


# ── errors ────────────────────────────────────────────────────────────────────

SOURCE_URL = "https://www.mvg.de/verbindungen/betriebsmeldungen.html"


def render_error(message: str, code: str, fmt: OutputFormat) -> None:
    if fmt == OutputFormat.json:
        json.dump({"error": message, "code": code}, sys.stderr)
        sys.stderr.write("\n")
    elif fmt == OutputFormat.llm:
        err_console.print(f"```toon\nerror:\n  code: {code}\n  message: {message}\n```")
    else:
        err_console.print(f"[red]Error:[/red] {message}")
