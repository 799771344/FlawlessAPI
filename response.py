import json
import gzip
import logging
import time
from typing import Dict, Any, Optional
from collections import OrderedDict

from pydantic import BaseModel

from cache.lru_cache import LRUCache
from dataclasses import dataclass
from typing import TypeVar, Generic, Optional
import functools


class ResponseCache:
    """响应缓存类,用于缓存响应数据
    
    属性:
        cache (OrderedDict): 有序字典,用于存储缓存的响应数据
        timestamps (OrderedDict): 有序字典,用于存储缓存项的时间戳
        capacity (int): 缓存容量上限
        ttl (int): 缓存项的生存时间(秒)
    """
    def __init__(self, capacity: int = 1000, ttl: int = 300):  # 添加TTL
        self.cache = OrderedDict()  # 使用OrderedDict保持缓存项的顺序
        self.timestamps = OrderedDict()  # 存储每个缓存项的时间戳
        self.capacity = capacity  # 缓存容量上限
        self.ttl = ttl  # 缓存生存时间,单位秒

    def get(self, key: str) -> Optional[bytes]:
        """获取缓存项
        
        Args:
            key: 缓存键
            
        Returns:
            bytes或None: 如果缓存命中返回缓存值,否则返回None
        """
        if key not in self.cache:
            return None
        self.cache.move_to_end(key)  # 将访问的项移到末尾(LRU策略)
        return self.cache[key]

    def set(self, key: str, value: bytes):
        """设置缓存项
        
        Args:
            key: 缓存键
            value: 要缓存的字节数据
        """
        current_time = time.time()
        self.cache[key] = value
        self.timestamps[key] = current_time
        self._cleanup_expired()  # 清理过期缓存
        
    def _cleanup_expired(self):
        """清理过期的缓存项"""
        current_time = time.time()
        # 找出所有过期的缓存项
        expired = [
            key for key, timestamp in self.timestamps.items()
            if current_time - timestamp > self.ttl
        ]
        # 删除过期项
        for key in expired:
            del self.cache[key]
            del self.timestamps[key]

