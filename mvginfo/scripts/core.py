import re
import subprocess
import sys
from datetime import datetime

from mvg import MvgApi, MvgApiError, TransportType

from .models import Connection, Departure, Disruption, Line, Station


class ClientError(Exception):
    pass


TRANSPORT_MAP: dict[str, TransportType] = {
    "UBAHN": TransportType.UBAHN,
    "SBAHN": TransportType.SBAHN,
    "TRAM": TransportType.TRAM,
    "BUS": TransportType.BUS,
    "BAHN": TransportType.BAHN,
    "REGIONAL_BUS": TransportType.REGIONAL_BUS,
    "SCHIFF": TransportType.SCHIFF,
    "SEV": TransportType.SEV,
}

_ALL_STATIONS: list[dict] | None = None


# ── MVG API ────────────────────────────────────────────────────────────────────

def _raw_to_station(raw: dict) -> Station:
    return Station(
        id=raw["id"],
        name=raw["name"],
        place=raw.get("place", "München"),
        latitude=raw.get("latitude", 0.0),
        longitude=raw.get("longitude", 0.0),
    )


def _raw_to_departure(raw: dict) -> Departure:
    platform = raw.get("platform")
    return Departure(
        line=raw.get("line") or "?",
        type=raw.get("type") or "?",
        destination=raw.get("destination") or "?",
        time=raw.get("time") or 0,
        delay=raw.get("delay") or 0,
        realtime=raw.get("realtime") or False,
        cancelled=raw.get("cancelled") or False,
        platform=str(platform) if platform is not None else None,
    )


def find_station(query: str) -> Station | None:
    try:
        raw = MvgApi.station(query)
    except MvgApiError as exc:
        raise ClientError(str(exc)) from exc
    return _raw_to_station(raw) if raw else None


def find_nearby(lat: float, lng: float, all_stations: bool = False) -> list[Station]:
    try:
        result = MvgApi.nearby(lat, lng, full_list=all_stations)
    except MvgApiError as exc:
        raise ClientError(str(exc)) from exc
    if result is None:
        return []
    items = result if isinstance(result, list) else [result]
    return [_raw_to_station(s) for s in items]


def get_lines(station_id: str) -> list[Line]:
    try:
        raw_lines = MvgApi.lines(station_id)
    except (MvgApiError, ValueError):
        return []
    return [
        Line(label=str(ln.get("label", "?")), transport_type=str(ln.get("transportType", "?")))
        for ln in raw_lines
    ]


def get_departures(
    station_id: str,
    limit: int = 20,
    offset: int = 0,
    transport_types: list[str] | None = None,
) -> list[Departure]:
    tt: list[TransportType] | None = None
    if transport_types:
        try:
            tt = [TRANSPORT_MAP[t.upper()] for t in transport_types]
        except KeyError as exc:
            raise ClientError(f"Unbekannter Verkehrstyp: {exc}") from exc
    try:
        raw = MvgApi(station_id).departures(limit=limit, offset=offset, transport_types=tt)
    except MvgApiError as exc:
        raise ClientError(str(exc)) from exc
    return [_raw_to_departure(d) for d in raw]


def _all_stations_cached() -> list[dict]:
    global _ALL_STATIONS
    if _ALL_STATIONS is None:
        _ALL_STATIONS = MvgApi.stations()
    return _ALL_STATIONS


def get_all_matching_stations(query: str) -> list[Station]:
    query = query.strip()
    if query.lower().startswith("de:"):
        s = find_station(query)
        return [s] if s else []
    needle = query.lower()
    try:
        all_s = _all_stations_cached()
    except MvgApiError as exc:
        raise ClientError(str(exc)) from exc
    return [_raw_to_station(s) for s in all_s if needle in s.get("name", "").lower()]


def _dest_matches(dep_dest: str, target: Station) -> bool:
    def core(s: str) -> str:
        return re.sub(r"\s*\(.*?\)", "", s).strip().lower()

    a, b = core(dep_dest), core(target.name)
    return a == b or b in a or a in b or target.place.lower() in a


def find_connections(
    origin_stations: list[Station],
    destination: Station,
    limit: int = 6,
    transport_types: list[str] | None = None,
    line_filter: set[str] | None = None,
) -> list[Connection]:
    tt: list[TransportType] | None = None
    if transport_types:
        try:
            tt = [TRANSPORT_MAP[t.upper()] for t in transport_types]
        except KeyError as exc:
            raise ClientError(f"Unbekannter Verkehrstyp: {exc}") from exc

    all_deps: list[dict] = []
    for station in origin_stations:
        try:
            deps = MvgApi(station.id).departures(limit=200, transport_types=tt)
        except (MvgApiError, ValueError):
            continue
        for dep in deps:
            if dep.get("cancelled"):
                continue
            if not _dest_matches(dep.get("destination", ""), destination):
                continue
            if line_filter and dep.get("line", "").upper() not in line_filter:
                continue
            dep["_origin_name"] = station.name
            all_deps.append(dep)

    seen: set[tuple] = set()
    result: list[Connection] = []
    for dep in sorted(all_deps, key=lambda d: d.get("time", 0)):
        key = (dep.get("line"), dep.get("destination"), dep.get("time"))
        if key in seen:
            continue
        seen.add(key)
        platform = dep.get("platform")
        result.append(Connection(
            origin_name=dep.get("_origin_name") or "",
            line=dep.get("line") or "?",
            type=dep.get("type") or "?",
            destination=dep.get("destination") or "?",
            time=dep.get("time") or 0,
            delay=dep.get("delay") or 0,
            realtime=dep.get("realtime") or False,
            platform=str(platform) if platform is not None else None,
        ))
        if len(result) >= limit:
            break
    return result


