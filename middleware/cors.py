from typing import List, Optional

class CORSMiddleware:
    """
    CORS(跨域资源共享)中间件
    用于处理跨域请求的访问控制
    """
    def __init__(self, 
                 allow_origins: List[str] = None,  # 允许的源域名列表
                 allow_methods: List[str] = None,  # 允许的HTTP方法列表  
                 allow_headers: List[str] = None,  # 允许的HTTP头部列表
                 allow_credentials: bool = False):  # 是否允许发送认证信息
        # 如果没有指定,默认允许所有源域名
        self.allow_origins = allow_origins or ["*"]
        # 如果没有指定,默认允许常用的HTTP方法
        self.allow_methods = allow_methods or ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
        # 如果没有指定,默认允许所有头部
        self.allow_headers = allow_headers or ["*"]
        # 是否允许发送认证信息(cookies等)
        self.allow_credentials = allow_credentials
        
    async def __call__(self, scope, timing):
        """
        处理CORS请求
        :param scope: ASGI scope对象
        :param timing: 中间件执行时机('before'/'after')
        :return: bool 是否继续执行后续中间件
        """
        if timing == 'before':
            # 获取请求头部信息
            headers = dict(scope.get('headers', []))
            # 获取请求源域名并解码
            origin = headers.get(b'origin', b'').decode()
            
            # 检查请求源是否在允许列表中
            if origin in self.allow_origins or "*" in self.allow_origins:
                # 设置CORS响应头
                scope['cors_headers'] = [
                    (b'Access-Control-Allow-Origin', origin.encode()),  # 允许的源
                    (b'Access-Control-Allow-Methods', ", ".join(self.allow_methods).encode()),  # 允许的方法
                    (b'Access-Control-Allow-Headers', ", ".join(self.allow_headers).encode()),  # 允许的头部
                    (b'Access-Control-Allow-Credentials', str(self.allow_credentials).lower().encode())  # 是否允许认证
                ]
        return True