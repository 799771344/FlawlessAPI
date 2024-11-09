import os
import secrets
import aiofiles
from typing import List, Dict
from pathlib import Path

class FileUploadHandler:
    """文件上传处理器"""
    
    # 文件签名映射
    FILE_SIGNATURES = {
        b'\xFF\xD8\xFF': 'image/jpeg',
        b'\x89\x50\x4E\x47': 'image/png',
        b'\x25\x50\x44\x46': 'application/pdf'
    }
    
    def __init__(self, upload_path: str, 
                 max_size: int = 5*1024*1024,  # 默认最大5MB
                 allowed_types: List[str] = None):  # 允许的文件类型
        self.upload_path = Path(upload_path)
        self.max_size = max_size
        self.allowed_types = allowed_types or ['image/jpeg', 'image/png', 'application/pdf']
        
        # 确保上传目录存在
        self.upload_path.mkdir(parents=True, exist_ok=True)
    
    def _check_file_type(self, content: bytes) -> str:
        """检查文件类型"""
        for signature, mime_type in self.FILE_SIGNATURES.items():
            if content.startswith(signature):
                return mime_type
        return 'application/octet-stream'
        
    async def handle_upload(self, request) -> Dict[str, str]:
        """处理文件上传"""
        try:
            form = await request.form()
            results = {}
            
            for field_name, file in form.items():
                if not hasattr(file, 'filename'):
                    continue
                    
                # 检查文件大小
                content = await file.read()
                if len(content) > self.max_size:
                    raise ValueError(f"File {file.filename} exceeds size limit")
                    
                # 检查文件类型
                file_type = self._check_file_type(content)
                if file_type not in self.allowed_types:
                    raise ValueError(f"File type {file_type} not allowed")
                    
                # 生成安全的文件名
                safe_filename = self._safe_filename(file.filename)
                file_path = self.upload_path / safe_filename
                
                # 写入文件
                async with aiofiles.open(file_path, 'wb') as f:
                    await f.write(content)
                    
                results[field_name] = str(file_path)
                
            return results
            
        except Exception as e:
            raise ValueError(f"Upload failed: {str(e)}")
            
    def _safe_filename(self, filename: str) -> str:
        """生成安全的文件名"""
        # 移除路径分隔符和特殊字符
        filename = os.path.basename(filename)
        filename = ''.join(c for c in filename if c.isalnum() or c in '._-')
        return f"{secrets.token_hex(8)}_{filename}"