# 导入所需的Python标准库
import time
from collections import defaultdict
import asyncio

class TokenBucket:
    """令牌桶算法实现类
    用于限制请求速率的令牌桶算法。令牌以固定速率生成,请求需要消耗令牌才能被处理。
    """
    def __init__(self, capacity: int, fill_rate: float):
        """初始化令牌桶
        Args:
            capacity: 令牌桶容量,即最大令牌数
            fill_rate: 令牌填充速率(每秒)
        """
        self.capacity = capacity  # 桶的容量
        self.fill_rate = fill_rate  # 令牌填充速率
        self.tokens = capacity  # 当前令牌数,初始化为满
        self.last_update = time.time()  # 上次更新时间
        self._lock = asyncio.Lock()  # 用于并发控制的锁
        
    async def acquire(self, tokens: int = 1) -> bool:
        """请求获取令牌
        Args:
            tokens: 需要的令牌数,默认为1
        Returns:
            bool: 是否成功获取令牌
        """
        async with self._lock:
            now = time.time()
            elapsed = now - self.last_update
            
            # 根据流逝的时间补充令牌
            # 补充的令牌数 = 流逝时间 * 填充速率
            self.tokens = min(
                self.capacity,
                self.tokens + elapsed * self.fill_rate
            )
            self.last_update = now
            
            # 如果当前令牌数足够,则消耗令牌并返回True
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False

class RateLimiter:
    """请求限流器类
    用于对API请求进行速率限制的类
    """
    def __init__(self, requests_per_second: int = 1000):
        """初始化限流器
        Args:
            requests_per_second: 每秒允许的最大请求数
        """
        self.bucket = TokenBucket(requests_per_second, requests_per_second)
        self.waiting_requests = asyncio.Queue()  # 等待队列
        
    async def __call__(self, scope, timing):
        """处理请求的限流逻辑
        Args:
            scope: 请求上下文
            timing: 处理时机
        Raises:
            Exception: 当超过限流阈值时抛出异常
        """
        if timing == 'before':
            if not await self.bucket.acquire():
                # 当无法获取令牌时,将请求放入等待队列
                await self.waiting_requests.put(scope)
                raise Exception("Rate limit exceeded")
