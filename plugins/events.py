# plugins/events.py
from typing import Dict, List, Any, Callable, Optional
import asyncio
import logging
from datetime import datetime

class Event:
    """事件类"""
    
    def __init__(self, name: str, data: Any = None):
        self.name = name
        self.data = data
        self.timestamp = datetime.now()
        
class EventEmitter:
    """事件发射器"""
    
    def __init__(self):
        self.handlers: Dict[str, List[Callable]] = {}
        self.logger = logging.getLogger(__name__)
        
    def on(self, event_name: str, handler: Callable):
        """注册事件处理器"""
        if event_name not in self.handlers:
            self.handlers[event_name] = []
        self.handlers[event_name].append(handler)
        
    def off(self, event_name: str, handler: Optional[Callable] = None):
        """移除事件处理器"""
        if event_name in self.handlers:
            if handler:
                self.handlers[event_name].remove(handler)
            else:
                del self.handlers[event_name]
                
    async def emit(self, event: Event):
        """触发事件"""
        if event.name not in self.handlers:
            return
            
        tasks = []
        for handler in self.handlers[event.name]:
            try:
                if asyncio.iscoroutinefunction(handler):
                    tasks.append(handler(event))
                else:
                    handler(event)
            except Exception as e:
                self.logger.error(f"Error in event handler: {e}")
                
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
            
    def get_handlers(self, event_name: str) -> List[Callable]:
        """获取事件处理器"""
        return self.handlers.get(event_name, [])

# 使用示例
class ApplicationEvents:
    """应用事件定义"""
    STARTUP = "app.startup"
    SHUTDOWN = "app.shutdown"
    REQUEST_START = "request.start"
    REQUEST_END = "request.end"
    ERROR = "app.error"

# 创建事件发射器实例
event_emitter = EventEmitter()

# 注册事件处理器
@event_emitter.on(ApplicationEvents.STARTUP)
async def handle_startup(event: Event):
    print(f"Application started at {event.timestamp}")

# 触发事件
asyncio.run(event_emitter.emit(Event(ApplicationEvents.STARTUP)))