import aiohttp
import asyncio
from typing import Dict, List, Optional
import json
import time

class ServiceRegistry:
    """服务注册与发现"""
    
    def __init__(self, registry_url: str, 
                 service_name: str,
                 service_url: str,
                 heartbeat_interval: int = 30):
        self.registry_url = registry_url
        self.service_name = service_name
        self.service_url = service_url
        self.heartbeat_interval = heartbeat_interval
        self.services: Dict[str, List[str]] = {}
        self._heartbeat_task = None
        
    async def start(self):
        """启动服务注册"""
        # 注册服务
        await self.register_service()
        # 启动心跳
        self._heartbeat_task = asyncio.create_task(self._heartbeat())
        
    async def stop(self):
        """停止服务注册"""
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            await asyncio.gather(self._heartbeat_task, return_exceptions=True)
        # 注销服务
        await self.deregister_service()
        
    async def register_service(self):
        """注册服务"""
        async with aiohttp.ClientSession() as session:
            data = {
                "name": self.service_name,
                "url": self.service_url,
                "timestamp": time.time()
            }
            try:
                async with session.post(f"{self.registry_url}/register", json=data) as resp:
                    if resp.status != 200:
                        raise Exception(f"Service registration failed: {await resp.text()}")
            except Exception as e:
                print(f"Registration error: {e}")
                
    async def deregister_service(self):
        """注销服务"""
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(f"{self.registry_url}/deregister", 
                                      json={"name": self.service_name, "url": self.service_url}) as resp:
                    if resp.status != 200:
                        raise Exception(f"Service deregistration failed: {await resp.text()}")
            except Exception as e:
                print(f"Deregistration error: {e}")
                
    async def discover_service(self, service_name: str) -> Optional[str]:
        """发现服务
        Args:
            service_name: 服务名称
        Returns:
            Optional[str]: 服务URL
        """
        if service_name in self.services:
            # 简单的轮询负载均衡
            urls = self.services[service_name]
            if urls:
                return urls[int(time.time()) % len(urls)]
        
        # 从注册中心获取服务信息
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(f"{self.registry_url}/discover/{service_name}") as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        self.services[service_name] = data["urls"]
                        return data["urls"][0] if data["urls"] else None
            except Exception as e:
                print(f"Service discovery error: {e}")
                return None
                
    async def _heartbeat(self):
        """发送心跳"""
        while True:
            try:
                await self.register_service()  # 重新注册作为心跳
                await asyncio.sleep(self.heartbeat_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Heartbeat error: {e}")
                await asyncio.sleep(5)  # 错误后等待一段时间再重试