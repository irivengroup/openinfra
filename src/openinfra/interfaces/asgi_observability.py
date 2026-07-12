from __future__ import annotations

from collections.abc import Awaitable, Callable, MutableMapping
from http import HTTPStatus
from typing import Any

from openinfra.application.ports import HttpRequestObservation

AsgiMessage = MutableMapping[str, Any]
AsgiSend = Callable[[AsgiMessage], Awaitable[None]]
AsgiReceive = Callable[[], Awaitable[AsgiMessage]]


class ObservedAsgiReceive:
    def __init__(self, upstream: AsgiReceive) -> None:
        self._upstream = upstream
        self.request_size_bytes = 0

    async def __call__(self) -> AsgiMessage:
        message = await self._upstream()
        if str(message.get("type", "")) == "http.request":
            self.request_size_bytes += len(bytes(message.get("body", b"")))
        return message


class ObservedAsgiSend:
    def __init__(self, downstream: AsgiSend, observation: HttpRequestObservation) -> None:
        self._downstream = downstream
        self._observation = observation
        self.status_code = HTTPStatus.INTERNAL_SERVER_ERROR.value
        self.response_size_bytes = 0
        self._started = False
        self._finished = False

    async def __call__(self, message: AsgiMessage) -> None:
        message_type = str(message.get("type", ""))
        if message_type == "http.response.start":
            self.status_code = int(message.get("status", HTTPStatus.INTERNAL_SERVER_ERROR.value))
            headers = list(message.get("headers", []))
            traceparent = self._observation.traceparent
            if traceparent and not any(
                bytes(name).lower() == b"traceparent" for name, _ in headers
            ):
                headers.append((b"traceparent", traceparent.encode("ascii")))
            message["headers"] = headers
            self._started = True
        elif message_type == "http.response.body":
            self.response_size_bytes += len(bytes(message.get("body", b"")))
        await self._downstream(message)

    def record_exception(self, exception: BaseException) -> None:
        self._observation.record_exception(exception)

    def finish(self, request_size_bytes: int) -> None:
        if self._finished:
            return
        self._finished = True
        self._observation.finish(
            status_code=self.status_code,
            request_size_bytes=max(0, int(request_size_bytes)),
            response_size_bytes=self.response_size_bytes,
        )
