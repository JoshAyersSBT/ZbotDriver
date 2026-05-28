# Status Snapshots

The status helpers return dictionaries with the latest runtime state:

```python
all_status = zbot.status()
motors = zbot.motor_status()
feedback = zbot.motor_feedback()
servos = zbot.servo_status()
sensors = zbot.sensors()
buttons = zbot.button_status()
imu = zbot.imu()
```

These are useful for debugging and dashboards. For normal robot behavior, prefer
the direct wrappers like `zbot.motor(1)`, `zbot.button(1)`, and `zbot.tof(1)`.
