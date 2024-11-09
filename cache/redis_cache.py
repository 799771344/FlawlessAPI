import aioredis  # 导入异步Redis客户端库
from typing import Optional, Any, Union  # 导入类型提示相关的类型
import pickle  # 导入序列化/反序列化库
import logging  # 导入日志模块
import json  # 导入JSON处理库
from datetime import datetime, timedelta  # 导入日期时间相关类

# 获取logger实例
logger = logging.getLogger(__name__)

class RedisCache:
    """Redis缓存类,提供异步的缓存操作接口"""
    
    def __init__(self, redis_url: str = "redis://localhost:6379", 
                 default_ttl: int = 3600):
        """
        初始化Redis缓存
        Args:
            redis_url: Redis连接URL,默认为localhost:6379
            default_ttl: 默认的缓存过期时间(秒),默认1小时
        """
        self.redis_url = redis_url
        self.default_ttl = default_ttl
        self._redis: Optional[aioredis.Redis] = None  # Redis客户端实例
        # 缓存统计信息
        self._stats = {
            'hits': 0,    # 缓存命中次数
            'misses': 0,  # 缓存未命中次数
            'errors': 0   # 错误次数
        }
    
    async def connect(self):
        """
        建立Redis连接
        Raises:
            Exception: Redis连接失败时抛出异常
        """
        try:
            self._redis = await aioredis.from_url(self.redis_url)
            logger.info(f"Connected to Redis at {self.redis_url}")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise
    
    async def get(self, key: str) -> Optional[Any]:
        """
        获取缓存值
        Args:
            key: 缓存键
        Returns:
            Any: 缓存的值,如果不存在则返回None
        """
        try:
            value = await self._redis.get(key)
            if value:
                self._stats['hits'] += 1
                return pickle.loads(value)  # 反序列化缓存值
            self._stats['misses'] += 1
            return None
        except Exception as e:
            self._stats['errors'] += 1
            logger.error(f"Redis get error: {e}")
            return None

    async def set(self, key: str, value: Any, 
                 expire: Optional[Union[int, timedelta]] = None):
        """
        设置缓存值
        Args:
            key: 缓存键
            value: 要缓存的值
            expire: 过期时间(秒或timedelta对象),None则使用默认过期时间
        """
        try:
            expire = expire or self.default_ttl
            pickled_value = pickle.dumps(value)  # 序列化值
            await self._redis.set(key, pickled_value, ex=expire)
        except Exception as e:
            self._stats['errors'] += 1
            logger.error(f"Redis set error: {e}")

    async def delete(self, key: str):
        """
        删除缓存
        Args:
            key: 要删除的缓存键
        """
        try:
            await self._redis.delete(key)
        except Exception as e:
            logger.error(f"Redis delete error: {e}")

    def get_stats(self):
        """
        获取缓存统计信息
        Returns:
            dict: 包含命中次数、未命中次数、错误次数和命中率的统计信息
        """
        total = self._stats['hits'] + self._stats['misses']
        hit_rate = self._stats['hits'] / total if total > 0 else 0
        return {
            **self._stats,
            'hit_rate': f"{hit_rate:.2%}"  # 格式化命中率为百分比
        }

    async def close(self):
        """关闭Redis连接"""
        if self._redis:
            await self._redis.close()