class AsyncResponse:
    """异步响应处理类
    
    提供JSON响应、文件响应、流式响应等功能,支持压缩和缓存
    
    属性:
        cache (ResponseCache): 响应缓存对象
        COMPRESSION_THRESHOLD (int): 启用压缩的阈值大小
        COMPRESSION_LEVEL (int): 默认压缩级别
        MIN_COMPRESSION_RATIO (float): 最小压缩比
        _compression_levels (dict): 不同数据大小对应的压缩级别
        serialization_cache (LRUCache): 序列化结果缓存
        logger (Logger): 日志记录器
        _stats (dict): 响应统计信息
    """
    def __init__(self):
        self.cache = ResponseCache()
        self.COMPRESSION_THRESHOLD = 2048  # 压缩阈值2KB
        self.COMPRESSION_LEVEL = 6  # 默认压缩级别
        self.MIN_COMPRESSION_RATIO = 0.9  # 最小压缩比
        # 根据数据大小设置不同的压缩级别
        self._compression_levels = {
            1024: 1,      # 1KB使用最低压缩级别
            10240: 4,     # 10KB使用中等压缩级别
            102400: 6,    # 100KB使用较高压缩级别
            1048576: 9    # 1MB使用最高压缩级别
        }
        self.serialization_cache = LRUCache(capacity=5000)  # 序列化缓存
        self.logger = logging.getLogger(__name__)
        # 统计信息
        self._stats = {
            'response_times': [],  # 响应时间列表
            'compression_ratios': [],  # 压缩比列表
            'cache_hits': 0,  # 缓存命中次数
            'cache_misses': 0  # 缓存未命中次数
        }

    def _get_compression_level(self, data_size: int) -> int:
        """根据数据大小动态确定压缩级别
        
        Args:
            data_size: 数据大小(字节)
            
        Returns:
            int: 合适的压缩级别(1-9)
        """
        for threshold, level in sorted(self._compression_levels.items()):
            if data_size <= threshold:
                return level
        return 9  # 对于超大数据使用最高压缩级别

    async def send_json_response(self, send, status_code: int, body_dict: Dict[str, Any]) -> None:
        """发送JSON响应
        
        Args:
            send: ASGI发送回调函数
            status_code: HTTP状态码
            body_dict: 要发送的字典数据
        """
        try:
            # 生成缓存键
            cache_key = f"{status_code}:{hash(str(body_dict))}"
            
            # 尝试从缓存获取
            cached_data = await self.serialization_cache.get(cache_key)
            if cached_data:
                await self._send_cached_response(send, status_code, cached_data)
                return

            # 序列化逻辑
            try:
                # 1. 处理 Pydantic 模型
                if hasattr(body_dict, 'model_dump_json'):  # Pydantic v2
                    bytes_data = body_dict.model_dump_json().encode('utf-8')
                elif hasattr(body_dict, 'json'):  # Pydantic v1
                    bytes_data = body_dict.json().encode('utf-8')
                # 2. 处理 dict 类型
                elif isinstance(body_dict, dict):
                    # 递归处理嵌套的 Pydantic 模型
                    def process_dict(d):
                        result = {}
                        for k, v in d.items():
                            if hasattr(v, 'dict'):
                                result[k] = v.dict()
                            elif isinstance(v, dict):
                                result[k] = process_dict(v)
                            elif isinstance(v, (list, tuple)):
                                result[k] = [
                                    item.dict() if hasattr(item, 'dict') else item 
                                    for item in v
                                ]
                            else:
                                result[k] = v
                        return result
                    
                    processed_dict = process_dict(body_dict)
                    bytes_data = json.dumps(processed_dict).encode('utf-8')
                # 3. 处理其他类型
                else:
                    bytes_data = json.dumps(str(body_dict)).encode('utf-8')

            except Exception as e:
                self.logger.error(f"Serialization error: {e}")
                # 发送错误响应
                error_data = json.dumps({
                    "error": "Serialization failed",
                    "message": str(e)
                }).encode('utf-8')
                await self._send_response(send, 500, error_data, 
                    [[b'content-type', b'application/json; charset=utf-8']])
                return

            # 设置响应头
            headers = [[b'content-type', b'application/json; charset=utf-8']]

            # 压缩处理
            if len(bytes_data) > self.COMPRESSION_THRESHOLD:
                compression_level = self._get_compression_level(len(bytes_data))
                compressed_data = gzip.compress(bytes_data, compresslevel=compression_level)
                
                if len(compressed_data) < len(bytes_data) * self.MIN_COMPRESSION_RATIO:
                    print(f"[Compression] Ratio: {len(compressed_data)/len(bytes_data):.2%}")
                    bytes_data = compressed_data
                    headers.append([b'content-encoding', b'gzip'])

            # 缓存响应
            self.cache.set(cache_key, bytes_data)
            
            # 发送响应
            await self._send_response(send, status_code, bytes_data, headers)

        except Exception as e:
            self.logger.error(f"Failed to send response: {e}")
            # 发送错误响应
            await self.send_error_response(send, 500, str(e))
    
    async def send_error_response(self, send, status_code: int, message: str):
        """发送错误响应
        
        Args:
            send: ASGI发送回调函数
            status_code: HTTP错误状态码
            message: 错误信息
        """
        body_dict = {
            "code": status_code,
            "message": message,
            "timestamp": time.time()
        }
        await self.send_json_response(send, status_code, body_dict)

    async def send_file_response(self, send, file_path: str, content_type: str = None):
        """发送文件响应
        
        Args:
            send: ASGI发送回调函数
            file_path: 文件路径
            content_type: 文件内容类型
        """
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
            
            headers = [[b'content-type', content_type.encode() if content_type else b'application/octet-stream']]
            await self._send_response(send, 200, content, headers)
        except Exception as e:
            await self.send_error_response(send, 500, f"Failed to send file: {str(e)}")

    async def send_stream_response(self, send, generator, content_type: str = 'text/plain'):
        """发送流式响应
        
        Args:
            send: ASGI发送回调函数
            generator: 数据生成器
            content_type: 内容类型
        """
        headers = [[b'content-type', content_type.encode()]]
        # 发送响应头
        await send({
            'type': 'http.response.start',
            'status': 200,
            'headers': headers,
        })
        
        # 逐块发送数据
        async for chunk in generator:
            await send({
                'type': 'http.response.body',
                'body': chunk if isinstance(chunk, bytes) else chunk.encode(),
                'more_body': True
            })
        
        # 发送结束标记
        await send({
            'type': 'http.response.body',
            'body': b'',
            'more_body': False
        })

    def get_stats(self):
        """获取响应统计信息
        
        Returns:
            dict: 包含平均响应时间、压缩比、缓存命中率等统计信息
        """
        avg_response_time = sum(self._stats['response_times']) / len(self._stats['response_times']) if self._stats['response_times'] else 0
        avg_compression_ratio = sum(self._stats['compression_ratios']) / len(self._stats['compression_ratios']) if self._stats['compression_ratios'] else 0
        
        return {
            'average_response_time': f"{avg_response_time:.2f}ms",
            'average_compression_ratio': f"{avg_compression_ratio:.2%}",
            'cache_hit_rate': f"{self._stats['cache_hits'] / (self._stats['cache_hits'] + self._stats['cache_misses']):.2%}" if (self._stats['cache_hits'] + self._stats['cache_misses']) > 0 else "0%"
        }

    async def _send_cached_response(self, send, status_code: int, body: bytes):
        """发送缓存的响应
        
        Args:
            send: ASGI发送回调函数
            status_code: HTTP状态码
            body: 响应体数据
        """
        headers = [[b'content-type', b'application/json']]
        if len(body) > self.COMPRESSION_THRESHOLD:
            headers.append([b'content-encoding', b'gzip'])
        await self._send_response(send, status_code, body, headers)

    @staticmethod
    async def _send_response(send, status_code: int, body: bytes, headers: list):
        """发送HTTP响应
        
        Args:
            send: ASGI发送回调函数
            status_code: HTTP状态码
            body: 响应体数据
            headers: 响应头列表
        """
        # 发送��应头
        await send({
            'type': 'http.response.start',
            'status': status_code,
            'headers': headers,
        })
        
        # 分块发送响应体
        chunk_size = 8192  # 8KB的块大小
        for i in range(0, len(body), chunk_size):
            chunk = body[i:i + chunk_size]
            more_body = i + chunk_size < len(body)
            await send({
                'type': 'http.response.body',
                'body': chunk,
                'more_body': more_body
            })

    async def send_not_found_response(self, send):
        """发送404 Not Found响应
        
        Args:
            send: ASGI发送回调函数
        """
        body_dict = {
            "code": 404,
            "message": "Not Found",
            "detail": "The requested resource was not found",
            "timestamp": time.time()
        }
        await self.send_json_response(send, 404, body_dict)

