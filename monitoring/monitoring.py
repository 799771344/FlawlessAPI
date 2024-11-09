# 导入所需的标准库
import time
from dataclasses import dataclass
from typing import Dict, List
import asyncio
from collections import defaultdict

from monitoring.metrics import MetricsCollector

@dataclass
class RequestMetrics:
    """
    请求指标数据类,用于存储单个请求的相关信息
    """
    path: str  # 请求路径
    method: str  # 请求方法(GET/POST等)
    start_time: float  # 请求开始时间戳
    duration: float  # 请求持续时间
    status_code: int  # 响应状态码

class PerformanceMonitor:
    """
    性能监控类,用于收集和统计API请求的性能指标
    """
    def __init__(self):
        # 存储所有请求记录
        self.requests: List[RequestMetrics] = []
        # 当前正在处理的请求数
        self.current_requests = 0
        # 统计数据字典
        self._stats = {
            'response_times': [],  # 响应时间列表
            'error_count': 0,  # 错误请求计数
            'status_codes': defaultdict(int),  # 各状态码计数
            'path_stats': defaultdict(lambda: {  # 各路径的统计信息
                'count': 0,  # 请求次数
                'total_time': 0,  # 总响应时间
                'errors': 0  # 错误次数
            }),
            'max_response_time': 0,  # 最大响应时间
            'min_response_time': float('inf')  # 最小响应时间
        }
        self._max_stored_requests = 1000  # 限制存储的请求数量
        # 添加系统指标收集器
        self.metrics_collector = MetricsCollector()

    async def start_collection(self):
        """
        启动性能指标收集
        定期收集系统级指标如CPU和内存使用情况
        """
        while True:
            try:
                await self.metrics_collector.collect_system_metrics()
                # 每60秒收集一次系统指标
                await asyncio.sleep(60)
            except Exception as e:
                # 记录错误但继续运行
                print(f"Error collecting metrics: {e}")
                await asyncio.sleep(60)  # 发生错误时也等待60秒

    async def get_stats(self):
        """
        获取监控统计信息
        
        Returns:
            dict: 包含各项统计指标的字典
        """
        total_requests = len(self.requests)
        # 如果没有请求记录,返回初始值
        if total_requests == 0:
            return {
                'total_requests': 0,
                'current_requests': self.current_requests,
                'average_response_time': 0,
                'max_response_time': 0,
                'min_response_time': 0,
                'error_rate': 0,
                'status_codes': dict(self._stats['status_codes']),
                'path_stats': dict(self._stats['path_stats'])
            }

        # 计算平均响应时间
        response_times = self._stats['response_times']
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0

        # 返回完整的统计信息
        return {
            'total_requests': total_requests,
            'current_requests': self.current_requests,
            'average_response_time': avg_response_time,
            'max_response_time': self._stats['max_response_time'],
            'min_response_time': self._stats['min_response_time'],
            'error_rate': (self._stats['error_count'] / total_requests) if total_requests > 0 else 0,
            'status_codes': dict(self._stats['status_codes']),
            'path_stats': dict(self._stats['path_stats'])
        }
        
    async def record_request(self, scope, timing):
        """
        记录请求信息
        
        Args:
            scope: 请求上下文信息
            timing: 时间点标记('before'/'after')
        """
        if timing == 'before':
            # 请求开始时记录
            self.current_requests += 1
            scope['start_time'] = time.time()
        else:
            # 请求结束时记录
            duration = time.time() - scope['start_time']
            path = scope['path']
            
            # 更新路径统计信息
            path_stat = self._stats['path_stats'][path]
            path_stat['count'] += 1
            path_stat['total_time'] += duration
            
            # 如果达到存储上限,移除最早的请求
            if len(self.requests) >= self._max_stored_requests:
                self.requests.pop(0)  # 移除最旧的请求
                
            # 添加新的请求记录
            self.requests.append(RequestMetrics(
                path=path,
                method=scope['method'],
                start_time=scope['start_time'],
                duration=duration,
                status_code=scope.get('status_code', 500)
            ))
            
            # 更新统计数据
            self._update_stats(duration, scope.get('status_code', 500), path)
            
    def _update_stats(self, duration: float, status_code: int, path: str):
        """
        更新统计数据
        
        Args:
            duration: 请求持续时间
            status_code: 响应状态码
            path: 请求路径
        """
        self._stats['response_times'].append(duration)
        self._stats['status_codes'][status_code] += 1
        self._stats['max_response_time'] = max(self._stats['max_response_time'], duration)
        self._stats['min_response_time'] = min(self._stats['min_response_time'], duration)
        
        # 如果是服务器错误(5xx),更新错误统计
        if status_code >= 500:
            self._stats['error_count'] += 1
            self._stats['path_stats'][path]['errors'] += 1
