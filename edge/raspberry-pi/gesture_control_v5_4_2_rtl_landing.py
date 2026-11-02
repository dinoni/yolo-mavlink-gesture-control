
import csv
import os
import time
from datetime import datetime

import cv2
import numpy as np

from picamera2 import Picamera2
from picamera2.devices import IMX500
from pymavlink import mavutil

from safety_manager_v2 import (
    SafetyManager,
    DroneStatus,
    FlightState,
)


# =====================================================
# CONFIGURATION - SITL ONLY
# =====================================================

MODEL_PATH = os.environ.get("IMX500_MODEL_PATH")
MAVLINK_ADDRESS = os.environ.get(
    "MAVLINK_ADDRESS",
    "udpin:0.0.0.0:14550",
)

CLASSES = [
    "dislike",
    "fist",
    "like",
    "no_gesture",
    "one",
    "palm",
    "three",
    "two_up",
]

CONFIDENCE = 0.50
MODEL_SIZE = 512

FRAME_WIDTH = 640
FRAME_HEIGHT = 480

TAKEOFF_ALTITUDE = 3.0
TAKEOFF_COMPLETE_ALTITUDE = 2.5

MAX_SPEED = 0.30
DEADZONE = 0.12
MIN_ALTITUDE = 1.5

PALM_CONFIRM = 1.0
FIST_CONFIRM = 0.5
ACTION_CONFIRM = 2.0
GESTURE_GAP = 0.25

HEARTBEAT_TIMEOUT = 2.0
ALTITUDE_TIMEOUT = 1.0

MODE_TIMEOUT = 6.0
ARM_TIMEOUT = 8.0
TAKEOFF_ACK_TIMEOUT = 8.0
TAKEOFF_CLIMB_TIMEOUT = 25.0
# SITL V5.4: tolerate only the initial GUIDED transition.
# Any later departure from GUIDED aborts the AI takeoff sequence.

RTL_MODE_TIMEOUT = 6.0

COMMAND_ACK_TIMEOUT = 5.0

VELOCITY_INTERVAL = 0.1
LOG_INTERVAL = 0.2

LOG_DIR = os.path.expanduser("~/gesture_logs")
os.makedirs(LOG_DIR, exist_ok=True)

LOG_PATH = os.path.join(
    LOG_DIR,
    datetime.now().strftime(
        "gesture_v5_4_%Y%m%d_%H%M%S.csv"
    ),
)


# =====================================================
# GLOBAL STATE
# =====================================================

safety = SafetyManager(palm_timeout=0.3)
status = DroneStatus()

# Keyboard authorization; RC5 is read independently via MAVLink.
# USB joystick is not a hardware safety switch.
sitl_permission = False

last_heartbeat = 0.0
last_altitude = 0.0

candidate = None
candidate_since = 0.0
candidate_seen = 0.0

last_palm_x = 0.0
last_palm_y = 0.0

last_velocity_send = 0.0
last_log = 0.0

takeoff_stage = None
stage_started = 0.0

rtl_stage = None
rtl_started = 0.0
rtl_confirmed = False
rtl_landed_state = None
rtl_landed_update = None
rtl_ground_reported = False

pending_command = None
pending_since = 0.0
pending_accepted = False
pending_in_progress = False

consumed_like = False
consumed_dislike = False

camera_started = False
picam2 = None
master = None

last_safety_event = None

# V5.3.2: HEARTBEAT system_status is a coarse safety signal, NOT
# a definitive RC radio-failsafe indicator. ArduPilot handles RC failsafe.
autopilot_system_status = None
AUTOPILOT_UNSAFE_STATES = {
    mavutil.mavlink.MAV_STATE_CRITICAL,
    mavutil.mavlink.MAV_STATE_EMERGENCY,
    mavutil.mavlink.MAV_STATE_FLIGHT_TERMINATION,
}


def autopilot_unsafe():
    return autopilot_system_status in AUTOPILOT_UNSAFE_STATES


