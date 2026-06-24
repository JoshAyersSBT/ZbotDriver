# Distance Sensor

Use `zbot.tof(port)` for a quick distance reading in millimeters.

```python
async def main(zbot):
    import uasyncio as asyncio

    front_port = 1

    try:
        while True:
            # tof(port) returns the latest distance in millimeters.
            # It returns None while the sensor hub is still detecting the port
            # or if no supported distance sensor is connected.
            distance_mm = zbot.tof(front_port)

            if distance_mm is None:
                status = zbot.sensor_status(front_port)
                zbot.display(
                    "Front sensor",
                    status.get("state", "waiting"),
                    status.get("kind", ""),
                )

            elif distance_mm < 200:
                # Stop when an object is closer than 200 mm.
                zbot.display("Obstacle", "{} mm".format(distance_mm))
                zbot.stop()

            else:
                zbot.display("Clear", "{} mm".format(distance_mm))
                zbot.forward(25)

            # Let the background sensor scanner update before reading again.
            await asyncio.sleep_ms(100)

    finally:
        zbot.stop()
```

You can also use the sensor wrapper directly:

```python
front = zbot.sensor(1)
distance_mm = front.read()
status = front.status()
```

`tof()` and `sensor(port).read()` return:

- an integer distance in millimeters when a distance sensor is available
- `None` when no distance reading is available yet

When `tof()` returns `None`, call `zbot.sensor_status(port)` or
`zbot.sensor(port).status()` to see whether the port is still detecting, empty,
unidentified, missing a driver, failing probe, or returning invalid readings.
