import uasyncio as asyncio

try:
    from machine import Pin
except ImportError:
    Pin = None


async def main(zbot):
    b1 = zbot.button(1)
    b2 = zbot.button(2)
    color_sensor = zbot.sensor(1)
    pins = []
    if Pin is not None:
        pins = [(15, Pin(15, Pin.IN, Pin.PULL_UP)), (12, Pin(12, Pin.IN, Pin.PULL_UP))]

    zbot.display("IO Test", "B1/B2 + Color", "starting")
    zbot.notify("INFO USER io display test running")

    while True:
        raw_line = ""
        if pins:
            raw_line = "P15:{} P12:{}".format(pins[0][1].value(), pins[1][1].value())

        if b1.was_pressed():
            line = "B1 pressed {}".format(b1.presses())
            zbot.display("IO Test", line, raw_line)
            print(line, raw_line)

        if b2.was_pressed():
            line = "B2 pressed {}".format(b2.presses())
            zbot.display("IO Test", line, raw_line)
            print(line, raw_line)

        if not b1.pressed() and not b2.pressed():
            match = color_sensor.color_match()
            if match is None:
                sensors = zbot.sensors()
                item = sensors.get("port_1_state", {})
                meta = item.get("meta", {})
                state = item.get("value", "?")
                addrs = meta.get("addrs", [])
                line = "P1 {}".format(state)
                detail = "ch{} {}".format(
                    meta.get("mux_channel", "?"),
                    ",".join(hex(a) for a in addrs) if addrs else "none",
                )
            else:
                rgb = match["rgb"]
                line = "R{} G{} B{}".format(rgb["r"], rgb["g"], rgb["b"])
                detail = "C{} {}".format(rgb["clear"], match["color"] or "?")

            zbot.display("Port 1 Color", raw_line, line, detail)
            print(raw_line, line, detail)

        await asyncio.sleep_ms(250)
