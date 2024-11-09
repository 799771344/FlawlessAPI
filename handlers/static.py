import os
import mimetypes
from pathlib import Path
import aiofiles
from typing import Optional

class StaticFileHandler:
    """静态文件服务处理器"""
    
    def __init__(self, directory: str, 
                 cache_control: str = "public, max-age=3600",
                 index_file: str = "index.html"):
        self.directory = Path(directory)
        self.cache_control = cache_control
        self.index_file = index_file
        
        # 确保目录存在
        if not self.directory.exists():
            raise ValueError(f"Directory {directory} does not exist")
            
    async def serve(self, path: str, send) -> bool:
        """
        服务静态文件
        
        Args:
            path: 请求路径
            send: ASGI send函数
            
        Returns:
            bool: 是否成功处理了请求
        """
        try:
            # 规范化路径
            normalized_path = self._normalize_path(path)
            if normalized_path is None:
                return False
                
            file_path = self.directory / normalized_path
            
            # 处理目录请求
            if file_path.is_dir():
                file_path = file_path / self.index_file
                
            # 检查文件是否存在
            if not file_path.is_file():
                return False
                
            # 获取文件类型
            content_type = self._get_content_type(file_path)
            
            # 发送响应头
            await send({
                "type": "http.response.start",
                "status": 200,
                "headers": [
                    [b"content-type", content_type.encode()],
                    [b"cache-control", self.cache_control.encode()]
                ]
            })
            
            # 分块读取并发送文件内容
            async with aiofiles.open(file_path, 'rb') as f:
                while chunk := await f.read(8192):  # 8KB chunks
                    await send({
                        "type": "http.response.body",
                        "body": chunk,
                        "more_body": True
                    })
                    
            # 发送结束标记
            await send({
                "type": "http.response.body",
                "body": b"",
                "more_body": False
            })
            
            return True
            
        except Exception as e:
            print(f"Static file error: {e}")
            return False
            
    def _normalize_path(self, path: str) -> Optional[str]:
        """规范化路径,防止目录遍历攻击"""
        try:
            normalized = Path(path).relative_to("/")
            # 确保路径在静态目录内
            if ".." in normalized.parts:
                return None
            return str(normalized)
        except ValueError:
            return None
            
    def _get_content_type(self, path: Path) -> str:
        """获取文件的Content-Type"""
        content_type, _ = mimetypes.guess_type(str(path))
        return content_type or 'application/octet-stream'