import json


class AsyncResponse:

    async def send_json_response(self, send, status_code, body_dict):
        bytes_data = json.dumps(body_dict).encode('utf-8')
        await self._send_response(
            send,
            status_code,
            bytes_data,
            headers=[
                [b'content-type', b'application/json'],
            ]
        )

    async def send_not_found_response(self, send):
        await self._send_response(
            send,
            404,
            b'Not Found',
            headers=[
                [b'content-type', b'text/plain'],
            ]
        )

    @staticmethod
    async def _send_response(send, status_code, body, headers):
        await send({
            'type': 'http.response.start',
            'status': status_code,
            'headers': headers,
        })
        await send({
            'type': 'http.response.body',
            'body': body,
            'more_body': False  # 表示这是响应的最后一部分
        })