import json
import typing
from urllib.parse import unquote
from http.client import HTTPConnection
from urllib.parse import parse_qsl
from multipart import parse_options_header
from starlette.datastructures import FormData, Headers, UploadFile
from starlette.formparsers import MultiPartParser, FormParser
from starlette.types import Message, Receive, Scope, Send


class RequestBodyCache:
    """请求体缓存类,用于缓存请求体数据"""
    def __init__(self, capacity=1000):
        """初始化缓存
        Args:
            capacity: 缓存容量,默认1000
        """
        # 存储缓存数据的字典
        self.cache = {}
        # 缓存容量上限
        self.capacity = capacity

    def get(self, key):
        """获取缓存值
        Args:
            key: 缓存键
        Returns:
            缓存的值,如果不存在返回None
        """
        return self.cache.get(key)

    def set(self, key, value):
        """设置缓存
        Args:
            key: 缓存键
            value: 缓存值
        """
        # 如果缓存已满,随机删除一个缓存项
        if len(self.cache) >= self.capacity:
            self.cache.pop(next(iter(self.cache)))
        self.cache[key] = value


class AsyncRequest(HTTPConnection):
    """异步HTTP请求处理类,继承自HTTPConnection"""
    def __init__(self, scope: Scope, receive: Receive, send: Send):
        """初始化请求对象
        Args:
            scope: ASGI scope对象,包含请求的基本信息
            receive: ASGI receive回调,用于接收请求数据
            send: ASGI send回调,用于发送响应数据
        """
        # 调用父类初始化,传入客户端地址和端口
        super().__init__(scope["client"][0], scope["client"][1])
        # 确保请求类型为HTTP
        assert scope["type"] == "http"
        # 保存ASGI相关对象
        self._scope = scope
        self._receive = receive
        self._send = send
        # 标记请求体流是否已被消费
        self._stream_consumed = False
        # 标记客户端是否已断开连接
        self._is_disconnected = False
        # 表单数据缓存
        self._form = None
        # 请求头部信息
        self.headers = self._scope['headers']
        # 请求体缓存
        self._body = None
        # 请求体缓存管理器
        self._body_cache = RequestBodyCache()

    async def stream(self) -> typing.AsyncGenerator[bytes, None]:
        """异步生成器,用于读取请求体数据流
        Yields:
            bytes: 请求体数据块
        Raises:
            RuntimeError: 如果数据流已被消费则抛出异常
        """
        if self._stream_consumed:
            raise RuntimeError("Stream has already been consumed.")
        self._stream_consumed = True
        while True:
            # 接收消息
            message = await self._receive()
            # 处理断开连接的情况
            if message["type"] == "http.disconnect":
                self._is_disconnected = True
                break
            # 只处理HTTP请求消息
            if message["type"] != "http.request":
                continue
            body = message.get("body", b"")
            if body:
                yield body
            # 如果没有更多数据,退出循环
            if not message.get("more_body", False):
                break

    @staticmethod
    def _parse_body(body: bytes, content_type: bytes) -> typing.Any:
        """解析请求体数据
        Args:
            body: 请求体字节数据
            content_type: Content-Type头部值
        Returns:
            解析后的请求体数据,解析失败则返回原始数据
        """
        try:
            # 根据不同的Content-Type解析数据
            if content_type == b'application/x-www-form-urlencoded':
                return dict(parse_qsl(body.decode()))
            elif content_type == b'application/json':
                return json.loads(body.decode())
            return body
        except Exception:
            return body

    async def body(self):
        """获取完整的请求体数据
        Returns:
            解析后的请求体数据
        Raises:
            RuntimeError: 如果数据流已被消费则抛出异常
        """
        # 如果已有缓存,直接返回
        if self._body is not None:
            return self._body
            
        if self._stream_consumed:
            raise RuntimeError("Stream has already been consumed.")
            
        body_bytes = b""
        # 获取Content-Type头部
        content_type = [header[1] for header in self.headers if header[0] == b'content-type']
        if len(content_type) == 0:
            return body_bytes
            
        # 读取并拼接所有数据块
        async for chunk in self.stream():
            body_bytes += chunk
            
        # 解析并缓存结果
        self._body = self._parse_body(body_bytes, content_type[0])
        return self._body

    async def json(self):
        """获取JSON格式的请求体数据
        Returns:
            解析后的JSON数据
        """
        # 获取Content-Type头部
        content_type = [header[1] for header in self.headers if header[0] == b'content-type']
        if len(content_type) == 0:
            return b""
        body_bytes = await self.body()
        return self._parse_body(body_bytes, content_type[0])

    async def query_string(self):
        """获取查询字符串参数
        Returns:
            dict: 解析后的查询参数字典
        """
        query_string = self._scope['query_string']
        return dict(parse_qsl(query_string.decode()))

    async def _get_form(self, *, max_files: typing.Union[int, float] = 1000,
                        max_fields: typing.Union[int, float] = 1000) -> FormData:
        """获取表单数据
        Args:
            max_files: 最大文件数限制
            max_fields: 最大字段数限制
        Returns:
            FormData: 解析后的表单数据对象
        """
        # 如果已有缓存,直接返回
        if self._form is not None:
            return self._form
        # 获取并解析Content-Type
        content_type_header = self.headers.get('content-type')
        content_type, options = parse_options_header(content_type_header)
        # 根据不同的Content-Type使用不同的解析器
        if content_type == b"multipart/form-data":
            multipart_parser = MultiPartParser(self.headers, self.stream(), max_files=max_files, max_fields=max_fields)
            self._form = await multipart_parser.parse()
        elif content_type == b"application/x-www-form-urlencoded":
            form_parser = FormParser(self.headers, self.stream())
            form_data = await form_parser.parse()
            self._form = FormData(form_data, encoding=options.get('charset', 'utf-8'))
        else:
            self._form = FormData()
        return self._form

    async def form(self) -> FormData:
        """获取表单数据的快捷方法
        Returns:
            FormData: 解析后的表单数据对象
        """
        return await self._get_form()

    async def close(self) -> None:
        """关闭请求,清理资源,主要是关闭上传的文件"""
        if self._form is not None:
            for value in self._form.values():
                if isinstance(value, UploadFile):
                    await value.close()

    async def is_disconnected(self) -> bool:
        """检查客户端是否已断开连接
        Returns:
            bool: 是否已断开连接
        """
        return self._is_disconnected

    async def send_push_promise(self, path: str) -> None:
        """发送HTTP/2服务器推送承诺
        Args:
            path: 要推送的资源路径
        """
        # 检查是否支持服务器推送
        if "http.response.push" in self._scope.get("extensions", {}):
            headers = self._scope["headers"]
            push_headers = Headers(raw=headers)
            # 发送推送承诺
            await self._send({
                "type": "http.response.push",
                "path": path,
                "headers": push_headers.raw
            })
