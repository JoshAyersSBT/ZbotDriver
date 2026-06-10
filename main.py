import time
import uasyncio as asyncio
from machine import I2C, Pin

PREACTIVE_BLE = None

import robot.config as robot_config

from robot.motors import Motor
from robot.servo import Servo
from robot.debug_io import (
    info,
    warn,
    error,
    diag,
    state,
    set_ble_sink,
)

SAFE_MODE_PIN = 0
BOOT_GRACE_SECONDS = 3
DEFAULT_STEER_CENTER_DEG = 90
DEFAULT_STEER_RANGE_DEG = 45
COLOR_CALIBRATION_DEFAULT_SAMPLES = 8
COLOR_CALIBRATION_DEFAULT_DELAY_MS = 40
COLOR_CALIBRATION_MAX_SAMPLES = 30
COLOR_CALIBRATION_MAX_DISTANCE = 180
COLOR_BLACK_TOTAL_MAX = 100
COLOR_BLACK_CLEAR_MAX = 120

API = None
zbot = None
_BOOT_SPINNER_FRAMES = ("|", "/", "-", "\\")
_boot_spinner_index = 0


def _cfg(name, default=None):
    return getattr(robot_config, name, default)


LEFT_PWM = _cfg("LEFT_PWM")
LEFT_DIR = _cfg("LEFT_DIR")
LEFT_ENC = _cfg("LEFT_ENC")

RIGHT_PWM = _cfg("RIGHT_PWM")
RIGHT_DIR = _cfg("RIGHT_DIR")
RIGHT_ENC = _cfg("RIGHT_ENC")

MOTOR_PWM_FREQ_HZ = _cfg("MOTOR_PWM_FREQ_HZ", 20000)
MOTOR_MAX_DUTY_U16 = _cfg("MOTOR_MAX_DUTY_U16", 40000)
MOTOR_INVERT_PWM = _cfg("MOTOR_INVERT_PWM", False)

STEER_SERVO_GPIO = _cfg("STEER_SERVO_GPIO", 18)
SERVO_FREQ_HZ = _cfg("SERVO_FREQ_HZ", 50)
SERVO_MIN_US = _cfg("SERVO_MIN_US", 500)
SERVO_MAX_US = _cfg("SERVO_MAX_US", 2500)
SERVO_CENTER_DEG = _cfg("SERVO_CENTER_DEG", 90)

TCA_I2C_ID = _cfg("TCA_I2C_ID", 0)
TCA_SDA_GPIO = _cfg("TCA_SDA_GPIO", 21)
TCA_SCL_GPIO = _cfg("TCA_SCL_GPIO", 22)
TCA_I2C_FREQ = _cfg("TCA_I2C_FREQ", 400000)
TCA_ADDR = _cfg("TCA_ADDR", 0x70)

MPU_ADDR = _cfg("MPU_ADDR", 0x68)
MPU_CHANNEL = _cfg("MPU_CHANNEL", 7)
MPU_PERIOD_MS = _cfg("MPU_PERIOD_MS", 10)
TURN_RADIUS_DEFAULT_SPEED_MPS = _cfg("TURN_RADIUS_DEFAULT_SPEED_MPS", 0.4)
TURN_RADIUS_DEFAULT_DRIVE_POWER = _cfg("TURN_RADIUS_DEFAULT_DRIVE_POWER", 40)
TURN_RADIUS_DEFAULT_TURN = _cfg("TURN_RADIUS_DEFAULT_TURN", 35)
TURN_RADIUS_MIN_YAW_DPS = _cfg("TURN_RADIUS_MIN_YAW_DPS", 2.0)
BLE_ENABLED = _cfg("BLE_ENABLED", True)

OLED_ADDR = _cfg("OLED_ADDR", 0x3C)
OLED_CHANNEL = _cfg("OLED_CHANNEL", 0)
OLED_WIDTH = _cfg("OLED_WIDTH", 128)
OLED_HEIGHT = _cfg("OLED_HEIGHT", 64)
OLED_STATUS_ENABLED = _cfg("OLED_STATUS_ENABLED", True)

SENSOR_SCAN_PERIOD_MS = _cfg("SENSOR_SCAN_PERIOD_MS", 100)
SENSOR_PORT_MODES = _cfg("SENSOR_PORT_MODES", {})
SENSOR_PORT_CHANNELS = _cfg("SENSOR_PORT_CHANNELS", {})

MOTOR_PORT_MAP = _cfg("MOTOR_PORT_MAP", {})
ACTIVE_MOTOR_PORTS = _cfg("ACTIVE_MOTOR_PORTS", tuple(sorted(MOTOR_PORT_MAP.keys())))
DRIVE_MOTOR_PORTS = _cfg("DRIVE_MOTOR_PORTS", ACTIVE_MOTOR_PORTS)

MOTOR_SCAN_POWER = _cfg("MOTOR_SCAN_POWER", 25)
MOTOR_SCAN_PULSE_MS = _cfg("MOTOR_SCAN_PULSE_MS", 250)
MOTOR_SCAN_PERIOD_MS = _cfg("MOTOR_SCAN_PERIOD_MS", 1500)
MOTOR_FEEDBACK_PERIOD_MS = _cfg("MOTOR_FEEDBACK_PERIOD_MS", 200)
MOTOR_FEEDBACK_ENABLED = _cfg("MOTOR_FEEDBACK_ENABLED", True)

BUTTON_MAP = _cfg("BUTTON_MAP", {
    1: {"name": "B1", "gpio": 15, "pull": "down", "active_low": False},
    2: {"name": "B2", "gpio": 12, "pull": "down", "active_low": False},
})
BUTTON_DEBOUNCE_MS = _cfg("BUTTON_DEBOUNCE_MS", 35)
BUTTON_SCAN_PERIOD_MS = _cfg("BUTTON_SCAN_PERIOD_MS", 10)
BUTTON_DEFAULT_PULL = _cfg("BUTTON_DEFAULT_PULL", "down")
BUTTON_DEFAULT_ACTIVE_LOW = _cfg("BUTTON_DEFAULT_ACTIVE_LOW", False)

# Optional future-facing config. Falls back cleanly to the legacy dedicated steer servo.
SERVO_PORT_MAP = _cfg("SERVO_PORT_MAP", None)
STEER_SERVO_PORT = _cfg("STEER_SERVO_PORT", 4)


def _build_default_servo_port_map():
    return {
        int(STEER_SERVO_PORT): {
            "name": "STEER",
            "gpio": int(STEER_SERVO_GPIO),
            "freq_hz": int(SERVO_FREQ_HZ),
            "min_us": int(SERVO_MIN_US),
            "max_us": int(SERVO_MAX_US),
            "center_deg": int(SERVO_CENTER_DEG),
            "role": "steering",
        }
    }


if SERVO_PORT_MAP is None:
    SERVO_PORT_MAP = _build_default_servo_port_map()


def _clamp(x, lo, hi):
    return lo if x < lo else hi if x > hi else x


def _normalized_rgb(rgb):
    r = int(rgb.get("r", 0))
    g = int(rgb.get("g", 0))
    b = int(rgb.get("b", 0))
    total = r + g + b
    if total <= 0:
        return {"r": 0, "g": 0, "b": 0}
    return {
        "r": int(r * 255 / total),
        "g": int(g * 255 / total),
        "b": int(b * 255 / total),
    }


def _color_distance(a, b):
    return (
        abs(int(a.get("r", 0)) - int(b.get("r", 0))) +
        abs(int(a.get("g", 0)) - int(b.get("g", 0))) +
        abs(int(a.get("b", 0)) - int(b.get("b", 0)))
    )


def _relative_channel_distance(a, b):
    a = int(a)
    b = int(b)
    scale = max(abs(a), abs(b), 1)
    return int(abs(a - b) * 255 / scale)


def _raw_rgb_total(rgb):
    return int(rgb.get("r", 0)) + int(rgb.get("g", 0)) + int(rgb.get("b", 0))


