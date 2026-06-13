import uasyncio as asyncio

from competition import sdv_config as cfg


async def main(zbot):
    edge_count = 0

    if cfg.FLOOR_COLOR_PORT is not None:
        zbot.reset_edge(cfg.FLOOR_COLOR_PORT)

    try:
        while True:
            color = None
            contrast = None
            edge = False
            distance = None

            if cfg.FLOOR_COLOR_PORT is not None:
                color = zbot.color(cfg.FLOOR_COLOR_PORT)
                contrast = zbot.contrast(cfg.FLOOR_COLOR_PORT)
                edge = zbot.find_edge(cfg.FLOOR_COLOR_PORT, cfg.EDGE_THRESHOLD)
                if edge:
                    edge_count += 1

            if cfg.FRONT_TOF_PORT is not None:
                distance = zbot.tof(cfg.FRONT_TOF_PORT)

            zbot.display(
                "C {}".format(color),
                "K {}".format(contrast),
                "E {}".format(edge_count),
                "T {}".format(distance),
            )

            await asyncio.sleep_ms(100)

    finally:
        zbot.stop()
