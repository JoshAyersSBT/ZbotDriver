# Servo

Use `zbot.servo(port)` to control a servo on an actuator port.

```python
async def main(zbot):
    import uasyncio as asyncio

    servo = zbot.servo(1)

    # Move to the configured center first so the mechanism starts in a known
    # position. On the default config, center is 90 degrees.
    servo.center()
    await asyncio.sleep_ms(500)

    # Sweep to two positions, then return to center.
    servo.angle(45)
    await asyncio.sleep_ms(500)

    servo.angle(135)
    await asyncio.sleep_ms(500)

    servo.center()
```

Servo wrapper methods:

- `angle(deg)`: move the servo to an angle in degrees
- `write_angle(deg)`: alias for `angle(deg)`
- `center()`: move to the configured center angle for that port
- `center(center_angle)`: move to a provided center angle

The top-level steering helper controls the configured steering servo:

```python
async def main(zbot):
    # steer() uses the configured steering servo port.
    zbot.steer(90)
```
