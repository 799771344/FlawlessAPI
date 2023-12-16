import asyncio
import json

import optional
import uvicorn
from typing import Callable, List, Tuple

from requests import AsyncRequest


class FlawlessAPI:
    def __init__(self):
        self.routes = []  # 路由表列表
        self.middleware_stack = []  # 中间件栈列表

    def add_route(self, method: list, path: str, handler: Callable):
        if len(method) == 0:
            method = ['GET', 'POST']
        self.routes.append((method, path, handler))  # 向路由表中添加路由

    def add_middleware(self, middleware: Callable):
        self.middleware_stack.append(self.create_middleware(middleware))  # 向中间件栈中添加中间件

    async def __call__(self, scope, receive, send):
        # 从中间件栈的顶部开始逐一应用中间件
        await self.process_middlewares(scope, receive, send)

    @staticmethod
    # 中间件工厂函数
    def create_middleware(logic):
        def middleware(scope, handler):
            async def new_handler(scope, receive, send):
                # 在请求处理前执行逻辑
                await logic(scope, 'before')
                # 调用下一个处理函数
                await handler(scope, receive, send)
                # 在请求处理后执行逻辑
                await logic(scope, 'after')

            return new_handler

        return middleware

    async def process_middlewares(self, scope, receive, send):
        handler = self.handle_request  # 最终处理请求的函数

        # 从中间件栈底部开始, 逐一包装处理函数
        for middleware in reversed(self.middleware_stack):
            handler = middleware(scope, handler)

        # 调用最终包装后的请求处理函数
        await handler(scope, receive, send)

    async def handle_request(self, scope, receive, send):
        assert scope['type'] == 'http'
        request_path = scope['path']
        request_method = scope['method']

        # 寻找匹配的路由
        for method, route_path, handler in self.routes:
            if route_path == request_path and request_method in method:
                request = AsyncRequest(scope, receive, send)
                response = await handler(request)
                print(response)
                assert isinstance(response, dict), "Response must be a dict"
                code = response.get('code', 200)
                await self._send_json_response(send, code, response)
                return

        # 没有找到匹配的路由时，发送404响应
        await self._send_not_found_response(send)

    async def _send_json_response(self, send, status_code, body_dict):
        bytes_data = json.dumps(body_dict).encode('utf-8')
        await self._send_response(
            send,
            status_code,
            bytes_data,
            headers=[
                [b'content-type', b'application/json'],
            ]
        )

    async def _send_not_found_response(self, send):
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


# 示例中间件函数
# 用户定义的逻辑函数
async def middleware_logic(scope, timing):
    if timing == 'before':
        print(f"Before request in {scope['path']}")
    elif timing == 'after':
        print(f"After request in {scope['path']}")


app = FlawlessAPI()

# 将示例中间件添加到应用中
app.add_middleware(middleware_logic)


# 处理函数: 返回 "Hello, World!"
async def hello_world(request: AsyncRequest):
    query_params = await request.query_string()
    print(query_params)
    if query_params:
        return {"msg": "", "code": 200, "data": query_params}
    body = await request.body()
    print(body)
    if body:
        return {"msg": "", "code": 200, "data": body}
    return {"msg": "", "code": 200, "data": 'Hello, World!'}


# 处理函数: 返回 "This is the about page."
async def about_page(request: AsyncRequest):
    return b'This is the about page.'


# 将路由和处理函数关联起来
app.add_route([], "/hello", hello_world)
app.add_route([], "/about", about_page)


# 主函数，会被异步运行
async def main():
    config = uvicorn.Config(app=app, loop='asyncio', host="0.0.0.0", port=8000)
    server = uvicorn.Server(config)  # 创建 uvicorn 服务器实例
    await server.serve()  # 启动服务器


# 当该脚本被作为程序运行时，执行 main 函数
if __name__ == "__main__":
    asyncio.run(main())
