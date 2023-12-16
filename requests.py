import json
import typing
from urllib.parse import unquote
from http.client import HTTPConnection
from urllib.parse import parse_qsl
from multipart import parse_options_header
from starlette.datastructures import FormData, Headers, UploadFile
from starlette.formparsers import MultiPartParser, FormParser
from starlette.types import Message, Receive, Scope, Send


class AsyncRequest(HTTPConnection):
    def __init__(self, scope: Scope, receive: Receive, send: Send):
        super().__init__(scope["client"][0], scope["client"][1])
        assert scope["type"] == "http"
        self._scope = scope
        self._receive = receive
        self._send = send
        self._stream_consumed = False
        self._is_disconnected = False
        self._form = None
        self._headers = self._scope['headers']

    async def stream(self) -> typing.AsyncGenerator[bytes, None]:
        if self._stream_consumed:
            raise RuntimeError("Stream has already been consumed.")
        self._stream_consumed = True
        while True:
            message = await self._receive()
            if message["type"] == "http.disconnect":
                self._is_disconnected = True
                break
            if message["type"] != "http.request":
                continue
            body = message.get("body", b"")
            if body:
                yield body
            if not message.get("more_body", False):
                break

    @staticmethod
    def _parse_body(body: bytes, content_type: bytes) -> typing.Any:
        if not isinstance(body.decode(), dict):
            raise TypeError("Failed to parse body as JSON")
        if content_type == b'application/x-www-form-urlencoded':
            return dict(parse_qsl(body.decode()))
        elif content_type == b'application/json':
            return json.loads(body.decode())
        return body

    async def body(self):
        if self._stream_consumed:
            raise RuntimeError("Stream has already been consumed.")
        body_bytes = b""
        content_type = [header[1] for header in self._headers if header[0] == b'content-type']
        if len(content_type) == 0:
            return body_bytes
        async for chunk in self.stream():
            body_bytes += chunk
        return self._parse_body(body_bytes, content_type[0])

    async def json(self):
        content_type = [header[1] for header in self._headers if header[0] == b'content-type']
        if len(content_type) == 0:
            return b""
        body_bytes = await self.body()
        return self._parse_body(body_bytes, content_type[0])

    async def query_string(self):
        query_string = self._scope['query_string']
        return dict(parse_qsl(query_string.decode()))

    async def _get_form(self, *, max_files: typing.Union[int, float] = 1000,
                        max_fields: typing.Union[int, float] = 1000) -> FormData:
        if self._form is not None:
            return self._form
        content_type_header = self._headers.get('content-type')
        content_type, options = parse_options_header(content_type_header)
        if content_type == b"multipart/form-data":
            multipart_parser = MultiPartParser(self._headers, self.stream(), max_files=max_files, max_fields=max_fields)
            self._form = await multipart_parser.parse()
        elif content_type == b"application/x-www-form-urlencoded":
            form_parser = FormParser(self._headers, self.stream())
            form_data = await form_parser.parse()
            self._form = FormData(form_data, encoding=options.get('charset', 'utf-8'))
        else:
            self._form = FormData()
        return self._form

    async def form(self) -> FormData:
        return await self._get_form()

    async def close(self) -> None:
        if self._form is not None:
            for value in self._form.values():
                if isinstance(value, UploadFile):
                    await value.close()

    async def is_disconnected(self) -> bool:
        # To avoid blocking, simply return the current state if the disconnect hasn't been received.
        return self._is_disconnected

    async def send_push_promise(self, path: str) -> None:
        if "http.response.push" in self._scope.get("extensions", {}):
            headers = self._scope["headers"]
            push_headers = Headers(raw=headers)
            await self._send({
                "type": "http.response.push",
                "path": path,
                "headers": push_headers.raw
            })
