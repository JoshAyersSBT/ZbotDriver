async def main(zbot):
    import uasyncio as asyncio
    from robot.ackermann import AckermannDrive

    color_sensor_port = 1
    stop_color = "red"
    drive_power = 35

    car = AckermannDrive(
        zbot,
        drive_motor_port=1,
        steering_port=4,
        center_angle=90,
    )

    zbot.display("Color stop", "Find {}".format(stop_color))
    car.steer_center()
    car.forward(drive_power)

    try:
        while True:
            color = zbot.color(color_sensor_port)
            print("I see:", color)

            if color == stop_color:
                car.stop()
                zbot.display("Stopped", "Saw {}".format(stop_color))
                break

            await asyncio.sleep_ms(100)

    finally:
        car.stop()
