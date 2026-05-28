# Distance Sensor

Use `zbot.tof(port)` for a quick distance reading in millimeters.

```python
distance_mm = zbot.tof(1)

if distance_mm is not None and distance_mm < 200:
    zbot.stop()
```

You can also use the sensor wrapper directly:

```python
front = zbot.sensor(1)
distance_mm = front.read()
```

`tof()` and `sensor(port).read()` return:

- an integer distance in millimeters when a distance sensor is available
- `None` when no distance reading is available yet
