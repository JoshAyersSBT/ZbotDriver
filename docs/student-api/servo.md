# Servo

Use `zbot.servo(port)` to control a servo on an actuator port.

```python
servo = zbot.servo(1)
servo.angle(90)
servo.center()
```

Servo wrapper methods:

- `angle(deg)`: move the servo to an angle in degrees
- `write_angle(deg)`: alias for `angle(deg)`
- `center()`: move to the configured center angle for that port
- `center(center_angle)`: move to a provided center angle

The top-level steering helper controls the configured steering servo:

```python
zbot.steer(90)
```
