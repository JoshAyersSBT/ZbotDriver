# Student API Overview

Student programs use the global `zbot` object to control ZebraBot. The helpers
are designed for simple scripts first, with lower-level status snapshots
available when you need more detail.

```python
zbot.forward(40)
zbot.display("Driving")
```

Programs may be written as `user_main.py` or compiled into firmware as a native
MicroPython C module named `user_main`. In both cases the runtime calls
`main(zbot)` when the robot finishes booting.

The runtime records which form was loaded in `zbot.status()["user"]["kind"]`.
It reports `"python"` for a filesystem/frozen Python module and `"c"` for a
native user module. A module can explicitly set `USER_MAIN_KIND = "python"` or
`USER_MAIN_KIND = "c"` to override detection.

Native C programs may also export `tick(zbot)` and `USER_MAIN_TICK_MS`. When a
C `main(zbot)` returns normally, the runtime calls `tick(zbot)` on that interval
as a cooperative user loop. This is the preferred native pattern for display and
sensor programs because background sensor polling continues to run.

Recommended workflow:

- prototype behavior in `user_main.py` with `async def main(zbot)`
- keep long-running Python programs cooperative with `await asyncio.sleep_ms(...)`
- move stable, performance-sensitive behavior to `user_main.c`
- in C, put one-time setup in `main(zbot)` and repeated work in `tick(zbot)`
- leave `user_main.py` off the device filesystem when testing native `user_main`

Power values are usually `-100` to `100`:

- positive power moves forward
- negative power moves backward
- `0` stops that motor or movement command
