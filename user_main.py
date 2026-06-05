async def main(zbot):
    import uasyncio as asyncio

    color_sensor_port = 1

    zbot.display("Color monitor", "Port {}".format(color_sensor_port))

    while True:
        match = zbot.sensor(color_sensor_port).color_match()

        if match is None:
            print("Color: none")
            zbot.display("Color", "none")
            await asyncio.sleep_ms(300)
            continue

        color = match.get("color")
        confidence = int(match.get("confidence", 0))
        rgb = match.get("rgb", {})

        print(
            "Color:",
            color,
            "confidence:",
            confidence,
            "rgb:",
            rgb,
        )

        zbot.display(
            "Color {}".format(color),
            "Conf {}".format(confidence),
            "R{} G{}".format(rgb.get("r", 0), rgb.get("g", 0)),
            "B{} C{}".format(rgb.get("b", 0), rgb.get("clear", 0)),
        )

        await asyncio.sleep_ms(300)
