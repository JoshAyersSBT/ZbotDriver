# Sensor Notes

- Sensor readings may be `None` briefly at startup while the hub scans ports.
- Color readings depend on lighting, distance from the surface, and the material
  being measured.
- For best color results, keep the sensor close to the target and avoid shadows
  or bright reflections.

Example robust sensor loop:

```python
async def main(zbot):
    import uasyncio as asyncio

    while True:
        # Read sensors every loop, then handle missing values explicitly.
        # This keeps startup and unplugged-sensor behavior predictable.
        distance = zbot.tof(1)
        color = zbot.color(2)

        if distance is None:
            zbot.display("Distance", "not ready")
        elif distance < 200:
            zbot.display("Too close", "{} mm".format(distance))
            zbot.stop()

        if color is None:
            zbot.notify("color sensor not ready")
        else:
            zbot.notify("color={}".format(color))

        await asyncio.sleep_ms(100)
```