def ai_commands_allowed():
    return (
        master is not None
        and status.heartbeat_ok
        and not autopilot_unsafe()
        and sitl_permission
        and rc5_permission.switch_on(time.monotonic())
        and safety.state not in (FlightState.MANUAL_OVERRIDE, FlightState.RTL_LOCKED)
    )



# =====================================================
# LOGGING
# =====================================================

log_file = open(LOG_PATH, "w", newline="")
writer = csv.writer(log_file)

writer.writerow([
    "timestamp",
    "state",
    "mode",
    "armed",
    "altitude",
    "heartbeat_ok",
    "altitude_ok",
    "gesture",
    "gesture_duration",
    "velocity_y",
    "velocity_z",
    "safety_event",
    "autopilot_system_status",
    "takeoff_stage",
    "rtl_stage",
    "pending_command",
])




# =========================================================
# V5.2 - RADIOMASTER POCKET SB / RC5
# =========================================================

RC5_ON_THRESHOLD = 1800
RC5_TIMEOUT = 1.0

# Tijekom prvog testa ne dozvoli AI polijetanje.
GROUND_TEST_ONLY = False
LOITER_CONFIRM_TIMEOUT = 6.0
loiter_requested_at = None
loiter_confirmed = False

class RC5Permission:
    def __init__(self):
        self.value = 0
        self.last_update = None
        self.off_seen = False
        self.armed_by_switch = False

    def ingest(self, msg, now):
        value = int(msg.chan5_raw)

        if not 800 <= value <= 2200:
            return

        self.value = value
        self.last_update = now

        if value <= 1200:
            self.off_seen = True
            self.armed_by_switch = False

        elif value >= RC5_ON_THRESHOLD:
            if self.off_seen:
                self.armed_by_switch = True

        else:
            self.armed_by_switch = False

    def fresh(self, now):
        return (
            self.last_update is not None
            and 0 <= now - self.last_update < RC5_TIMEOUT
        )

    def switch_on(self, now):
        return (
            self.fresh(now)
            and self.armed_by_switch
            and self.value >= RC5_ON_THRESHOLD
        )


rc5_permission = RC5Permission()

# =========================================================

def log_data(gesture, duration, vy, vz):
    writer.writerow([
        datetime.now().isoformat(),
        safety.state.name,
        status.mode,
        status.armed,
        round(status.altitude, 3),
        status.heartbeat_ok,
        status.altitude_ok,
        gesture,
        round(duration, 2),
        round(vy, 3),
        round(vz, 3),
        safety.last_event,
        autopilot_system_status,
        takeoff_stage,
        rtl_stage,
        pending_command,
    ])

    log_file.flush()


# =====================================================
# MAVLINK COMMAND HANDLING
# =====================================================

def command_name(command):
    names = {
        mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM:
            "ARM_DISARM",

        mavutil.mavlink.MAV_CMD_NAV_TAKEOFF:
            "TAKEOFF",
    }

    return names.get(command, str(command))


def clear_pending():
    global pending_command
    global pending_since
    global pending_accepted
    global pending_in_progress

    pending_command = None
    pending_since = 0.0
    pending_accepted = False
    pending_in_progress = False


def send_command(command, params):
    global pending_command
    global pending_since
    global pending_accepted
    global pending_in_progress

    if GROUND_TEST_ONLY and command in (
        mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
        mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
    ):
        print("[SAFETY] ARM/TAKEOFF blocked: GROUND_TEST_ONLY")
        return False

    if not ai_commands_allowed():
        print("[SAFETY] Command blocked: AI not authorized or autopilot unsafe")
        return False

    if pending_command is not None:
        print("[MAVLINK] Another command is pending")
        return False

    master.mav.command_long_send(
        master.target_system,
        master.target_component,
        command,
        0,
        *params
    )

    pending_command = command
    pending_since = time.monotonic()
    pending_accepted = False
    pending_in_progress = False

    print(
        "[MAVLINK] COMMAND SENT:",
        command_name(command)
    )

    return True


def request_arm():
    return send_command(
        mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
        [1, 0, 0, 0, 0, 0, 0]
    )


