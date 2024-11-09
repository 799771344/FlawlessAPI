# monitoring/metrics.py
from dataclasses import dataclass
import time
from typing import Dict, List, Optional
import json
import asyncio
import psutil

@dataclass
class MetricPoint:
    """指标数据点类,用于存储单个指标的时间戳和数值"""
    timestamp: float  # 时间戳
    value: float     # 指标值
    
class MetricsCollector:
    """指标收集器类,用于收集、存储和导出各类系统指标"""
    def __init__(self):
        # 初始化指标存储字典,包含CPU使用率、内存使用率、GC统计和线程统计
        self._metrics ={
            'cpu_usage': [],      # CPU使用率指标列表
            'memory_usage': [],   # 内存使用率指标列表
            'gc_stats': [],       # 垃圾回收统计指标列表
            'thread_stats': []    # 线程统计指标列表
        }
        self._thresholds = {}
        self._alerts = []
        
    def record(self, name: str, value: float):
        """记录一个指标数据点
        Args:
            name: 指标名称
            value: 指标值
        """
        point = MetricPoint(time.time(), value)
        self._metrics[name].append(point)
        self._check_threshold(name, value)
        
    def set_threshold(self, metric_name: str, threshold: float, 
                     alert_message: str):
        """设置指标阈值和告警消息
        Args:
            metric_name: 指标名称
            threshold: 阈值
            alert_message: 超过阈值时的告警消息
        """
        self._thresholds[metric_name] = (threshold, alert_message)
        
    def _check_threshold(self, name: str, value: float):
        """检查指标是否超过阈值,如果超过则生成告警
        Args:
            name: 指标名称
            value: 指标值
        """
        if name in self._thresholds:
            threshold, message = self._thresholds[name]
            if value > threshold:
                alert = {
                    'timestamp': time.time(),
                    'metric': name,
                    'value': value,
                    'threshold': threshold,
                    'message': message
                }
                self._alerts.append(alert)
                
    def get_metrics(self, name: str, 
                   start_time: Optional[float] = None) -> List[MetricPoint]:
        """获取指定名称的指标数据
        Args:
            name: 指标名称
            start_time: 可选的开始时间戳,用于过滤数据
        Returns:
            指标数据点列表
        """
        points = self._metrics[name]
        if start_time:
            points = [p for p in points if p.timestamp >= start_time]
        return points
        
    def export_metrics(self, format: str = 'json') -> str:
        """导出所有指标数据
        Args:
            format: 导出格式,默认为json
        Returns:
            格式化后的指标数据
        """
        data = {
            name: [(p.timestamp, p.value) for p in points]
            for name, points in self._metrics.items()
        }
        if format == 'json':
            return json.dumps(data)
        # 支持其他格式...
        return data
        
    async def collect_system_metrics(self):
        """收集系统级指标,包括CPU和内存使用率"""
        cpu = psutil.cpu_percent()      # 获取CPU使用率百分比
        memory = psutil.virtual_memory().percent  # 获取内存使用率百分比
        
        self.record('cpu_usage', cpu)
        self.record('memory_usage', memory)
        
    async def start_collection(self):
        """启动定期收集指标的异步任务,每分钟执行一次"""
        while True:
            await self.collect_system_metrics()
            await asyncio.sleep(60)  # 每分钟收集一次