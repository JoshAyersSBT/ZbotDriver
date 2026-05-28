# Driving

The top-level driving helpers use the default runtime drive bridge.

```python
zbot.forward(50)
zbot.backward(30)
zbot.drive(40, 0)
zbot.drive(40, 25)
zbot.tank(50, 20)
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
