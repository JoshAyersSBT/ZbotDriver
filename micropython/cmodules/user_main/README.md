# Native `user_main.c`

This optional module lets a user program be compiled into the MicroPython
firmware as `user_main`.

The ZebraBot runtime imports `user_main` and calls:

```c
main(zbot)
```

where `zbot` is the same runtime API object passed to Python `user_main.py`
programs.

For a diagram of how native `user_main.c` interacts with the Python scheduler,
runtime services, and driver modules, see
[Runtime Architecture](../../../docs/runtime-architecture.md).

## Beginner-Friendly C Workflow

The normal ZebraBot hardware layout is constrained enough that most C user
programs can start from the same recipe:

- OLED display is managed by the runtime through `zbot.display(...)`
- sensor port `1` is commonly used for the color sensor
- sensor port `2` is commonly used for the ToF distance sensor
- actuator ports `1` through `4` are available, but do not command motors unless
  motors are actually attached
- runtime background tasks keep scanning sensors and buttons for you

For most native C user programs, edit only these parts first:

```c
#define COLOR_PORT 1
#define TOF_PORT 2
#define USER_TICK_MS 1000
```

Then change the lines shown on the display inside `user_main_tick(...)`.

The intended shape is:

```c
main(zbot)      // show startup text, initialize small state, then return
tick(zbot)      // read sensors and update display once per tick
```

Avoid this shape:

```c
while (true) {
    // do not do this in C user_main
}
```

The runtime already owns the loop. Letting the runtime call `tick(zbot)` keeps
sensor polling, buttons, display ownership, and other services alive.

## Recommended Native User Pattern

Use `main(zbot)` for one-time startup work and use `tick(zbot)` for repeated
work. This mirrors the Python user pattern:

```python
async def main(zbot):
    zbot.display("Starting")
    while True:
        # read sensors, update display, command motors
        await asyncio.sleep_ms(100)
```

In C, do not write an infinite blocking loop in `main()`. A blocking C loop will
prevent the MicroPython scheduler from running the sensor hub, button task,
display status task, BLE task, and other runtime services. Instead, return from
`main()` and let the runtime call `tick()` cooperatively:

```c
#include "py/runtime.h"
#include "py/obj.h"
#include <string.h>

static void call_display(mp_obj_t zbot, const char *a, const char *b, const char *c, const char *d) {
    mp_obj_t dest[6];
    mp_load_method_maybe(zbot, MP_QSTR_display, dest);
    if (dest[0] == MP_OBJ_NULL) {
        return;
    }

    dest[2] = mp_obj_new_str(a, strlen(a));
    dest[3] = mp_obj_new_str(b, strlen(b));
    dest[4] = mp_obj_new_str(c, strlen(c));
    dest[5] = mp_obj_new_str(d, strlen(d));
    mp_call_method_n_kw(4, 0, dest);
}

static mp_obj_t user_main_main(size_t n_args, const mp_obj_t *args) {
    mp_obj_t zbot = n_args > 0 ? args[0] : mp_const_none;
    call_display(zbot, "C user", "Starting", "", "");
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(user_main_main_obj, 0, 1, user_main_main);

static mp_obj_t user_main_tick(size_t n_args, const mp_obj_t *args) {
    mp_obj_t zbot = n_args > 0 ? args[0] : mp_const_none;

    // Read through the same zbot API Python users call.
    // Example helpers include zbot.tof(port), zbot.color(port), zbot.rgb(port),
    // zbot.display(...), zbot.notify(...), zbot.motor(port), and zbot.button(id).

    call_display(zbot, "C user", "Sensors live", "P1 color", "P2 ToF");
    return mp_const_none;
}
static MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(user_main_tick_obj, 0, 1, user_main_tick);

static const mp_rom_map_elem_t user_main_module_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_user_main) },
    { MP_ROM_QSTR(MP_QSTR_USER_MAIN_KIND), MP_ROM_QSTR(MP_QSTR_c) },
    { MP_ROM_QSTR(MP_QSTR_USER_MAIN_TICK_MS), MP_ROM_INT(1000) },
    { MP_ROM_QSTR(MP_QSTR_main), MP_ROM_PTR(&user_main_main_obj) },
    { MP_ROM_QSTR(MP_QSTR_tick), MP_ROM_PTR(&user_main_tick_obj) },
};
static MP_DEFINE_CONST_DICT(user_main_module_globals, user_main_module_globals_table);

const mp_obj_module_t user_main_module = {
    .base = { &mp_type_module },
    .globals = (mp_obj_dict_t *)&user_main_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_user_main, user_main_module);
```

The important pieces are:

- `USER_MAIN_KIND = "c"` tells the runtime this is a native user program.
- `main(zbot)` is called once after the robot runtime boots.
- `tick(zbot)` is optional, but recommended for repeated behavior.
- `USER_MAIN_TICK_MS` controls the cooperative tick interval.
- The `zbot` object is the same API object used by Python user programs.

## Simple Native Sensor Display

The included `user_main.c` is the recommended starting point for a first native
C program. It:

- announces that the C user program started
- displays a startup page
- reads color data from port `1`
- reads ToF distance from port `2`
- refreshes the OLED once per second

The beginner edit points are:

```c
bool color_ok = user_main_read_color(zbot, 1, color, sizeof(color));
bool rgb_ok = user_main_read_rgb(zbot, 1, &r, &g, &b, &clear);
bool tof_ok = user_main_read_tof(zbot, 2, &tof);
```

Change only the port numbers when the hardware moves. For example, if the ToF
sensor moves from port `2` to port `3`, change the `2` in
`user_main_read_tof(zbot, 2, &tof)` to `3`.

Display lines are plain text:

```c
user_main_display(zbot, "C User Sensors", line2, line3, line4);
```

Keep each line short. The OLED is small, so aim for about 16 characters per
line.

## Runtime API Calls From C

Native C code calls the same `zbot` methods that Python user code calls, but it
does so through MicroPython's C API. The helper functions in `user_main.c`
hide most of that.

Use these helpers as the first layer:

- `user_main_display(zbot, line1, line2, line3, line4)`
- `user_main_notify(zbot, message)`
- `user_main_read_color(zbot, port, buffer, buffer_len)`
- `user_main_read_rgb(zbot, port, &r, &g, &b, &clear)`
- `user_main_read_tof(zbot, port, &distance_mm)`

Add new helpers in this same style when you need more of the runtime API. For
example, a motor helper would call `zbot.motor(port)` or another existing zbot
method, but keep motor examples separate from sensor examples so beginner
programs do not move hardware by accident.

## How It Ties Into The Python Runtime

The runtime always tries to import a module named `user_main`. That module can
come from either:

- `user_main.py` on the MicroPython filesystem
- a frozen/compiled Python module
- the native C module compiled into firmware

Once imported, the runtime calls `user_main.main(zbot)`. For Python programs,
`main()` is usually an `async def` coroutine and the runtime awaits it. For C
programs, `main()` usually returns `None`; when a C module also exports
`tick()`, the runtime keeps the user program marked as running and calls
`tick(zbot)` on the configured interval.

If both a filesystem `user_main.py` and a native `user_main` module are present,
MicroPython import order determines which one is loaded. For native C testing,
keep `user_main.py` off the device filesystem so the compiled module is the
user program.

Use the Python API first when prototyping behavior. Move code into
`user_main.c` when the behavior is stable, needs lower overhead, or should ship
as part of the firmware image.

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
