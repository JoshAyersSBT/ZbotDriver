# Ackermann Drive

Use `robot.ackermann.AckermannDrive` when your robot has a drive motor and a
steering servo.

```python
from robot.ackermann import AckermannDrive

car = AckermannDrive(
    zbot,
    drive_motor_port=1,
    steering_port=2,
    center_angle=90,
    min_angle=45,
    max_angle=135,
)

car.forward(40)
car.steer(110)
car.drive(50, 90)
car.stop()
```

Ackermann drive methods:

- `forward(power)`: drive forward
- `backward(power)`: drive backward
- `drive(throttle, steering_angle)`: set drive power and steering angle
- `steer(angle)`: set the steering angle
- `steer_center()`: move steering to the configured center angle
- `stop()`: stop the drive motor

Ackermann drive also supports optional IMU heading reference:

```python
car = AckermannDrive(zbot, 1, 2, imu_ref=True)
car.forward(40)

while True:
    car.update()
```

Call `update()` regularly when `imu_ref=True` so the drive helper can refresh
the heading estimate.