def parse_transport_types(value: str) -> list[str]:
    return [t.strip().upper() for t in value.split(",") if t.strip()]


def parse_line_filter(value: str) -> set[str]:
    return {ln.strip().upper() for ln in value.split(",") if ln.strip()}


# ── Disruptions (Playwright) ───────────────────────────────────────────────────

_DISRUPTIONS_URL = "https://www.mvg.de/verbindungen/betriebsmeldungen.html"

_MESSAGE_URL_PATTERNS = [
    "message", "incident", "disruption", "stoerung", "meldung",
    "interruption", "alert", "news", "ticker",
]


def ensure_chromium() -> None:
    from playwright.sync_api import sync_playwright

    try:
        with sync_playwright() as p:
            b = p.chromium.launch(headless=True)
            b.close()
    except Exception:
        subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            check=True,
        )


def fetch_disruptions(debug: bool = False) -> list[Disruption]:
    from playwright.sync_api import sync_playwright

    captured: list[dict] = []
    all_api_urls: list[str] = []

    def on_response(response):
        url = response.url
        if "json" not in response.headers.get("content-type", ""):
            return
        all_api_urls.append(url)
        try:
            body = response.json()
        except Exception:
            return
        if any(pat in url.lower() for pat in _MESSAGE_URL_PATTERNS):
            captured.append({"url": url, "data": body})
            return
        items = body if isinstance(body, list) else (
            body.get("messages") or body.get("incidents") or body.get("meldungen") or []
        )
        if isinstance(items, list) and items:
            first = items[0] if isinstance(items[0], dict) else {}
            if any(k in first for k in ("title", "headline", "type", "validFrom")):
                captured.append({"url": url, "data": body})

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page()
        page.on("response", on_response)
        page.goto(_DISRUPTIONS_URL, wait_until="networkidle", timeout=30_000)
        page.wait_for_timeout(3_000)
        browser.close()

    if debug:
        sys.stderr.write("\n=== Intercepted JSON API calls ===\n")
        for u in all_api_urls:
            sys.stderr.write(f"  {u}\n")

    return _extract_disruptions(captured)


def _extract_disruptions(captured: list[dict]) -> list[Disruption]:
    def score(entry: dict) -> tuple:
        url_match = any(pat in entry["url"].lower() for pat in _MESSAGE_URL_PATTERNS)
        items = _items_from(entry["data"])
        return (not url_match, -len(items))

    for entry in sorted(captured, key=score):
        items = _items_from(entry["data"])
        if items:
            return [_normalise_disruption(i) for i in items if isinstance(i, dict)]
    return []


def _items_from(data: dict | list) -> list:
    if isinstance(data, list):
        return data
    return data.get("messages") or data.get("incidents") or data.get("meldungen") or []


def _normalise_disruption(raw: dict) -> Disruption:
    raw_lines = raw.get("lines") or raw.get("affectedLines") or []
    if raw_lines and isinstance(raw_lines[0], dict):
        lines = [str(ln.get("label") or ln.get("lineNumber") or ln.get("line") or "") for ln in raw_lines]
        tts = list({
            str(ln.get("transportType") or ln.get("product") or "").upper()
            for ln in raw_lines
            if ln.get("transportType") or ln.get("product")
        })
    else:
        lines, tts = [str(ln) for ln in raw_lines], []

    def _ts(val) -> str:
        if not val:
            return ""
        if isinstance(val, (int, float)):
            ts = val / 1000 if val > 1_000_000_000_000 else val
            try:
                return datetime.fromtimestamp(ts).strftime("%d.%m.%Y %H:%M")
            except Exception:
                return str(val)
        return str(val)

    return Disruption(
        type=str(raw.get("type") or raw.get("msgType") or "MESSAGE").upper(),
        title=raw.get("title") or raw.get("headline") or "",
        description=re.sub(r"<[^>]+>", " ", raw.get("text") or raw.get("description") or "").strip(),
        lines=[ln for ln in lines if ln],
        transport_types=tts,
        valid_from=_ts(raw.get("validFrom") or raw.get("activeFrom")),
        valid_to=_ts(raw.get("validTo") or raw.get("activeTo")),
        link=raw.get("link") or raw.get("url") or "",
    )
