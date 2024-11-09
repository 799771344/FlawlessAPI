# tasks/scheduler.py
import asyncio
import aiocron
from typing import Dict, Any, Callable, Optional
from datetime import datetime, timedelta
import logging

class TaskScheduler:
    """任务调度器"""
    
    def __init__(self):
        self.tasks: Dict[str, aiocron.Cron] = {}
        self.logger = logging.getLogger(__name__)
        
    async def add_cron_task(self, 
                           name: str,
                           func: Callable,
                           cron: str,
                           args: tuple = None,
                           kwargs: dict = None):
        """添加定时任务
        Args:
            name: 任务名称
            func: 任务函数
            cron: cron表达式 (例如: "*/5 * * * *" 每5分钟执行一次)
            args: 位置参数
            kwargs: 关键字参数
        """
        try:
            job = aiocron.crontab(cron, func=func, args=args, kwargs=kwargs)
            self.tasks[name] = job
            self.logger.info(f"Added cron task: {name} with schedule: {cron}")
        except Exception as e:
            self.logger.error(f"Failed to add cron task {name}: {e}")
            raise
            
    async def add_interval_task(self,
                               name: str,
                               func: Callable,
                               seconds: int,
                               args: tuple = None,
                               kwargs: dict = None):
        """添加间隔任务"""
        async def wrapper():
            while True:
                try:
                    await func(*(args or ()), **(kwargs or {}))
                except Exception as e:
                    self.logger.error(f"Error in interval task {name}: {e}")
                await asyncio.sleep(seconds)
                
        task = asyncio.create_task(wrapper())
        self.tasks[name] = task
        self.logger.info(f"Added interval task: {name} with interval: {seconds}s")
        
    async def add_delayed_task(self,
                              name: str,
                              func: Callable,
                              delay: int,
                              args: tuple = None,
                              kwargs: dict = None):
        """添加延迟任务"""
        async def wrapper():
            await asyncio.sleep(delay)
            try:
                await func(*(args or ()), **(kwargs or {}))
            except Exception as e:
                self.logger.error(f"Error in delayed task {name}: {e}")
                
        task = asyncio.create_task(wrapper())
        self.tasks[name] = task
        self.logger.info(f"Added delayed task: {name} with delay: {delay}s")
        
    async def remove_task(self, name: str):
        """移除任务"""
        if name in self.tasks:
            task = self.tasks[name]
            if isinstance(task, aiocron.Cron):
                task.stop()
            else:
                task.cancel()
            del self.tasks[name]
            self.logger.info(f"Removed task: {name}")
            
    async def start(self):
        """启动调度器"""
        self.logger.info("Task scheduler started")
        
    async def stop(self):
        """停止调度器"""
        for name in list(self.tasks.keys()):
            await self.remove_task(name)
        self.logger.info("Task scheduler stopped")
        
    def get_tasks(self) -> Dict[str, Any]:
        """获取所有任务信息"""
        return {
            name: {
                "type": "cron" if isinstance(task, aiocron.Cron) else "async",
                "status": "running"
            }
            for name, task in self.tasks.items()
        }