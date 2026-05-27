import uasyncio as asyncio


async def main(zbot):
    zbot.display("BLE Upload", "user_main.py", "running")
    zbot.notify("INFO USER BLE upload test running")

    while True:
        await asyncio.sleep_ms(1000)