class RuntimeDriveBridge:
    """
    Generic boot/runtime drive bridge used by BLE teleop and legacy calls.

    This intentionally does not define the student's drive model.
    It only provides a minimal motion bridge so:
      - BLE teleop can command the robot
      - legacy helpers still have a neutral fallback

    Semantics:
      throttle: -100..100
      turn:     -100..100

    Behavior:
      - all propulsion motors receive the same signed throttle
      - steering servo is mapped around center using turn
    """
    def __init__(self, api, propulsion_ports=None, steer_center_deg=DEFAULT_STEER_CENTER_DEG, steer_range_deg=DEFAULT_STEER_RANGE_DEG):
        self.api = api
        ports = propulsion_ports if propulsion_ports is not None else ACTIVE_MOTOR_PORTS
        self.propulsion_ports = tuple(int(p) for p in ports)
        self.steer_center_deg = int(steer_center_deg)
        self.steer_range_deg = int(steer_range_deg)

    def drive(self, throttle: int, turn: int):
        throttle = _clamp(int(throttle), -100, 100)
        turn = _clamp(int(turn), -100, 100)

        for port in self.propulsion_ports:
            try:
                self.api.set_motor(port, throttle)
            except Exception as e:
                error("RUNTIME_DRIVE_PORT_{}".format(port), e)

        steer_angle = self.steer_center_deg + ((turn * self.steer_range_deg) // 100)
        try:
            self.api.set_steering(steer_angle)
        except Exception as e:
            error("RUNTIME_DRIVE_STEER", e)

    def stop(self):
        try:
            self.api.stop_all()
        except Exception as e:
            error("RUNTIME_DRIVE_STOP_ALL", e)


class RobotAPI:
    """
    Shared low-level runtime API exposed to user programs and internal services.

    This API intentionally avoids hard-coding a student-facing drive model.
    User code should compose motion behavior in robot modules such as:
      - robot.ackermann
      - robot.differential
    """

    def __init__(self):
        self.status = {
            "boot": {"state": "init", "safe_mode": False},
            "system": {"heartbeat": 0, "ready": False},
            "motors": {},
            "servos": {},
            "steering": {},
            "imu": {},
            "turn_radius": {
                "active": False,
                "status": "idle",
                "radius_m": None,
            },
            "sensors": {},
            "buttons": {},
            "services": {},
            "user": {
                "running": False,
                "last_error": None,
                "kind": None,
                "module": None,
                "file": None,
            },
        }
        self.handles = {}
        self.tasks = {}
        self.color_calibrations = {}
        self._oled_user_hold_until = 0

    def register_handle(self, name, value):
        self.handles[name] = value
        return value

    def get_handle(self, name, default=None):
        return self.handles.get(name, default)

    def register_task(self, name, task):
        self.tasks[name] = task
        return task

    def set_ready(self, ready=True):
        self.status["system"]["ready"] = bool(ready)

    def get_status(self):
        return self.status

    def get_services(self):
        return self.status.get("services", {})

    def get_button_status(self):
        return self.status.get("buttons", {})

    def get_button_snapshot(self):
        return self.status.get("buttons", {})

    def button(self, button_id=1):
        manager = self.handles.get("button_manager")
        if manager is None:
            return _ZBotButton(None, button_id)
        return _ZBotButton(self, button_id)

    def mark_user_display(self, hold_ms=2500):
        try:
            self._oled_user_hold_until = time.ticks_add(time.ticks_ms(), int(hold_ms))
        except Exception:
            self._oled_user_hold_until = 0

    def user_display_active(self):
        try:
            return time.ticks_diff(self._oled_user_hold_until, time.ticks_ms()) > 0
        except Exception:
            return False

    def list_motor_ports(self):
        return sorted(self.handles.get("motors", {}).keys())

    def get_motor_ports(self):
        return self.list_motor_ports()

    def get_motor_map(self):
        return self.handles.get("motor_port_map", {})

    def get_motor_status(self):
        return self.status.get("motors", {})

    def get_motor_feedback(self):
        return self.status.get("motor_feedback", {})

    def get_servo_ports(self):
        return sorted(self.handles.get("servos", {}).keys())

    def get_servo_map(self):
        return self.handles.get("servo_port_map", {})

    def get_servo_status(self):
        return self.status.get("servos", {})

    def _power_to_duty(self, power):
        mag = abs(int(power))
        if mag > 100:
            mag = 100
        return (mag * MOTOR_MAX_DUTY_U16) // 100

    def _ensure_motor(self, port):
        port = int(port)
        motors = self.handles.get("motors", {})
        motor = motors.get(port)
        if motor is not None:
            return motor

        cfg = self.get_motor_map().get(port)
        if cfg is None:
            raise ValueError("unknown motor port {}".format(port))

        servos = self.handles.get("servos", {})
        servo = servos.pop(port, None)
        if servo is not None:
            try:
                if hasattr(servo, "deinit"):
                    servo.deinit()
            except Exception as e:
                error("MOTOR_PORT_SERVO_DEINIT_{}".format(port), e)

        motor = Motor(
            cfg["pwm"],
            cfg["dir"],
            pwm_freq_hz=MOTOR_PWM_FREQ_HZ,
            invert_pwm=bool(cfg.get("invert_pwm", MOTOR_INVERT_PWM)),
        )
        motors[port] = motor
        self.status["motors"][port] = {
            "power": 0,
            "duty_u16": 0,
            "ts_ms": time.ticks_ms(),
            "name": cfg.get("name", "M{}".format(port)),
            "mode": "motor",
        }
        diag(
            "MOTOR_PORT {} {} pwm={} dir={} enc={} mode=motor".format(
                port,
                cfg.get("name", "M{}".format(port)),
                cfg.get("pwm"),
                cfg.get("dir"),
                cfg.get("enc"),
            )
        )
        return motor

    def set_motor(self, port, power):
        port = int(port)
        motor = self._ensure_motor(port)

        power = int(power)

        if hasattr(motor, "set_power"):
            motor.set_power(power)
        else:
            if power == 0:
                if hasattr(motor, "stop"):
                    motor.stop()
                else:
                    motor.set(True, 0)
            else:
                forward = power > 0
                duty_u16 = self._power_to_duty(power)
                motor.set(forward, duty_u16)

        self.status["motors"][port] = {
            "power": power,
            "duty_u16": self._power_to_duty(power),
            "ts_ms": time.ticks_ms(),
            "name": self.get_motor_map().get(port, {}).get("name", "M{}".format(port)),
            "mode": "motor",
        }
        return self.status["motors"][port]

    def stop_motor(self, port):
        motors = self.handles.get("motors", {})
        port = int(port)
        motor = motors.get(port)
        if motor is None:
            if port in self.get_servo_map():
                return self.status["motors"].get(port, {
                    "power": 0,
                    "duty_u16": 0,
                    "ts_ms": time.ticks_ms(),
                    "name": self.get_motor_map().get(port, {}).get("name", "M{}".format(port)),
                    "mode": "servo",
                })
            raise ValueError("unknown motor port {}".format(port))

        if hasattr(motor, "stop"):
            motor.stop()
        else:
            motor.set(True, 0)

        self.status["motors"][port] = {
            "power": 0,
            "duty_u16": 0,
            "ts_ms": time.ticks_ms(),
            "name": self.get_motor_map().get(port, {}).get("name", "M{}".format(port)),
            "mode": "motor",
        }
        return self.status["motors"][port]

    def stop_all(self):
        motors = self.handles.get("motors", {})
        for port in tuple(motors.keys()):
            try:
                self.stop_motor(port)
            except Exception as e:
                error("STOP_MOTOR_{}".format(port), e)

    def _ensure_servo(self, port):
        port = int(port)
        servos = self.handles.get("servos", {})
        servo = servos.get(port)
        if servo is not None:
            return servo

        cfg = self.get_servo_map().get(port)
        if cfg is None:
            raise ValueError("unknown servo port {}".format(port))

        motors = self.handles.get("motors", {})
        motor = motors.pop(port, None)
        if motor is not None:
            try:
                if hasattr(motor, "stop"):
                    motor.stop()
            except Exception as e:
                error("SERVO_PORT_STOP_{}".format(port), e)
            try:
                if hasattr(motor, "deinit"):
                    motor.deinit()
            except Exception as e:
                error("SERVO_PORT_DEINIT_{}".format(port), e)
            self.status["motors"][port] = {
                "power": 0,
                "duty_u16": 0,
                "ts_ms": time.ticks_ms(),
                "name": self.get_motor_map().get(port, {}).get("name", "M{}".format(port)),
                "mode": "servo",
            }

        servo = Servo(
            int(cfg.get("gpio", STEER_SERVO_GPIO)),
            freq_hz=int(cfg.get("freq_hz", SERVO_FREQ_HZ)),
            min_us=int(cfg.get("min_us", SERVO_MIN_US)),
            max_us=int(cfg.get("max_us", SERVO_MAX_US)),
        )
        servos[port] = servo
        self.status["servos"][port] = {
            "angle": None,
            "ts_ms": time.ticks_ms(),
            "name": cfg.get("name", "S{}".format(port)),
            "mode": "servo",
        }
        diag(
            "SERVO_PORT {} {} gpio={} freq={} min_us={} max_us={}".format(
                port,
                cfg.get("name", "S{}".format(port)),
                cfg.get("gpio", STEER_SERVO_GPIO),
                cfg.get("freq_hz", SERVO_FREQ_HZ),
                cfg.get("min_us", SERVO_MIN_US),
                cfg.get("max_us", SERVO_MAX_US),
            )
        )
        return servo

    def set_servo(self, port, angle):
        port = int(port)
        servo = self._ensure_servo(port)

        angle = int(angle)

        if hasattr(servo, "write_angle"):
            servo.write_angle(angle)
        elif hasattr(servo, "angle"):
            servo.angle(angle)
        else:
            raise AttributeError("servo object has no write_angle/angle")

        cfg = self.get_servo_map().get(port, {})
        item = {
            "angle": angle,
            "ts_ms": time.ticks_ms(),
            "name": cfg.get("name", "S{}".format(port)),
            "mode": "servo",
        }
        self.status["servos"][port] = item
        return item

    def center_servo(self, port):
        cfg = self.get_servo_map().get(int(port), {})
        center_deg = int(cfg.get("center_deg", 90))
        return self.set_servo(int(port), center_deg)

    def set_steering(self, angle):
        steer = self.handles.get("steer")
        if steer is None:
            steer_port = int(self.handles.get("steer_port", STEER_SERVO_PORT))
            steer = self._ensure_servo(steer_port)
            self.register_handle("steer", steer)
            self.register_handle("steer_port", steer_port)

        angle = int(angle)
        if hasattr(steer, "write_angle"):
            steer.write_angle(angle)
        elif hasattr(steer, "angle"):
            steer.angle(angle)
        else:
            raise AttributeError("steering object has no write_angle/angle")

        self.status["steering"] = {
            "angle": angle,
            "ts_ms": time.ticks_ms(),
        }

        steer_port = self.handles.get("steer_port", None)
        if steer_port is not None:
            try:
                self.status["servos"][int(steer_port)] = {
                    "angle": angle,
                    "ts_ms": time.ticks_ms(),
                    "name": self.get_servo_map().get(int(steer_port), {}).get("name", "STEER"),
                }
            except Exception:
                pass

        return self.status["steering"]

    def publish_sensor(self, name, value, meta=None):
        item = {
            "value": value,
            "ts_ms": time.ticks_ms(),
        }
        if meta is not None:
            item["meta"] = meta
        self.status["sensors"][name] = item
        return item

    def get_sensor(self, name, default=None):
        return self.status.get("sensors", {}).get(name, default)

    def get_sensor_snapshot(self):
        return self.status.get("sensors", {})

    def get_color_calibrations(self, port=None):
        if port is None:
            return self.color_calibrations
        return self.color_calibrations.get(int(port), {})

    def set_color_calibration(self, port, name, rgb, samples=1):
        port = int(port)
        label = str(name).strip().lower()
        if not label:
            raise ValueError("color name required")
        if rgb is None:
            raise ValueError("rgb sample required")

        raw = {
            "r": int(rgb.get("r", 0)),
            "g": int(rgb.get("g", 0)),
            "b": int(rgb.get("b", 0)),
            "clear": int(rgb.get("clear", 0)),
        }
        normalized = _normalized_rgb(raw)
        item = {
            "name": label,
            "rgb": raw,
            "normalized": normalized,
            "total": _raw_rgb_total(raw),
            "clear": int(raw.get("clear", 0)),
            "samples": int(samples),
            "ts_ms": time.ticks_ms(),
        }
        self.color_calibrations.setdefault(port, {})[label] = item
        return item

    def clear_color_calibration(self, port=None, name=None):
        if port is None:
            self.color_calibrations = {}
            return True

        port = int(port)
        if name is None:
            self.color_calibrations.pop(port, None)
            return True

        labels = self.color_calibrations.get(port, {})
        labels.pop(str(name).strip().lower(), None)
        if not labels:
            self.color_calibrations.pop(port, None)
        return True

    def match_calibrated_color(self, port, rgb):
        labels = self.color_calibrations.get(int(port), {})
        if not labels or rgb is None:
            return None

        sample = _normalized_rgb(rgb)
        best = None
        best_distance = None
        for item in labels.values():
            chroma_distance = _color_distance(sample, item.get("normalized", {}))
            total_distance = _relative_channel_distance(
                _raw_rgb_total(rgb),
                item.get("total", _raw_rgb_total(item.get("rgb", {}))),
            )
            clear_distance = _relative_channel_distance(
                rgb.get("clear", 0),
                item.get("clear", item.get("rgb", {}).get("clear", 0)),
            )
            distance = chroma_distance + total_distance + clear_distance
            if best_distance is None or distance < best_distance:
                best = item
                best_distance = distance

        if best is None:
            return None

        best_name = best.get("name")
        if (
            best_name == "black"
            and (
                _raw_rgb_total(rgb) < COLOR_BLACK_TOTAL_MAX
                or int(rgb.get("clear", 0)) < COLOR_BLACK_CLEAR_MAX
            )
        ):
            best_distance = min(best_distance, 0)
        elif best_distance > COLOR_CALIBRATION_MAX_DISTANCE:
            return None

        confidence = max(0, 100 - int(best_distance * 100 / COLOR_CALIBRATION_MAX_DISTANCE))
        return {
            "color": best_name,
            "confidence": confidence,
            "rgb": {
                "r": int(rgb.get("r", 0)),
                "g": int(rgb.get("g", 0)),
                "b": int(rgb.get("b", 0)),
                "clear": int(rgb.get("clear", 0)),
            },
            "normalized": sample,
            "calibrated": True,
            "distance": int(best_distance),
            "reference": best,
        }

    def get_imu(self):
        if self.handles.get("imu") is not None:
            self.refresh_imu_snapshot()
        return self.status.get("imu", {})

    def _turn_radius_state(self):
        state = self.status.get("turn_radius")
        if not isinstance(state, dict):
            state = {
                "active": False,
                "status": "idle",
                "radius_m": None,
            }
            self.status["turn_radius"] = state
        return state

    def _update_turn_radius(self, reading, ts_ms=None):
        state = self._turn_radius_state()
        if not state.get("active"):
            return state

        if ts_ms is None:
            ts_ms = time.ticks_ms()

        speed_mps = state.get("speed_mps")
        min_yaw_dps = float(state.get("min_yaw_dps", TURN_RADIUS_MIN_YAW_DPS))
        gz = None

        if isinstance(reading, dict):
            for key in ("gz_dps", "gyro_z_dps", "gz", "gyro_z"):
                value = reading.get(key)
                if isinstance(value, (int, float)):
                    gz = float(value)
                    break

        if not isinstance(speed_mps, (int, float)):
            state.update({
                "status": "missing_speed",
                "radius_m": None,
                "yaw_rate_dps": gz,
                "yaw_rate_rad_s": None,
                "ts_ms": ts_ms,
            })
            return state

        if gz is None:
            state.update({
                "status": "missing_imu",
                "radius_m": None,
                "yaw_rate_dps": None,
                "yaw_rate_rad_s": None,
                "ts_ms": ts_ms,
            })
            return state

        if -min_yaw_dps < gz < min_yaw_dps:
            state.update({
                "status": "waiting",
                "radius_m": None,
                "yaw_rate_dps": gz,
                "yaw_rate_rad_s": 0.0,
                "ts_ms": ts_ms,
            })
            return state

        yaw_rate_rad_s = abs(gz) * 0.017453292519943295
        radius_m = abs(float(speed_mps)) / yaw_rate_rad_s
        state.update({
            "status": "ok",
            "radius_m": radius_m,
            "diameter_m": radius_m * 2,
            "speed_mps": float(speed_mps),
            "yaw_rate_dps": gz,
            "yaw_rate_rad_s": yaw_rate_rad_s,
            "turn_direction": "positive_z" if gz > 0 else "negative_z",
            "ts_ms": ts_ms,
        })
        return state

    def start_turn(self, speed_mps=TURN_RADIUS_DEFAULT_SPEED_MPS, drive_power=TURN_RADIUS_DEFAULT_DRIVE_POWER, turn=TURN_RADIUS_DEFAULT_TURN, min_yaw_dps=TURN_RADIUS_MIN_YAW_DPS):
        state = self._turn_radius_state()
        state.update({
            "active": True,
            "status": "waiting",
            "speed_mps": float(speed_mps),
            "drive_power": int(drive_power),
            "turn": int(turn),
            "min_yaw_dps": float(min_yaw_dps),
            "radius_m": None,
            "ts_ms": time.ticks_ms(),
        })
        self.drive(int(drive_power), int(turn))
        self.refresh_imu_snapshot()
        return state

    def stop_turn(self, stop_drive=True):
        state = self._turn_radius_state()
        state.update({
            "active": False,
            "status": "idle",
            "ts_ms": time.ticks_ms(),
        })
        if stop_drive:
            self.stop()
        return state

    def get_turn_radius(self):
        if self._turn_radius_state().get("active"):
            self.refresh_imu_snapshot()
        return self._turn_radius_state()

    def refresh_imu_snapshot(self):
        imu = self.handles.get("imu")
        if imu is None:
            return None

        try:
            if hasattr(imu, "read_scaled"):
                reading = imu.read_scaled()
            elif hasattr(imu, "read"):
                reading = imu.read()
            else:
                raise AttributeError("imu object has no read_scaled/read")

            ts_ms = time.ticks_ms()
            turn_radius = self._update_turn_radius(reading, ts_ms)
            self.status["imu"] = {
                "value": reading,
                "ts_ms": ts_ms,
                "turn_radius": turn_radius,
            }
            return self.status["imu"]
        except Exception as e:
            self.status["imu"] = {
                "error": repr(e),
                "ts_ms": time.ticks_ms(),
            }
            return None

    def notify(self, msg):
        teleop = self.handles.get("teleop")
        if teleop is not None:
            try:
                teleop.notify_line(msg)
                return True
            except Exception as e:
                error("API_NOTIFY", e)
        return False

    def show_lines(self, *lines):
        oled = self.handles.get("oled")
        if oled is None:
            return False
        try:
            self.mark_user_display(hold_ms=5000)
            oled.show_lines(*lines)
            return True
        except Exception as e:
            error("API_OLED", e)
            return False

    # Compatibility shims so old student code fails less harshly.
    def drive(self, throttle, turn=0):
        bridge = self.handles.get("runtime_drive")
        if bridge is None:
            raise RuntimeError("runtime drive bridge unavailable")
        bridge.drive(int(throttle), int(turn))

    def stop(self):
        self.stop_all()

    def display(self, line1="", line2="", line3="", line4=""):
        lines = [str(x) for x in (line1, line2, line3, line4) if str(x) != ""]
        return self.show_lines(*lines)

    def sensor(self, port):
        return _ZBotSensor(self, port)

    def motor(self, port, motor_type="DC"):
        return _ZBotMotor(self, port, motor_type)

    def servo(self, port=1):
        return _ZBotServo(self, port)


class _ZBotButton:
    def __init__(self, api, button_id=1):
        self.api = api
        self.button_id = int(button_id)

    def _button(self):
        if self.api is None:
            return None
        manager = self.api.get_handle("button_manager")
        if manager is None:
            return None
        return manager.button(self.button_id)

    def read(self):
        button = self._button()
        return False if button is None else button.read()

    def value(self):
        button = self._button()
        return 0 if button is None else button.value()

    def pressed(self):
        button = self._button()
        return False if button is None else button.pressed()

    def released(self):
        button = self._button()
        return True if button is None else button.released()

    def was_pressed(self):
        button = self._button()
        return False if button is None else button.was_pressed()

    def was_released(self):
        button = self._button()
        return False if button is None else button.was_released()

    def presses(self, reset=False):
        button = self._button()
        return 0 if button is None else button.presses(reset=reset)

    def releases(self, reset=False):
        button = self._button()
        return 0 if button is None else button.releases(reset=reset)

    def snapshot(self):
        button = self._button()
        if button is None:
            return {"id": self.button_id, "available": False, "pressed": False}
        return button.snapshot()


class _ZBotSensor:
    def __init__(self, api, port):
        self.api = api
        self.port = int(port)

    def _find_snapshot_value(self):
        if self.api is None:
            return None

        sensors = self.api.get_sensor_snapshot()

        key = "tof_port_{}".format(self.port)
        item = sensors.get(key)
        if isinstance(item, dict):
            value = item.get("value")
            if isinstance(value, (int, float)):
                return int(value)

        fallback_keys = (
            "port{}_tof".format(self.port),
            "tof_{}".format(self.port),
            "sensor_port_{}".format(self.port),
        )

        for key in fallback_keys:
            item = sensors.get(key)
            if isinstance(item, dict):
                value = item.get("value")
                if isinstance(value, (int, float)):
                    return int(value)

        for key, item in sensors.items():
            if not isinstance(item, dict):
                continue

            value = item.get("value")
            if not isinstance(value, (int, float)):
                continue

            meta = item.get("meta", {})
            key_s = str(key).lower()
            meta_s = str(meta).lower()

            if "tof" in key_s and str(self.port) in key_s:
                return int(value)

            if "tof" in meta_s and str(self.port) in meta_s:
                return int(value)

        return None

    def _find_color_item(self):
        if self.api is None:
            return None

        sensors = self.api.get_sensor_snapshot()
        candidates = (
            "color_port_{}".format(self.port),
            "port{}_color".format(self.port),
        )

        for key in candidates:
            item = sensors.get(key)
            if isinstance(item, dict) and isinstance(item.get("value"), dict):
                return item

        return None

    def read(self):
        return self._find_snapshot_value()

    def rgb(self):
        item = self._find_color_item()
        if item is None:
            return None

        value = item.get("value", {})
        if not all(k in value for k in ("r", "g", "b")):
            return None

        return {
            "r": int(value.get("r", 0)),
            "g": int(value.get("g", 0)),
            "b": int(value.get("b", 0)),
            "clear": int(value.get("clear", 0)),
        }

    def color(self):
        match = self.color_match()
        if match is None:
            return None
        color = match.get("color")
        if color is None:
            return None
        return str(color)

    def color_match(self):
        item = self._find_color_item()
        if item is None:
            return None

        value = item.get("value", {})
        rgb = {
            "r": int(value.get("r", 0)),
            "g": int(value.get("g", 0)),
            "b": int(value.get("b", 0)),
            "clear": int(value.get("clear", 0)),
        }

        if self.api is not None:
            calibrated = self.api.match_calibrated_color(self.port, rgb)
            if calibrated is not None:
                return calibrated

        return {
            "color": value.get("color"),
            "confidence": int(value.get("confidence", 0)),
            "rgb": rgb,
            "normalized": value.get("normalized"),
            "range": item.get("meta", {}).get("range"),
            "calibrated": False,
        }

    def is_color(self, name):
        color = self.color()
        if color is None:
            return False
        return color.lower() == str(name).lower()

    def calibrate_color(self, name, samples=COLOR_CALIBRATION_DEFAULT_SAMPLES, delay_ms=COLOR_CALIBRATION_DEFAULT_DELAY_MS):
        if self.api is None:
            return None

        count = _clamp(int(samples), 1, COLOR_CALIBRATION_MAX_SAMPLES)
        delay = max(0, int(delay_ms))
        totals = {"r": 0, "g": 0, "b": 0, "clear": 0}
        got = 0

        for index in range(count):
            rgb = self.rgb()
            if rgb is not None:
                totals["r"] += int(rgb.get("r", 0))
                totals["g"] += int(rgb.get("g", 0))
                totals["b"] += int(rgb.get("b", 0))
                totals["clear"] += int(rgb.get("clear", 0))
                got += 1

            if delay and index + 1 < count:
                time.sleep_ms(delay)

        if got <= 0:
            return None

        avg = {
            "r": int(totals["r"] / got),
            "g": int(totals["g"] / got),
            "b": int(totals["b"] / got),
            "clear": int(totals["clear"] / got),
        }
        return self.api.set_color_calibration(self.port, name, avg, got)

    def color_calibrations(self):
        if self.api is None:
            return {}
        return self.api.get_color_calibrations(self.port)

    def clear_color_calibration(self, name=None):
        if self.api is None:
            return False
        return self.api.clear_color_calibration(self.port, name)


class _ZBotServo:
    def __init__(self, api, port=1):
        self.api = api
        self.port = int(port)

    def angle(self, deg):
        if self.api is None:
            return False
        self.api.set_servo(self.port, int(deg))
        return True

    def write_angle(self, deg):
        return self.angle(deg)

    def center(self, center_angle=None):
        if self.api is None:
            return False
        if center_angle is None:
            self.api.center_servo(self.port)
        else:
            self.api.set_servo(self.port, int(center_angle))
        return True


class _ZBotMotor:
    def __init__(self, api, port, motor_type="DC"):
        self.api = api
        self.port = int(port)
        self.motor_type = str(motor_type)
        self._publish_meta()

    def _publish_meta(self):
        if self.api is None:
            return
        try:
            if "student_motors" not in self.api.status:
                self.api.status["student_motors"] = {}
            self.api.status["student_motors"][self.port] = {
                "type": self.motor_type,
                "ts_ms": time.ticks_ms(),
            }
        except Exception:
            pass

    def on(self, power=50):
        if self.api is None:
            return False
        self._publish_meta()
        self.api.set_motor(self.port, int(power))
        return True

    def off(self):
        if self.api is None:
            return False
        self.api.stop_motor(self.port)
        return True

    def stop(self):
        return self.off()

    def speed(self, power):
        return self.on(power)

    def set(self, power):
        return self.on(power)

    def value(self):
        if self.api is None:
            return None
        try:
            return self.api.get_motor_status().get(self.port, {})
        except Exception:
            return None


class ZBot:
    """
    Student-facing neutral wrapper.

    This wrapper exposes primitives only. Drive-model decisions belong in
    user modules (robot.ackermann, robot.differential, etc).
    """
    def __init__(self, api=None):
        self.api = api
        self._motor_wrappers = {}
        self._servo_wrappers = {}
        self._button_wrappers = {}

    def bind(self, api):
        self.api = api
        return self

    def ready(self):
        return self.api is not None and bool(self.api.status["system"].get("ready", False))

    def stop(self):
        if self.api is None:
            return False
        self.api.stop_all()
        return True

    def steer(self, angle):
        if self.api is None:
            return False
        self.api.set_steering(int(angle))
        return True

    def display(self, line1="", line2="", line3="", line4=""):
        if self.api is None:
            return False
        return self.api.display(line1, line2, line3, line4)

    def say(self, line1="", line2="", line3="", line4=""):
        return self.display(line1, line2, line3, line4)

    def notify(self, text):
        if self.api is None:
            return False
        return self.api.notify(str(text))

    def button(self, button_id=1):
        key = int(button_id)
        if self.api is None:
            return _ZBotButton(None, button_id)

        if key not in self._button_wrappers:
            self._button_wrappers[key] = _ZBotButton(self.api, button_id)

        return self._button_wrappers[key]

    def buttons(self, button_id=1):
        return self.button(button_id)

    def servo(self, port=1):
        key = int(port)
        if self.api is None:
            return _ZBotServo(None, port)

        if key not in self._servo_wrappers:
            self._servo_wrappers[key] = _ZBotServo(self.api, port)

        return self._servo_wrappers[key]

    def motor(self, port, motor_type="DC"):
        key = (int(port), str(motor_type))
        if self.api is None:
            return _ZBotMotor(None, port, motor_type)

        if key not in self._motor_wrappers:
            self._motor_wrappers[key] = _ZBotMotor(self.api, port, motor_type)

        return self._motor_wrappers[key]

    def motors(self, port, motor_type="DC"):
        return self.motor(port, motor_type)

    def sensor(self, port):
        if self.api is None:
            return _ZBotSensor(None, port)
        return _ZBotSensor(self.api, port)

    def tof(self, port):
        s = self.sensor(port)
        return s.read()

    def color(self, port):
        s = self.sensor(port)
        return s.color()

    def rgb(self, port):
        s = self.sensor(port)
        return s.rgb()

    def calibrate_color(self, port, name, samples=COLOR_CALIBRATION_DEFAULT_SAMPLES, delay_ms=COLOR_CALIBRATION_DEFAULT_DELAY_MS):
        s = self.sensor(port)
        return s.calibrate_color(name, samples=samples, delay_ms=delay_ms)

    def color_calibrations(self, port=None):
        if self.api is None:
            return {}
        return self.api.get_color_calibrations(port)

    def clear_color_calibration(self, port=None, name=None):
        if self.api is None:
            return False
        return self.api.clear_color_calibration(port, name)

    def status(self):
        if self.api is None:
            return {}
        return self.api.get_status()

    def sensors(self):
        if self.api is None:
            return {}
        return self.api.get_sensor_snapshot()

    def button_status(self):
        if self.api is None:
            return {}
        return self.api.get_button_status()

    def imu(self):
        if self.api is None:
            return {}
        return self.api.get_imu()

    def start_turn(self, speed_mps=TURN_RADIUS_DEFAULT_SPEED_MPS, drive_power=TURN_RADIUS_DEFAULT_DRIVE_POWER, turn=TURN_RADIUS_DEFAULT_TURN, min_yaw_dps=TURN_RADIUS_MIN_YAW_DPS):
        if self.api is None:
            return {}
        return self.api.start_turn(
            speed_mps=speed_mps,
            drive_power=drive_power,
            turn=turn,
            min_yaw_dps=min_yaw_dps,
        )

    def stop_turn(self, stop_drive=True):
        if self.api is None:
            return {}
        return self.api.stop_turn(stop_drive=stop_drive)

    def turn_radius(self):
        if self.api is None:
            return {}
        return self.api.get_turn_radius()

    def motor_status(self):
        if self.api is None:
            return {}
        return self.api.get_motor_status()

    def motor_feedback(self):
        if self.api is None:
            return {}
        return self.api.get_motor_feedback()

    def servo_status(self):
        if self.api is None:
            return {}
        return self.api.get_servo_status()

    # Backward-compatible motion shims. They use the neutral runtime bridge.
    def drive(self, throttle, turn=0):
        if self.api is None:
            return False
        self.api.drive(int(throttle), int(turn))
        return True

    def forward(self, power=50):
        return self.drive(abs(int(power)), 0)

    def backward(self, power=50):
        return self.drive(-abs(int(power)), 0)

    def tank(self, left_power, right_power):
        left_power = int(left_power)
        right_power = int(right_power)
        throttle = (left_power + right_power) // 2
        turn = (left_power - right_power) // 2
        return self.drive(throttle, turn)


def get_api():
    return API


def get_zbot():
    return zbot


def _emergency_stop_motors(api, reason="UNHANDLED_ERROR", exc=None):
    try:
        if api is None:
            return False

        stopped = False
        motors = api.handles.get("motors", {})
        for port, motor in motors.items():
            try:
                if hasattr(motor, "stop"):
                    motor.stop()
                else:
                    motor.set(True, 0)

                api.status["motors"][port] = {
                    "power": 0,
                    "duty_u16": 0,
                    "ts_ms": time.ticks_ms(),
                    "name": api.get_motor_map().get(port, {}).get("name", "M{}".format(port)),
                    "stop_reason": str(reason),
                }
                stopped = True
            except Exception as stop_err:
                error("EMERGENCY_STOP_{}".format(port), stop_err)

        if stopped:
            api.status["system"]["last_stop_reason"] = str(reason)
            teleop = api.get_handle("teleop")
            if teleop is not None:
                try:
                    teleop.notify_line("ERR MOTORS_STOPPED {}".format(reason))
                except Exception:
                    pass
        return stopped
    except Exception as stop_outer:
        try:
            error("EMERGENCY_STOP", stop_outer)
        except Exception:
            pass
        return False


async def _guarded_task(api, name, coro):
    try:
        await coro
    except Exception as e:
        _emergency_stop_motors(api, "TASK_{}".format(name), e)
        error("TASK_{}".format(name), e)
        try:
            api.status["services"]["task_error"] = {
                "name": str(name),
                "error": repr(e),
                "ts_ms": time.ticks_ms(),
            }
        except Exception:
            pass

        teleop = api.get_handle("teleop") if api is not None else None
        if teleop is not None:
            try:
                teleop.notify_error("TASK_{}".format(name), e)
            except Exception:
                pass


def _create_guarded_task(api, name, coro):
    return asyncio.create_task(_guarded_task(api, name, coro))


def _start_user_main_task(api):
    if api is None:
        return False
    if api.tasks.get("user_main") is not None:
        return False
    api.register_task("user_main", _create_guarded_task(api, "user_main", _run_user_program(api)))
    info("BOOT: user_main task started")
    state("TASK", "user_main_started")
    return True


def _boot_spinner_text(text):
    global _boot_spinner_index

    value = str(text)
    frame = _BOOT_SPINNER_FRAMES[_boot_spinner_index % len(_BOOT_SPINNER_FRAMES)]
    _boot_spinner_index += 1
    if value:
        return "{} {}".format(value, frame)
    return frame


def _boot_oled(api, line1, line2="", line3="", spinner=True):
    try:
        if api is None:
            return

        if api.status.get("boot", {}).get("state") == "complete":
            return

        if api.user_display_active():
            return

        oled = api.get_handle("oled")
        if oled is not None and getattr(oled, "available", False):
            if spinner:
                line2 = _boot_spinner_text(line2)
            oled.show_lines(line1, line2, line3)
    except Exception as e:
        error("BOOT_OLED", e)


def _format_tof_line(api):
    sensors = api.status.get("sensors", {})
    for port in range(1, 7):
        key = "tof_port_{}".format(port)
        item = sensors.get(key)
        if isinstance(item, dict):
            value = item.get("value")
            if isinstance(value, (int, float)):
                return "TOF{}: {}mm".format(port, int(value))
    return "TOF: --"


def _format_user_line(api):
    user = api.status.get("user", {})
    if user.get("last_error"):
        return "User ERR"
    if user.get("running"):
        return "User: running"
    return "User: idle"


def _format_ble_line(api):
    teleop = api.get_handle("teleop")
    if teleop is None:
        return "BLE: off"
    try:
        if teleop._conn_handle is None:
            return "BLE: waiting"
        return "BLE: connected"
    except Exception:
        return "BLE: ?"


def _sensor_port_line(api, port):
    sensors = api.status.get("sensors", {})

    candidates = [
        "tof_port_{}".format(port),
        "port{}_tof".format(port),
        "tof_{}".format(port),
        "sensor_port_{}".format(port),
        "color_port_{}".format(port),
        "port{}_color".format(port),
    ]

    for key in candidates:
        item = sensors.get(key)
        if not isinstance(item, dict):
            continue

        value = item.get("value")
        meta = item.get("meta", {})
        key_l = key.lower()
        meta_l = str(meta).lower()

        if isinstance(value, (int, float)) and ("tof" in key_l or "tof" in meta_l):
            return "P{} TOF {}mm".format(port, int(value))

        if isinstance(value, dict):
            if "r" in value and "g" in value and "b" in value:
                calibrated = api.match_calibrated_color(port, value)
                color = calibrated.get("color") if calibrated is not None else value.get("color")
                if color:
                    return "P{} {}".format(port, str(color)[:10])
                return "P{} RGB".format(port)

        if isinstance(value, (int, float)):
            return "P{} {}".format(port, int(value))

        if value is not None:
            return "P{} {}".format(port, str(value)[:10])

    for key, item in sensors.items():
        if not isinstance(item, dict):
            continue
        key_l = str(key).lower()
        meta_l = str(item.get("meta", {})).lower()
        if str(port) not in key_l and str(port) not in meta_l:
            continue

        value = item.get("value")
        if isinstance(value, (int, float)) and ("tof" in key_l or "tof" in meta_l):
            return "P{} TOF {}mm".format(port, int(value))
        if value is not None:
            return "P{} {}".format(port, str(value)[:10])

    mode = None
    try:
        mode = SENSOR_PORT_MODES.get(port)
    except Exception:
        mode = None

    if mode:
        return "P{} {}".format(port, str(mode))
    return "P{} empty".format(port)


def _sensor_overview_pages(api):
    pages = []

    user = api.status.get("user", {})
    if user.get("last_error"):
        err_name = str(user.get("last_error"))[:18]
        pages.append(("ZebraBot", "User Error", err_name))
    elif user.get("module"):
        kind = str(user.get("kind") or "user")[:10]
        pages.append(("ZebraBot", "User stopped", kind))
    else:
        pages.append(("ZebraBot", "Starting user", "Sensor monitor"))

    ports = [1, 2, 3, 4, 5, 6]
    for i in range(0, len(ports), 3):
        chunk = ports[i:i + 3]
        lines = ["Sensors"]
        for port in chunk:
            lines.append(_sensor_port_line(api, port))
        pages.append(tuple(lines))

    imu = api.status.get("imu", {})
    if imu:
        if "error" in imu:
            pages.append(("IMU", "error", str(imu.get("error"))[:18]))
        else:
            value = imu.get("value")
            pages.append(("IMU", str(value)[:20], ""))

    return pages


async def _api_housekeeping_task(api):
    while True:
        try:
            motor_feedback = api.get_handle("motor_feedback")
            if motor_feedback is not None and hasattr(motor_feedback, "snapshot"):
                api.status["motor_feedback"] = motor_feedback.snapshot()
        except Exception:
            pass

        try:
            sensor_hub = api.get_handle("sensor_hub")
            if sensor_hub is not None and hasattr(sensor_hub, "snapshot"):
                api.status["sensors"] = sensor_hub.snapshot()
        except Exception:
            pass

        try:
            api.refresh_imu_snapshot()
        except Exception:
            pass

        await asyncio.sleep_ms(100)


async def _oled_status_task(api):
    last_lines = None
    page_idx = 0
    last_page_ms = 0
    page_period_ms = 1400

    while True:
        try:
            oled = api.get_handle("oled")
            if oled is None or not getattr(oled, "available", False):
                await asyncio.sleep_ms(500)
                continue

            if api.user_display_active():
                await asyncio.sleep_ms(200)
                continue

            user = api.status.get("user", {})
            fallback_mode = (not user.get("running")) or bool(user.get("last_error"))

            if user.get("running") and not user.get("last_error"):
                await asyncio.sleep_ms(250)
                continue

            if fallback_mode:
                pages = _sensor_overview_pages(api)
                now = time.ticks_ms()
                if not pages:
                    lines = ("ZebraBot", "No sensors", "")
                else:
                    if (
                        last_page_ms == 0
                        or time.ticks_diff(now, last_page_ms) >= page_period_ms
                    ):
                        page_idx = (page_idx + 1) % len(pages)
                        last_page_ms = now
                    lines = pages[page_idx]
            else:
                line1 = "ZebraBot Ready" if api.status["system"].get("ready") else "ZebraBot Boot"
                line2 = _format_ble_line(api)
                line3 = _format_user_line(api)
                line4 = _format_tof_line(api)
                lines = (line1, line2, line3, line4)
                page_idx = 0
                last_page_ms = 0

            if lines != last_lines:
                oled.show_lines(*lines)
                last_lines = lines

        except Exception as e:
            error("OLED_STATUS_TASK", e)

        await asyncio.sleep_ms(250)


async def _boot_complete_message(api):
    _boot_oled(api, "ZebraBot", "Boot Complete", "Starting tasks...")
    await asyncio.sleep_ms(1200)


def _attach_ble_teleop(api, teleop, imu=None, start_imu=True):
    api.register_handle("teleop", teleop)
    set_ble_sink(teleop)

    motor_feedback = api.get_handle("motor_feedback")
    motor_scanner = api.get_handle("motor_scanner")
    motor_port_map = api.get_handle("motor_port_map", {})

    teleop.motor_feedback = motor_feedback
    teleop.motor_scanner = motor_scanner
    teleop.motor_ports = ACTIVE_MOTOR_PORTS
    teleop.motor_port_map = dict(motor_port_map)

    sensor_hub = api.get_handle("sensor_hub")
    if sensor_hub is not None:
        try:
            sensor_hub.notify = teleop.notify_line
        except Exception as e:
            error("BLE_SENSOR_NOTIFY_ATTACH", e)

    if motor_scanner is not None:
        try:
            motor_scanner.notify = teleop.notify_line
        except Exception as e:
            error("BLE_MOTOR_NOTIFY_ATTACH", e)

    if start_imu and imu is not None and api.get_handle("teleop_imu_task_started") is None:
        imu_task_fn = getattr(teleop, "imu_task", None)
        if imu_task_fn is not None:
            try:
                api.register_task("imu", _create_guarded_task(api, "imu", imu_task_fn()))
                api.register_handle("teleop_imu_task_started", True)
                info("BOOT: IMU task started")
                state("TASK", "imu_started")
            except Exception as e:
                error("IMU_TASK_START", e)


async def _deferred_ble_start_task(api, drive, steering, imu, oled):
    await asyncio.sleep_ms(3000)

    for attempt in range(1, 3):
        if api.get_handle("teleop") is not None:
            return

        try:
            info("BOOT: deferred BLE init attempt {}".format(attempt))
            from robot.ble_teleop import BleTeleop

            teleop = BleTeleop(
                drive=drive,
                steering=steering,
                imu=imu,
                imu_period_ms=MPU_PERIOD_MS,
                oled=oled,
            )
            _attach_ble_teleop(api, teleop, imu=imu)
            info("BOOT: BLE teleop initialized")
            state("BOOT", "ble_ok")
            return
        except Exception as e:
            error("BLE_DEFERRED_INIT", e)
            state("BOOT", "ble_retry_{}".format(attempt))
            await asyncio.sleep_ms(5000)

    warn("BOOT: deferred BLE init exhausted")
    state("BOOT", "ble_failed")


def _detect_user_main_kind(user_main, user_fn):
    try:
        override = getattr(user_main, "USER_MAIN_KIND", None)
        if override is not None:
            kind = str(override).strip().lower()
            if kind in ("c", "native", "python"):
                return "c" if kind == "native" else kind
    except Exception:
        pass

    try:
        module_file = getattr(user_main, "__file__", None)
        if module_file:
            return "python"
    except Exception:
        pass

    try:
        if getattr(user_fn, "__code__", None) is not None:
            return "python"
    except Exception:
        pass

    return "c"


async def _run_user_program(api):
    user_main_name = "user_main"
    try:
        import user_main
    except Exception as e:
        error("USER_IMPORT", e)
        api.status["user"]["last_error"] = repr(e)

        teleop = api.get_handle("teleop")
        if teleop is not None:
            try:
                teleop.notify_error("USER_IMPORT", e)
            except Exception:
                pass
        return

    try:
        user_main_name = getattr(user_main, "__name__", "user_main")
    except Exception:
        user_main_name = "user_main"

    user_fn = getattr(user_main, "main", None)
    user_file = None
    try:
        user_file = getattr(user_main, "__file__", None)
    except Exception:
        user_file = None

    user_kind = _detect_user_main_kind(user_main, user_fn) if user_fn is not None else "unknown"
    api.status["user"]["kind"] = user_kind
    api.status["user"]["module"] = user_main_name
    api.status["user"]["file"] = user_file

    if user_fn is None:
        warn("USER: user_main.main missing")
        api.status["user"]["last_error"] = "user_main.main missing"

        teleop = api.get_handle("teleop")
        if teleop is not None:
            try:
                teleop.notify_line("ERR USER main() missing")
            except Exception:
                pass
        return

    api.status["user"]["running"] = True
    api.status["user"]["last_error"] = None

    teleop = api.get_handle("teleop")
    if teleop is not None:
        try:
            teleop.notify_line("INFO USER {} {}.main starting".format(user_kind, user_main_name))
        except Exception:
            pass

    try:
        result = None
        called = False

        try:
            argc = user_fn.__code__.co_argcount
        except Exception:
            argc = None

        if argc == 0:
            result = user_fn()
            called = True
        elif argc is not None:
            result = user_fn(zbot)
            called = True

        if not called:
            try:
                result = user_fn(zbot)
            except TypeError:
                result = user_fn()

        if hasattr(result, "__await__") or hasattr(result, "send"):
            await result
        else:
            tick_fn = getattr(user_main, "tick", None)
            if tick_fn is not None:
                tick_ms = int(getattr(user_main, "USER_MAIN_TICK_MS", 1000))
                if tick_ms < 50:
                    tick_ms = 50
                while True:
                    try:
                        tick_fn(zbot)
                    except TypeError:
                        tick_fn()
                    await asyncio.sleep_ms(tick_ms)

    except Exception as e:
        api.status["user"]["last_error"] = repr(e)
        _emergency_stop_motors(api, "USER_MAIN", e)
        error("USER_MAIN", e)

        if teleop is not None:
            try:
                teleop.notify_error("USER_MAIN", e)
            except Exception:
                pass

    finally:
        api.status["user"]["running"] = False

        if teleop is not None:
            try:
                teleop.notify_line("INFO USER main stopped")
            except Exception:
                pass


async def main():
    global API
    global zbot
    global PREACTIVE_BLE

    teleop = None
    sensor_hub = None
    imu = None
    oled = None
    mux = None
    base_i2c = None
    runtime_drive = None
    steer = None

    motors = {}
    servos = {}
    motor_feedback = None
    motor_scanner = None
    button_manager = None

    api = RobotAPI()
    API = api
    zbot = ZBot(api)

    info("BOOT: starting robot init")
    state("BOOT", "start")
    api.status["boot"]["state"] = "starting"

    try:
        for port in sorted(MOTOR_PORT_MAP.keys()):
            cfg = MOTOR_PORT_MAP[port]
            motors[port] = Motor(
                cfg["pwm"],
                cfg["dir"],
                pwm_freq_hz=MOTOR_PWM_FREQ_HZ,
                invert_pwm=bool(cfg.get("invert_pwm", MOTOR_INVERT_PWM)),
            )
            diag(
                "MOTOR_PORT {} {} pwm={} dir={} enc={}".format(
                    port,
                    cfg.get("name", "M{}".format(port)),
                    cfg.get("pwm"),
                    cfg.get("dir"),
                    cfg.get("enc"),
                )
            )
            api.status["motors"][port] = {
                "power": 0,
                "duty_u16": 0,
                "name": cfg.get("name", "M{}".format(port)),
                "enc": cfg.get("enc"),
                "ts_ms": time.ticks_ms(),
            }

        api.register_handle("motors", motors)
        api.register_handle("motor_port_map", dict(MOTOR_PORT_MAP))

        info("BOOT: motors initialized")
        diag("DRIVE LEFT PWM={} DIR={} ENC={}".format(LEFT_PWM, LEFT_DIR, LEFT_ENC))
        diag("DRIVE RIGHT PWM={} DIR={} ENC={}".format(RIGHT_PWM, RIGHT_DIR, RIGHT_ENC))
        state("BOOT", "motors_ok")

    except Exception as e:
        error("MOTOR_INIT", e)
        raise

    try:
        api.register_handle("servos", servos)
        api.register_handle("servo_port_map", dict(SERVO_PORT_MAP))

        steer_port = None
        for port, cfg in SERVO_PORT_MAP.items():
            if str(cfg.get("role", "")).lower() == "steering":
                steer_port = int(port)
                break
        if steer_port is None:
            steer_port = int(STEER_SERVO_PORT)

        api.register_handle("steer_port", int(steer_port))
        api.status["steering"] = {"angle": None, "ts_ms": time.ticks_ms(), "available": True}
        info("BOOT: servo ports registered")
        state("BOOT", "servo_ports_ok")

        try:
            steer = api._ensure_servo(steer_port)
            api.register_handle("steer", steer)
            api.center_servo(steer_port)
            api.status["steering"] = {
                "angle": int(SERVO_PORT_MAP.get(steer_port, {}).get("center_deg", SERVO_CENTER_DEG)),
                "ts_ms": time.ticks_ms(),
                "available": True,
            }
        except Exception as center_err:
            error("SERVO_CENTER_INIT", center_err)
            warn("BOOT: steering servo will remain lazy until first use")

    except Exception as e:
        error("SERVO_INIT", e)
        warn("BOOT: continuing without servos")
        servos = {}
        steer = None
        api.register_handle("servos", servos)
        api.register_handle("servo_port_map", {})
        api.status["steering"] = {"angle": None, "ts_ms": time.ticks_ms(), "available": False}
        state("BOOT", "servo_failed")

    try:
        runtime_drive = RuntimeDriveBridge(api, propulsion_ports=DRIVE_MOTOR_PORTS)
        api.register_handle("runtime_drive", runtime_drive)
    except Exception as e:
        error("RUNTIME_DRIVE_INIT", e)

    try:
        from robot.button import ButtonManager

        button_manager = ButtonManager(
            api=api,
            button_map=BUTTON_MAP,
            debounce_ms=BUTTON_DEBOUNCE_MS,
            scan_period_ms=BUTTON_SCAN_PERIOD_MS,
            default_pull=BUTTON_DEFAULT_PULL,
            default_active_low=BUTTON_DEFAULT_ACTIVE_LOW,
        )
        button_manager.start()
        api.register_handle("button_manager", button_manager)
        info("BOOT: buttons initialized")
        diag("BUTTONS {}".format(button_manager.snapshot()))
        state("BOOT", "buttons_ok")
    except Exception as e:
        button_manager = None
        error("BUTTON_INIT", e)
        warn("BOOT: continuing without buttons")
        state("BOOT", "buttons_failed")

    try:
        from robot.tca9548a import TCA9548A

        base_i2c = I2C(
            TCA_I2C_ID,
            sda=Pin(TCA_SDA_GPIO),
            scl=Pin(TCA_SCL_GPIO),
            freq=TCA_I2C_FREQ,
        )
        mux = TCA9548A(base_i2c, addr=TCA_ADDR)
        api.register_handle("base_i2c", base_i2c)
        api.register_handle("mux", mux)
        info("BOOT: TCA9548A initialized")
        diag(
            "TCA BUS sda={} scl={} addr={}".format(
                TCA_SDA_GPIO, TCA_SCL_GPIO, hex(TCA_ADDR)
            )
        )
        state("BOOT", "mux_ok")

        try:
            devices = base_i2c.scan()
            api.status["services"]["i2c"] = {
                "bus": TCA_I2C_ID,
                "devices": devices,
                "ts_ms": time.ticks_ms(),
            }
            diag("I2C_BASE {}".format(",".join(hex(d) for d in devices) if devices else "none"))
        except Exception as scan_err:
            error("I2C_SCAN", scan_err)

    except Exception as e:
        error("TCA_INIT", e)

    try:
        from robot.mpu6050 import MPU6050

        imu = MPU6050(
            i2c_id=TCA_I2C_ID,
            sda_gpio=TCA_SDA_GPIO,
            scl_gpio=TCA_SCL_GPIO,
            freq=TCA_I2C_FREQ,
            addr=MPU_ADDR,
            mux=mux,
            mux_channel=MPU_CHANNEL,
        )
        api.register_handle("imu", imu)
        info("BOOT: MPU-6050 initialized")
        diag("MPU CH={} ADDR={}".format(MPU_CHANNEL, hex(MPU_ADDR)))
        state("BOOT", "mpu_ok")
    except Exception as e:
        error("MPU_INIT", e)
        imu = None
        warn("BOOT: MPU unavailable")

    try:
        from robot.oled_status import OledStatus

        oled = OledStatus(
            i2c_id=TCA_I2C_ID,
            sda_gpio=TCA_SDA_GPIO,
            scl_gpio=TCA_SCL_GPIO,
            width=OLED_WIDTH,
            height=OLED_HEIGHT,
            addr=OLED_ADDR,
            mux=mux,
            mux_channel=OLED_CHANNEL,
        )
        if oled and oled.available:
            api.register_handle("oled", oled)
            _boot_oled(api, "ZebraBot", "Booting...", "OLED online")
            info("BOOT: OLED initialized")
            diag("OLED CH={} ADDR={}".format(OLED_CHANNEL, hex(OLED_ADDR)))
            state("BOOT", "oled_ok")
        else:
            info("BOOT: OLED unavailable")
            state("BOOT", "oled_unavailable")
    except Exception as e:
        error("OLED_INIT", e)
        oled = None

    if BLE_ENABLED:
        _boot_oled(api, "ZebraBot", "Starting BLE", "")
        try:
            from robot.ble_teleop import BleTeleop

            teleop = BleTeleop(
                drive=runtime_drive,
                steering=steer,
                imu=imu,
                imu_period_ms=MPU_PERIOD_MS,
                oled=oled,
                ble=PREACTIVE_BLE,
            )
            PREACTIVE_BLE = None
            _attach_ble_teleop(api, teleop, imu=imu, start_imu=False)

            info("BOOT: BLE teleop initialized")
            state("BOOT", "ble_ok")
        except Exception as e:
            teleop = None
            error("BLE_INIT", e)
            _boot_oled(api, "ZebraBot", "BLE init fail", str(type(e).__name__))
            warn("BOOT: BLE init deferred")
            state("BOOT", "ble_deferred")
    else:
        teleop = None
        PREACTIVE_BLE = None
        warn("BOOT: BLE disabled by config")
        state("BOOT", "ble_disabled")

    _boot_oled(api, "ZebraBot", "Sensors init", "")
    try:
        from robot.sensor_hub import SensorHub

        notify_fn = teleop.notify_line if teleop is not None else None
        sensor_hub = SensorHub(
            i2c_id=TCA_I2C_ID,
            sda_gpio=TCA_SDA_GPIO,
            scl_gpio=TCA_SCL_GPIO,
            freq=TCA_I2C_FREQ,
            mux=mux,
            port_modes=SENSOR_PORT_MODES,
            notify_fn=notify_fn,
            scan_period_ms=SENSOR_SCAN_PERIOD_MS,
            port_channels=SENSOR_PORT_CHANNELS,
        )
        api.register_handle("sensor_hub", sensor_hub)
        info("BOOT: SensorHub initialized")
        state("BOOT", "sensorhub_ok")
        _boot_oled(api, "ZebraBot", "Sensors ok", "")
    except Exception as e:
        error("SENSOR_HUB_INIT", e)
        sensor_hub = None
        _boot_oled(api, "ZebraBot", "Sensors fail", str(type(e).__name__))

    if MOTOR_FEEDBACK_ENABLED:
        _boot_oled(api, "ZebraBot", "Starting motors", "")

        try:
            from robot.motor_feedback import MotorFeedback
            from robot.motor_scan import MotorScanner

            motor_port_map = dict(MOTOR_PORT_MAP)
            motor_feedback = MotorFeedback(motor_port_map)
            motor_scanner = MotorScanner(
                motors=motors,
                feedback=motor_feedback,
                notify_fn=teleop.notify_line if teleop is not None else None,
                ports=ACTIVE_MOTOR_PORTS,
                scan_power=MOTOR_SCAN_POWER,
                pulse_ms=MOTOR_SCAN_PULSE_MS,
                period_ms=MOTOR_SCAN_PERIOD_MS,
                max_duty_u16=MOTOR_MAX_DUTY_U16,
            )

            api.register_handle("motor_feedback", motor_feedback)
            api.register_handle("motor_scanner", motor_scanner)

            if teleop is not None:
                teleop.motor_feedback = motor_feedback
                teleop.motor_scanner = motor_scanner
                teleop.motor_ports = ACTIVE_MOTOR_PORTS
                teleop.motor_port_map = motor_port_map

            info("BOOT: motor feedback/scanner initialized")
            state("BOOT", "motor_scan_ok")

        except Exception as e:
            error("MOTOR_SCAN_INIT", e)
            motor_feedback = None
            motor_scanner = None
    else:
        motor_feedback = None
        motor_scanner = None
        info("BOOT: motor feedback/scanner disabled")
        state("BOOT", "motor_scan_disabled")
        _boot_oled(api, "ZebraBot", "Motors skipped", "")

    if BLE_ENABLED and teleop is None:
        try:
            api.register_task(
                "ble_deferred",
                _create_guarded_task(api, "ble_deferred", _deferred_ble_start_task(api, runtime_drive, steer, imu, oled)),
            )
            info("BOOT: deferred BLE task scheduled")
            state("TASK", "ble_deferred_started")
        except Exception as e:
            error("BLE_DEFERRED_TASK", e)

    info("BOOT: robot boot complete")
    state("BOOT", "complete")
    api.status["boot"]["state"] = "complete"
    api.set_ready(True)

    await _boot_complete_message(api)

    if api.get_handle("teleop_imu_task_started") is not None:
        pass
    elif imu is not None and teleop is not None:
        _attach_ble_teleop(api, teleop, imu=imu)
    elif imu is not None:
        info("BOOT: IMU task waiting for BLE")
        state("TASK", "imu_waiting_ble")
    else:
        info("BOOT: IMU task skipped (no IMU)")
        state("TASK", "imu_skipped")
    ENABLE_ACTIVE_MOTOR_SCAN = False

    if motor_scanner is not None:
        if ENABLE_ACTIVE_MOTOR_SCAN:
            try:
                api.register_task("motor_scan", _create_guarded_task(api, "motor_scan", motor_scanner.task()))
                info("BOOT: MotorScanner task started")
                state("TASK", "motor_scan_started")
            except Exception as e:
                error("MOTOR_SCAN_TASK", e)
        else:
            warn("BOOT: active motor scan disabled during user runtime")

        try:
            api.register_task(
                "motor_feedback",
                _create_guarded_task(
                    api,
                    "motor_feedback",
                    motor_scanner.feedback_task(period_ms=MOTOR_FEEDBACK_PERIOD_MS),
                ),
            )
            info("BOOT: Motor feedback task started")
            state("TASK", "motor_feedback_started")
        except Exception as e:
            error("MOTOR_FB_TASK", e)
    else:
        warn("BOOT: motor scan tasks skipped")

    if button_manager is not None:
        try:
            api.register_task("buttons", _create_guarded_task(api, "buttons", button_manager.task()))
            info("BOOT: Button task started")
            state("TASK", "buttons_started")
        except Exception as e:
            error("BUTTON_TASK", e)

    try:
        api.register_task("api_housekeeping", _create_guarded_task(api, "api_housekeeping", _api_housekeeping_task(api)))
    except Exception as e:
        error("API_HOUSEKEEPING", e)

    if OLED_STATUS_ENABLED:
        try:
            api.register_task("oled_status", _create_guarded_task(api, "oled_status", _oled_status_task(api)))
            info("BOOT: OLED status task started")
            state("TASK", "oled_status_started")
        except Exception as e:
            error("OLED_STATUS_START", e)
    else:
        info("BOOT: OLED status task disabled")
        state("TASK", "oled_status_disabled")

    try:
        _start_user_main_task(api)
    except Exception as e:
        error("USER_TASK_START", e)

    if sensor_hub is not None:
        try:
            api.register_task("sensor_hub", _create_guarded_task(api, "sensor_hub", sensor_hub.task()))
            info("BOOT: SensorHub task started")
            state("TASK", "sensorhub_started")
        except Exception as e:
            error("SENSOR_HUB_TASK", e)

    while True:
        api.status["system"]["heartbeat"] += 1
        state("SYS", "heartbeat")
        await asyncio.sleep(5)


def _safe_mode_requested():
    try:
        pin = Pin(SAFE_MODE_PIN, Pin.IN, Pin.PULL_UP)
        return pin.value() == 0
    except Exception as e:
        warn("SAFE_MODE_PIN unavailable: {}".format(e))
        return False


def boot():
    global PREACTIVE_BLE

    info("BOOT: main.py entry")

    if _safe_mode_requested():
        warn("BOOT: safe mode requested on GPIO{}; staying in REPL".format(SAFE_MODE_PIN))
        print("SAFE MODE: GPIO{} held low, normal boot skipped.".format(SAFE_MODE_PIN))
        print("SAFE MODE: release the pin and soft reset to boot normally.")
        state("BOOT", "safe_mode")
        if API is not None:
            API.status["boot"]["safe_mode"] = True
        return

    print("BOOT: starting in {} second(s); press Ctrl-C for REPL.".format(BOOT_GRACE_SECONDS))
    for remaining in range(BOOT_GRACE_SECONDS, 0, -1):
        state("BOOT", "grace_{}".format(remaining))
        print("BOOT: launch in {}...".format(remaining))
        time.sleep(1)

    asyncio.run(main())


try:
    boot()
except Exception as e:
    _emergency_stop_motors(API, "BOOT_UNHANDLED", e)
    try:
        if API is not None:
            _boot_oled(API, "BOOT ERROR", str(type(e).__name__), str(e)[:20], spinner=False)
    except Exception:
        pass
    error("BOOT_UNHANDLED", e)
    raise
finally:
    asyncio.new_event_loop()
