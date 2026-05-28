# Differential Drive

Use `robot.differential.DifferentialDrive` when your robot has separate left and
right drive motors.

```python
from robot.differential import DifferentialDrive

drive = DifferentialDrive(zbot, left_port=1, right_port=2)

drive.forward(50)
drive.drive(40, 20)
drive.tank(60, 30)
drive.stop()
```

Differential drive methods:

- `forward(power)`: drive both motors forward
- `backward(power)`: drive both motors backward
- `drive(throttle, turn)`: mix throttle and turn into left/right power
- `tank(left_power, right_power)`: set left and right motor power directly
- `stop()`: stop both motors
- `status()`: return the last commanded drive state
