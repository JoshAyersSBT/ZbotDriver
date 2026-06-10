# IMU

Use `zbot.imu()` to read the latest IMU snapshot.

```python
async def main(zbot):
    import uasyncio as asyncio

    while True:
        # imu() returns the latest snapshot collected by the background IMU
        # task. It may be empty during startup or if no IMU is configured.
        imu = zbot.imu()

        if imu:
            value = imu.get("value", {})

            # Field names depend on the IMU driver payload. Common fields
            # include accel/gyro values such as ax_g, ay_g, az_g, and gz_dps.
            gz = value.get("gz_dps")

            if gz is not None:
                zbot.display("Gyro Z", "{} dps".format(gz))

        await asyncio.sleep_ms(100)
```

The exact fields depend on the IMU driver payload. Use the full snapshot while
debugging to see what is available.
