from pydantic import BaseModel


class Line(BaseModel):
    label: str
    transport_type: str


class Station(BaseModel):
    id: str
    name: str
    place: str = "München"
    latitude: float = 0.0
    longitude: float = 0.0
    lines: list[Line] = []


class Departure(BaseModel):
    line: str
    type: str
    destination: str
    time: int
    delay: int = 0
    realtime: bool = False
    cancelled: bool = False
    platform: str | None = None


class Connection(BaseModel):
    origin_name: str
    line: str
    type: str
    destination: str
    time: int
    delay: int = 0
    realtime: bool = False
    platform: str | None = None


class JourneyLeg(BaseModel):
    line: str
    type: str
    origin: str
    departure: str
    departure_rt: str | None = None
    transfer_at: str
    arrival: str
    direction: str
    platform: str | None = None


class Journey(BaseModel):
    duration: int
    transfers: int
    legs: list[JourneyLeg]


class Disruption(BaseModel):
    type: str
    title: str
    description: str = ""
    lines: list[str] = []
    transport_types: list[str] = []
    valid_from: str = ""
    valid_to: str = ""
    link: str = ""
