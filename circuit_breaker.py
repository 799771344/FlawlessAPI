import time

class CircuitBreaker:
    """
    熔断器类，用于处理服务故障和自动恢复
    
    熔断器有三种状态:
    - CLOSED: 正常状态，允许请求通过
    - OPEN: 熔断状态，快速失败，拒绝所有请求
    - HALF-OPEN: 半开状态，允许一个请求尝试，测试服务是否恢复
    """
    def __init__(self, failure_threshold: int = 5, reset_timeout: int = 60):
        """
        初始化熔断器
        
        Args:
            failure_threshold: 触发熔断的连续失败次数阈值
            reset_timeout: 熔断后尝试恢复的超时时间(秒)
        """
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        self.failures = 0  # 当前连续失败次数
        self.last_failure_time = 0  # 最后一次失败的时间戳
        self.state = 'CLOSED'  # 熔断器初始状态为关闭

        
    async def __call__(self, scope, timing):
        """
        熔断器的调用方法，在请求前后进行状态检查和更新
        
        Args:
            scope: 请求上下文
            timing: 调用时机，'before'表示请求前，'after'表示请求后
        """
        if timing == 'before':
            current_time = time.time()
            
            if self.state == 'OPEN':
                # 在熔断状态下，检查是否达到重置时间
                if current_time - self.last_failure_time > self.reset_timeout:
                    self.state = 'HALF-OPEN'  # 转换为半开状态，允许下一个请求尝试
                else:
                    raise Exception("Circuit breaker is OPEN")  # 熔断期间拒绝请求
                    
            elif self.state == 'HALF-OPEN':
                # 半开状态下允许一个请求通过，用于测试服务是否恢复
                pass
                
        elif timing == 'after':
            if scope.get('status_code', 200) >= 500:  # 只有服务器错误(5xx)才计入失败次数
                self.failures += 1
                self.last_failure_time = time.time()
                
                if self.failures >= self.failure_threshold:
                    self.state = 'OPEN'  # 达到失败阈值，触发熔断
            else:
                # 请求成功，进行状态恢复
                if self.state == 'HALF-OPEN':
                    self.state = 'CLOSED'  # 半开状态下请求成功，恢复为正常状态
                self.failures = 0  # 重置失败计数
