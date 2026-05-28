# Color Match Details

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
