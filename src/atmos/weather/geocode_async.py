"""Async geocoder for the location-search UI.

Same shape as `atmos.weather.refresher.WeatherRefresher`: a daemon
thread consumes (request_id, query) tuples from a queue, runs the
synchronous `resolve_location`, and posts the result back through
another queue. The UI thread calls `submit(query)` and `poll()` and
never blocks on network I/O.

Stale-result handling: a new `submit()` overwrites any pending work
in the request queue (the queue has maxsize=1, so the previous
request is dropped on the floor). On the result side, `poll()` only
returns a result whose request_id matches the most recent submit;
older results are silently discarded. This matches the existing
debounce-on-typing behavior in `LocationSearchState`.
"""

from __future__ import annotations

import queue
import threading
from dataclasses import dataclass
from typing import Optional

from atmos.weather.geocode import resolve_location
from atmos.weather.location import Location


@dataclass
class GeocodeRequest:
    id: int
    query: str


@dataclass
class GeocodeResult:
    request_id: int
    locations: list[Location]
    error: Optional[str] = None


class GeocodeWorker:
    """Single-flight async geocoder.

    Spawn one daemon thread on first `submit`. The thread loops:
    take (id, query) from `_req`, call `resolve_location`, put
    GeocodeResult on `_res`. `submit()` and `poll()` are non-blocking.
    """

    def __init__(self) -> None:
        self._req: queue.Queue[GeocodeRequest] = queue.Queue(maxsize=1)
        self._res: queue.Queue[GeocodeResult] = queue.Queue(maxsize=8)
        self._latest_id: int = 0
        self._thread: threading.Thread | None = None
        self._started = False

    def _ensure_started(self) -> None:
        if self._started:
            return
        self._started = True
        self._thread = threading.Thread(
            target=self._run, name="atmos-geocode", daemon=True
        )
        self._thread.start()

    def submit(self, query: str) -> GeocodeRequest:
        """Queue a geocode request. Returns immediately.

        If a previous request is still pending, it is dropped (we only
        care about the most recent typing).
        """
        self._ensure_started()
        self._latest_id += 1
        req = GeocodeRequest(id=self._latest_id, query=query)
        # Drain any pending request and replace.
        try:
            self._req.get_nowait()
        except queue.Empty:
            pass
        self._req.put_nowait(req)
        return req

    def poll(self) -> GeocodeResult | None:
        """Return the most recent result whose request_id is current.

        Stale results (older than the latest submit) are discarded.
        """
        latest: GeocodeResult | None = None
        try:
            while True:
                latest = self._res.get_nowait()
        except queue.Empty:
            pass
        if latest is None:
            return None
        if latest.request_id != self._latest_id:
            # Stale; the user has typed more characters since.
            return None
        return latest

    def latest_request_id(self) -> int:
        return self._latest_id

    def _run(self) -> None:
        while True:
            try:
                req = self._req.get()
            except Exception:  # noqa: BLE001
                continue
            try:
                locations = resolve_location(req.query, count=5)
                result = GeocodeResult(
                    request_id=req.id, locations=locations, error=None
                )
            except Exception as exc:  # noqa: BLE001
                result = GeocodeResult(
                    request_id=req.id, locations=[], error=str(exc)
                )
            try:
                self._res.put_nowait(result)
            except queue.Full:
                # Drop oldest.
                try:
                    self._res.get_nowait()
                except queue.Empty:
                    pass
                try:
                    self._res.put_nowait(result)
                except queue.Full:
                    pass


__all__ = ["GeocodeRequest", "GeocodeResult", "GeocodeWorker"]