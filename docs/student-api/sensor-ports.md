# Sensor Ports

Sensor ports are numbered `1` through `6`. The sensor hub scans enabled ports and
auto-detects supported I2C sensors.

The current supported sensor types are:

- VL53L0X / VL53L1X time-of-flight distance sensors
- TCS3472 color sensors

Example port check:

```python
async def main(zbot):
    import uasyncio as asyncio

    while True:
        sensors = zbot.sensors()

        for port in range(1, 7):
            # Each port has a state item even when no sensor is found.
            item = sensors.get("port_{}_state".format(port), {})
            state = item.get("value", "unknown")
            zbot.notify("port {}: {}".format(port, state))

        await asyncio.sleep_ms(1000)
```
