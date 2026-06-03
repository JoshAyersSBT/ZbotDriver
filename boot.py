# This file is executed on every boot before main.py.
#
# Keep it intentionally small. Activating BLE here consumes heap before the
# application imports, which can cause early MemoryError on ESP32.
print("[INFO] BOOT: boot.py minimal startup")