def request_takeoff():
    return send_command(
        mavutil.mavlink.MAV_CMD_NAV_TAKEOFF,
        [0, 0, 0, 0, 0, 0, TAKEOFF_ALTITUDE]
    )


def request_mode(mode, safety_request=False):
    if safety_request:
        # Never fight an autopilot failsafe or an existing RTL.
        if (master is None or not status.heartbeat_ok
                or autopilot_unsafe() or status.mode == "RTL"):
            print("[SAFETY] Safety mode request suppressed")
            return False
        if mode != "LOITER":
            return False
    elif mode == "RTL" and safety.state == FlightState.RTL_LOCKED:
        # The FSM intentionally locks out ordinary AI commands before RTL is sent.
        # Permit only this latched safety transition with the original authorization
        # and healthy telemetry; never reopen ordinary AI movement commands.
        if not (
            master is not None
            and status.heartbeat_ok
            and not autopilot_unsafe()
            and sitl_permission
            and rc5_permission.switch_on(time.monotonic())
            and status.armed
            and status.mode == "GUIDED"
        ):
            print("[SAFETY] RTL request blocked: authorization or flight-state check failed")
            return False
    elif not ai_commands_allowed():
        print("[SAFETY] AI mode request blocked")
        return False

    mapping = master.mode_mapping()

    if not mapping or mode not in mapping:
        print("[MAVLINK] Unsupported mode:", mode)
        return False

    master.set_mode(mapping[mode])

    print("[MAVLINK] MODE REQUEST:", mode)
    return True


def send_velocity(vy, vz, safety_stop=False):
    if safety_stop:
        if (master is None or not status.heartbeat_ok
                or autopilot_unsafe() or status.mode != "GUIDED"
                or not status.armed):
            return False
        vy, vz = 0.0, 0.0
    elif not (ai_commands_allowed()
              and safety.state in (FlightState.HOLD, FlightState.TRACKING)
              and status.mode == "GUIDED" and status.armed):
        return False

    master.mav.set_position_target_local_ned_send(
        0,
        master.target_system,
        master.target_component,
        mavutil.mavlink.MAV_FRAME_BODY_NED,
        0x0DC7,
        0, 0, 0,
        0, float(vy), float(vz),
        0, 0, 0,
        0, 0
    )
    return True


def stop_velocity():
    if (
        master is not None
        and status.heartbeat_ok
        and status.mode == "GUIDED"
        and status.armed
    ):
        send_velocity(0.0, 0.0, safety_stop=True)


def speed(error):
    if abs(error) <= DEADZONE:
        return 0.0

    magnitude = (
        abs(error) - DEADZONE
    ) / (1.0 - DEADZONE)

    return float(
        np.sign(error)
        * min(
            MAX_SPEED,
            magnitude * MAX_SPEED
        )
    )


# =====================================================
# SAFETY HELPERS
# =====================================================

def fail_safe(reason):
    global takeoff_stage
    global rtl_stage
    global sitl_permission

    print("[SAFETY] FAILURE:", reason)

    # Best-effort stop, not a guaranteed flight failsafe.
    stop_velocity()

    safety.manual_override(reason)

    takeoff_stage = None
    rtl_stage = None
    sitl_permission = False

    clear_pending()


def process_safety_transition(previous_state, now):
    """Latch override and request LOITER once, only in SITL when armed.

    Mode requests are best-effort. LOITER requires a healthy position estimate.
    """
    global takeoff_stage, rtl_stage, sitl_permission
    global loiter_requested_at, loiter_confirmed

    if previous_state == safety.state:
        return

    if previous_state == FlightState.TRACKING:
        stop_velocity()

    if safety.state != FlightState.MANUAL_OVERRIDE:
        return

    takeoff_stage = None
    rtl_stage = None
    sitl_permission = False
    clear_pending()

    if previous_state not in (
        FlightState.TAKEOFF, FlightState.HOLD, FlightState.TRACKING
    ):
        return

    # Never override an already engaged RTL mode.
    if not status.armed or not status.heartbeat_ok or status.mode == "RTL":
        print("[OVERRIDE] No LOITER request: unarmed, stale heartbeat or RTL")
        return

    stop_velocity()
    if request_mode("LOITER", safety_request=True):
        loiter_requested_at = now
        loiter_confirmed = False
        print("[OVERRIDE] LOITER requested; awaiting HEARTBEAT confirmation")
    else:
        print("[OVERRIDE] LOITER request failed; manual intervention required")


