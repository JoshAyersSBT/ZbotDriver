# Safety

Always stop motors when your program exits or hits an error condition.

```python
async def main(zbot):
    import uasyncio as asyncio

    try:
        zbot.forward(40)

        while True:
            # Put the robot's normal behavior here.
            # Sleeping keeps the runtime cooperative and lets sensor/button
            # background tasks continue to run.
            await asyncio.sleep_ms(50)

    finally:
        # This is the most important line in almost every movement program.
        zbot.stop()
```

This makes user code much friendlier during testing.
