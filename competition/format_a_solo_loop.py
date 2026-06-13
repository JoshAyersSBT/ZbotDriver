import uasyncio as asyncio

from competition import sdv_config as cfg
from competition.sdv_drive import TimedGridDrive, clean_grid


def _solo_plan(start, direction):
    row, col = clean_grid(start)
    direction = str(direction).lower()
    if direction not in ("clockwise", "counterclockwise"):
        raise ValueError("direction must be clockwise or counterclockwise")

    if row == "A":
        if direction == "clockwise":
            return "right", [5 - col, 4, 4, 4, col - 1]
        return "left", [col - 1, 4, 4, 4, 5 - col]

    if row == "E":
        if direction == "clockwise":
            return "right", [col - 1, 4, 4, 4, 5 - col]
        return "left", [5 - col, 4, 4, 4, col - 1]

    raise ValueError("solo start row must be A or E")


async def _run_lap(car, segments, turn):
    for index, cells in enumerate(segments):
        if cells > 0:
            await car.forward_cells(cells, label="Lap segment")
        if index < 4:
            if turn == "right":
                await car.turn_right()
            else:
                await car.turn_left()


async def main(zbot):
    car = TimedGridDrive(zbot)
    turn, segments = _solo_plan(cfg.SOLO_START, cfg.SOLO_DIRECTION)

    try:
        zbot.display("Solo loop", cfg.SOLO_START)
        await asyncio.sleep_ms(800)

        for lap in range(3):
            zbot.display("Solo lap", str(lap + 1))
            await _run_lap(car, segments, turn)

        zbot.display("Solo loop", "done")

    finally:
        car.stop()