def monitor_override_mode(now):
    global loiter_requested_at, loiter_confirmed
    if loiter_requested_at is None or loiter_confirmed:
        return
    if status.heartbeat_ok and status.mode == "LOITER":
        loiter_confirmed = True
        print("[OVERRIDE] LOITER confirmed by HEARTBEAT")
    elif now - loiter_requested_at >= LOITER_CONFIRM_TIMEOUT:
        print("[WARNING] LOITER NOT CONFIRMED; check SITL mode and take control")
        loiter_requested_at = None


# =====================================================
# TELEMETRY
# =====================================================

def process_mavlink(now):
    global last_heartbeat
    global last_altitude
    global pending_accepted
    global pending_in_progress
    global pending_since
    global autopilot_system_status
    global rtl_landed_state, rtl_landed_update

    for _ in range(100):
        msg = master.recv_match(blocking=False)

        if msg is None:
            break

        if msg.get_srcSystem() != master.target_system:
            continue

        msg_type = msg.get_type()
        if msg_type == 'RC_CHANNELS':
            rc5_permission.ingest(msg, now)


        if msg_type == "HEARTBEAT":
            if msg.get_srcComponent() not in (0, 1):
                continue

            last_heartbeat = now
            autopilot_system_status = int(msg.system_status)

            status.mode = mavutil.mode_string_v10(msg)

            status.armed = bool(
                msg.base_mode
                & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED
            )

        elif msg_type == "EXTENDED_SYS_STATE":
            rtl_landed_state = int(msg.landed_state)
            rtl_landed_update = now

        elif msg_type == "GLOBAL_POSITION_INT":
            last_altitude = now
            status.altitude = (
                msg.relative_alt / 1000.0
            )

        elif msg_type == "COMMAND_ACK":
            if pending_command != msg.command:
                continue

            result = msg.result

            print(
                "[ACK]",
                command_name(msg.command),
                "result:",
                result
            )

            if result == mavutil.mavlink.MAV_RESULT_ACCEPTED:
                pending_accepted = True
                pending_in_progress = False

            elif result == mavutil.mavlink.MAV_RESULT_IN_PROGRESS:
                pending_in_progress = True

                # Keep original timeout policy.
                # IN_PROGRESS is not completion.

            else:
                fail_safe(
                    "COMMAND_REJECTED_" + str(result)
                )
                return

    status.heartbeat_ok = (
        now - last_heartbeat < HEARTBEAT_TIMEOUT
    )

    status.altitude_ok = (
        now - last_altitude < ALTITUDE_TIMEOUT
    )

    # MAV_STATE_CRITICAL/EMERGENCY/FLIGHT_TERMINATION are coarse
    # autopilot danger indications. They do not uniquely mean RC failsafe.
    if autopilot_unsafe() and safety.state not in (
        FlightState.DISABLED, FlightState.MANUAL_OVERRIDE, FlightState.RTL_LOCKED
    ):
        fail_safe("AUTOPILOT_UNSAFE_STATE_" + str(autopilot_system_status))


# =====================================================
# TAKEOFF STATE MACHINE
# =====================================================

