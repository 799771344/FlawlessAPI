from typing import Optional, Dict, Any
import databases
import sqlalchemy
from contextlib import asynccontextmanager

class DatabaseManager:
    """数据库管理器"""
    
    def __init__(self, url: str, min_size: int = 5, max_size: int = 20):
        self.database = databases.Database(url, min_size=min_size, max_size=max_size)
        self.engine = sqlalchemy.create_engine(url)
        self._transaction_contexts = {}  # 存储事务上下文
        
    async def connect(self):
        """连接数据库"""
        if not self.database.is_connected:
            await self.database.connect()
            
    async def disconnect(self):
        """断开数据库连接"""
        if self.database.is_connected:
            await self.database.disconnect()
            
    @asynccontextmanager
    async def transaction(self):
        """事务上下文管理器"""
        async with self.database.transaction() as transaction:
            try:
                yield transaction
            except Exception as e:
                print(f"Transaction error: {e}")
                raise
                
    async def execute(self, query: str, values: Optional[Dict[str, Any]] = None):
        """执行SQL查询"""
        try:
            return await self.database.execute(query=query, values=values)
        except Exception as e:
            print(f"Query execution error: {e}")
            raise
            
    async def fetch_all(self, query: str, values: Optional[Dict[str, Any]] = None):
        """获取所有查询结果"""
        try:
            return await self.database.fetch_all(query=query, values=values)
        except Exception as e:
            print(f"Fetch error: {e}")
            raise
            
    async def fetch_one(self, query: str, values: Optional[Dict[str, Any]] = None):
        """获取单个查询结果"""
        try:
            return await self.database.fetch_one(query=query, values=values)
        except Exception as e:
            print(f"Fetch error: {e}")
            raise