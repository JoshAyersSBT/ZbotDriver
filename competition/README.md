# SDV Competition Programs

Starter programs for the STRIPE Self-Driving Vehicle Challenge manual.

The manual describes two competition formats:

- Format A, Solo Challenge: start on A2/A3/A4 or E2/E3/E4, drive three laps around the outer loop, then stop in the original starting grid.
- Format B, Alliance Challenge: start on A2/A3/A4 or E2/E3/E4, collect a trailer from C1 or C5, and deliver it so the trailer touches D3.

## Files

- `sdv_config.py`: Ackermann ports, steering angles, speeds, timing, start grid, direction, and trailer choices.
- `sdv_user_main.py`: `user_main`-style launcher that selects the configured SDV program.
- `sdv_drive.py`: timed grid-cell driving primitives shared by the programs.
- `sdv_sensor_check.py`: live color, contrast, edge-count, and ToF display.
- `format_a_solo_loop.py`: three-lap outer-loop routine.
- `format_b_alliance_shuttle.py`: first-pass single trailer delivery routine.

## Tune Before Competition

1. Set `PROGRAM` to `sensor_check`, `solo`, or `alliance`.
2. Tune `ACK_CENTER_ANGLE`, `ACK_LEFT_ANGLE`, and `ACK_RIGHT_ANGLE`.
3. Set `FLOOR_COLOR_PORT` for the downward color sensor.
4. Tune `EDGE_THRESHOLD` so grid or road edges are detected reliably.
5. Tune `EDGE_TO_CENTER_MS` so the robot stops near the center of the next grid cell after an edge.
6. Set `FRONT_TOF_PORT` and `STOP_DISTANCE_MM` for obstacle/wall safety.
7. Tune `CELL_MS`; it is still used as the timeout and for partial moves.
8. Tune `TURN_90_MS` until one turn is exactly 90 degrees.
9. Set `SOLO_START` and `SOLO_DIRECTION` before each Format A run.
10. Set `ALLIANCE_START` and `ALLIANCE_TRAILER` before each Format B run.
11. Place the vehicle facing the first cell in its selected route.

## Running One Program

The top-level `user_main.py` follows the normal ZebraBot runtime paradigm:

```python
from competition.sdv_user_main import USER_MAIN_KIND, main
```

The runtime imports `user_main`, sees `USER_MAIN_KIND = "python"`, and calls
`main(zbot)`. The launcher then runs the program selected by `PROGRAM` in
`sdv_config.py`.

When deploying to a robot, copy both the top-level `user_main.py` and the
`competition/` package. The launcher imports files from that package at runtime.

These routines use color edge detection for grid-cell counting when
`USE_COLOR_EDGES` is true, and front ToF stopping when `USE_TOF_STOP` is true.
The next upgrade should add line centering or wall following once the real
sensor placement on the vehicle is known.
