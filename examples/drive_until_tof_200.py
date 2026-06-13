async def main(zbot):
    import uasyncio as asyncio
    from robot.ackermann import AckermannDrive

    front_port = 1
    stop_distance_mm = 200
    drive_power = 30
    car = AckermannDrive(
        zbot,
        drive_motor_port=2,
        steering_port=1,
        center_angle=90,
    )

    try:
        car.steer_center()

        while True:
            distance_mm = zbot.tof(front_port)

            if distance_mm is None:
                car.stop()
                zbot.display("ToF", "waiting")

            elif distance_mm <= stop_distance_mm:
                car.stop()
                zbot.display("Stopped", "{} mm".format(distance_mm))
                break

            else:
                car.drive(drive_power, 90)
                zbot.display("Forward", "{} mm".format(distance_mm))

            await asyncio.sleep_ms(100)

    finally:
        car.stop()
        car.steer_center()
