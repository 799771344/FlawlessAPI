from typing import Callable, List
from response import AsyncResponse

from requests import AsyncRequest


class FlawlessAPI:
    def __init__(self):
        self.routes = []  # 路由表列表
        self.routes = {}
        self.middleware_stack = []  # 中间件栈列表
        self.async_response = AsyncResponse()

    def route(self, path: str, methods: List[str] = None):
        if methods is None:
            methods = ["POST", "GET"]
        def decorator(handler):
            self.routes[path] = (methods, handler)
            return handler

        return decorator

    def add_route(self, path: str, handler: Callable, method=None):
        if method is None:
            method = ["POST", "GET"]
        self.routes[path] = (method, handler)

    def add_middleware(self, middleware: Callable):
        self.middleware_stack.append(self.create_middleware(middleware))  # 向中间件栈中添加中间件

    async def __call__(self, scope, receive, send):
        # 从中间件栈的顶部开始逐一应用中间件
        await self.process_middlewares(scope, receive, send)

    @staticmethod
    # 中间件工厂函数
    def create_middleware(middleware):
        def exe_middleware(scope, handler):
            async def new_handler(scope, receive, send):
                # 在请求处理前执行逻辑
                await middleware(scope, 'before')
                # 调用下一个处理函数
                await handler(scope, receive, send)
                # 在请求处理后执行逻辑
                await middleware(scope, 'after')

            return new_handler

        return exe_middleware

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
        method, handler = self.routes[request_path]
        # 寻找匹配的路由
        if request_method in method:
            request = AsyncRequest(scope, receive, send)
            response = await handler(request)
            print(response)
            assert isinstance(response, dict), "Response must be a dict"
            code = response.get('code', 200)
            await self.async_response.send_json_response(send, code, response)
            return

        # 没有找到匹配的路由时，发送404响应
        await self.async_response.send_not_found_response(send)



