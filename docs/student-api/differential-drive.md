# Differential Drive

Use `robot.differential.DifferentialDrive` when your robot has separate left and
right drive motors.

```python
async def main(zbot):
    import uasyncio as asyncio
    from robot.differential import DifferentialDrive

    # Use this helper when the robot turns by driving the left and right
    # motors at different speeds.
    drive = DifferentialDrive(zbot, left_port=1, right_port=2)

    try:
        # Both motors forward.
        drive.forward(50)
        await asyncio.sleep_ms(1000)

        # Mixed driving: throttle is forward/backward, turn is left/right.
        drive.drive(40, 20)
        await asyncio.sleep_ms(1000)

        # Tank driving: set each side directly.
        drive.tank(60, 30)
        await asyncio.sleep_ms(1000)

        zbot.notify("drive status {}".format(drive.status()))

    finally:
        drive.stop()
```

Differential drive methods:

- `forward(power)`: drive both motors forward
- `backward(power)`: drive both motors backward
- `drive(throttle, turn)`: mix throttle and turn into left/right power
- `tank(left_power, right_power)`: set left and right motor power directly
- `stop()`: stop both motors
- `status()`: return the last commanded drive state
