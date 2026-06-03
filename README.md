# ZebraBot Driver

MicroPython robot driver code for ZebraBot.

## Native Driver Modules

Core runtime drivers can be compiled into MicroPython as C user modules from
`micropython/cmodules/zbot_drivers`. The Python runtime imports the native
modules when they are present and falls back to the pure-Python drivers when
they are not.

Users can also compile a native `user_main.c` entry point as a MicroPython
module. The runtime calls `user_main.main(zbot)` whether `user_main` is Python
or C.

## Documentation

- [ZebraBoard overview](docs/board-overview.md)
- [Student API](docs/student-api.md)
- [Build and deploy firmware](docs/build-deploy.md)
- [Runtime architecture and file map](docs/runtime-architecture.md)
- [MicroPython C modules](micropython/cmodules/zbot_drivers/README.md)
- [Native user_main.c](micropython/cmodules/user_main/README.md)

## Wi-Fi Code Upload

The runtime starts a small HTTP upload service when `WIFI_CODE_ENABLED` is true
in `robot/config.py`. By default the robot creates the `ZebraBot-Code` access
point and listens at `http://192.168.4.1:8080`.

Upload from a browser by opening the robot URL, or from this repo with:

```powershell
python tools\wifi_put.py http://192.168.4.1:8080 user_main.py --reset
```

To join a normal router instead, set `WIFI_STA_SSID` and
`WIFI_STA_PASSWORD` in `robot/config.py`. The AP can stay enabled as a fallback.

Run the serial-side Wi-Fi module tests on a board attached to COM7 with:

```powershell
python tools\wifi_code_test.py --deploy
```

After the robot is reachable over Wi-Fi, add the HTTP upload test:

```powershell
python tools\wifi_code_test.py --url http://192.168.4.1:8080
```
