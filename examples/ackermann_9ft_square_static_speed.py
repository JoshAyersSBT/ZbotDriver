async def main(zbot):
    import time
    import uasyncio as asyncio
    from robot.ackermann import AckermannDrive

    FEET_TO_METERS = 0.3048

    DRIVE_MOTOR_PORT = 2
    STEERING_PORT = 1
    CENTER_ANGLE = 90
    RIGHT_TURN_ANGLE = 132

    DRIVE_POWER = 35
    TURN_POWER = 30

    SQUARE_SIDE_FT = 9
    SIDE_DISTANCE_M = SQUARE_SIDE_FT * FEET_TO_METERS

    # Measured: 124 cm in 10.13 seconds.
    CAL_DISTANCE_M = 1.24
    CAL_TIME_S = 10.13
    CALIBRATED_SPEED_MPS = CAL_DISTANCE_M / CAL_TIME_S

    TURN_90_DEG = 90
    START_DELAY_S = 5
    LOOP_MS = 20
    GYRO_DEADBAND_DPS = 1.0

    # At the measured speed, one 9 ft side is about 22.4 seconds.
    MAX_SIDE_MS = 45000
    MAX_TURN_MS = 8000

    car = AckermannDrive(
        zbot,
        drive_motor_port=DRIVE_MOTOR_PORT,
        steering_port=STEERING_PORT,
        center_angle=CENTER_ANGLE,
        imu_ref=True,
        kp=1.1,
        kd=0.08,
        max_correction_deg=18,
        gyro_deadband_dps=GYRO_DEADBAND_DPS,
    )

    def show(line1, line2="", line3=""):
        zbot.display(line1, line2, line3)
        print("SQUARE_9FT:", line1, line2, line3)

    def gyro_z_dps():
        imu = zbot.imu()
        value = imu.get("value", {}) if imu else {}
        gz = value.get("gz_dps")
        if gz is None:
            return 0.0
        if -GYRO_DEADBAND_DPS < gz < GYRO_DEADBAND_DPS:
            return 0.0
        return float(gz)

    async def stop_and_center():
        car.stop()
        car.steer_center()
        await asyncio.sleep_ms(250)

    async def drive_side(index):
        show(
            "Side {}".format(index),
            "{:.2f} m".format(SIDE_DISTANCE_M),
            "{:.3f} m/s".format(CALIBRATED_SPEED_MPS),
        )

        planned_ms = int((SIDE_DISTANCE_M / CALIBRATED_SPEED_MPS) * 1000)
        start_ms = time.ticks_ms()
        timed_distance_m = 0.0
        reason = "target_distance"

        if hasattr(zbot, "reset_imu_distance"):
            zbot.reset_imu_distance()

        car.steer_center()
        await asyncio.sleep_ms(250)
        car.enable_imu_reference(True, reset_reference=True)

        try:
            while True:
                now_ms = time.ticks_ms()
                elapsed_ms = time.ticks_diff(now_ms, start_ms)
                timed_distance_m = CALIBRATED_SPEED_MPS * (elapsed_ms / 1000.0)

                # Re-command center each loop so older AckermannDrive versions
                # keep straight-line IMU hold active after steering correction.
                car.drive(DRIVE_POWER, CENTER_ANGLE)
                car.update()

                show(
                    "Side {}".format(index),
                    "{:.2f}/{:.2f} m".format(timed_distance_m, SIDE_DISTANCE_M),
                    "{:.1f}s".format(elapsed_ms / 1000.0),
                )

                if timed_distance_m >= SIDE_DISTANCE_M:
                    break

                if elapsed_ms >= MAX_SIDE_MS:
                    reason = "max_time"
                    break

                await asyncio.sleep_ms(LOOP_MS)

        finally:
            await stop_and_center()

        imu_distance_m = None
        imu_status = "missing"
        if hasattr(zbot, "imu_distance"):
            imu = zbot.imu_distance()
            if isinstance(imu, dict):
                imu_distance_m = imu.get("distance_m")
                imu_status = imu.get("status", "ok")

        result = {
            "reason": reason,
            "target_m": SIDE_DISTANCE_M,
            "speed_mps": CALIBRATED_SPEED_MPS,
            "planned_ms": planned_ms,
            "elapsed_ms": time.ticks_diff(time.ticks_ms(), start_ms),
            "timed_distance_m": timed_distance_m,
            "imu_distance_m": imu_distance_m,
            "imu_status": imu_status,
        }

        show(
            "Side done",
            result.get("reason", "done"),
            "{:.1f}s".format(result.get("elapsed_ms", 0) / 1000.0),
        )
        await asyncio.sleep_ms(500)
        return result

    async def turn_right_90(index):
        show("Turn {}".format(index), "right", "{} deg".format(TURN_90_DEG))
        car.enable_imu_reference(False)
        car.drive(TURN_POWER, RIGHT_TURN_ANGLE)

        turned_abs_deg = 0.0
        last_ms = time.ticks_ms()
        start_ms = last_ms

        try:
            while turned_abs_deg < float(TURN_90_DEG):
                now_ms = time.ticks_ms()
                dt_s = time.ticks_diff(now_ms, last_ms) / 1000.0
                last_ms = now_ms

                turned_abs_deg += abs(gyro_z_dps()) * dt_s
                show(
                    "Turning",
                    "{:.1f}/{:.1f}".format(turned_abs_deg, TURN_90_DEG),
                    "steer {}".format(RIGHT_TURN_ANGLE),
                )

                if time.ticks_diff(now_ms, start_ms) >= MAX_TURN_MS:
                    show("Turn timeout", "{:.1f} deg".format(turned_abs_deg))
                    break

                await asyncio.sleep_ms(LOOP_MS)

        finally:
            await stop_and_center()

        return turned_abs_deg

    try:
        await stop_and_center()

        for seconds_left in range(START_DELAY_S, 0, -1):
            show("Place robot", "9 ft square", "{} sec".format(seconds_left))
            await asyncio.sleep_ms(1000)

        results = []
        turns = []

        for side in range(1, 5):
            results.append(await drive_side(side))
            if side < 4:
                turns.append(await turn_right_90(side))

        show(
            "Square done",
            "speed {:.3f}".format(CALIBRATED_SPEED_MPS),
            "sides {}".format(len(results)),
        )
        print("SQUARE_9FT results:", results)
        print("SQUARE_9FT turns:", turns)

    finally:
        await stop_and_center()
