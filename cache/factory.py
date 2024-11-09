from config.cache_config import CacheConfig, RedisConfig


class CacheFactory:
    """
    缓存工厂类
    用于根据配置创建不同类型的缓存实例
    支持创建Redis缓存和LRU缓存
    """
    
    @staticmethod
    def create_cache(config: CacheConfig):
        """
        根据配置创建缓存实例的工厂方法
        
        Args:
            config: 缓存配置对象,可以是RedisConfig或CacheConfig类型
            
        Returns:
            根据配置返回对应的缓存实例:
            - 如果是RedisConfig配置,返回RedisCache实例
            - 如果是CacheConfig配置,返回LRUCache实例
        """
        if isinstance(config, RedisConfig):
            # 如果是Redis配置,则创建Redis缓存
            from .redis_cache import RedisCache
            return RedisCache(
                redis_url=config.url,  # Redis连接URL
                default_ttl=config.ttl  # 默认过期时间
            )
        else:
            # 默认创建LRU缓存
            from .lru_cache import LRUCache 
            return LRUCache(
                capacity=config.capacity,  # LRU缓存容量
                ttl=config.ttl  # 缓存过期时间
            )
