# Motor

Use `zbot.motor(port)` to control one motor port directly.

```python
async def main(zbot):
    import uasyncio as asyncio

    left = zbot.motor(1)

    try:
        # Positive power turns the motor forward.
        left.on(50)
        await asyncio.sleep_ms(800)

        # Negative power reverses the motor.
        left.on(-50)
        await asyncio.sleep_ms(800)

    finally:
        # Stop this motor even if an exception interrupts the program.
        left.off()
```

Motor ports are numbered by the configured motor map. The default physical motor
ports are `1` through `4`.

Motor wrapper methods:

- `on(power)`: set motor power from `-100` to `100`
- `speed(power)`: alias for `on(power)`
- `set(power)`: alias for `on(power)`
- `off()`: stop the motor
- `stop()`: alias for `off()`
- `value()`: return the latest status dictionary for that motor

Example:

```python
async def main(zbot):
    import uasyncio as asyncio

    m1 = zbot.motor(1)
    m1.on(75)
    await asyncio.sleep_ms(500)

    # value() reads the latest status for the wrapper's motor port.
    status = m1.value()
    zbot.notify("M1 {}".format(status.get("power")))

    m1.stop()
```

You can pass a motor type label when constructing the wrapper. This is recorded
in status metadata for user code and tools.

```python
arm = zbot.motor(3, motor_type="arm")
arm.on(25)
```
