import asyncio
from datetime import datetime
import json

from pydantic import BaseModel
from config.cache_config import CacheConfig, RedisConfig
from config.settings import APIConfig
from queue.task_queue import TaskPriority
from requests import AsyncRequest
from response import ApiResponse, error_response, success_response
from router.core import FlawlessAPI
import uvicorn
from middleware.cors import CORSMiddleware
from middleware.rate_limit import RateLimiter

# 1. 创建应用实例,配置缓存和API选项
app = FlawlessAPI(
    # Redis缓存配置
    cache_config=CacheConfig(
        type="lru",
        capacity=1000,
        ttl=3600
    ),
    # API配置
    api_config=APIConfig(
        enable_builtin_routes=True,
        builtin_route_prefix="",
        expose_traces=True,
        enable_api_docs=True,
        api_title="示例API",
        api_version="1.0.0",
        
        # 启用模板支持
        # enable_templates=True,
        # template_dir="templates",
        
        # 启用文件上传
        # enable_file_uploads=True,
        # upload_dir="uploads",
        
        # 启用WebSocket
        enable_websocket=True,
        
        # 启用静态文件
        # enable_static_files=True,
        # static_dir="static",
        
        # 启用数据库
        # database_url="postgresql://user:pass@localhost/dbname",
        
        # 启用国际化
        # enable_i18n=True,
        # locale_dir="locales",
        
        # 启用任务队列
        enable_task_queue=True,
        
        # 启用服务注册
        enable_service_registry=True,
        registry_url="http://registry:8000",
        service_name="my-service",
        service_url="http://localhost:8000"
    )
)

# 2. 添加中间件
app.add_middleware(CORSMiddleware(
    allow_origins=["*"],
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"]
))
app.add_middleware(RateLimiter(requests_per_second=100))

# 3. 注册启动和关闭事件处理器
@app.on_event("startup")
async def startup():
    print("应用启动...")

@app.on_event("shutdown") 
async def shutdown():
    print("应用关闭...")

class UserCreate(BaseModel):
    name: str
    email: str
    age: int
    

class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    created_at: str

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

        arbitrary_types_allowed = True

# 添加路由
async def get_user(request: AsyncRequest, id: int) -> UserResponse:
    """
    获取用户信息
    
    根据用户ID获取用户详细信息
    
    Args:
        user_id (int): 用户ID，从路径参数获取
        
    Returns:
        UserResponse: 用户信息对象
    """
    user_data = UserResponse(
        id=id,
        name="John Doe",
        email="john@example.com",
        created_at=datetime.now().isoformat()
    )
    return success_response(data=user_data)

# 修改用户创建处理函数
async def create_user(request: AsyncRequest, user: UserCreate) -> UserResponse:
    """
    创建新用户
    
    创建一个新的用户账号
    
    Args:
        request: HTTP请求对象
        user: 用户创建信息
        
    Returns:
        UserResponse: 创建的用户信息
    """
    try:
        response = UserResponse(
            id=1,
            name=user.name,
            email=user.email,
            created_at=datetime.now().isoformat()
        )
        return success_response(data=response)
    except Exception as e:
        return error_response(message=f"Invalid user data: {str(e)}")



# 9. 异步任务示例
async def long_running_task():
    print(123412423423)
    await asyncio.sleep(10)
    print("Task completed")
    return "Task completed"

async def start_task(request: AsyncRequest):
    # 添加任务并指定优先级和回调
    task_id = await app.task_queue.add_task(
        long_running_task,
        priority=TaskPriority.NORMAL,
        callback=lambda task: print(f"Task {task.id} completed with result: {task.result}")
    )
    return success_response(data={
        "task_id": task_id,
        "message": "Task started successfully"
    })

# 10. 注册路由
app.add_route("/users/{id}", get_user, ["GET"])
app.add_route("/users", create_user, ["POST"])
app.add_route("/tasks", start_task, ["POST"])

# 11. 启动应用
if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )

"""
现在可以访问:
- GET http://localhost:8000/users/1 获取用户信息
- POST http://localhost:8000/users 创建用户
- GET http://localhost:8000/docs 查看API文档
- GET http://localhost:8000/_metrics 查看性能指标
- GET http://localhost:8000/_health 查看健康状态
"""