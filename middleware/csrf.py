import secrets
from typing import Optional
from datetime import datetime, timedelta

class CSRFMiddleware:
    """CSRF防护中间件"""
    
    def __init__(self, secret_key: str = None):
        self.secret_key = secret_key or secrets.token_urlsafe(32)
        self.tokens = {}  # 存储token
        
    def generate_token(self) -> str:
        """生成CSRF token"""
        token = secrets.token_urlsafe(32)
        self.tokens[token] = datetime.now()
        return token
        
    def validate_token(self, token: str) -> bool:
        """验证CSRF token"""
        if token not in self.tokens:
            return False
            
        # 检查token是否过期(1小时)
        token_time = self.tokens[token]
        if datetime.now() - token_time > timedelta(hours=1):
            del self.tokens[token]
            return False
            
        return True
        
    async def __call__(self, scope, timing):
        """中间件处理方法"""
        if timing == 'before':
            if scope['method'] in ['POST', 'PUT', 'DELETE', 'PATCH']:
                # 获取请求头中的token
                headers = dict(scope.get('headers', []))
                token = headers.get(b'x-csrf-token', b'').decode()
                
                if not self.validate_token(token):
                    raise Exception("Invalid or missing CSRF token")
                    
        return True