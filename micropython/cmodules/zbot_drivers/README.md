# ZebraBot MicroPython C Modules

Native modules for the core ZebraBot runtime drivers.

Build them into a MicroPython firmware with Make:

```sh
make USER_C_MODULES=/path/to/zbotDriver/micropython/cmodules/zbot_drivers
```

For CMake-based ports, point `USER_C_MODULES` at:

```sh
/path/to/zbotDriver/micropython/cmodules/zbot_drivers/micropython.cmake
```

The Python files under `robot/` import these modules when present and keep
their existing Python implementations as fallbacks.

Exposed modules:

- `zbot_motor.Motor`
- `zbot_servo.Servo`
- `zbot_tca9548a.TCA9548A`
- `zbot_mpu6050.MPU6050`
- `zbot_tcs3472.TCS3472`
- `zbot_vl53l0x.VL53L0X`
- `zbot_vl53l1x.VL53L1X`
- `zbot_drive.mix(throttle, steering)`
- `zbot_drive.duty(command, max_duty_u16)`
