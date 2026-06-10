# Status Snapshots

The status helpers return dictionaries with the latest runtime state:

```python
async def main(zbot):
    import uasyncio as asyncio

    while True:
        all_status = zbot.status()
        motors = zbot.motor_status()
        feedback = zbot.motor_feedback()
        servos = zbot.servo_status()
        sensors = zbot.sensors()
        buttons = zbot.button_status()
        imu = zbot.imu()

        # Snapshot dictionaries are best for debugging and dashboards.
        # Keep normal robot behavior on the simpler wrappers when possible.
        zbot.notify("ready={}".format(all_status["system"]["ready"]))
        zbot.notify("motors={}".format(motors))
        zbot.notify("servos={}".format(servos))

        await asyncio.sleep_ms(1000)
```

These are useful for debugging and dashboards. For normal robot behavior, prefer
the direct wrappers like `zbot.motor(1)`, `zbot.button(1)`, and `zbot.tof(1)`.
