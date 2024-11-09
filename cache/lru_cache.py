# 导入所需的标准库
import functools  # 用于装饰器功能
import time  # 用于时间相关操作
import asyncio  # 用于异步编程
import logging  # 用于日志记录
from typing import Optional, Any, Dict, Tuple, Callable  # 类型提示
from collections import OrderedDict  # 有序字典数据结构

class CacheItem:
    """缓存项类,用于存储缓存的值和相关元数据"""
    def __init__(self, value: Any, expire_at: Optional[float] = None):
        self.value = value  # 缓存的实际值
        self.expire_at = expire_at  # 过期时间戳
        self.access_count = 0  # 访问计数
        self.created_at = time.time()  # 创建时间戳

class LRUCache:
    """LRU(最近最少使用)缓存实现类"""
    def __init__(self, 
                 capacity: int = 1000,  # 缓存容量
                 max_memory_mb: Optional[float] = None,  # 最大内存限制(MB)
                 logger: Optional[logging.Logger] = None,  # 日志记录器
                 cleanup_interval: int = 60,  # 清理间隔(秒)
                 ttl: int = 3600):  # 默认生存时间(秒)
        self.cache: OrderedDict[str, CacheItem] = OrderedDict()  # 使用OrderedDict存储缓存项
        self.capacity = capacity  # 缓存容量
        self.max_memory = max_memory_mb * 1024 * 1024 if max_memory_mb else None  # 转换MB为字节
        self._lock = asyncio.Lock()  # 异步锁,用于线程安全
        self.hits = 0  # 缓存命中次数
        self.misses = 0  # 缓存未命中次数
        self.logger = logger or logging.getLogger(__name__)  # 日志记录器
        self._cleanup_task = None  # 清理任务引用
        self.cleanup_interval = cleanup_interval  # 清理间隔
        self.ttl = ttl  # 生存时间
        self._stats = {  # 统计信息
            'hits': 0,
            'misses': 0,
            'evictions': 0,
            'memory_usage': 0
        }

    async def start(self):
        """启动缓存清理任务"""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
            
    async def _cleanup_loop(self):
        """定期清理过期缓存的循环"""
        while True:
            await asyncio.sleep(60)  # 每分钟清理一次
            self._cleanup_expired()
            
    def _cleanup_expired(self):
        """清理过期的缓存项"""
        current_time = time.time()
        expired = [
            key for key, timestamp in self.timestamps.items()
            if current_time - timestamp > self.ttl
        ]
        for key in expired:
            if key in self.cache:
                del self.cache[key]
                del self.timestamps[key]
        
    async def get(self, key: str) -> Optional[Any]:
        """
        获取缓存值
        :param key: 缓存键
        :return: 缓存值,如果不存在或已过期则返回None
        """
        async with self._lock:
            if key not in self.cache:
                self.misses += 1
                self.logger.debug(f"Cache miss for key: {key}")
                return None
                
            item = self.cache[key]
            current_time = time.time()
            
            # 检查是否过期
            if item.expire_at and current_time > item.expire_at:
                self.cache.pop(key)
                self.misses += 1
                self.logger.debug(f"Cache expired for key: {key}")
                return None
                
            item.access_count += 1
            self.hits += 1
            self.logger.debug(f"Cache hit for key: {key}")
            
            # 将访问的项移到末尾(最近使用)
            self.cache.move_to_end(key)
            return item.value

    async def set(self, key: str, value: Any, expire: Optional[int] = None):
        """
        设置缓存值
        :param key: 缓存键
        :param value: 缓存值
        :param expire: 过期时间(秒)
        """
        async with self._lock:
            # 检查内存限制
            if self.max_memory and self._estimate_memory_usage() >= self.max_memory:
                self._cleanup_by_memory()
            
            expire_at = time.time() + (expire or self.ttl)  # 计算过期时间戳
            cache_item = CacheItem(value, expire_at)
            
            # 如果键已存在,移到末尾
            if key in self.cache:
                self.cache.move_to_end(key)
            self.cache[key] = cache_item
            
            await self._cleanup()

    def _estimate_memory_usage(self) -> int:
        """估算当前缓存使用的内存(字节)"""
        import sys
        return sum(sys.getsizeof(item.value) for item in self.cache.values())

    def _cleanup_by_memory(self):
        """基于内存使用清理缓存,移除最旧的项直到内存使用量低于限制"""
        while (self.max_memory and 
               self._estimate_memory_usage() >= self.max_memory and 
               self.cache):
            self.cache.popitem(last=False)

    async def _cleanup(self):
        """清理过期和超出容量的缓存项"""
        current_time = time.time()
        
        # 清理过期项
        expired_keys = [
            k for k, v in self.cache.items()
            if v.expire_at and current_time > v.expire_at
        ]
        for k in expired_keys:
            self.cache.pop(k)
            
        # 清理超出容量的项
        while len(self.cache) > self.capacity:
            self.cache.popitem(last=False)

    async def clear(self):
        """清空整个缓存"""
        async with self._lock:
            self.cache.clear()

    async def get_stats(self):
        """获取缓存统计信息"""
        return {
            'size': len(self.cache),
            'capacity': self.capacity,
            'ttl': self.ttl
        }
    
# 创建全局缓存实例
cache = LRUCache()

# 定义缓存键生成器类型
KeyGenerator = Callable[..., str]

def default_key_generator(prefix: str, func_name: str, args: tuple, kwargs: dict) -> str:
    """
    默认的缓存键生成器
    :param prefix: 键前缀
    :param func_name: 函数名
    :param args: 位置参数
    :param kwargs: 关键字参数
    :return: 生成的缓存键
    """
    return f"{prefix}:{func_name}:{hash(str(args))}:{hash(str(kwargs))}"

def cached(expire: int = 60, 
          key_prefix: str = "",
          key_generator: Optional[KeyGenerator] = None):
    """
    缓存装饰器
    :param expire: 缓存过期时间(秒)
    :param key_prefix: 缓存键前缀
    :param key_generator: 自定义缓存键生成器
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            # 使用自定义或默认的键生成器
            key_gen = key_generator or default_key_generator
            cache_key = key_gen(key_prefix, func.__name__, args, kwargs)
            
            # 尝试获取缓存
            cached_value = await cache.get(cache_key)
            if cached_value is not None:
                return cached_value
            
            # 执行原函数并缓存结果
            try:
                result = await func(*args, **kwargs)
            except Exception as e:
                cache.logger.error(f"Error executing {func.__name__}: {str(e)}")
                raise e
                
            await cache.set(cache_key, result, expire)
            return result
            
        async def clear_cache(*args, **kwargs):
            """清除特定函数的缓存"""
            key_gen = key_generator or default_key_generator
            cache_key = key_gen(key_prefix, func.__name__, args, kwargs)
            await cache.clear()
            
        wrapper.clear_cache = clear_cache
        return wrapper
    return decorator
