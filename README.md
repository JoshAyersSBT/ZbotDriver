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

- [Student API](docs/student-api.md)
- [Build and deploy firmware](docs/build-deploy.md)
- [Runtime architecture and file map](docs/runtime-architecture.md)
- [MicroPython C modules](micropython/cmodules/zbot_drivers/README.md)
- [Native user_main.c](micropython/cmodules/user_main/README.md)
