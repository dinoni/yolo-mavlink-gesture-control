
from dataclasses import dataclass
from enum import Enum, auto
import time


class FlightState(Enum):
    DISABLED = auto()
    READY = auto()
    TAKEOFF = auto()
    HOLD = auto()
    TRACKING = auto()
    RTL_LOCKED = auto()
    MANUAL_OVERRIDE = auto()


@dataclass
class DroneStatus:
    armed: bool = False
    mode: str = "UNKNOWN"
    altitude: float = 0.0

    heartbeat_ok: bool = False
    altitude_ok: bool = False

    palm_visible: bool = False
    rc_enabled: bool = False


class SafetyManager:

    def __init__(self, palm_timeout=0.3):
        self.state = FlightState.DISABLED
        self.authorized = False

        self.palm_timeout = palm_timeout
        self.last_palm_seen = None

        self.last_event = "INITIALIZED"

    def _event(self, message):
        self.last_event = message
        print("[SAFETY]", message)

    def telemetry_ok(self, status):
        return (
            status.heartbeat_ok
            and status.altitude_ok
        )

    def on_ground(self, status):
        return (
            not status.armed
            and abs(status.altitude) <= 0.2
        )

    def in_flight(self, status):
        return (
            status.armed
            and status.altitude >= 0.8
        )

    def authorize(self, status):
        if (
            self.state == FlightState.DISABLED
            and self.telemetry_ok(status)
            and self.on_ground(status)
            and status.mode != "RTL"
            and status.rc_enabled
        ):
            self.authorized = True
            self.state = FlightState.READY
            self._event("AUTHORIZED")
            return True

        return False

    def can_takeoff(self, status):
        return (
            self.authorized
            and self.state == FlightState.READY
            and self.telemetry_ok(status)
            and self.on_ground(status)
            and status.rc_enabled
            and status.mode != "RTL"
        )

    def begin_takeoff(self, status):
        if not self.can_takeoff(status):
            return False

        self.authorized = False
        self.state = FlightState.TAKEOFF
        self._event("TAKEOFF_STARTED")
        return True

    def takeoff_complete(self, status):
        if (
            self.state == FlightState.TAKEOFF
            and self.telemetry_ok(status)
            and self.in_flight(status)
            and status.mode == "GUIDED"
            and status.altitude >= 2.5
            and status.rc_enabled
        ):
            self.state = FlightState.HOLD
            self._event("TAKEOFF_COMPLETE")
            return True

        return False

    def can_track(self, status):
        return (
            self.state in (
                FlightState.HOLD,
                FlightState.TRACKING
            )
            and self.telemetry_ok(status)
            and self.in_flight(status)
            and status.mode == "GUIDED"
            and status.rc_enabled
        )

    def start_tracking(self, status):
        if not self.can_track(status):
            return False

        if not status.palm_visible:
            return False

        self.state = FlightState.TRACKING
        self.last_palm_seen = time.monotonic()

        self._event("TRACKING_STARTED")
        return True

    def stop_tracking(self):
        if self.state == FlightState.TRACKING:
            self.state = FlightState.HOLD
            self.last_palm_seen = None
            self._event("TRACKING_STOPPED")

    def request_rtl(self, status):
        if (
            self.state in (
                FlightState.HOLD,
                FlightState.TRACKING
            )
            and self.telemetry_ok(status)
            and self.in_flight(status)
            and status.rc_enabled
        ):
            self.state = FlightState.RTL_LOCKED
            self.authorized = False
            self.last_palm_seen = None

            self._event("RTL_REQUESTED")
            return True

        return False

    def manual_override(self, reason="MANUAL_OVERRIDE"):
        self.state = FlightState.MANUAL_OVERRIDE
        self.authorized = False
        self.last_palm_seen = None

        self._event(reason)

    def update(self, status, now=None):
        if now is None:
            now = time.monotonic()

        # 1. Ne dopustamo AI upravljanje bez RC dozvole.
        if self.state in (
            FlightState.READY,
            FlightState.TAKEOFF,
            FlightState.HOLD,
            FlightState.TRACKING
        ):
            if not status.rc_enabled:
                self.manual_override("RC_DISABLED")
                return

        # 2. Gubitak telemetrije.
        if self.state in (
            FlightState.READY,
            FlightState.TAKEOFF,
            FlightState.HOLD,
            FlightState.TRACKING
        ):
            if not self.telemetry_ok(status):
                self.manual_override("TELEMETRY_LOST")
                return

        # 3. Neocekivana promjena moda.
        if self.state in (
            FlightState.HOLD,
            FlightState.TRACKING
        ):
            if status.mode != "GUIDED":
                self.manual_override("GUIDED_MODE_LOST")
                return

        # 4. Dron vise nije u letu.
        if self.state in (
            FlightState.HOLD,
            FlightState.TRACKING
        ):
            if not self.in_flight(status):
                self.manual_override("FLIGHT_STATE_INVALID")
                return

        # 5. Gubitak dlana tijekom pracenja.
        if self.state == FlightState.TRACKING:
            if status.palm_visible:
                self.last_palm_seen = now

            elif (
                self.last_palm_seen is None
                or now - self.last_palm_seen >= self.palm_timeout
            ):
                self.stop_tracking()
                self._event("PALM_LOST")

        # 6. RTL je zakljucano stanje.
        # Nema automatskog ponovnog aktiviranja.
        if self.state == FlightState.RTL_LOCKED:
            self.authorized = False

    def reset(self, status):
        if (
            self.state in (
                FlightState.RTL_LOCKED,
                FlightState.MANUAL_OVERRIDE
            )
            and self.telemetry_ok(status)
            and self.on_ground(status)
            and status.mode != "RTL"
        ):
            self.state = FlightState.DISABLED
            self.authorized = False
            self.last_palm_seen = None

            self._event("RESET")
            return True

        return False
