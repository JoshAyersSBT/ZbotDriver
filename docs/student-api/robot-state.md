# Robot State

Check whether the robot runtime is ready:

```python
async def main(zbot):
    import uasyncio as asyncio

    while not zbot.ready():
        # Most programs start after the runtime is ready, but this pattern is
        # useful in shared helper code.
        await asyncio.sleep_ms(50)

    zbot.notify("Ready")
```

Stop all motors:

```python
async def main(zbot):
    # stop() stops all active motor ports controlled by the runtime.
    zbot.stop()
```
