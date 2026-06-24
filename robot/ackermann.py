import time

class AckermannDrive:
    """
    Ackermann drive helper with optional IMU-referenced heading hold.

    Required zbot capabilities:
      - zbot.motor(port) -> object with on(power), off(), stop()
      - zbot.api.set_steering(angle)
      - zbot.api.get_imu() -> {"value": {...}} or raw dict payload

    IMU heading hold:
      Pass imu_ref=True to enable a PID loop that biases steering relative to
      the current yaw estimate, so "straight" is maintained against drift.

      Because IMU integrations vary between runtimes, this class tries several
      common gyro field names and integrates yaw internally from gyro Z.
      For best results, call update() frequently in your main loop.
    """

    def __init__(
        self,
        zbot,
        drive_motor_port,
        steering_port,
        center_angle=90,
        min_angle=45,
        max_angle=135,
        imu_ref=False,
        kp=0.9,
        ki=0.0,
        kd=0.12,
        max_correction_deg=20,
        gyro_deadband_dps=0.8,
    ):
        self.zbot = zbot
        self.drive_motor = zbot.motor(int(drive_motor_port))
        self.steering_port = int(steering_port)

        self.center_angle = int(center_angle)
        self.min_angle = int(min_angle)
        self.max_angle = int(max_angle)

        self._last_throttle = 0
        self._last_angle = self.center_angle
        self._last_commanded_angle = self.center_angle

        # IMU / heading-hold settings
        self.imu_ref = bool(imu_ref)
        self.kp = float(kp)
        self.ki = float(ki)
        self.kd = float(kd)
        self.max_correction_deg = float(max_correction_deg)
        self.gyro_deadband_dps = float(gyro_deadband_dps)

        self._target_heading_deg = None
        self._estimated_heading_deg = 0.0
        self._heading_integral = 0.0
        self._heading_prev_error = 0.0
        self._last_update_ms = None
        self._last_gyro_z_dps = 0.0

    def _clamp_power(self, power):
        power = int(power)
        if power > 100:
            return 100
        if power < -100:
            return -100
        return power

    def _clamp_angle(self, angle):
        angle = int(angle)
        if angle < self.min_angle:
            return self.min_angle
        if angle > self.max_angle:
            return self.max_angle
        return angle

    def _ticks_ms(self):
        try:
            import time
            return time.ticks_ms()
        except Exception:
            return None

    def _ticks_diff_ms(self, now, prev):
        try:
            import time
            return time.ticks_diff(now, prev)
        except Exception:
            if now is None or prev is None:
                return 0
            return int(now) - int(prev)

    def _extract_imu_payload(self):
        if not hasattr(self.zbot, "api"):
            return None
        api = self.zbot.api
        if not hasattr(api, "get_imu"):
            return None

        snap = api.get_imu()
        if not snap:
            return None

        if isinstance(snap, dict) and "value" in snap and isinstance(snap["value"], dict):
            return snap["value"]
        if isinstance(snap, dict):
            return snap
        return None

    def _extract_gyro_z_dps(self, imu_payload):
        if not isinstance(imu_payload, dict):
            return None

        for key in ("gz_dps", "gyro_z_dps", "gz", "gyro_z"):
            value = imu_payload.get(key)
            if isinstance(value, (int, float)):
                return float(value)
        return None

    def _update_heading_estimate(self):
        if not self.imu_ref:
            return self._estimated_heading_deg

        now = self._ticks_ms()
        imu_payload = self._extract_imu_payload()
        gyro_z = self._extract_gyro_z_dps(imu_payload)

        if self._last_update_ms is None:
            self._last_update_ms = now
            if gyro_z is not None:
                self._last_gyro_z_dps = gyro_z
            return self._estimated_heading_deg

        dt_ms = self._ticks_diff_ms(now, self._last_update_ms)
        self._last_update_ms = now
        if dt_ms <= 0:
            return self._estimated_heading_deg

        if gyro_z is None:
            gyro_z = self._last_gyro_z_dps
        else:
            self._last_gyro_z_dps = gyro_z

        if -self.gyro_deadband_dps < gyro_z < self.gyro_deadband_dps:
            gyro_z = 0.0

        dt_s = dt_ms / 1000.0
        self._estimated_heading_deg += gyro_z * dt_s

        while self._estimated_heading_deg > 180.0:
            self._estimated_heading_deg -= 360.0
        while self._estimated_heading_deg < -180.0:
            self._estimated_heading_deg += 360.0

        return self._estimated_heading_deg

    def _angle_error_deg(self, target, current):
        err = float(target) - float(current)
        while err > 180.0:
            err -= 360.0
        while err < -180.0:
            err += 360.0
        return err

    def _pid_correction_deg(self):
        if not self.imu_ref or self._target_heading_deg is None:
            return 0.0

        heading = self._update_heading_estimate()
        error = self._angle_error_deg(self._target_heading_deg, heading)

        dt_s = 0.0
        if self._last_update_ms is not None:
            # dt already consumed inside _update_heading_estimate; use conservative fixed step fallback
            dt_s = 0.02

        if self.ki != 0.0 and dt_s > 0.0:
            self._heading_integral += error * dt_s
        else:
            self._heading_integral = 0.0 if self.ki == 0.0 else self._heading_integral

        derivative = 0.0
        if dt_s > 0.0:
            derivative = (error - self._heading_prev_error) / dt_s
        self._heading_prev_error = error

        corr = (self.kp * error) + (self.ki * self._heading_integral) + (self.kd * derivative)
        if corr > self.max_correction_deg:
            corr = self.max_correction_deg
        elif corr < -self.max_correction_deg:
            corr = -self.max_correction_deg
        return corr

    def reset_heading_reference(self):
        self._update_heading_estimate()
        self._target_heading_deg = self._estimated_heading_deg
        self._heading_integral = 0.0
        self._heading_prev_error = 0.0
        return self._target_heading_deg

    def set_heading_reference(self, heading_deg):
        self._target_heading_deg = float(heading_deg)
        self._heading_integral = 0.0
        self._heading_prev_error = 0.0
        return self._target_heading_deg

    def enable_imu_reference(self, enabled=True, reset_reference=True):
        self.imu_ref = bool(enabled)
        if self.imu_ref and reset_reference:
            self.reset_heading_reference()
        return self.imu_ref

    def forward(self, power=50):
        power = abs(self._clamp_power(power))
        self._last_throttle = power
        self.drive_motor.on(power)
        if self.imu_ref and self._target_heading_deg is None:
            self.reset_heading_reference()
        return power

    def backward(self, power=50):
        power = abs(self._clamp_power(power))
        self._last_throttle = -power
        self.drive_motor.on(-power)
        if self.imu_ref and self._target_heading_deg is None:
            self.reset_heading_reference()
        return -power

    def stop(self):
        self._last_throttle = 0
        self.drive_motor.off()
        self._heading_integral = 0.0
        self._heading_prev_error = 0.0
        return 0

    def _apply_steering(self, angle):
        angle = self._clamp_angle(angle)
        self._last_angle = angle
        self.zbot.api.set_servo(self.steering_port, angle)
        return angle

    def steer(self, angle):
        angle = self._clamp_angle(angle)
        self._last_commanded_angle = angle
        return self._apply_steering(angle)

    def steer_center(self):
        return self.steer(self.center_angle)

    def drive_straight(self, throttle, reset_reference=False):
        """
        Drive with centered Ackermann steering and IMU heading hold.

        This wraps the straight-line pattern used by challenge programs:
        enable the IMU reference, command the center angle, and keep reapplying
        that centered command from the driving loop.
        """
        if not self.imu_ref:
            self.enable_imu_reference(True, reset_reference=reset_reference)
        elif reset_reference or self._target_heading_deg is None:
            self.reset_heading_reference()

        return self.drive(throttle, self.center_angle)

    def start_straight(self, throttle):
        self.steer_center()
        return self.drive_straight(throttle, reset_reference=True)

    async def drive_straight_distance(
        self,
        distance_m,
        throttle=35,
        speed_mps=None,
        loop_ms=20,
        max_ms=None,
        stop_at_end=True,
        settle_ms=250,
        stop_on_imu=False,
        imu_progress_timeout_ms=1500,
        imu_progress_epsilon_m=0.01,
    ):
        """
        Drive a straight distance using time-at-speed as the primary stop.

        The MPU-6050 is used for heading hold and telemetry. It can optionally
        stop the run early, but the default is to trust calibrated time because
        accelerometer-only displacement drifts quickly.
        """
        import uasyncio as asyncio

        target_m = abs(float(distance_m))
        power = self._clamp_power(throttle)
        if target_m <= 0.0 or power == 0:
            self.stop()
            return {
                "status": "skipped",
                "reason": "zero_distance_or_power",
                "target_m": target_m,
                "elapsed_ms": 0,
                "timed_distance_m": 0.0,
                "imu_distance_m": None,
            }

        if speed_mps is None:
            # First-pass tuning model: power 40 is roughly 0.4 m/s.
            speed_mps = 0.01 * abs(power)
        speed_mps = abs(float(speed_mps))
        if speed_mps <= 0.0:
            raise ValueError("speed_mps must be greater than 0")

        planned_ms = int((target_m / speed_mps) * 1000)
        if max_ms is None:
            max_ms = planned_ms + max(750, int(planned_ms * 0.35))
        else:
            max_ms = int(max_ms)

        if hasattr(self.zbot, "reset_imu_distance"):
            try:
                self.zbot.reset_imu_distance()
            except Exception:
                pass

        self.steer_center()
        if settle_ms:
            await asyncio.sleep_ms(int(settle_ms))

        start_ms = self._ticks_ms()
        last_progress_ms = start_ms
        last_imu_distance_m = 0.0
        timed_distance_m = 0.0
        imu_distance_m = None
        imu_status = "missing"
        reason = "target_distance"

        self.start_straight(power)

        try:
            while True:
                now_ms = self._ticks_ms()
                elapsed_ms = self._ticks_diff_ms(now_ms, start_ms)
                timed_distance_m = speed_mps * (elapsed_ms / 1000.0)

                self.drive_straight(power)

                imu_state = None
                if hasattr(self.zbot, "imu_distance"):
                    try:
                        imu_state = self.zbot.imu_distance()
                    except Exception:
                        imu_state = None

                if isinstance(imu_state, dict):
                    imu_status = str(imu_state.get("status", "ok"))
                    imu_distance_m = float(imu_state.get("distance_m", 0.0))
                    if imu_distance_m > last_imu_distance_m + float(imu_progress_epsilon_m):
                        last_imu_distance_m = imu_distance_m
                        last_progress_ms = now_ms

                if stop_on_imu and imu_distance_m is not None and imu_distance_m >= target_m:
                    reason = "imu_distance"
                    break

                if timed_distance_m >= target_m:
                    reason = "target_distance"
                    break

                if elapsed_ms >= max_ms:
                    reason = "max_time"
                    break

                if (
                    imu_distance_m is not None
                    and imu_progress_timeout_ms is not None
                    and self._ticks_diff_ms(now_ms, last_progress_ms) >= int(imu_progress_timeout_ms)
                ):
                    # Report stale IMU, but keep the time-based stop as the
                    # primary distance source.
                    imu_status = "stale"
                    imu_distance_m = last_imu_distance_m

                await asyncio.sleep_ms(int(loop_ms))

        finally:
            if stop_at_end:
                self.stop()
                self.steer_center()

        elapsed_ms = self._ticks_diff_ms(self._ticks_ms(), start_ms)
        return {
            "status": "ok" if reason == "target_distance" else "stopped",
            "reason": reason,
            "target_m": target_m,
            "speed_mps": speed_mps,
            "throttle": power,
            "planned_ms": planned_ms,
            "elapsed_ms": elapsed_ms,
            "timed_distance_m": timed_distance_m,
            "imu_distance_m": imu_distance_m,
            "imu_status": imu_status,
            "heading_ref": self._target_heading_deg,
            "heading_est": self._estimated_heading_deg,
        }

    def drive(self, throttle, steering_angle=None):
        throttle = self._clamp_power(throttle)

        if steering_angle is None:
            steering_angle = self.center_angle
        else:
            steering_angle = int(steering_angle)
        self._last_commanded_angle = self._clamp_angle(steering_angle)

        if throttle > 0:
            self.forward(throttle)
        elif throttle < 0:
            self.backward(-throttle)
        else:
            self.stop()

        # Only apply heading hold when roughly driving straight.
        final_angle = self._last_commanded_angle
        if self.imu_ref and abs(self._last_commanded_angle - self.center_angle) <= 2 and throttle != 0:
            if self._target_heading_deg is None:
                self.reset_heading_reference()
            final_angle = self._last_commanded_angle + self._pid_correction_deg()
        else:
            # When intentionally steering away from center, clear heading hold integral windup.
            self._heading_integral = 0.0
            self._heading_prev_error = 0.0
            if abs(self._last_commanded_angle - self.center_angle) > 2 and self.imu_ref:
                self._target_heading_deg = None

        final_angle = self._apply_steering(final_angle)

        return {
            "mode": "ackermann",
            "throttle": throttle,
            "commanded_steering_angle": self._last_commanded_angle,
            "steering_angle": final_angle,
            "imu_ref": self.imu_ref,
            "heading_ref": self._target_heading_deg,
            "heading_est": self._estimated_heading_deg,
        }

    def update(self):
        """
        Call this regularly from the user loop when using imu_ref=True.
        It refreshes the heading estimate and reapplies straight-line correction.
        """
        self._update_heading_estimate()
        if self.imu_ref and self._last_throttle != 0 and abs(self._last_commanded_angle - self.center_angle) <= 2:
            corrected = self._last_commanded_angle + self._pid_correction_deg()
            self._apply_steering(corrected)
        return {
            "heading_ref": self._target_heading_deg,
            "heading_est": self._estimated_heading_deg,
            "last_throttle": self._last_throttle,
            "last_angle": self._last_angle,
            "last_commanded_angle": self._last_commanded_angle,
        }
