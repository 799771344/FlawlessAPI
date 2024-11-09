# 导入所需的Python标准库
from functools import lru_cache  # 用于缓存函数结果
from typing import Optional, Union  # 用于类型提示
import os  # 用于获取环境变量
import yaml  # 用于解析YAML配置文件
from dataclasses import dataclass  # 用于创建数据类

# 导入自定义的缓存配置类
from config.cache_config import CacheConfig, RedisConfig

class Settings:
    """
    应用程序配置管理类
    负责管理和加载各种配置选项
    """
    
    @lru_cache()  # 使用LRU缓存装饰器缓存配置结果
    def get_cache_config(self) -> Union[CacheConfig, RedisConfig]:
        """
        获取缓存配置
        根据环境变量返回LRU缓存或Redis缓存的配置
        
        Returns:
            Union[CacheConfig, RedisConfig]: 缓存配置对象
        """
        cache_type = os.getenv("CACHE_TYPE", "lru")  # 获取缓存类型,默认为LRU
        
        if cache_type == "redis":
            # 如果是Redis缓存,返回Redis配置
            return RedisConfig(
                host=os.getenv("REDIS_HOST", "localhost"),  # Redis主机地址
                port=int(os.getenv("REDIS_PORT", "6379")),  # Redis端口
                password=os.getenv("REDIS_PASSWORD"),  # Redis密码
                db=int(os.getenv("REDIS_DB", "0")),  # Redis数据库编号
                ttl=int(os.getenv("CACHE_TTL", "3600"))  # 缓存过期时间
            )
        
        # 默认返回LRU缓存配置
        return CacheConfig(
            capacity=int(os.getenv("CACHE_CAPACITY", "1000")),  # LRU缓存容量
            ttl=int(os.getenv("CACHE_TTL", "3600"))  # 缓存过期时间
        )
    
    @classmethod
    def from_yaml(cls, path: str) -> "Settings":
        """
        从YAML文件加载配置
        
        Args:
            path (str): YAML配置文件路径
            
        Returns:
            Settings: 配置对象实例
        """
        with open(path) as f:
            config = yaml.safe_load(f)
        # 处理配置...
        return cls()

@dataclass
class APIConfig:
    """
    API相关配置的数据类
    控制内置路由和暴露的系统接口
    """
    enable_builtin_routes: bool = True  # 是否启用内置路由
    builtin_route_prefix: str = "_"     # 内置路由的URL前缀
    expose_metrics: bool = True         # 是否暴露指标接口
    expose_traces: bool = True          # 是否暴露追踪接口
    expose_health: bool = True          # 是否暴露健康检查接口
    expose_info: bool = True            # 是否暴露系统信息接口

    # 模板配置
    enable_templates: bool = False
    template_dir: str = "templates"
    template_cache_size: int = 100
    
    # 文件上传配置
    enable_file_uploads: bool = False
    upload_dir: str = "uploads"
    max_upload_size: int = 5 * 1024 * 1024  # 5MB
    
    # WebSocket配置
    enable_websocket: bool = False
    
    # 数据库配置
    database_url: Optional[str] = None
    
    # 国际化配置
    enable_i18n: bool = False
    locale_dir: str = "locales"
    default_locale: str = "en"
    
    # 任务队列配置
    enable_task_queue: bool = False
    task_queue_workers: int = 3
    
    # 服务注册配置
    enable_service_registry: bool = False
    registry_url: Optional[str] = None
    service_name: Optional[str] = None
    service_url: Optional[str] = None
    
    # API文档配置
    enable_api_docs: bool = True
    api_title: str = "API Documentation"
    api_version: str = "1.0.0"

# 创建全局配置实例
settings = Settings()
