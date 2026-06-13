import uasyncio as asyncio

from competition import sdv_config as cfg


HEADINGS = ("N", "E", "S", "W")


class TimedGridDrive:
    def __init__(self, zbot):
        self.zbot = zbot
        self.model = cfg.DRIVE_MODEL
        self.drive = None

        if self.model == "differential":
            from robot.differential import DifferentialDrive
            self.drive = DifferentialDrive(
                zbot,
                left_port=cfg.DIFF_LEFT_PORT,
                right_port=cfg.DIFF_RIGHT_PORT,
            )
        elif self.model == "ackermann":
            from robot.ackermann import AckermannDrive
            self.drive = AckermannDrive(
                zbot,
                drive_motor_port=cfg.ACK_DRIVE_MOTOR_PORT,
                steering_port=cfg.ACK_STEERING_PORT,
                center_angle=cfg.ACK_CENTER_ANGLE,
            )

    def stop(self):
        if self.drive is not None:
            self.drive.stop()
        else:
            self.zbot.stop()

    def _forward(self, power):
        if self.model == "differential":
            self.drive.forward(power)
        elif self.model == "ackermann":
            self.drive.drive(power, cfg.ACK_CENTER_ANGLE)
        else:
            self.zbot.forward(power)

    def _backward(self, power):
        if self.model == "differential":
            self.drive.backward(power)
        elif self.model == "ackermann":
            self.drive.drive(-power, cfg.ACK_CENTER_ANGLE)
        else:
            self.zbot.backward(power)

    def _turn(self, side):
        if self.model == "differential":
            power = cfg.DIFF_TURN_POWER
            if side == "left":
                self.drive.tank(-power, power)
            else:
                self.drive.tank(power, -power)
        elif self.model == "ackermann":
            angle = cfg.ACK_LEFT_ANGLE if side == "left" else cfg.ACK_RIGHT_ANGLE
            self.drive.drive(cfg.ACK_DRIVE_POWER, angle)
        else:
            turn = -cfg.RUNTIME_TURN_POWER if side == "left" else cfg.RUNTIME_TURN_POWER
            self.zbot.drive(cfg.RUNTIME_DRIVE_POWER, turn)

    async def settle(self):
        self.stop()
        await asyncio.sleep_ms(cfg.SETTLE_MS)

    async def forward_cells(self, cells, power=None, label="Forward"):
        power = cfg.RUNTIME_DRIVE_POWER if power is None else int(power)
        cells = float(cells)
        if cells <= 0:
            return

        if cfg.USE_COLOR_EDGES and cfg.FLOOR_COLOR_PORT is not None:
            whole_cells = int(cells)
            partial_cells = cells - whole_cells

            self.zbot.display(label, "{} cells".format(cells))
            for _ in range(whole_cells):
                await self._forward_one_edge_cell(power)

            if partial_cells > 0:
                await self._forward_timed_ms(int(round(partial_cells * cfg.CELL_MS)), power)
            return

        total = int(round(float(cells) * cfg.CELL_MS))
        await self._forward_timed_ms(total, power, label=label, cells=cells)

    async def _forward_timed_ms(self, total, power, label="Forward", cells=None):
        step = 50
        elapsed = 0

        if cells is not None:
            self.zbot.display(label, "{} cells".format(cells))
        self._forward(power)

        try:
            while elapsed < total:
                if self._front_blocked():
                    self.zbot.display("Stopped", "front ToF")
                    break
                await asyncio.sleep_ms(step)
                elapsed += step
        finally:
            await self.settle()

    async def _forward_one_edge_cell(self, power):
        timeout_ms = int(cfg.CELL_MS * cfg.EDGE_TIMEOUT_FACTOR)
        elapsed = 0

        try:
            self.zbot.reset_edge(cfg.FLOOR_COLOR_PORT)
            self._forward(power)

            while elapsed < timeout_ms:
                if self._front_blocked():
                    self.zbot.display("Stopped", "front ToF")
                    break

                if self.zbot.find_edge(cfg.FLOOR_COLOR_PORT, threshold=cfg.EDGE_THRESHOLD):
                    self.zbot.display("Edge", "center")
                    await asyncio.sleep_ms(cfg.EDGE_TO_CENTER_MS)
                    break

                await asyncio.sleep_ms(cfg.EDGE_CHECK_MS)
                elapsed += cfg.EDGE_CHECK_MS
        finally:
            await self.settle()

    async def backward_cells(self, cells, power=None, label="Backward"):
        power = cfg.RUNTIME_DRIVE_POWER if power is None else int(power)
        self.zbot.display(label, "{} cells".format(cells))
        self._backward(power)
        await asyncio.sleep_ms(int(round(float(cells) * cfg.CELL_MS)))
        await self.settle()

    async def turn_left(self):
        self.zbot.display("Turn", "left")
        self._turn("left")
        await asyncio.sleep_ms(cfg.TURN_90_MS)
        await self.settle()

    async def turn_right(self):
        self.zbot.display("Turn", "right")
        self._turn("right")
        await asyncio.sleep_ms(cfg.TURN_90_MS)
        await self.settle()

    async def turn_around(self):
        await self.turn_right()
        await self.turn_right()

    async def hitch_open(self):
        if cfg.HITCH_SERVO_PORT is not None:
            self.zbot.servo(cfg.HITCH_SERVO_PORT).angle(cfg.HITCH_OPEN_ANGLE)
            await asyncio.sleep_ms(250)

    async def hitch_close(self):
        if cfg.HITCH_SERVO_PORT is not None:
            self.zbot.servo(cfg.HITCH_SERVO_PORT).angle(cfg.HITCH_CLOSED_ANGLE)
            await asyncio.sleep_ms(250)

    def _front_blocked(self):
        if not cfg.USE_TOF_STOP or cfg.FRONT_TOF_PORT is None:
            return False
        distance = self.zbot.tof(cfg.FRONT_TOF_PORT)
        return distance is not None and distance <= cfg.STOP_DISTANCE_MM


def clean_grid(grid):
    grid = str(grid).upper().strip()
    if len(grid) != 2:
        raise ValueError("grid must look like A3")
    row = grid[0]
    col = int(grid[1])
    if row not in ("A", "B", "C", "D", "E") or col < 1 or col > 5:
        raise ValueError("grid must be in A1 through E5")
    return row, col


def turn_side(current, target):
    cur = HEADINGS.index(current)
    nxt = HEADINGS.index(target)
    delta = (nxt - cur) % 4
    if delta == 0:
        return None
    if delta == 1:
        return "right"
    if delta == 3:
        return "left"
    return "around"
