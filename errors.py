# errors.py - 错误处理模块

import time
from typing import Optional, Dict, Any
import traceback
import logging

from response import error_response

class APIError(Exception):
    """
    自定义API错误类,用于规范化API错误响应
    继承自Exception基类
    """
    def __init__(self, 
                 message: str,  # 错误消息
                 code: int = 400,  # HTTP状态码,默认400表示客户端错误
                 detail: Optional[Dict[str, Any]] = None):  # 错误详情,可选
        self.message = message  # 错误消息
        self.code = code  # 状态码
        self.detail = detail  # 详细错误信息
        super().__init__(message)  # 调用父类构造函数

class ErrorHandler:
    """
    错误处理器类
    统一处理API错误和系统错误,提供错误日志记录功能
    """
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        初始化错误处理器
        Args:
            logger: 日志记录器实例,如果为None则创建默认logger
        """
        self.logger = logger or logging.getLogger(__name__)
        
    async def handle(self, error: Exception) -> Dict[str, Any]:
        """处理错误并返回标准化的错误响应"""
        if isinstance(error, APIError):
            return error_response(
                code=error.code,
                message=error.message,
                data=error.detail
            ).dict()
            
        # 处理系统错误
        error_id = self._log_error(error)
        return error_response(
            code=500,
            message="Internal Server Error",
            data={"error_id": error_id}
        ).dict()
        
    def _log_error(self, error: Exception) -> str:
        """
        记录错误日志
        Args:
            error: 异常对象
        Returns:
            str: 生成的错误ID
        """
        error_id = str(hash(time.time()))  # 基于时间戳生成唯一错误ID
        self.logger.error(  # 记录详细的错误信息
            f"Error ID: {error_id}\n"
            f"Type: {type(error).__name__}\n"  # 错误类型
            f"Message: {str(error)}\n"  # 错误消息
            f"Traceback:\n{traceback.format_exc()}"  # 完整的堆栈跟踪
        )
        return error_id