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

To build the complete ZebraBot native firmware, including these driver modules
and the optional native `user_main.c`, point `USER_C_MODULES` at the aggregate
CMake file:

```sh
make BOARD=ESP32_GENERIC BUILD=build-ZBOT \
  USER_C_MODULES=/path/to/zbotDriver/micropython/cmodules/micropython.cmake
```

See [Build And Deploy Firmware](../../../docs/build-deploy.md) for the full
WSL build and COM-port flash workflow.

Exposed modules:

- `zbot_motor.Motor`
- `zbot_servo.Servo`
- `zbot_tca9548a.TCA9548A`
- `zbot_mpu6050.MPU6050`
- `zbot_tcs3472.TCS3472`
- `zbot_vl53l0x.VL53L0X`
- `zbot_vl53l1x.VL53L1X`
- `zbot_oled.SH1106_I2C`
- `zbot_drive.mix(throttle, steering)`
- `zbot_drive.duty(command, max_duty_u16)`
