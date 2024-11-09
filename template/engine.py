from typing import Any
from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape


class TemplateEngine:
    """异步模板引擎"""
    
    def __init__(self, template_dir: str, 
                 cache_size: int = 100,
                 auto_reload: bool = True):
        """
        初始化模板引擎
        Args:
            template_dir: 模板目录
            cache_size: 模板缓存大小
            auto_reload: 是否自动重载模板
        """
        self.template_dir = Path(template_dir)
        self.env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            autoescape=select_autoescape(['html', 'xml']),
            enable_async=True,  # 启用异步渲染
            cache_size=cache_size,
            auto_reload=auto_reload
        )
        
        # 添加默认过滤器
        self.add_default_filters()
        
    def add_default_filters(self):
        """添加默认的模板过滤器"""
        # 修改这里，使用 filters 字典而不是装饰器
        def datetime_format(value, format="%Y-%m-%d %H:%M:%S"):
            return value.strftime(format)
            
        def truncate(value, length=100, suffix='...'):
            if len(value) <= length:
                return value
            return value[:length] + suffix
            
        # 直接添加到 filters 字典
        self.env.filters['datetime_format'] = datetime_format
        self.env.filters['truncate'] = truncate
    
    async def render(self, template_name: str, **context) -> str:
        """异步渲染模板
        Args:
            template_name: 模板文件名
            **context: 模板上下文数据
        Returns:
            str: 渲染后的内容
        """
        try:
            template = self.env.get_template(template_name)
            return await template.render_async(**context)
        except Exception as e:
            print(f"Template rendering error: {e}")
            raise
            
    def add_filter(self, name: str, filter_func):
        """添加自定义过滤器"""
        self.env.filters[name] = filter_func
        
    def add_global(self, name: str, value: Any):
        """添加全局变量"""
        self.env.globals[name] = value
        
    async def render_string(self, source: str, **context) -> str:
        """渲染字符串模板"""
        template = self.env.from_string(source)
        return await template.render_async(**context)