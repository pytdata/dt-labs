from __future__ import annotations
from enum import Enum


class LabStage(str, Enum):
    BOOKING = "booking"
    SAMPLING = "sampling"
    RUNNING = "running"
    COMPLETE = "complete"
    ANALYZING = "analyzing"
    PRINTING = "printing"
    ENDED = "ended"

    @classmethod
    def ordered(cls) -> list["LabStage"]:
        return [
            cls.BOOKING,
            cls.SAMPLING,
            cls.RUNNING,
            cls.COMPLETE,
            cls.ANALYZING,
            cls.PRINTING,
            cls.ENDED,
        ]


class PhlebotomyStatus(str, Enum):
    pending = "pending"
    collected = "collected"
    completed = "completed"
