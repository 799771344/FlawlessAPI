# distributed/lock.py
import asyncio
from typing import Optional
import aioredis
import time

class DistributedLock:
    """基于Redis的分布式锁实现"""
    
    def __init__(self, redis: aioredis.Redis, lock_name: str, expire: int = 10):
        """
        初始化分布式锁
        Args:
            redis: Redis客户端实例
            lock_name: 锁的名称
            expire: 锁的过期时间(秒)
        """
        self.redis = redis
        self.lock_name = f"lock:{lock_name}"  # 锁的键名
        self.expire = expire  # 锁的过期时间
        self.owner = None  # 当前是否持有锁
        
    async def acquire(self, blocking: bool = True, timeout: Optional[float] = None) -> bool:
        """
        获取锁
        Args:
            blocking: 是否阻塞等待
            timeout: 最大等待时间(秒)
        Returns:
            bool: 是否成功获取锁
        """
        start = time.time()
        while True:
            # 尝试设置锁,nx=True表示key不存在时才设置,ex设置过期时间
            if await self.redis.set(self.lock_name, "1", nx=True, ex=self.expire):
                self.owner = True
                return True
                
            # 非阻塞模式下直接返回False
            if not blocking:
                return False
                
            # 超过等待时间则返回False
            if timeout is not None and time.time() - start > timeout:
                return False
                
            # 等待100ms后重试
            await asyncio.sleep(0.1)
            
    async def release(self):
        """释放锁"""
        if self.owner:
            await self.redis.delete(self.lock_name)  # 删除锁
            self.owner = False  # 更新状态