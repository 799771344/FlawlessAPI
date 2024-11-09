import logging
import json
import time
import traceback
from typing import Any, Dict, Optional
from pathlib import Path
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler
from datetime import datetime

# 配置基本的日志设置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

class JSONFormatter(logging.Formatter):
    """JSON格式的日志格式化器"""
    
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        super().__init__()
        
    def format(self, record) -> str:
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "line": record.lineno
        }
        
        # 添加异常信息
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__,
                "message": str(record.exc_info[1]),
                "stacktrace": traceback.format_exception(*record.exc_info)
            }
            
        # 添加额外字段
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
            
        # 添加自定义字段
        log_data.update(self.kwargs)
        
        return json.dumps(log_data)

class LoggerManager:
    """日志管理器"""
    
    def __init__(self, 
                 name: str,
                 log_dir: str = "logs",
                 level: str = "INFO",
                 max_size: int = 10*1024*1024,  # 10MB
                 backup_count: int = 10,
                 format_json: bool = True):
        self.name = name
        self.log_dir = Path(log_dir)
        self.level = getattr(logging, level.upper())
        self.max_size = max_size
        self.backup_count = backup_count
        self.format_json = format_json
        
        # 创建日志目录
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化日志器
        self.logger = self._setup_logger()
        
    def _setup_logger(self) -> logging.Logger:
        """设置日志器"""
        logger = logging.getLogger(self.name)
        logger.setLevel(self.level)
        
        # 添加控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(self.level)
        
        # 添加文件处理器
        file_handler = RotatingFileHandler(
            self.log_dir / f"{self.name}.log",
            maxBytes=self.max_size,
            backupCount=self.backup_count
        )
        file_handler.setLevel(self.level)
        
        # 添加错误日志处理器
        error_handler = TimedRotatingFileHandler(
            self.log_dir / f"{self.name}_error.log",
            when="midnight",
            interval=1,
            backupCount=30
        )
        error_handler.setLevel(logging.ERROR)
        
        # 设置格式化器
        if self.format_json:
            formatter = JSONFormatter()
        else:
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            
        console_handler.setFormatter(formatter)
        file_handler.setFormatter(formatter)
        error_handler.setFormatter(formatter)
        
        # 添加处理器
        logger.addHandler(console_handler)
        logger.addHandler(file_handler)
        logger.addHandler(error_handler)
        
        return logger
        
    def get_logger(self) -> logging.Logger:
        """获取日志器"""
        return self.logger

class RequestLogger:
    """请求日志记录器"""
    
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        
    async def log_request(self, request, response=None, error=None):
        """记录请求日志"""
        log_data = {
            "request": {
                "method": request.get("method"),
                "path": request.get("path"),
                "query_params": request.get("query_params"),
                "headers": dict(request.get("headers", {})),
                "client": request.get("client")
            }
        }
        
        if response:
            log_data["response"] = {
                "status": response.get("status"),
                "headers": dict(response.get("headers", {}))
            }
            
        if error:
            log_data["error"] = {
                "type": type(error).__name__,
                "message": str(error)
            }
            self.logger.error("Request failed", extra=log_data)
        else:
            self.logger.info("Request completed", extra=log_data)