# 导入所需的Python标准库
from dataclasses import dataclass
from typing import Optional

@dataclass
class CacheConfig:
    """缓存配置的基类
    
    定义了基本的缓存参数,包括缓存类型、容量和TTL(生存时间)
    """
    type: str = "lru"  # 缓存类型,默认为LRU(最近最少使用)
    capacity: int = 1000  # 缓存容量,默认1000条
    ttl: int = 3600  # 缓存生存时间,默认3600秒(1小时)
    
@dataclass 
class RedisConfig(CacheConfig):
    """Redis缓存配置类
    
    继承自CacheConfig,添加了Redis特有的连接参数
    """
    type: str = "redis"  # 指定缓存类型为redis
    host: str = "localhost"  # Redis服务器地址,默认本地
    port: int = 6379  # Redis端口号,默认6379
    password: Optional[str] = None  # Redis密码,可选
    db: int = 0  # Redis数据库编号,默认0号库
    
    @property
    def url(self) -> str:
        """生成Redis连接URL
        
        Returns:
            str: 标准格式的Redis连接URL
        """
        auth = f":{self.password}@" if self.password else ""
        return f"redis://{auth}{self.host}:{self.port}/{self.db}"