def update_takeoff(now):
    global takeoff_stage
    global stage_started

    if safety.state != FlightState.TAKEOFF:
        takeoff_stage = None
        return

    if takeoff_stage is None:
        return

    elapsed = now - stage_started

    # Once GUIDED was confirmed, never continue ARM/TAKEOFF if the
    # autopilot has switched modes. This also prevents an unexpected
    # transition back into GUIDED from silently resuming the sequence.
    if takeoff_stage != "WAIT_GUIDED" and status.mode != "GUIDED":
        fail_safe("TAKEOFF_GUIDED_MODE_LOST")
        return

    # During arming and climb the vehicle must remain armed once ARM
    # has been acknowledged; unexpected disarm aborts the sequence.
    if takeoff_stage in ("WAIT_TAKEOFF_ACK", "WAIT_ALTITUDE") and not status.armed:
        fail_safe("TAKEOFF_UNEXPECTED_DISARM")
        return

    if takeoff_stage == "WAIT_GUIDED":
        if status.mode == "GUIDED":
            if request_arm():
                takeoff_stage = "WAIT_ARM"
                stage_started = now
            else:
                fail_safe("ARM_REQUEST_FAILED")
                return

        elif elapsed >= MODE_TIMEOUT:
            fail_safe("GUIDED_MODE_TIMEOUT")

    elif takeoff_stage == "WAIT_ARM":

        # If armed, but the ARM ACK has not arrived yet, wait for the
        # ACK instead of treating the vehicle as ready for takeoff.
        if (
            pending_command
            == mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM
            and pending_accepted
            and status.armed
        ):
            clear_pending()

            if request_takeoff():
                takeoff_stage = "WAIT_TAKEOFF_ACK"
                stage_started = now

            else:
                fail_safe("TAKEOFF_REQUEST_FAILED")

        elif elapsed >= ARM_TIMEOUT:
            fail_safe("ARM_TIMEOUT")

    elif takeoff_stage == "WAIT_TAKEOFF_ACK":

        if (
            pending_command
            == mavutil.mavlink.MAV_CMD_NAV_TAKEOFF
            and pending_accepted
        ):
            clear_pending()

            takeoff_stage = "WAIT_ALTITUDE"
            stage_started = now

        elif elapsed >= TAKEOFF_ACK_TIMEOUT:
            fail_safe("TAKEOFF_ACK_TIMEOUT")

    elif takeoff_stage == "WAIT_ALTITUDE":

        if safety.takeoff_complete(status):
            print("[FLIGHT] TAKEOFF COMPLETE")
            takeoff_stage = None

        elif elapsed >= TAKEOFF_CLIMB_TIMEOUT:
            fail_safe("TAKEOFF_CLIMB_TIMEOUT")


# =====================================================
# RTL MONITOR
# =====================================================

def update_rtl(now):
    """Observe RTL until landing; never disarm or resume AI commands."""
    global rtl_stage, rtl_confirmed, rtl_ground_reported

    if rtl_stage is None:
        return

    if not status.heartbeat_ok:
        # Do not infer a landing from missing telemetry.
        return

    if rtl_stage == "WAIT_RTL":
        if status.mode == "RTL":
            print("[FLIGHT] RTL MODE CONFIRMED")
            rtl_confirmed = True
            rtl_stage = "MONITOR_LANDING"
        elif now - rtl_started >= RTL_MODE_TIMEOUT:
            print("[WARNING] RTL mode not confirmed; landing monitor inactive")
            rtl_stage = None
        return

    if rtl_stage != "MONITOR_LANDING" or not rtl_confirmed:
        return

    landed_fresh = (
        rtl_landed_update is not None
        and 0 <= now - rtl_landed_update < 3.0
    )
    on_ground = (
        landed_fresh
        and rtl_landed_state == mavutil.mavlink.MAV_LANDED_STATE_ON_GROUND
    )

    if on_ground and not rtl_ground_reported:
        print("[FLIGHT] GROUND CONTACT REPORTED BY AUTOPILOT")
        rtl_ground_reported = True

    if not status.armed:
        # Post-RTL DISARM is authoritative for motors, but on-ground state
        # is checked separately. Avoid claiming a safe landing if telemetry
        # is absent or reports an airborne vehicle.
        if on_ground:
            print("[FLIGHT] RTL LANDING COMPLETE: ON_GROUND + DISARMED")
        elif landed_fresh:
            print("[WARNING] RTL DISARMED, but landed state is not ON_GROUND")
        else:
            print("[WARNING] RTL DISARMED; landing state unavailable/stale")
        rtl_stage = None
        return

    if status.mode != "RTL" and not on_ground:
        print("[WARNING] RTL mode exited while airborne; check Mission Planner")
        rtl_stage = None


