# IMU

Use `zbot.imu()` to read the latest IMU snapshot. The robot uses an
MPU-6050, so each scaled reading contains acceleration, gyro rotation rate, and
temperature:

```python
{
    "ax_g": -0.291,
    "ay_g": 0.082,
    "az_g": 0.983,
    "gx_dps": -0.809,
    "gy_dps": 2.702,
    "gz_dps": -0.099,
    "temp_c": 43.92,
}
```

Field meanings:

- `ax_g`, `ay_g`, `az_g`: acceleration on the X, Y, and Z axes, in g.
- `gx_dps`, `gy_dps`, `gz_dps`: rotation rate around the X, Y, and Z axes, in
  degrees per second.
- `temp_c`: IMU chip temperature, in degrees Celsius.

`zbot.imu()` wraps this payload in a snapshot dictionary:

```python
async def main(zbot):
    import uasyncio as asyncio

    while True:
        # imu() refreshes and returns the latest IMU snapshot.
        # It may be empty during startup or if no IMU is configured.
        imu = zbot.imu()

        if imu:
            value = imu.get("value", {})
            gz = value.get("gz_dps")

            if gz is not None:
                zbot.display("Gyro Z", "{} dps".format(gz))

        await asyncio.sleep_ms(100)
```

## Pitch, roll, and yaw

Pitch and roll can be estimated from gravity when the robot is not accelerating
hard. Yaw is different: the MPU-6050 does not have a compass, so yaw must be
integrated from `gz_dps`. That gives a relative heading that starts at 0 when
your program starts and will slowly drift over time.

```python
async def main(zbot):
    import math
    import time
    import uasyncio as asyncio

    yaw = 0.0
    last_ms = time.ticks_ms()
    rad_to_deg = 180 / math.pi

    while True:
        imu = zbot.imu()
        value = imu.get("value", {}) if imu else {}

        ax = value.get("ax_g")
        ay = value.get("ay_g")
        az = value.get("az_g")
        gz = value.get("gz_dps")

        if ax is not None and ay is not None and az is not None:
            roll = math.atan2(ay, az) * rad_to_deg
            pitch = math.atan2(-ax, math.sqrt(ay * ay + az * az)) * rad_to_deg

            now_ms = time.ticks_ms()
            dt_s = time.ticks_diff(now_ms, last_ms) / 1000
            last_ms = now_ms

            if gz is not None:
                yaw += gz * dt_s

            zbot.display("IMU", "P:{:.1f} R:{:.1f} Y:{:.1f}".format(
                pitch,
                roll,
                yaw,
            ))

        await asyncio.sleep_ms(50)
```

For serial or BLE debugging, the background IMU task also emits lines in this
order:

```text
IMU ax_g ay_g az_g gx_dps gy_dps gz_dps temp_c
```

For example:

```text
IMU -0.291 0.082 0.983 -0.809 2.702 -0.099 43.92
```

## Live turn radius

Turn radius needs two things:

- forward speed, in meters per second
- yaw rate from `gz_dps`, converted from degrees per second to radians per
  second

The formula is:

```text
turn_radius_m = speed_mps / yaw_rate_rad_s
```

The IMU gives yaw rate, but it does not know how fast the robot is moving
across the floor. Start with a measured speed for the drive power you use. For
example, if the robot travels 1 meter in 2.5 seconds at power 40, use
`SPEED_MPS = 0.4`.

`zbot.start_turn()` starts the runtime drive bridge turning and turns on live
radius measurement. `zbot.turn_radius()` returns the latest radius state.

```python
async def main(zbot):
    import uasyncio as asyncio

    # Replace this with your button/BLE/program trigger.
    zbot.start_turn(
        speed_mps=0.4,
        drive_power=40,
        turn=35,
    )

    try:
        while True:
            turn = zbot.turn_radius()

            if turn.get("status") == "ok":
                zbot.say(
                    "Turn radius",
                    "{:.2f} m".format(turn["radius_m"]),
                    "yaw {:.1f} dps".format(turn["yaw_rate_dps"]),
                )
            else:
                zbot.say("Turn radius", turn.get("status", "waiting"))

            await asyncio.sleep_ms(100)

    finally:
        zbot.stop_turn()
```

For better numbers, measure `SPEED_MPS` for the same battery level, surface,
drive power, and robot build.

`zbot.turn_radius()` returns a dictionary like:

```python
{
    "active": True,
    "status": "ok",
    "radius_m": 1.24,
    "diameter_m": 2.48,
    "speed_mps": 0.4,
    "yaw_rate_dps": 18.5,
    "yaw_rate_rad_s": 0.323,
}
```

When the robot is not turning fast enough, `status` is `"waiting"` and
`radius_m` is `None`.

## Turn 90 degrees

To turn a specific angle, integrate the Z gyro rate over time. The example
below turns until the robot has rotated about 90 degrees, then stops.

```python
async def main(zbot):
    import time
    import uasyncio as asyncio

    TARGET_DEG = 90
    DRIVE_POWER = 35
    TURN = 45
    GYRO_DEADBAND_DPS = 1.0

    heading = 0.0
    last_ms = time.ticks_ms()

    zbot.drive(DRIVE_POWER, TURN)

    try:
        while abs(heading) < TARGET_DEG:
            imu = zbot.imu()
            value = imu.get("value", {}) if imu else {}
            gz = value.get("gz_dps")

            now_ms = time.ticks_ms()
            dt_s = time.ticks_diff(now_ms, last_ms) / 1000
            last_ms = now_ms

            if gz is not None:
                if -GYRO_DEADBAND_DPS < gz < GYRO_DEADBAND_DPS:
                    gz = 0.0
                heading += gz * dt_s

            zbot.say("Turning", "{:.1f} deg".format(heading))
            await asyncio.sleep_ms(20)

    finally:
        zbot.stop()
        zbot.say("Turn done", "{:.1f} deg".format(heading))
```

Use a negative `TURN` value to turn the other direction. If your robot tends to
overshoot, lower `DRIVE_POWER` or `TURN`, or stop a few degrees early.
