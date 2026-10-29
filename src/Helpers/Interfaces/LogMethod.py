from __future__ import annotations

from enum import Enum

from typing_extensions import Protocol
from typing import Optional


class LogLevel(Enum):
    NONE = 0
    ERROR = 1
    WARN = 2
    INFO = 3
    DEBUG = 4
    VERBOSE = 5
    SILLY = 6

    def log_letter(self):
        return {
            LogLevel.NONE: "",
            LogLevel.ERROR: "E",
            LogLevel.WARN: "W",
            LogLevel.INFO: "I",
            LogLevel.DEBUG: "D",
            LogLevel.VERBOSE: "V",
            LogLevel.SILLY: "~"
        }[self]

    @staticmethod
    def parse_from_letter(letter: str) -> LogLevel:
        return {
            "E": LogLevel.ERROR,
            "W": LogLevel.WARN,
            "I": LogLevel.INFO,
            "D": LogLevel.DEBUG,
            "V": LogLevel.VERBOSE,
            "~": LogLevel.SILLY,
            "": LogLevel.NONE,
        }[letter.upper()]

    def __gt__(self, other: LogLevel):
        return self.value > other.value

    def __lt__(self, other: LogLevel):
        return self.value < other.value

    def __ge__(self, other: LogLevel):
        return self.value >= other.value

    def __le__(self, other: LogLevel):
        return self.value <= other.value


class LogMethod(Protocol):
    def __call__(self, message: str, heading: Optional[str] = None, level: LogLevel = LogLevel.VERBOSE, **kwargs) \
            -> None: ...

    @classmethod
    def empty(cls) -> LogMethod:
        return cls.null

    @staticmethod
    def null(message: str, heading: Optional[str] = None, level: LogLevel = LogLevel.VERBOSE, **kwargs) -> None:
        pass

    @classmethod
    def printer(cls) -> LogMethod:
        return cls.print

    @staticmethod
    def print(message: str, heading: Optional[str] = None, level: LogLevel = LogLevel.VERBOSE, **kwargs) -> None:
        print(f"{('[%s] : ' % heading) if heading else ''}{message}",
              **{k: v for k, v in kwargs.items() if k in ["end", "flush"]})

    @staticmethod
    def logger_with_kwargs(logger: LogMethod, **kwargs) -> LogMethod:
        def log_method(message: str, heading: Optional[str] = None, level: LogLevel = LogLevel.VERBOSE, **_kwargs) -> None:
            logger(message=message, heading=heading, level=level, **{**kwargs, **_kwargs})
        return log_method


def default_logger(message: str, heading: Optional[str] = None, level: LogLevel = LogLevel.VERBOSE, **kwargs) -> None:
    print("[%s]%s : %s" % (
        level.log_letter(),
        ("[%s]" % heading) if heading else "",
        message
    ))
