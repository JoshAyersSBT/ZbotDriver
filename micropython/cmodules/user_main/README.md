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
