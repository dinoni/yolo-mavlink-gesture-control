
from safety_manager_v2 import SafetyManager, DroneStatus, FlightState


def setup_tracking():
    safety = SafetyManager(palm_timeout=0.3)

    drone = DroneStatus(
        armed=False,
        mode="STABILIZE",
        altitude=0.0,
        heartbeat_ok=True,
        altitude_ok=True,
        palm_visible=False,
        rc_enabled=True
    )

    assert safety.authorize(drone)
    assert safety.begin_takeoff(drone)

    drone.armed = True
    drone.mode = "GUIDED"
    drone.altitude = 3.0
    drone.palm_visible = True

    assert safety.takeoff_complete(drone)
    assert safety.start_tracking(drone)

    return safety, drone


def test_mavlink_loss():
    safety, drone = setup_tracking()
    drone.heartbeat_ok = False
    safety.update(drone)
    assert safety.state == FlightState.MANUAL_OVERRIDE


def test_altitude_loss():
    safety, drone = setup_tracking()
    drone.altitude_ok = False
    safety.update(drone)
    assert safety.state == FlightState.MANUAL_OVERRIDE


def test_guided_loss():
    safety, drone = setup_tracking()
    drone.mode = "STABILIZE"
    safety.update(drone)
    assert safety.state == FlightState.MANUAL_OVERRIDE


def test_rc_disabled():
    safety, drone = setup_tracking()
    drone.rc_enabled = False
    safety.update(drone)
    assert safety.state == FlightState.MANUAL_OVERRIDE


def test_palm_loss():
    safety, drone = setup_tracking()

    # Koristimo vrijeme zadnje detekcije,
    # bez cekanja u stvarnom vremenu.
    last_seen = safety.last_palm_seen

    drone.palm_visible = False
    safety.update(
        drone,
        now=last_seen + 0.4
    )

    assert safety.state == FlightState.HOLD
    assert safety.last_event == "PALM_LOST"


def test_rtl_lock():
    safety, drone = setup_tracking()

    assert safety.request_rtl(drone)
    assert safety.state == FlightState.RTL_LOCKED

    safety.update(drone)

    assert safety.state == FlightState.RTL_LOCKED
    assert not safety.can_track(drone)


def test_no_takeoff_without_rc():
    safety = SafetyManager()

    drone = DroneStatus(
        armed=False,
        mode="STABILIZE",
        altitude=0.0,
        heartbeat_ok=True,
        altitude_ok=True,
        rc_enabled=False
    )

    assert not safety.authorize(drone)
    assert not safety.can_takeoff(drone)

def test_negative_ground_altitude():
    safety = SafetyManager()

    drone = DroneStatus(
        armed=False,
        mode="STABILIZE",
        altitude=-0.002,
        heartbeat_ok=True,
        altitude_ok=True,
        rc_enabled=True
    )

    assert safety.authorize(drone)
    assert safety.state == FlightState.READY

tests = [
    ("Gubitak MAVLink veze", test_mavlink_loss),
    ("Gubitak telemetrije visine", test_altitude_loss),
    ("Izlazak iz GUIDED moda", test_guided_loss),
    ("Iskljucenje RC dozvole", test_rc_disabled),
    ("Gubitak dlana", test_palm_loss),
    ("RTL zakljucavanje", test_rtl_lock),
    ("Negativna visina na zemlji", test_negative_ground_altitude),
    ("Zabrana polijetanja bez RC dozvole", test_no_takeoff_without_rc)
]

passed = 0

print("\n===== SAFETY MANAGER V2 TEST =====\n")

for name, test in tests:
    try:
        test()
        print(f"[PASS] {name}")
        passed += 1
    except Exception as error:
        print(f"[FAIL] {name}: {error}")

print(f"\nREZULTAT: {passed}/{len(tests)}")

if passed != len(tests):
    raise SystemExit(1)
