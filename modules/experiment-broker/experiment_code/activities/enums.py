from enum import Enum, StrEnum


class ParameterMapFailuremode(Enum):
    """Enum to arbitrate failure mode"""

    FailFast = True
    Continue = False


if __name__ == "__main__":
    test = ParameterMapFailuremode(True)
    print(test)
