import time

COLOR_CALIBRATION_DEFAULT_SAMPLES = 8
COLOR_CALIBRATION_DEFAULT_DELAY_MS = 40
COLOR_CALIBRATION_MAX_SAMPLES = 30


def _clamp(x, lo, hi):
    return lo if x < lo else hi if x > hi else x


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

    def color_match(self, port):
        s = self.sensor(port)
        return s.color_match()

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
