# security/jwt.py
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import jwt
from jwt.exceptions import InvalidTokenError
import logging

class JWTAuth:
    """JWT认证管理器"""
    
    def __init__(self, 
                 secret_key: str,
                 algorithm: str = 'HS256',
                 access_token_expire: int = 15,  # 访问令牌过期时间(分钟)
                 refresh_token_expire: int = 7*24*60,  # 刷新令牌过期时间(分钟)
                 token_type: str = "Bearer"):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expire = access_token_expire
        self.refresh_token_expire = refresh_token_expire
        self.token_type = token_type
        self.logger = logging.getLogger(__name__)
        
    def create_access_token(self, data: Dict[str, Any]) -> str:
        """创建访问令牌"""
        return self._create_token(
            data,
            expires_delta=timedelta(minutes=self.access_token_expire)
        )
        
    def create_refresh_token(self, data: Dict[str, Any]) -> str:
        """创建刷新令牌"""
        return self._create_token(
            data,
            expires_delta=timedelta(minutes=self.refresh_token_expire)
        )
        
    def _create_token(self, data: Dict[str, Any], 
                     expires_delta: Optional[timedelta] = None) -> str:
        """创建JWT令牌"""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=15)
            
        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": "access"
        })
        
        try:
            encoded_jwt = jwt.encode(
                to_encode, 
                self.secret_key, 
                algorithm=self.algorithm
            )
            return encoded_jwt
        except Exception as e:
            self.logger.error(f"Token creation failed: {e}")
            raise
            
    def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """验证JWT令牌"""
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )
            return payload
        except jwt.ExpiredSignatureError:
            self.logger.warning("Token has expired")
            return None
        except InvalidTokenError as e:
            self.logger.warning(f"Invalid token: {e}")
            return None
            
    def refresh_access_token(self, refresh_token: str) -> Optional[str]:
        """使用刷新令牌获取新的访问令牌"""
        try:
            payload = self.verify_token(refresh_token)
            if payload and payload.get("type") == "refresh":
                # 创建新的访问令牌,但不包含令牌类型和过期时间
                new_payload = payload.copy()
                del new_payload["exp"]
                del new_payload["iat"]
                del new_payload["type"]
                return self.create_access_token(new_payload)
        except Exception as e:
            self.logger.error(f"Token refresh failed: {e}")
        return None

    def get_token_from_header(self, authorization: str) -> Optional[str]:
        """从Authorization头部获取令牌"""
        if not authorization:
            return None
            
        parts = authorization.split()
        if parts[0].lower() != self.token_type.lower() or len(parts) != 2:
            return None
            
        return parts[1]

# 使用示例
jwt_auth = JWTAuth(
    secret_key="your-secret-key",
    access_token_expire=15,
    refresh_token_expire=7*24*60
)

# 创建令牌
user_data = {"user_id": 123, "username": "john"}
access_token = jwt_auth.create_access_token(user_data)
refresh_token = jwt_auth.create_refresh_token(user_data)

# 验证令牌
payload = jwt_auth.verify_token(access_token)
if payload:
    print(f"Valid token for user: {payload['username']}")

# 刷新令牌
new_access_token = jwt_auth.refresh_access_token(refresh_token)