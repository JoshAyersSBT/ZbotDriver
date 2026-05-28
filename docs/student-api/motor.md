# Motor

Use `zbot.motor(port)` to control one motor port directly.

```python
left = zbot.motor(1)

left.on(50)
left.on(-50)
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
m1 = zbot.motor(1)
m1.on(75)

status = m1.value()
zbot.notify("M1 {}".format(status.get("power")))
```

You can pass a motor type label when constructing the wrapper. This is recorded
in status metadata for user code and tools.

```python
arm = zbot.motor(3, motor_type="arm")
arm.on(25)
```
