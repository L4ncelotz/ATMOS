"""Location: a resolved city for weather queries.

Returned by geocode.search() and consumed by WeatherProvider.current().
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Location:
    name: str
    country: str
    latitude: float
    longitude: float
    timezone: str

    @property
    def label(self) -> str:
        return f"{self.name}, {self.country}"