# 定义泛型类型变量
T = TypeVar('T')

class ApiResponse(Generic[T]):
    """统一API响应类"""
    code: int = 200
    message: str = "success"
    data: Optional[T] = None
    timestamp: float = time.time()

    def __init__(
        self,
        *,
        code: int = 200,
        message: str = "success",
        data: Optional[T] = None
    ):
        self.code = code
        self.message = message
        self.data = data
        self.timestamp = time.time()

    def dict(self) -> dict:
        """转换为字典格式"""
        # 处理 Pydantic 模型
        if isinstance(self.data, BaseModel):
            data = self.data.model_dump() if hasattr(self.data, 'model_dump') else self.data.dict()
        else:
            data = self.data

        return {
            "code": self.code,
            "message": self.message,
            "data": data,
            "timestamp": self.timestamp
        }

def api_response(func):
    """API响应包装器装饰器"""
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            # 执行原函数
            result = await func(*args, **kwargs)
            
            # 如果返回值已经是ApiResponse类型,直接返回其字典表示
            if isinstance(result, ApiResponse):
                return result.dict()
                
            # 如果是异常响应(带code的字典),保持原样
            if isinstance(result, dict) and "code" in result and result["code"] != 0:
                return result
                
            # 如果是Pydantic模型,直接返回
            if hasattr(result, 'model_dump'):  # Pydantic v2
                return result.model_dump()
            elif hasattr(result, 'dict'):  # Pydantic v1
                return result.dict()
                
            # 包装正常响应
            return ApiResponse(data=result).dict()
            
        except Exception as e:
            # 处理异常情况
            return ApiResponse(
                code=getattr(e, 'code', 500),
                message=str(e),
                data=None
            ).dict()
            
    return wrapper

def success_response(data: Any = None, message: str = "success") -> ApiResponse:
    """成功响应"""
    return ApiResponse(code=200, message=message, data=data)

def error_response(code: int = 400, message: str = "error", data: Any = None) -> ApiResponse:
    """错误响应"""
    return ApiResponse(code=code, message=message, data=data)

def not_found_response(message: str = "Resource not found") -> ApiResponse:
    """404响应"""
    return ApiResponse(code=404, message=message)

def validation_error_response(message: str = "Validation error", errors: Any = None) -> ApiResponse:
    """验证错误响应"""
    return ApiResponse(code=422, message=message, data=errors)