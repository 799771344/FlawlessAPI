from typing import Optional, Dict, List
import time
import uuid
import contextvars
import logging
from dataclasses import dataclass

@dataclass
class Span:
    """
    表示一个追踪片段的数据类
    
    Attributes:
        trace_id: 追踪ID,用于标识整个调用链
        span_id: 当前片段的唯一ID
        parent_span_id: 父片段ID,用于构建调用层级关系
        name: 片段名称
        start_time: 开始时间戳
        end_time: 结束时间戳
        tags: 附加的标签信息
    """
    trace_id: str
    span_id: str
    parent_span_id: Optional[str]
    name: str
    start_time: float
    end_time: Optional[float] = None
    tags: Dict[str, str] = None
    
class DistributedTracer:
    """
    分布式追踪器的实现类
    
    用于追踪和记录分布式系统中的调用链路信息
    """
    
    def __init__(self):
        """
        初始化追踪器
        
        创建上下文变量存储当前span,初始化spans列表和日志记录器
        """
        self.current_span = contextvars.ContextVar('current_span', default=None)
        self.spans = []
        self.logger = logging.getLogger(__name__)
        
    async def trace_request(self, scope, timing):
        """
        中间件接口方法，用于追踪HTTP请求
        
        Args:
            scope: ASGI scope对象,包含请求信息
            timing: 时机标识,'before'表示请求前,'after'表示请求后
        """
        if timing == 'before':
            # 开始一个新的span
            span = self.start_span(f"HTTP {scope['method']} {scope['path']}")
            # 添加基本标签
            span.tags.update({
                'http.method': scope['method'],
                'http.path': scope['path'],
                'http.scheme': scope['scheme']
            })
            # 保存span到scope中以便后续使用
            scope['span'] = span
            
        elif timing == 'after':
            # 结束span
            span = scope.get('span')
            if span:
                # 添加响应状态码
                span.tags['http.status_code'] = str(scope.get('status_code', 200))
                self.end_span(span)
        
    def start_span(self, name: str, parent_span_id: Optional[str] = None) -> Span:
        """
        开始一个新的追踪span
        
        Args:
            name: span名称
            parent_span_id: 父span的ID,可选
            
        Returns:
            新创建的Span对象
        """
        span = Span(
            trace_id=str(uuid.uuid4()),
            span_id=str(uuid.uuid4()),
            parent_span_id=parent_span_id,
            name=name,
            start_time=time.time(),
            tags={}
        )
        self.current_span.set(span)
        return span
        
    def end_span(self, span: Span):
        """
        结束一个追踪span
        
        Args:
            span: 要结束的Span对象
        """
        span.end_time = time.time()
        self.spans.append(span)
        
    def add_tag(self, key: str, value: str):
        """
        为当前span添加标签
        
        Args:
            key: 标签键
            value: 标签值
        """
        span = self.current_span.get()
        if span:
            span.tags[key] = value
            
    def get_traces(self) -> List[Span]:
        """
        获取所有追踪spans
        
        Returns:
            所有已记录的Span对象列表
        """
        return self.spans