import json
from typing import Dict, Set, Callable, Any
import asyncio
import uuid

class WebSocketHandler:
    """WebSocket连接处理器"""
    
    def __init__(self):
        self.connections: Set = set()  # 存储所有活动连接
        self.handlers: Dict[str, Callable] = {}  # 消息处理器映射
        
    async def __call__(self, scope, receive, send):
        """ASGI应用接口"""
        if scope["type"] == "websocket":
            await self.handle_websocket(scope, receive, send)
            
    async def handle_websocket(self, scope, receive, send):
        """处理WebSocket连接"""
        try:
            # 接受连接
            await send({
                "type": "websocket.accept"
            })
            
            # 创建连接对象
            connection = WebSocketConnection(scope, receive, send)
            self.connections.add(connection)
            
            try:
                while True:
                    message = await receive()
                    
                    if message["type"] == "websocket.disconnect":
                        break
                        
                    if message["type"] == "websocket.receive":
                        await self.handle_message(connection, message.get("text"))
                        
            finally:
                self.connections.remove(connection)
                
        except Exception as e:
            print(f"WebSocket error: {e}")
            
    async def handle_message(self, connection, message: str):
        """处理收到的消息"""
        try:
            data = json.loads(message)
            message_type = data.get("type")
            
            if message_type in self.handlers:
                await self.handlers[message_type](connection, data)
            else:
                await connection.send_json({
                    "error": f"Unknown message type: {message_type}"
                })
                
        except json.JSONDecodeError:
            await connection.send_json({
                "error": "Invalid JSON message"
            })
            
    def on_message(self, message_type: str):
        """消息处理器装饰器"""
        def decorator(f):
            self.handlers[message_type] = f
            return f
        return decorator
        
    async def broadcast(self, message: Any):
        """广播消息给所有连接"""
        for connection in self.connections:
            await connection.send_json(message)

class WebSocketConnection:
    """WebSocket连接封装类"""
    
    def __init__(self, scope, receive, send):
        self.scope = scope
        self.receive = receive
        self.send = send
        self.id = str(uuid.uuid4())
        
    async def send_text(self, text: str):
        """发送文本消息"""
        await self.send({
            "type": "websocket.send",
            "text": text
        })
        
    async def send_json(self, data: Any):
        """发送JSON消息"""
        await self.send_text(json.dumps(data))