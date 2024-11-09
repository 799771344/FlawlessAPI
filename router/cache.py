from collections import defaultdict
import time
from typing import Optional, Any
from cache.lru_cache import LRUCache

# 路由缓存类
class RouteCache(LRUCache):
    """
    路由缓存管理类
    实现LRU缓存策略,支持热点路由保护
    """
    def __init__(self, capacity: int = 1000):
        """
        初始化缓存
        :param capacity: 缓存容量
        """
        super().__init__(capacity)
        self.hit_patterns = defaultdict(int)      # 记录模式命中次数
        self.pattern_latencies = defaultdict(list) # 记录模式响应延迟
        self.hot_routes = set()                   # 记录热点路由
        self.access_count = defaultdict(int)      # 记录访问次数

    async def start(self):
        """启动缓存清理任务"""
        await super().start()

    async def get(self, key: str) -> Optional[Any]:
        """
        获取缓存值并更新访问统计
        :param key: 缓存键
        :return: 缓存的值
        """
        self.access_count[key] += 1
        # 判断是否为热点路由
        if self.access_count[key] > 1000:  
            self.hot_routes.add(key)
        return await super().get(key)
        
    async def _cleanup_expired(self):
        """
        清理过期缓存
        保护热点路由不被清理
        """
        current_time = time.time()
        expired = [
            key for key, timestamp in self.timestamps.items()
            if current_time - timestamp > self.ttl and key not in self.hot_routes
        ]
        for key in expired:
            self.delete(key)
        
    async def set(self, key: str, value: Any, pattern: str = None):
        """
        设置缓存值
        :param key: 缓存键
        :param value: 缓存值
        :param pattern: 路由模式
        """
        await super().set(key, value)
        if pattern:
            self.hit_patterns[pattern] += 1
            
    async def get_pattern_stats(self):
        """
        获取路由模式统计信息
        :return: 包含热门模式和延迟统计的字典
        """
        return {
            'popular_patterns': sorted(
                self.hit_patterns.items(),
                key=lambda x: x[1],
                reverse=True
            )[:10],  # 返回访问最多的10个模式
            'pattern_latencies': {
                pattern: sum(times)/len(times)  # 计算平均延迟
                for pattern, times in self.pattern_latencies.items()
            }
        }
