# Build And Deploy Firmware

This project can run with the pure-Python drivers on a stock MicroPython build,
or with the ZebraBot native C modules compiled into the ESP32 MicroPython
firmware.

The aggregate user-module entry point is:

```text
micropython/cmodules/micropython.cmake
```

It includes both:

- `zbot_drivers`: native motor, servo, mux, IMU, color, ToF, OLED, and drive helpers
- `user_main`: optional native `user_main.c`

## Build With WSL

The Windows command line can run into long command/path issues while building
MicroPython. The known-good path is to build from Debian WSL against the Linux
MicroPython and ESP-IDF checkouts:

```sh
cd ~/zbot-fw/micropython/ports/esp32
export IDF_TOOLS_PATH=/home/laptop/zbot-fw/idf_tools
. /home/laptop/zbot-fw/esp-idf/export.sh
make BOARD=ESP32_GENERIC BUILD=build-ZBOT \
  USER_C_MODULES=/mnt/c/Users/Laptop/Documents/GitHub/zbotDriver/micropython/cmodules/micropython.cmake
```

After a successful build, copy the deployable binaries back to the repo:

```sh
mkdir -p /mnt/c/Users/Laptop/Documents/GitHub/zbotDriver/build_tools/zbot_firmware
cp ~/zbot-fw/micropython/ports/esp32/build-ZBOT/bootloader/bootloader.bin \
  /mnt/c/Users/Laptop/Documents/GitHub/zbotDriver/build_tools/zbot_firmware/bootloader.bin
cp ~/zbot-fw/micropython/ports/esp32/build-ZBOT/partition_table/partition-table.bin \
  /mnt/c/Users/Laptop/Documents/GitHub/zbotDriver/build_tools/zbot_firmware/partition-table.bin
cp ~/zbot-fw/micropython/ports/esp32/build-ZBOT/micropython.bin \
  /mnt/c/Users/Laptop/Documents/GitHub/zbotDriver/build_tools/zbot_firmware/micropython.bin
```

## Flash ESP32

Put the board into ROM download mode before flashing. On boards where the reset
lines do not auto-enter bootloader, hold `BOOT`, tap `EN`/`RESET`, keep holding
`BOOT` while esptool starts connecting, then release it.

Erase flash when replacing an older pure-Python firmware:

```powershell
C:\Users\Laptop\.espressif\python_env\idf5.5_py3.13_env\Scripts\python.exe -m esptool `
  --chip esp32 --port COM7 --baud 115200 erase_flash
```

Write the rebuilt firmware:

```powershell
C:\Users\Laptop\.espressif\python_env\idf5.5_py3.13_env\Scripts\python.exe -m esptool `
  --chip esp32 --port COM7 --baud 460800 `
  --before default_reset --after hard_reset write_flash `
  --flash_mode dio --flash_size 4MB --flash_freq 40m `
  0x1000 build_tools\zbot_firmware\bootloader.bin `
  0x8000 build_tools\zbot_firmware\partition-table.bin `
  0x10000 build_tools\zbot_firmware\micropython.bin
```

If auto-reset does not work, use `--before no_reset` after manually entering
bootloader mode.

## Restore Runtime Files

Erasing flash clears the MicroPython filesystem. Copy the runtime files back
after the native firmware is flashed:

```powershell
.\.venv\Scripts\mpremote.exe connect COM7 mkdir robot
.\.venv\Scripts\mpremote.exe connect COM7 cp main.py :main.py
```

Then copy each Python file from `robot/` to `:robot/`. In PowerShell:

```powershell
$files = Get-ChildItem -Path .\robot -File -Filter *.py | Sort-Object Name
foreach ($f in $files) {
    .\.venv\Scripts\mpremote.exe connect COM7 cp $f.FullName (':robot/' + $f.Name)
}
```

For native `user_main.c` testing, do not copy a filesystem `user_main.py`; the
built-in native `user_main` module should be imported instead.

## Verify Native Modules

After flashing and restoring files, check that the native modules are present:

```powershell
.\.venv\Scripts\mpremote.exe connect COM7 exec "import user_main, zbot_tcs3472, zbot_vl53l0x, zbot_oled; print(user_main.USER_MAIN_KIND)"
```

Expected output includes:

```text
c
```

The current native `user_main.c` displays live sensor data as a user program:

- color sensor on port 1
- RGB values from port 1
- ToF distance on port 2

The runtime calls `user_main.main(zbot)` once. If the native module also exports
`tick(zbot)`, the runtime calls it cooperatively every `USER_MAIN_TICK_MS`
milliseconds so sensors and background tasks keep running.
