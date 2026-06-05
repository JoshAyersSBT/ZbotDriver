# Full Sensor Snapshot

For advanced code, use `zbot.sensors()` to get the full sensor snapshot.

```python
sensors = zbot.sensors()
color_item = sensors.get("color_port_2")
tof_item = sensors.get("tof_port_1")
```

Color snapshots keep backward-compatible raw RGB values and add matched color
metadata:

```python
{
    "value": {
        "r": 210,
        "g": 35,
        "b": 28,
        "clear": 310,
        "color": "red",
        "confidence": 92,
        "normalized": {"r": 196, "g": 32, "b": 26},
    },
    "meta": {
        "kind": "TCS3472",
        "port": 2,
        "palette": "COLOR_PALETTE_32",
        "range": {"center": (255, 0, 0), "min": (165, 0, 0), "max": (255, 90, 90), "tolerance": 90},
    },
}
```

Calibration changes the result of helpers like `zbot.color(port)` and
`zbot.sensor(port).color_match()`. The raw snapshot still reports the built-in
palette match so advanced code can inspect both behaviors if needed.

Distance snapshots look like:

```python
{
    "value": 245,
    "meta": {"kind": "VL53L0X", "port": 1, "unit": "mm"},
}
```
