from __future__ import annotations
from enum import Enum


class LabStage(str, Enum):
    BOOKING = "booking"
    SAMPLING = "sampling"
    RUNNING = "analysis"  # Must be lowercase to match DB
    ANALYZING = "review"  # Must be lowercase to match DB
    COMPLETE = "complete"
    PRINTING = "printing"
    ENDED = "ended"


class PhlebotomyStatus(str, Enum):
    pending = "in_progress"
    collected = "collected"
    completed = "completed"


class LabStatus(str, Enum):
    AWAITING_SAMPLE = "AWAITING_SAMPLE"
    AWAITING_RESULTS = "AWAITING_RESULTS"
    IN_PROGRESS = "IN_PROGRESS"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
