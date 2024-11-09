from typing import Dict, Any, Optional
import asyncio
import aiohttp
from contextlib import asynccontextmanager

class ConnectionPool:
    """连接池类,用于管理和复用连接"""
    def __init__(self, pool_size: int = 1000):
        """
        初始化连接池
        Args:
            pool_size: 连接池大小,默认1000
        """
        self.pool_size = pool_size
        self.semaphore = asyncio.Semaphore(pool_size)  # 使用信号量控制并发连接数
        self._pools: Dict[str, Any] = {}  # 存储不同名称的连接池
        self._stats = {
            'active_connections': 0,  # 当前活跃连接数
            'total_connections': 0,   # 总连接数
            'connection_errors': 0    # 连接错误数
        }
        
    @asynccontextmanager
    async def acquire(self, pool_name: str):
        """
        获取指定名称连接池中的连接
        Args:
            pool_name: 连接池名称
        Returns:
            连接池对象
        Raises:
            ValueError: 当指定的连接池不存在时
        """
        async with self.semaphore:
            try:
                self._stats['active_connections'] += 1
                self._stats['total_connections'] += 1
                pool = self._pools.get(pool_name)
                if not pool:
                    raise ValueError(f"Pool {pool_name} not found")
                return pool
            except Exception as e:
                self._stats['connection_errors'] += 1
                raise e
            
    def get_stats(self):
        """获取连接池统计信息"""
        return self._stats
    
    async def create_http_pool(self, name: str, **kwargs):
        """
        创建HTTP连接池
        Args:
            name: 连接池名称
            **kwargs: 传递给ClientSession的额外参数
        """
        if name in self._pools:
            return
        
        connector = aiohttp.TCPConnector(limit=self.pool_size)
        session = aiohttp.ClientSession(connector=connector, **kwargs)
        self._pools[name] = session
        
    async def close(self):
        """关闭所有连接池并清理资源"""
        for pool in self._pools.values():
            await pool.close()
        self._pools.clear()
        
    async def warmup(self, pool_name: str, connections: int):
        """预热连接池"""
        if pool_name not in self._pools:
            raise ValueError(f"Pool {pool_name} not found")
            
        async def test_connection():
            try:
                async with self.acquire(pool_name) as session:
                    async with session.head('http://localhost') as response:
                        return response.status == 200
            except Exception as e:
                self._stats['connection_errors'] += 1
                return False

        tasks = [test_connection() for _ in range(connections)]
        await asyncio.gather(*tasks)
        