# Tiny boot launcher. Keep this file small so ESP32 can compile it early.
print("[INFO] MAIN: launcher")

try:
    import gc
    gc.collect()
except Exception:
    pass

from robot import runtime

boot = runtime.boot
run = runtime.run
get_api = runtime.get_api
get_zbot = runtime.get_zbot
zbot = runtime.zbot
API = runtime.API

run()
