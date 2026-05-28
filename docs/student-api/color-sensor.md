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

## Raw RGB Readings

If you need the raw color sensor values, use `zbot.rgb(port)` or
`zbot.sensor(port).rgb()`.

```python
rgb = zbot.rgb(2)

if rgb is not None:
    red = rgb["r"]
    green = rgb["g"]
    blue = rgb["b"]
    clear = rgb["clear"]
```

Raw RGB readings are useful for calibration, debugging, or checking how lighting
affects the sensor.

## Color Match Details

Use `color_match()` when you want the matched color plus debugging details.

```python
match = zbot.sensor(2).color_match()

if match is not None:
    zbot.notify("{} {}".format(match["color"], match["confidence"]))
```

`color_match()` returns a dictionary like:

```python
{
    "color": "red",
    "confidence": 92,
    "rgb": {"r": 210, "g": 35, "b": 28, "clear": 310},
    "normalized": {"r": 196, "g": 32, "b": 26},
    "range": {
        "center": (255, 0, 0),
        "min": (165, 0, 0),
        "max": (255, 90, 90),
        "tolerance": 90,
    },
}
```

`confidence` is a rough score from `0` to `100`. It is meant for quick robot
logic and debugging, not precise color science.

## 32-Color Palette

The built-in palette currently includes:

```text
black, white, silver, gray,
red, maroon, orange, coral, salmon, brown, tan,
yellow, gold, olive, lime, chartreuse, green, spring_green,
cyan, turquoise, teal, azure, sky_blue, blue, navy,
indigo, purple, violet, lavender, magenta, pink, rose
```

Use these exact names with `zbot.color(port)` comparisons or
`zbot.sensor(port).is_color(name)`.
