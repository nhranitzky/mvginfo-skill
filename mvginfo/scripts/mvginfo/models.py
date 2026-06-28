from __future__ import annotations

from pydantic import BaseModel


class Line(BaseModel):
    label: str
    transport_type: str


class Station(BaseModel):
    id: str
    name: str
    place: str
    latitude: float
    longitude: float
    lines: list[Line] = []


class Departure(BaseModel):
    line: str
    type: str
    destination: str
    planned_time: int  # millisecond timestamp
    realtime_time: int  # millisecond timestamp
    delay_minutes: int
    realtime: bool
    cancelled: bool
    platform: int | None = None


class ConnectionLeg(BaseModel):
    line: str
    type: str
    origin: str
    departure: str  # HH:MM planned
    departure_rt: str | None = None  # HH:MM realtime if delayed
    destination: str
    arrival: str  # HH:MM
    direction: str
    platform: int | None = None


class Connection(BaseModel):
    duration: int  # minutes
    transfers: int
    legs: list[ConnectionLeg]


class Disruption(BaseModel):
    type: str
    title: str
    description: str = ""
    lines: list[str] = []
    transport_types: list[str] = []
    valid_from: str = ""
    valid_to: str = ""
