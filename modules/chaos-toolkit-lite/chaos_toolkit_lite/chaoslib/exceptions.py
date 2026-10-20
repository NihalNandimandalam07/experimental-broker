__all__ = [
    "ChaosException",
    "ActivityFailed",
    "InvalidActivity",
    "InvalidExperiment",
    "InvalidSource",
]


class ChaosException(Exception):
    pass


class InvalidActivity(ChaosException):
    pass


class InvalidExperiment(ChaosException):
    pass


class InvalidSource(ChaosException):
    pass


class ActivityFailed(ChaosException):
    pass
