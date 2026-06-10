async def main(zbot):
    import time
    import uasyncio as asyncio

    steering = zbot.servo(1)
    drive_motor = zbot.motor(2)
    color_sensor = zbot.sensor(1)
    last_seen = None

    async def wait_and_watch(ms):
        nonlocal last_seen
        end_ms = time.ticks_add(time.ticks_ms(), int(ms))

        while time.ticks_diff(end_ms, time.ticks_ms()) > 0:
            color = color_sensor.color()

            if color is not None:
                color = color.lower()

                if color == "blue" and last_seen != "blue":
                    last_seen = "blue"
                    print("seen blue")
                    zbot.display("seen blue")

                elif color == "red" and last_seen != "red":
                    last_seen = "red"
                    print("seen red")
                    zbot.display("seen red")

            await asyncio.sleep_ms(100)

    try:
        zbot.display("Drive test", "Center")
        steering.center(90)
        drive_motor.off()
        await wait_and_watch(1000)

        zbot.display("Drive test", "Forward")
        steering.angle(90)
        drive_motor.on(35)
        await wait_and_watch(1000)

        zbot.display("Drive test", "Stop")
        drive_motor.off()
        await wait_and_watch(1000)

        zbot.display("Drive test", "Turn left")
        steering.angle(60)
        drive_motor.on(30)
        await wait_and_watch(1000)

        zbot.display("Drive test", "Stop")
        drive_motor.off()
        await wait_and_watch(700)

        zbot.display("Drive test", "Turn right")
        steering.angle(120)
        drive_motor.on(30)
        await wait_and_watch(1000)

        drive_motor.off()
        steering.center(90)
        zbot.display("Drive test", "Done")

    finally:
        drive_motor.off()
        steering.center(90)
