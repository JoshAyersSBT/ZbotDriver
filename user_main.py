
async def main(zbot):
    import uasyncio as asyncio

    try:
        zbot.display("Drive test", "Forward")
        zbot.forward(35)
        await asyncio.sleep_ms(1000)

        zbot.display("Drive test", "Stop")
        zbot.stop()
        await asyncio.sleep_ms(1000)

        zbot.display("Drive test", "Backward")
        zbot.backward(35)
        await asyncio.sleep_ms(1000)

        zbot.display("Drive test", "Stop")
        zbot.stop()
        await asyncio.sleep_ms(1000)

        zbot.display("Drive test", "Done")

    finally:
        zbot.stop()