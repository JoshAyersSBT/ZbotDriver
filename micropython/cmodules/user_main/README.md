# Native `user_main.c`

This optional module lets a user program be compiled into the MicroPython
firmware as `user_main`.

The ZebraBot runtime imports `user_main` and calls:

```c
main(zbot)
```

where `zbot` is the same runtime API object passed to Python `user_main.py`
programs.

The template exports `USER_MAIN_KIND = "c"` so the runtime can report that the
loaded user program is native. Python programs may set `USER_MAIN_KIND =
"python"` if they need to override automatic detection.

For CMake-based MicroPython ports:

```sh
make USER_C_MODULES=/path/to/zbotDriver/micropython/cmodules/user_main/micropython.cmake
```

For Make-based ports:

```sh
make USER_C_MODULES=/path/to/zbotDriver/micropython/cmodules/user_main
```

Edit `user_main.c` to implement the robot behavior. Native `main()` may return
normally, or it may return a coroutine object if you build one from C.

For cooperative native user programs, export a `tick(zbot)` function and set
`USER_MAIN_TICK_MS`. The runtime calls `main(zbot)` once, then calls
`tick(zbot)` on that interval when `main()` returns normally. This is preferred
for display and sensor loops because it lets the MicroPython scheduler continue
running the sensor hub and other runtime tasks.

The included example uses this pattern to update the OLED with:

- color sensor data from port 1
- RGB readings from port 1
- ToF distance from port 2

See [Build And Deploy Firmware](../../../docs/build-deploy.md) for the WSL
build, firmware artifact, flash, and runtime restore workflow.
