import asyncio
from typing import Any, Callable, Dict, Optional, List
from datetime import datetime, timedelta
import logging
from enum import Enum
import uuid

class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"

class TaskPriority(Enum):
    LOW = 0
    NORMAL = 1
    HIGH = 2

class Task:
    """任务类"""
    def __init__(self, func: Callable, *args, 
                 priority: TaskPriority = TaskPriority.NORMAL,
                 max_retries: int = 3,
                 retry_delay: int = 5,
                 callback: Optional[Callable] = None,
                 **kwargs):
        self.id = str(uuid.uuid4())
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.priority = priority
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.retry_count = 0
        self.callback = callback
        
        self.created_at = datetime.now()
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.status = TaskStatus.PENDING
        self.result = None
        self.error = None

    def __lt__(self, other):
        # 用于优先级队列比较
        return self.priority.value > other.priority.value

class Consumer:
    """任务消费者"""
    def __init__(self, name: str, queue: 'TaskQueue', 
                 task_types: List[str] = None):
        self.name = name
        self.queue = queue
        self.task_types = task_types or ["default"]
        self.is_running = False
        self.current_task: Optional[Task] = None
        
    async def start(self):
        """启动消费者"""
        self.is_running = True
        while self.is_running:
            try:
                task = await self.queue.get_task(self.task_types)
                if task:
                    await self._process_task(task)
            except Exception as e:
                logging.error(f"Consumer {self.name} error: {e}")
                await asyncio.sleep(1)
                
    async def stop(self):
        """停止消费者"""
        self.is_running = False
        if self.current_task:
            self.current_task.status = TaskStatus.CANCELLED
            
    async def _process_task(self, task: Task):
        """处理任务"""
        self.current_task = task
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()
        
        try:
            task.result = await task.func(*task.args, **task.kwargs)
            task.status = TaskStatus.COMPLETED
            # 执行回调
            if task.callback:
                await task.callback(task)
                
        except Exception as e:
            task.error = e
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                task.status = TaskStatus.RETRYING
                await asyncio.sleep(task.retry_delay)
                await self.queue.retry_task(task)
            else:
                task.status = TaskStatus.FAILED
                
        finally:
            task.completed_at = datetime.now()
            self.current_task = None

class TaskQueue:
    """异步任务队列"""
    def __init__(self, max_workers: int = 3):
        self.queue = asyncio.PriorityQueue()
        self.max_workers = max_workers
        self.tasks: Dict[str, Task] = {}
        self.consumers: List[Consumer] = []
        self.logger = logging.getLogger(__name__)
        
    async def start(self):
        """启动任务队列"""
        # 创建默认消费者
        for i in range(self.max_workers):
            consumer = Consumer(f"consumer-{i}", self)
            self.consumers.append(consumer)
            asyncio.create_task(consumer.start())
            
    async def stop(self):
        """停止任务队列"""
        for consumer in self.consumers:
            await consumer.stop()
            
    async def add_task(self, func: Callable, *args, 
                      priority: TaskPriority = TaskPriority.NORMAL,
                      task_type: str = "default",
                      max_retries: int = 3,
                      retry_delay: int = 5,
                      callback: Optional[Callable] = None,
                      **kwargs) -> str:
        """添加任务"""
        task = Task(func, *args, 
                   priority=priority,
                   max_retries=max_retries,
                   retry_delay=retry_delay,
                   callback=callback,
                   **kwargs)
        self.tasks[task.id] = task
        await self.queue.put((priority.value, task_type, task))
        return task.id
        
    async def get_task(self, task_types: List[str]) -> Optional[Task]:
        """获取任务"""
        try:
            _, task_type, task = await self.queue.get()
            if task_type in task_types:
                return task
            else:
                # 如果任务类型不匹配,放回队列
                await self.queue.put((task.priority.value, task_type, task))
                return None
        except asyncio.QueueEmpty:
            return None
            
    async def retry_task(self, task: Task):
        """重试任务"""
        await self.queue.put((task.priority.value, "default", task))
        
    async def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """获取任务状态"""
        task = self.tasks.get(task_id)
        if not task:
            return {"status": "not_found"}
            
        return {
            "id": task.id,
            "status": task.status.value,
            "created_at": task.created_at,
            "started_at": task.started_at,
            "completed_at": task.completed_at,
            "result": task.result,
            "error": str(task.error) if task.error else None,
            "retry_count": task.retry_count
        }

    async def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        task = self.tasks.get(task_id)
        if not task:
            return False
            
        if task.status in [TaskStatus.PENDING, TaskStatus.RETRYING]:
            task.status = TaskStatus.CANCELLED
            return True
        return False