# =====================================================
# CAMERA / AI DETECTION
# =====================================================

def detect_gesture(frame, metadata, imx500):
    height, width = frame.shape[:2]

    outputs = imx500.get_outputs(metadata)

    detected = None
    best_conf = 0.0
    palm_center = None

    if outputs is None:
        return detected, palm_center

    boxes, scores, classes = outputs[:3]
    count = int(outputs[3][0])

    for i in range(min(count, len(boxes))):
        conf = float(scores[i])
        class_id = int(classes[i])

        if (
            conf < CONFIDENCE
            or not 0 <= class_id < len(CLASSES)
        ):
            continue

        gesture = CLASSES[class_id]

        x1, y1, x2, y2 = np.asarray(
            boxes[i], dtype=float
        )

        x1 = int(np.clip(
            x1 / MODEL_SIZE * width,
            0, width - 1
        ))

        x2 = int(np.clip(
            x2 / MODEL_SIZE * width,
            0, width - 1
        ))

        y1 = int(np.clip(
            y1 / MODEL_SIZE * height,
            0, height - 1
        ))

        y2 = int(np.clip(
            y2 / MODEL_SIZE * height,
            0, height - 1
        ))

        cv2.rectangle(
            frame,
            (x1, y1),
            (x2, y2),
            (0, 255, 0),
            2
        )

        cv2.putText(
            frame,
            f"{gesture} {conf:.2f}",
            (x1, max(20, y1 - 10)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 255, 0),
            2
        )

        if conf > best_conf:
            best_conf = conf
            detected = gesture

            if gesture == "palm":
                palm_center = (
                    (x1 + x2) // 2,
                    (y1 + y2) // 2
                )

    return detected, palm_center


# =====================================================
# MAIN
# =====================================================

