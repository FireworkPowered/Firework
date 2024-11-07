from __future__ import annotations

from enum import Enum
from typing import Tuple


class Stage(int, Enum):
    PREPARE = 0
    ONLINE = 1
    CLEANUP = 2
    EXIT = 3


class Phase(int, Enum):
    WAITING = 0
    PENDING = 1
    COMPLETED = 2


ServiceStatusValue = Tuple[Stage, Phase]
