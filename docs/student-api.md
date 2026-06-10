# Student API

Student programs use the global `zbot` object to control ZebraBot. The helpers
are designed for simple scripts first, with lower-level status snapshots
available when you need more detail.

```python
async def main(zbot):
    import uasyncio as asyncio

    zbot.display("Driving")
    zbot.forward(40)
    await asyncio.sleep_ms(1000)
    zbot.stop()
```

Each API topic has its own page:

- [ZebraBoard overview](board-overview.md)
- [Overview](student-api/overview.md)
- [Robot state](student-api/robot-state.md)
- [Driving](student-api/driving.md)
- [Motor](student-api/motor.md)
- [Servo](student-api/servo.md)
- [Differential drive](student-api/differential-drive.md)
- [Ackermann drive](student-api/ackermann-drive.md)
- [Button](student-api/button.md)
- [Display and notifications](student-api/display-notifications.md)
- [Sensors](student-api/sensors.md)
- [Sensor ports](student-api/sensor-ports.md)
- [Distance sensor](student-api/distance-sensor.md)
- [Color sensor](student-api/color-sensor.md)
- [Full sensor snapshot](student-api/sensor-snapshot.md)
- [Sensor notes](student-api/sensor-notes.md)
- [IMU](student-api/imu.md)
- [Status snapshots](student-api/status-snapshots.md)
- [Safety](student-api/safety.md)
