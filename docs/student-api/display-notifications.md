# Display And Notifications

Show text on the OLED:

```python
async def main(zbot):
    import uasyncio as asyncio

    # display() accepts up to four short lines for the OLED.
    ok = zbot.display("Line 1", "Line 2", "Line 3", "Line 4")

    # The return value tells you whether an OLED was available.
    if not ok:
        zbot.notify("OLED not available")

    await asyncio.sleep_ms(1000)
```

`zbot.say()` is an alias for `zbot.display()`.

Send a message over the active telemetry link:

```python
async def main(zbot):
    # notify() sends a line over the active telemetry/debug channel.
    # It is useful for logs that are too detailed for the small OLED.
    zbot.notify("Hello from user code")
```

`display()` returns `True` when the OLED is available. `notify()` returns `True`
when a telemetry connection is available.
