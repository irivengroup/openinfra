from __future__ import annotations

import os
from collections.abc import Mapping
from threading import RLock
from types import TracebackType
from typing import Literal


class OpenInfraRuntimeEnvironmentScope:
    """Temporarily expose runtime values to child worker processes.

    Uvicorn reads application-factory settings from the process environment so
    spawned workers inherit an identical immutable configuration.  The scope
    restores the previous process state when the server exits or startup fails,
    preventing configuration leakage into embedded runtimes and test processes.
    """

    _lock = RLock()

    def __init__(self, values: Mapping[str, str]) -> None:
        self._values = {str(key): str(value) for key, value in values.items()}
        self._previous: dict[str, str | None] = {}
        self._entered = False

    def __enter__(self) -> OpenInfraRuntimeEnvironmentScope:
        self._lock.acquire()
        try:
            self._previous = {key: os.environ.get(key) for key in self._values}
            os.environ.update(self._values)
            self._entered = True
            return self
        except BaseException:
            self._lock.release()
            raise

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> Literal[False]:
        del exc_type, exc_value, traceback
        if not self._entered:
            return False
        try:
            for key, previous in self._previous.items():
                if previous is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = previous
        finally:
            self._previous.clear()
            self._entered = False
            self._lock.release()
        return False