try:
    if not MODEL_PATH:
        raise RuntimeError(
            "IMX500_MODEL_PATH is not set. "
            "Set it to the path of the local network.rpk model."
        )

    master = mavutil.mavlink_connection(
        MAVLINK_ADDRESS,
        source_system=250,
        source_component=191
    )

    print("Cekam ArduPilot SITL...")

    if master.wait_heartbeat(timeout=15) is None:
        raise RuntimeError("MAVLink connection timeout")

    print("MAVLink povezan")

    # Request telemetry at suitable rates.
    for message_id, frequency in [
        (mavutil.mavlink.MAVLINK_MSG_ID_HEARTBEAT, 2),
        (mavutil.mavlink.MAVLINK_MSG_ID_GLOBAL_POSITION_INT, 5),
        (mavutil.mavlink.MAVLINK_MSG_ID_RC_CHANNELS, 5),
        (mavutil.mavlink.MAVLINK_MSG_ID_EXTENDED_SYS_STATE, 2),
    ]:
        master.mav.command_long_send(
            master.target_system,
            master.target_component,
            mavutil.mavlink.MAV_CMD_SET_MESSAGE_INTERVAL,
            0,
            message_id,
            int(1_000_000 / frequency),
            0, 0, 0, 0, 0
        )

    imx500 = IMX500(MODEL_PATH)
    picam2 = Picamera2(imx500.camera_num)

    config = picam2.create_preview_configuration(
        main={
            "size": (FRAME_WIDTH, FRAME_HEIGHT),
            "format": "RGB888"
        },
        controls={"FrameRate": 15}
    )

    picam2.configure(config)
    picam2.start()
    camera_started = True

    print("Gesture Control V5.4 - SITL (ground tests)")
    print("GROUND_TEST_ONLY:", GROUND_TEST_ONLY)
    print("T = authorize")
    print("X = disable AI")
    print("R = reset")
    print("Q = quit")
    print("CSV:", LOG_PATH)

    while True:
        now = time.monotonic()

        # ----------------------------------
        # TELEMETRY
        # ----------------------------------

        previous_state = safety.state
        process_mavlink(now)

        status.rc_enabled = (
            bool(sitl_permission)
            and rc5_permission.switch_on(now)
        )

        # Pending command timeout
        if (
            pending_command is not None
            and now - pending_since > COMMAND_ACK_TIMEOUT
            and not pending_accepted
        ):
            fail_safe("COMMAND_ACK_TIMEOUT")

        # ----------------------------------
        # CAMERA
        # ----------------------------------

        with picam2.captured_request() as request:
            frame = request.make_array("main")
            metadata = request.get_metadata()

        height, width = frame.shape[:2]

        detected, palm_center = detect_gesture(
            frame,
            metadata,
            imx500
        )

        # ----------------------------------
        # GESTURE FILTER
        # ----------------------------------

        if detected is not None:
            if (
                detected != candidate
                or now - candidate_seen > GESTURE_GAP
            ):
                candidate = detected
                candidate_since = now

            candidate_seen = now

        elif now - candidate_seen > GESTURE_GAP:
            candidate = None

        duration = (
            now - candidate_since
            if candidate is not None
            else 0.0
        )

        if candidate != "like":
            consumed_like = False

        if candidate != "dislike":
            consumed_dislike = False

        status.palm_visible = (
            detected == "palm"
            and palm_center is not None
        )

        if status.palm_visible:
            last_palm_x = (
                palm_center[0] - width / 2
            ) / (width / 2)

            last_palm_y = (
                palm_center[1] - height / 2
            ) / (height / 2)

            cv2.circle(
                frame,
                palm_center,
                6,
                (0, 0, 255),
                -1
            )

        # ----------------------------------
        # SAFETY
        # ----------------------------------

        safety.update(status, now)

        process_safety_transition(previous_state, now)
        monitor_override_mode(now)

        # ----------------------------------
        # TAKEOFF REQUEST
        # ----------------------------------

        if (
            safety.state == FlightState.READY
            and candidate == "like"
            and duration >= ACTION_CONFIRM
            and not consumed_like
        ):
            consumed_like = True

            if (not GROUND_TEST_ONLY and safety.begin_takeoff(status)):
                takeoff_stage = "WAIT_GUIDED"
                stage_started = now

                if not request_mode("GUIDED"):
                    fail_safe("GUIDED_REQUEST_FAILED")

        # ----------------------------------
        # TAKEOFF PROGRESS
        # ----------------------------------

        state_before_takeoff_update = safety.state
        update_takeoff(now)
        process_safety_transition(state_before_takeoff_update, now)

        # ----------------------------------
        # TRACKING / FIST / RTL
        # ----------------------------------

        if safety.state in (
            FlightState.HOLD,
            FlightState.TRACKING
        ):

            if (
                candidate == "fist"
                and duration >= FIST_CONFIRM
            ):
                safety.stop_tracking()

            elif (
                candidate == "palm"
                and duration >= PALM_CONFIRM
                and status.palm_visible
                and safety.state == FlightState.HOLD
            ):
                safety.start_tracking(status)

            elif (
                candidate == "dislike"
                and duration >= ACTION_CONFIRM
                and not consumed_dislike
            ):
                consumed_dislike = True

                if safety.request_rtl(status):
                    stop_velocity()

                    rtl_stage = "WAIT_RTL"
                    rtl_started = now
                    rtl_confirmed = False
                    rtl_landed_state = None
                    rtl_landed_update = None
                    rtl_ground_reported = False

                    if not request_mode("RTL"):
                        print(
                            "[WARNING] RTL request failed"
                        )

        # ----------------------------------
        # RTL MONITOR
        # ----------------------------------

        update_rtl(now)

        # ----------------------------------
        # VELOCITY CONTROL
        # HOLD currently sends zero velocity in GUIDED; this is NOT
        # an independently verified position-hold guarantee.
        # ----------------------------------

        vy = 0.0
        vz = 0.0

        control_ok = (
            safety.state == FlightState.TRACKING
            and safety.can_track(status)
            and status.palm_visible
        )

        if control_ok:
            vy = speed(last_palm_x)
            vz = speed(last_palm_y)

            if (
                vz > 0
                and status.altitude <= MIN_ALTITUDE
            ):
                vz = 0.0

        if now - last_velocity_send >= VELOCITY_INTERVAL:

            if (
                safety.state in (
                    FlightState.HOLD,
                    FlightState.TRACKING
                )
                and safety.can_track(status)
            ):
                send_velocity(vy, vz)

            last_velocity_send = now

        # ----------------------------------
        # LOG
        # ----------------------------------

        if now - last_log >= LOG_INTERVAL:
            log_data(
                detected,
                duration,
                vy,
                vz
            )
            last_log = now

        # ----------------------------------
        # DISPLAY
        # ----------------------------------

        cv2.putText(
            frame,
            f"STATE: {safety.state.name}",
            (15, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 255, 255),
            2
        )

        cv2.putText(
            frame,
            f"MODE: {status.mode} ALT: {status.altitude:.2f}m",
            (15, 60),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            2
        )

        cv2.putText(
            frame,
            f"GESTURE: {detected or 'none'} {duration:.1f}s",
            (15, 90),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            2
        )

        cv2.putText(
            frame,
            f"Vy:{vy:+.2f} Vz:{vz:+.2f}",
            (15, 120),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (255, 255, 255),
            2
        )

        cv2.putText(
            frame,
            f"SAFETY: {safety.last_event}",
            (15, 150),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 255),
            1
        )

        cv2.putText(
            frame,
            f"TAKEOFF: {takeoff_stage or '-'}",
            (15, 180),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (255, 255, 255),
            1
        )

        cv2.putText(
            frame,
            f"RC5:{rc5_permission.value} "
            f"FRESH:{rc5_permission.fresh(now)} "
            f"SB:{'ON' if rc5_permission.switch_on(now) else 'OFF'}",
            (15, 210), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
            (0, 255, 0) if rc5_permission.switch_on(now) else (0, 0, 255), 1
        )
        cv2.imshow(
            "Gesture Control V5.4 - SITL",
            frame
        )

        key = cv2.waitKey(1) & 0xFF

        if key == ord("q"):
            break

        elif key == ord('t'):
            if autopilot_unsafe():
                print('[SAFETY] Authorization blocked: autopilot unsafe')
                continue
            if not rc5_permission.switch_on(now):
                print('[RC5] SB mora biti ON (2000)')
                continue
            sitl_permission = True
            status.rc_enabled = rc5_permission.switch_on(now)
            print(
    "[DEBUG AUTH]",
    "state=", safety.state.name,
    "armed=", status.armed,
    "altitude=", status.altitude,
    "heartbeat_ok=", status.heartbeat_ok,
    "altitude_ok=", status.altitude_ok,
    "mode=", status.mode,
    "rc_enabled=", status.rc_enabled
)

            if safety.authorize(status):
                print("[SITL] AUTHORIZED")
            else:
                print("[SITL] AUTHORIZATION DENIED")
                sitl_permission = False

        elif key == ord("x"):
            state_before_key = safety.state
            stop_velocity()

            sitl_permission = False
            status.rc_enabled = False

            safety.manual_override(
                "USER_DISABLED"
            )

            takeoff_stage = None

            process_safety_transition(state_before_key, now)
            print("[SITL] AI DISABLED")

        elif key == ord("r"):
            if safety.reset(status):
                sitl_permission = False
                print("[SITL] RESET COMPLETE")
            else:
                print("[SITL] RESET DENIED")

except KeyboardInterrupt:
    print("\nKeyboard interrupt")

finally:
    print("Stopping Gesture Control V5.4")

    try:
        stop_velocity()
    except Exception as error:
        print("Stop error:", error)

    if camera_started and picam2 is not None:
        picam2.stop()

    cv2.destroyAllWindows()

    log_file.close()

    if master is not None:
        master.close()

    print("CSV:", LOG_PATH)
