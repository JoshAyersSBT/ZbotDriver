async def main(zbot):
    import time
    import uasyncio as asyncio
    from robot.ackermann import AckermannDrive

    FEET_TO_METERS = 0.3048

    DRIVE_MOTOR_PORT = 2
    STEERING_PORT = 1
    CENTER_ANGLE = 90
    RIGHT_TURN_ANGLE = 120

    DRIVE_POWER = 35
    TURN_POWER = 30
    FORWARD_DISTANCE_M = 6 * FEET_TO_METERS
    RIGHT_TURN_DEG = 90

    LOOP_MS = 20
    GYRO_DEADBAND_DPS = 1.0
    MAX_FORWARD_MS = 12000
    IMU_PROGRESS_TIMEOUT_MS = 1500
    IMU_PROGRESS_EPSILON_M = 0.01
    MAX_TURN_MS = 6000

    car = AckermannDrive(
        zbot,
        drive_motor_port=DRIVE_MOTOR_PORT,
        steering_port=STEERING_PORT,
        center_angle=CENTER_ANGLE,
        imu_ref=True,
    )

    def gyro_z_dps():
        imu = zbot.imu()
        value = imu.get("value", {}) if imu else {}
        gz = value.get("gz_dps")
        if gz is None:
            return 0.0
        if -GYRO_DEADBAND_DPS < gz < GYRO_DEADBAND_DPS:
            return 0.0
        return float(gz)

    async def drive_forward_distance(distance_m):
        zbot.reset_imu_distance()
        car.steer_center()
        await asyncio.sleep_ms(300)

        car.enable_imu_reference(True, reset_reference=True)
        car.drive(DRIVE_POWER, CENTER_ANGLE)

        start_ms = time.ticks_ms()
        last_progress_ms = start_ms
        last_traveled_m = 0.0
        while True:
            car.update()
            dist = zbot.imu_distance()
            traveled_m = float(dist.get("distance_m", 0.0))

            zbot.display(
                "Forward",
                "{:.2f}/{:.2f} m".format(traveled_m, distance_m),
                "IMU hold",
            )

            if traveled_m >= distance_m:
                break

            now_ms = time.ticks_ms()
            if traveled_m > last_traveled_m + IMU_PROGRESS_EPSILON_M:
                last_traveled_m = traveled_m
                last_progress_ms = now_ms

            if time.ticks_diff(now_ms, last_progress_ms) >= IMU_PROGRESS_TIMEOUT_MS:
                zbot.display("Forward", "IMU timeout", "{:.2f} m".format(traveled_m))
                break

            elapsed_ms = time.ticks_diff(now_ms, start_ms)
            if elapsed_ms >= MAX_FORWARD_MS:
                zbot.display("Forward", "timeout", "{:.2f} m".format(traveled_m))
                break

            await asyncio.sleep_ms(LOOP_MS)

        car.stop()
        car.steer_center()
        return zbot.imu_distance()

    async def turn_right_degrees(degrees):
        car.enable_imu_reference(False)
        car.drive(TURN_POWER, RIGHT_TURN_ANGLE)

        turned_abs_deg = 0.0
        last_ms = time.ticks_ms()
        start_ms = last_ms

        while turned_abs_deg < float(degrees):
            now_ms = time.ticks_ms()
            dt_s = time.ticks_diff(now_ms, last_ms) / 1000
            last_ms = now_ms

            turned_abs_deg += abs(gyro_z_dps()) * dt_s
            zbot.display(
                "Right turn",
                "{:.1f}/{:.1f} deg".format(turned_abs_deg, degrees),
                "steer {}".format(RIGHT_TURN_ANGLE),
            )

            if time.ticks_diff(now_ms, start_ms) >= MAX_TURN_MS:
                zbot.display("Right turn", "timeout", "{:.1f} deg".format(turned_abs_deg))
                break

            await asyncio.sleep_ms(LOOP_MS)

        car.stop()
        car.steer_center()
        return turned_abs_deg

    try:
        zbot.display("Ackermann", "6 ft then right")
        await asyncio.sleep_ms(1000)

        forward = await drive_forward_distance(FORWARD_DISTANCE_M)
        await asyncio.sleep_ms(500)

        turned = await turn_right_degrees(RIGHT_TURN_DEG)

        zbot.display(
            "Done",
            "{:.2f} m".format(forward.get("distance_m", 0.0)),
            "{:.1f} deg".format(turned),
        )

    finally:
        car.stop()
        car.steer_center()
