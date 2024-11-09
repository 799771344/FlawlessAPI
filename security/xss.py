# security/xss.py
import html
import re
from typing import Any, Dict, List, Union

class XSSCleaner:
    """XSS清理器"""
    
    def __init__(self):
        # 定义允许的HTML标签和属性
        self.ALLOWED_TAGS = {
            'a': ['href', 'title'],
            'b': [],
            'br': [],
            'div': ['class'],
            'em': [],
            'i': [],
            'p': [],
            'span': ['class'],
            'strong': []
        }
        
        # 定义危险的属性
        self.DANGEROUS_ATTRS = [
            'onclick', 'onmouseover', 'onload', 'onerror',
            'javascript:', 'vbscript:', 'expression'
        ]
        
    def clean(self, value: Any) -> str:
        """清理可能包含XSS的内容"""
        if value is None:
            return ""
            
        if isinstance(value, (int, float)):
            return str(value)
            
        value = str(value)
        
        # 转义HTML特殊字符
        value = html.escape(value)
        
        # 移除危险的属性
        for attr in self.DANGEROUS_ATTRS:
            value = re.sub(
                f'[a-z]*{attr}[a-z]*\s*=',
                '',
                value,
                flags=re.IGNORECASE
            )
            
        return value
        
    def clean_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """清理字典中的所有值"""
        return {k: self.clean(v) for k, v in data.items()}
        
    def clean_list(self, data: List[Any]) -> List[Any]:
        """清理列表中的所有值"""
        return [self.clean(v) for v in data]
        
    def strip_tags(self, value: str) -> str:
        """完全移除所有HTML标签"""
        return re.sub(r'<[^>]*?>', '', str(value))

class XSSMiddleware:
    """XSS防护中间件"""
    
    def __init__(self):
        self.cleaner = XSSCleaner()
        
    async def __call__(self, scope, timing):
        """中间件处理方法"""
        if timing == 'before':
            # 清理请求数据
            if scope.get('method') in ['POST', 'PUT', 'PATCH']:
                if 'json' in scope.get('headers', {}).get('content-type', ''):
                    # 清理JSON数据
                    body = await scope.get('body', {})
                    if isinstance(body, dict):
                        scope['body'] = self.cleaner.clean_dict(body)
                    elif isinstance(body, list):
                        scope['body'] = self.cleaner.clean_list(body)
                        
            # 清理查询参数
            query_params = scope.get('query_params', {})
            scope['query_params'] = self.cleaner.clean_dict(query_params)
            
        return True

# 使用示例
xss_cleaner = XSSCleaner()

# 清理单个值
clean_text = xss_cleaner.clean('<script>alert("xss")</script>')
print(clean_text)  # &lt;script&gt;alert(&quot;xss&quot;)&lt;/script&gt;

# 清理字典
data = {
    'name': '<script>alert("xss")</script>',
    'description': 'Normal text'
}
clean_data = xss_cleaner.clean_dict(data)
print(clean_data)