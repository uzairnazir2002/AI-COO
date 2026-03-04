from enum import StrEnum


class Role(StrEnum):
    OWNER = "OWNER"
    EDITOR = "EDITOR"
    VIEWER = "VIEWER"


class TransactionType(StrEnum):
    REVENUE = "REVENUE"
    EXPENSE = "EXPENSE"


class AlertKind(StrEnum):
    ANOMALY = "ANOMALY"
    PROFIT_LEAK = "PROFIT_LEAK"
    RUNWAY = "RUNWAY"


class AlertStatus(StrEnum):
    OPEN = "OPEN"
    DISMISSED = "DISMISSED"


class Scenario(StrEnum):
    BASE = "BASE"
    HIGH = "HIGH"
    LOW = "LOW"
