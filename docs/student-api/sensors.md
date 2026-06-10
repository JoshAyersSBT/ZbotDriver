# Sensors

ZebraBot exposes sensors through the global `zbot` object. Plug a sensor into one
of the six sensor ports, then read it by port number from student code.

The most common sensor helpers are:

```python
async def main(zbot):
    import uasyncio as asyncio

    while True:
        # Port 1 has a time-of-flight distance sensor in this example.
        distance = zbot.tof(1)

        # Port 2 has a TCS3472 color sensor in this example.
        color = zbot.color(2)
        rgb = zbot.rgb(2)

        if distance is not None:
            zbot.notify("distance={}mm".format(distance))

        if color is not None:
            zbot.notify("color={}".format(color))

        if rgb is not None:
            zbot.notify("raw={}".format(rgb))

        # Sensor values are updated by a background scanner, so wait briefly
        # before reading again.
        await asyncio.sleep_ms(250)
```

Sensor topics:

- [Sensor ports](sensor-ports.md)
- [Distance sensor](distance-sensor.md)
- [Color sensor](color-sensor.md)
- [Full sensor snapshot](sensor-snapshot.md)
- [Sensor notes](sensor-notes.md)
