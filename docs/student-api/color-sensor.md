# Color Sensor

Use `zbot.color(port)` to read the nearest color name from the 32-color range
palette. This avoids needing to match an exact raw RGB value.

```python
async def main(zbot):
    import uasyncio as asyncio

    floor_port = 2

    try:
        while True:
            # color(port) returns the nearest color name, such as "red" or
            # "blue". It returns None until the color sensor is detected.
            color = zbot.color(floor_port)

            if color is None:
                zbot.display("Color", "waiting")

            elif color == "red":
                zbot.display("Stop line", "red")
                zbot.stop()
                break

            elif color == "blue":
                zbot.display("Marker", "blue")
                zbot.forward(20)

            else:
                zbot.display("Color", color)
                zbot.forward(30)

            await asyncio.sleep_ms(100)

    finally:
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
async def main(zbot):
    import uasyncio as asyncio

    port = 2

    while True:
        # Raw RGB is useful when the named color match is surprising.
        rgb = zbot.rgb(port)

        if rgb is not None:
            red = rgb["r"]
            green = rgb["g"]
            blue = rgb["b"]
            clear = rgb["clear"]
            zbot.notify("R{} G{} B{} C{}".format(red, green, blue, clear))

        await asyncio.sleep_ms(250)
```

Raw RGB readings are useful for calibration, debugging, or checking how lighting
affects the sensor.

## Color Match Details

Use `color_match()` when you want the matched color plus debugging details.

```python
async def main(zbot):
    import uasyncio as asyncio

    floor = zbot.sensor(2)

    while True:
        match = floor.color_match()

        if match is not None:
            zbot.notify("{} {}".format(match["color"], match["confidence"]))

        await asyncio.sleep_ms(250)
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

## Calibration

Use calibration when the built-in color names do not match your lighting,
surface, or sensor height. Put the sensor over a sample surface, call
`calibrate_color()`, then use `zbot.color()` normally.

```python
async def main(zbot):
    import uasyncio as asyncio

    port = 2

    # Place the sensor over each sample before that calibration step runs.
    zbot.display("Calibrate", "Put on red")
    await asyncio.sleep_ms(3000)
    zbot.calibrate_color(port, "red")

    zbot.display("Calibrate", "Put on blue")
    await asyncio.sleep_ms(3000)
    zbot.calibrate_color(port, "blue")

    while True:
        color = zbot.color(port)

        if color == "red":
            zbot.stop()
            break

        await asyncio.sleep_ms(100)
```

Each calibration takes several quick RGB samples and stores the averaged
reference in memory. Calibrated names are checked before the built-in palette.
The same helper is available from a direct sensor wrapper:

```python
floor = zbot.sensor(2)
floor.calibrate_color("line")
floor.calibrate_color("floor")

if floor.is_color("line"):
    zbot.notify("On the line")
```

To inspect or reset the learned references:

```python
refs = zbot.color_calibrations(2)
zbot.clear_color_calibration(2)
```
