# Color Sensor

Use `zbot.color(port)` to read the nearest color name from the 32-color range
palette. This avoids needing to match an exact raw RGB value.

```python
color = zbot.color(2)

if color == "red":
    zbot.stop()
```

The direct wrapper has the same helper:

```python
floor = zbot.sensor(2)

if floor.is_color("blue"):
    zbot.notify("Blue marker")
```

Color matching is case-insensitive when using `is_color()`.
