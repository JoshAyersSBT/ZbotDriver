# Raw RGB Readings

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
