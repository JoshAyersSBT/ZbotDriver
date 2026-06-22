# Ackermann Drive

Use `robot.ackermann.AckermannDrive` when your robot has a drive motor and a
steering servo.

```python
async def main(zbot):
    import uasyncio as asyncio
    from robot.ackermann import AckermannDrive

    # Use this helper when one motor drives the car and a servo steers it.
    car = AckermannDrive(
        zbot,
        drive_motor_port=1,
        steering_port=2,
        center_angle=90,
        min_angle=45,
        max_angle=135,
    )

    try:
        # Start centered before moving.
        car.steer_center()
        await asyncio.sleep_ms(500)

        # Drive forward and steer right.
        car.forward(40)
        car.steer(110)
        await asyncio.sleep_ms(1000)

        # drive(throttle, steering_angle) sets speed and steering together.
        car.drive(50, 90)
        await asyncio.sleep_ms(1000)

    finally:
        car.stop()
        car.steer_center()
```

Ackermann drive methods:

- `forward(power)`: drive forward
- `backward(power)`: drive backward
- `drive(throttle, steering_angle)`: set drive power and steering angle
- `start_straight(throttle)`: center steering, reset the IMU heading reference, and begin straight driving
- `drive_straight(throttle)`: keep driving straight with IMU heading hold
- `steer(angle)`: set the steering angle
- `steer_center()`: move steering to the configured center angle
- `stop()`: stop the drive motor

Ackermann drive also supports optional IMU heading reference:

```python
async def main(zbot):
    import uasyncio as asyncio
    from robot.ackermann import AckermannDrive

    car = AckermannDrive(zbot, 1, 2, imu_ref=True)

    try:
        # Heading reference is captured when straight-line driving starts.
        car.start_straight(40)

        while True:
            # Reapply the centered command often. The helper keeps the servo
            # correction separate from the commanded straight-ahead angle.
            car.drive_straight(40)
            await asyncio.sleep_ms(20)

    finally:
        car.stop()
```

When using straight-line heading hold, call `drive_straight()` regularly from
the driving loop. `update()` is still available when you want to refresh IMU
correction without re-commanding motor power.
