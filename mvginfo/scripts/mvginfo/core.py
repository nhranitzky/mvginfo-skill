from __future__ import annotations

import datetime
import re

from mvg_api.v3.syncapi import SyncApi

from .models import Connection, ConnectionLeg, Departure, Disruption, Line, Station

VALID_TRANSPORT_TYPES = {
    "UBAHN",
    "SBAHN",
    "TRAM",
    "BUS",
    "BAHN",
    "REGIONAL_BUS",
    "SCHIFF",
    "SEV",
}


class ClientError(Exception):
    pass


def _api() -> SyncApi:
    return SyncApi()


# ── stations ──────────────────────────────────────────────────────────────────


def find_station(query: str) -> Station | None:
    try:
        api = _api()
        if query.lower().startswith("de:"):
            s = api.get_station(query)
            if s is None:
                return None
            return Station(id=s.id, name=s.name, place=s.place, latitude=s.latitude, longitude=s.longitude)
        loc = api.find_location_station(query)
        if loc is None:
            return None
        return Station(
            id=loc.globalId or "", name=loc.name, place=loc.place, latitude=loc.latitude, longitude=loc.longitude
        )
    except Exception as exc:
        raise ClientError(str(exc)) from exc


def find_nearby(lat: float, lng: float) -> list[Station]:
    try:
        result = _api().get_nearby(lat, lng)
        return [
            Station(id=s.globalId, name=s.name, place=s.place, latitude=s.latitude, longitude=s.longitude)
            for s in result
        ]
    except Exception as exc:
        raise ClientError(str(exc)) from exc


def get_station_lines(station_id: str) -> list[Line]:
    try:
        result = _api().get_lines(station_id=station_id)
        return [Line(label=ln.label, transport_type=ln.transportType) for ln in result]
    except Exception:
        return []


# ── departures ────────────────────────────────────────────────────────────────


def get_departures(
    station_id: str,
    limit: int = 20,
    offset: int = 0,
    transport_types: list[str] | None = None,
) -> list[Departure]:
    try:
        result = _api().get_departures(
            station_id,
            limit=limit,
            offset_minutes=offset or None,
            transport_types=transport_types,
        )
    except Exception as exc:
        raise ClientError(str(exc)) from exc
    return [
        Departure(
            line=d.label,
            type=d.transportType,
            destination=d.destination,
            planned_time=d.plannedDepartureTime,
            realtime_time=d.realtimeDepartureTime,
            delay_minutes=d.delayInMinutes or 0,
            realtime=d.realtime,
            cancelled=d.cancelled,
            platform=d.platform,
        )
        for d in result
    ]


# ── connections ───────────────────────────────────────────────────────────────


def _iso_hhmm(iso: str) -> str:
    return iso[11:16] if len(iso) >= 16 else ""


def _iso_rt(iso: str, delay_min: int) -> str | None:
    if not delay_min:
        return None
    try:
        dt = datetime.datetime.fromisoformat(iso)
        return (dt + datetime.timedelta(minutes=delay_min)).strftime("%H:%M")
    except Exception:
        return None


def get_connections(
    origin_id: str,
    dest_id: str,
    limit: int = 6,
    transport_types: list[str] | None = None,
) -> list[Connection]:
    routing_dt = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    tt_str = ",".join(transport_types) if transport_types else None
    try:
        result = _api().get_connections(origin_id, dest_id, routing_dt, transport_types=tt_str)
    except Exception as exc:
        raise ClientError(str(exc)) from exc

    connections: list[Connection] = []
    for conn in result:
        legs: list[ConnectionLeg] = []
        for part in conn.parts:
            if part.line.transportType == "PEDESTRIAN":
                continue
            dep_iso = part.from_.plannedDeparture
            delay = part.from_.departureDelayInMinutes or 0
            legs.append(
                ConnectionLeg(
                    line=part.line.label,
                    type=part.line.transportType,
                    origin=part.from_.name,
                    departure=_iso_hhmm(dep_iso),
                    departure_rt=_iso_rt(dep_iso, delay),
                    destination=part.to.name,
                    arrival=_iso_hhmm(part.to.plannedDeparture),
                    direction=part.line.destination,
                    platform=part.from_.platform,
                )
            )
        if not legs:
            continue
        duration = 0
        try:
            d1 = datetime.datetime.fromisoformat(conn.parts[0].from_.plannedDeparture)
            d2 = datetime.datetime.fromisoformat(conn.parts[-1].to.plannedDeparture)
            duration = max(0, int((d2 - d1).total_seconds() // 60))
        except Exception:
            pass
        connections.append(Connection(duration=duration, transfers=max(0, len(legs) - 1), legs=legs))
        if len(connections) >= limit:
            break
    return connections


# ── disruptions ───────────────────────────────────────────────────────────────


def _fmt_ts(ms: int | None) -> str:
    if not ms:
        return ""
    try:
        return datetime.datetime.fromtimestamp(ms / 1000).strftime("%d.%m.%Y %H:%M")
    except Exception:
        return ""


def get_disruptions(
    transport_types: list[str] | None = None,
    line_filter: set[str] | None = None,
) -> list[Disruption]:
    try:
        result = _api().get_messages()
    except Exception as exc:
        raise ClientError(str(exc)) from exc

    disruptions: list[Disruption] = []
    for msg in result:
        msg_lines = [ln.label for ln in msg.lines]
        msg_tts = list({ln.transportType.upper() for ln in msg.lines if ln.transportType})

        if transport_types:
            wanted = {t.upper() for t in transport_types}
            if not set(msg_tts) & wanted:
                continue

        if line_filter:
            if not {ln.upper() for ln in msg_lines} & line_filter:
                continue

        disruptions.append(
            Disruption(
                type=msg.type.value,
                title=msg.title,
                description=re.sub(r"<[^>]+>", " ", msg.description).strip(),
                lines=msg_lines,
                transport_types=msg_tts,
                valid_from=_fmt_ts(msg.validFrom),
                valid_to=_fmt_ts(msg.validTo),
            )
        )
    return disruptions


# ── input parsing ─────────────────────────────────────────────────────────────


def parse_transport_types(value: str) -> list[str]:
    parts = [t.strip().upper() for t in value.split(",") if t.strip()]
    invalid = [t for t in parts if t not in VALID_TRANSPORT_TYPES]
    if invalid:
        valid_list = ", ".join(sorted(VALID_TRANSPORT_TYPES))
        raise ValueError(f"Unknown transport type: {', '.join(invalid)}. Valid: {valid_list}")
    return parts


def parse_line_filter(value: str) -> set[str]:
    return {ln.strip().upper() for ln in value.split(",") if ln.strip()}
