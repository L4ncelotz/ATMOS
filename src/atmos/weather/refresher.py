"""Background weather refresher.

Pulls new WeatherState + ForecastDay list from a WeatherProvider every
`interval` seconds and delivers results through a thread-safe queue.

queue carries RefreshResult; main loop pops the most recent. Older
results are discarded — fresher data wins.
"""

from __future__ import annotations

import queue
import threading
import time
from dataclasses import dataclass, field

from atmos.weather.cache import (
    read_forecast_for,
    read_for_location,
    write_forecast,
    write_state,
)
from atmos.weather.client import WeatherError, WeatherProvider
from atmos.weather.forecast import ForecastDay
from atmos.weather.location import Location
from atmos.weather.models import WeatherState


def _persist_resolved_location(loc: Location) -> None:
    """Best-effort: write the resolved city to the user config so the
    next launch can hit the cache without the geocoder.

    Imported lazily to avoid importing `atmos.config` at module load
    time (it is loaded by `atmos/__init__.py` indirectly).
    """
    try:
        from atmos.config import update_resolved_location
        update_resolved_location(loc)
    except Exception:  # noqa: BLE001
        # Persisting is best-effort; never break the refresh thread.
        pass


@dataclass
class RefreshResult:
    state: WeatherState
    forecast: list[ForecastDay] = field(default_factory=list)
    offline: bool = False
    error: str | None = None


class WeatherRefresher:
    """Pulls weather on a schedule, results via queue.Queue."""

    def __init__(
        self,
        provider: WeatherProvider,
        location: Location,
        *,
        interval_s: float = 900.0,
        forecast_days: int = 5,
        maxsize: int = 8,
    ) -> None:
        self._provider = provider
        self._location = location
        self._interval = max(30.0, interval_s)
        self._forecast_days = max(1, min(16, forecast_days))
        self._queue: queue.Queue[RefreshResult] = queue.Queue(maxsize=maxsize)
        self._stop = threading.Event()
        self._kick = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._run, name="atmos-weather", daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._kick.set()
        if self._thread:
            self._thread.join(timeout=2.0)

    def request_refresh(self) -> None:
        """Force an immediate fetch (R key)."""
        self._kick.set()

    def request_location(self, location: Location) -> None:
        """Update the city and trigger an immediate fetch.

        Equivalent to `update_location(loc)` + `request_refresh()` in
        one call. Used by the location-search selection flow so a new
        city appears without the user waiting for the next periodic
        refresh.
        """
        self.update_location(location)
        self.request_refresh()

    def update_location(self, location: Location) -> None:
        """Switch the city without restarting the thread."""
        self._location = location
        self._kick.set()

    def drain_newest(self) -> RefreshResult | None:
        latest: RefreshResult | None = None
        try:
            while True:
                latest = self._queue.get_nowait()
        except queue.Empty:
            pass
        return latest

    def _run(self) -> None:
        # Initial fetch right away so the UI doesn't sit on mock data.
        self._fetch_once()
        while not self._stop.is_set():
            self._kick.wait(timeout=self._interval)
            if self._stop.is_set():
                break
            self._kick.clear()
            self._fetch_once()

    def _fetch_once(self) -> None:
        # Try current first; only hit forecast endpoint if current succeeds
        # — keeps the network budget smaller when something is broken.
        try:
            state = self._provider.current(self._location)
            offline = False
            error = None
            try:
                write_state(self._location, state)
            except Exception:  # noqa: BLE001
                pass
            _persist_resolved_location(self._location)
        except WeatherError as exc:
            error = str(exc)
            cached = read_for_location(self._location)
            if cached is not None:
                state = cached
                offline = True
            else:
                return

        # Forecast: only fetch on online success; otherwise serve cache.
        forecast: list[ForecastDay] = []
        if not offline:
            try:
                forecast = self._provider.forecast(
                    self._location, days=self._forecast_days
                )
                try:
                    write_forecast(self._location, forecast)
                except Exception:  # noqa: BLE001
                    pass
            except WeatherError:
                forecast = read_forecast_for(self._location)
        else:
            forecast = read_forecast_for(self._location)

        result = RefreshResult(
            state=state, forecast=forecast, offline=offline, error=error
        )
        try:
            self._queue.put_nowait(result)
        except queue.Full:
            try:
                self._queue.get_nowait()
            except queue.Empty:
                pass
            try:
                self._queue.put_nowait(result)
            except queue.Full:
                pass
        time.sleep(0.01)