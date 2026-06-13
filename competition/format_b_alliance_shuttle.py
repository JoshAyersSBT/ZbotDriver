import uasyncio as asyncio

from competition import sdv_config as cfg
from competition.sdv_drive import TimedGridDrive, clean_grid, turn_side


ROUTES = {
    ("A2", "left"): ["A1", "B1", "C1", "C2", "C3", "D3"],
    ("A3", "left"): ["A2", "A1", "B1", "C1", "C2", "C3", "D3"],
    ("A4", "left"): ["A3", "A2", "A1", "B1", "C1", "C2", "C3", "D3"],
    ("E2", "left"): ["E1", "D1", "C1", "C2", "C3", "D3"],
    ("E3", "left"): ["E2", "E1", "D1", "C1", "C2", "C3", "D3"],
    ("E4", "left"): ["E3", "E2", "E1", "D1", "C1", "C2", "C3", "D3"],
    ("A2", "right"): ["A3", "A4", "A5", "B5", "C5", "C4", "C3", "D3"],
    ("A3", "right"): ["A4", "A5", "B5", "C5", "C4", "C3", "D3"],
    ("A4", "right"): ["A5", "B5", "C5", "C4", "C3", "D3"],
    ("E2", "right"): ["E3", "E4", "E5", "D5", "C5", "C4", "C3", "D3"],
    ("E3", "right"): ["E4", "E5", "D5", "C5", "C4", "C3", "D3"],
    ("E4", "right"): ["E5", "D5", "C5", "C4", "C3", "D3"],
}


def _heading_between(src, dst):
    row_a, col_a = clean_grid(src)
    row_b, col_b = clean_grid(dst)

    if row_a == row_b and col_b == col_a + 1:
        return "E"
    if row_a == row_b and col_b == col_a - 1:
        return "W"
    if col_a == col_b and ord(row_b) == ord(row_a) + 1:
        return "S"
    if col_a == col_b and ord(row_b) == ord(row_a) - 1:
        return "N"

    raise ValueError("route steps must move to adjacent cells")


async def _follow_route(car, start, route):
    heading = _heading_between(start, route[0])
    current = start

    for next_grid in route:
        target_heading = _heading_between(current, next_grid)
        turn = turn_side(heading, target_heading)

        if turn == "left":
            await car.turn_left()
        elif turn == "right":
            await car.turn_right()
        elif turn == "around":
            await car.turn_around()

        heading = target_heading
        await car.forward_cells(1, label=next_grid)
        current = next_grid


async def main(zbot):
    car = TimedGridDrive(zbot)
    start = cfg.ALLIANCE_START.upper()
    trailer = cfg.ALLIANCE_TRAILER.lower()
    route = ROUTES[(start, trailer)]

    try:
        zbot.display("Alliance", "{} {}".format(start, trailer))
        await car.hitch_open()
        await asyncio.sleep_ms(800)

        zbot.display("Delivery", "1")
        await _follow_route(car, start, route)
        await car.hitch_close()
        await asyncio.sleep_ms(400)
        await car.hitch_open()

        zbot.display("Alliance", "done")

    finally:
        car.stop()
