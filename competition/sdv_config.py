"""
Calibration and hardware settings for SDV competition programs.

Tune these values on the actual mat before running at competition speed.
Distances are expressed as grid cells. The SDV manual uses a 5 x 5 field
with each cell approximately 2 ft x 2 ft.
"""

DRIVE_MODEL = "ackermann"

# Runtime bridge settings. Kept for bench testing only.
RUNTIME_DRIVE_POWER = 35
RUNTIME_TURN_POWER = 35

# Differential settings. Kept for bench testing only.
DIFF_LEFT_PORT = 1
DIFF_RIGHT_PORT = 2
DIFF_DRIVE_POWER = 35
DIFF_TURN_POWER = 30

# Ackermann settings. All competition robots use this drive model.
ACK_DRIVE_MOTOR_PORT = 2
ACK_STEERING_PORT = 1
ACK_CENTER_ANGLE = 90
ACK_LEFT_ANGLE = 55
ACK_RIGHT_ANGLE = 125
ACK_DRIVE_POWER = 35

# Core timing calibration.
CELL_MS = 1200
TURN_90_MS = 750
SETTLE_MS = 120

# Color sensor behavior. When enabled, each grid-cell move looks for a color
# contrast edge, then drives a short extra distance to settle near cell center.
USE_COLOR_EDGES = True
FLOOR_COLOR_PORT = 2
EDGE_THRESHOLD = 150
EDGE_CHECK_MS = 40
EDGE_TO_CENTER_MS = 600
EDGE_TIMEOUT_FACTOR = 1.5

# ToF behavior. Set FRONT_TOF_PORT to None when a sensor is not installed.
FRONT_TOF_PORT = 1
STOP_DISTANCE_MM = 150
USE_TOF_STOP = True

# Trailer mechanism. Set HITCH_SERVO_PORT to None if your hitch is passive.
HITCH_SERVO_PORT = None
HITCH_OPEN_ANGLE = 45
HITCH_CLOSED_ANGLE = 100

# Match choices changed at the field before a run.
PROGRAM = "sensor_check"

SOLO_START = "A3"
SOLO_DIRECTION = "clockwise"

ALLIANCE_START = "A3"
ALLIANCE_TRAILER = "left"
