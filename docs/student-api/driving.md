# Driving

The top-level driving helpers use the default runtime drive bridge.

```python
async def main(zbot):
    import uasyncio as asyncio

    try:
        # Drive straight forward at 50 percent power.
        zbot.forward(50)
        await asyncio.sleep_ms(1000)

        # Drive backward at 30 percent power.
        zbot.backward(30)
        await asyncio.sleep_ms(800)

        # drive(throttle, turn): positive throttle moves forward,
        # and positive turn asks the runtime bridge to steer/turn right.
        zbot.drive(40, 25)
        await asyncio.sleep_ms(800)

        # tank(left, right) is kept for differential-style compatibility.
        # On the default runtime bridge it is converted to throttle/turn.
        zbot.tank(50, 20)
        await asyncio.sleep_ms(800)

    finally:
        # The finally block runs even if the program is interrupted by an error.
        zbot.stop()
```

`zbot.drive(throttle, turn)` takes:

- `throttle`: forward/backward power from `-100` to `100`
- `turn`: steering/turn command from `-100` to `100`

`zbot.tank(left_power, right_power)` is a compatibility helper. It converts left
and right motor powers into a throttle/turn command for the runtime bridge.

For custom robot layouts, prefer one of the drive model helpers:

- [Differential drive](differential-drive.md)
- [Ackermann drive](ackermann-drive.md)
