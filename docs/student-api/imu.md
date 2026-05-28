# IMU

Use `zbot.imu()` to read the latest IMU snapshot.

```python
imu = zbot.imu()

if imu:
    value = imu.get("value", {})
    gz = value.get("gz_dps")
```

The exact fields depend on the IMU driver payload. Use the full snapshot while
debugging to see what is available.
