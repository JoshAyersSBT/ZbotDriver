import uasyncio as asyncio


async def main(zbot):
    b1 = zbot.button(1)
    b2 = zbot.button(2)
    last_line = "Waiting..."

    zbot.display("Button Test", "B1/B2 ready", last_line)
    zbot.notify("INFO USER button display test running")

    while True:
        if b1.was_pressed():
            last_line = "B1 pressed {}".format(b1.presses())
            zbot.display("Button Test", last_line, "B2: {}".format(b2.presses()))
            print(last_line)

        if b2.was_pressed():
            last_line = "B2 pressed {}".format(b2.presses())
            zbot.display("Button Test", "B1: {}".format(b1.presses()), last_line)
            print(last_line)

        await asyncio.sleep_ms(20)
