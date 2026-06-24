async def main(zbot):
    import uasyncio as asyncio
    from robot.ackermann import AckermannDrive

    FEET_TO_METERS = 0.3048

    DRIVE_MOTOR_PORT = 2
    STEERING_PORT = 1
    CENTER_ANGLE = 90

    DRIVE_POWER = 35
    REFERENCE_DISTANCE_FT = 8
    REFERENCE_DISTANCE_M = REFERENCE_DISTANCE_FT * FEET_TO_METERS

    # First guess. After the run, update this using:
    # new_speed = old_speed * actual_distance_m / timed_distance_m
    CALIBRATED_SPEED_MPS = 0.35

    LOOP_MS = 20
    MAX_RUN_MS = 12000
    START_DELAY_S = 5

    car = AckermannDrive(
        zbot,
        drive_motor_port=DRIVE_MOTOR_PORT,
        steering_port=STEERING_PORT,
        center_angle=CENTER_ANGLE,
        imu_ref=True,
        kp=1.1,
        kd=0.08,
        max_correction_deg=18,
        gyro_deadband_dps=1.0,
    )

    def show(line1, line2="", line3=""):
        zbot.display(line1, line2, line3)
        print("CAL_8FT:", line1, line2, line3)

    try:
        car.stop()
        car.steer_center()

        for seconds_left in range(START_DELAY_S, 0, -1):
            show("Place robot", "8 ft reference", "{} sec".format(seconds_left))
            await asyncio.sleep_ms(1000)

        show("Cal drive", "{:.2f} m".format(REFERENCE_DISTANCE_M), "power {}".format(DRIVE_POWER))

        result = await car.drive_straight_distance(
            REFERENCE_DISTANCE_M,
            throttle=DRIVE_POWER,
            speed_mps=CALIBRATED_SPEED_MPS,
            loop_ms=LOOP_MS,
            max_ms=MAX_RUN_MS,
        )

        timed_m = float(result.get("timed_distance_m", 0.0))
        elapsed_s = float(result.get("elapsed_ms", 0)) / 1000.0
        measured_speed_mps = 0.0
        if elapsed_s > 0.0:
            measured_speed_mps = REFERENCE_DISTANCE_M / elapsed_s

        show(
            "Measure stop",
            "entered {:.3f}".format(CALIBRATED_SPEED_MPS),
            "new {:.3f}".format(measured_speed_mps),
        )
        await asyncio.sleep_ms(3000)

        show(
            "Run result",
            result.get("reason", "done"),
            "time {:.2f}s".format(elapsed_s),
        )
        await asyncio.sleep_ms(3000)

        show(
            "IMU",
            result.get("imu_status", "missing"),
            "{:.2f} m".format(result.get("imu_distance_m", 0.0) or 0.0),
        )
        print("CAL_8FT result:", result)
        zbot.display("CAL_8FT result:", result)
        print("CAL_8FT measured_speed_mps:", measured_speed_mps)
        zbot.display("CAL_8FT measured_speed_mps:", measured_speed_mps)
        print("CAL_8FT set CALIBRATED_SPEED_MPS to:", measured_speed_mps)
        zbot.display("CAL_8FT set CALIBRATED_SPEED_MPS to:", measured_speed_mps)

    finally:
        car.stop()
        car.steer_center()
