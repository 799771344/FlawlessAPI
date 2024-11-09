# validation/validators.py
from typing import Any, Dict, List, Optional, Union, Type
from dataclasses import dataclass
import re
from datetime import datetime

@dataclass 
class ValidationError:
    field: str
    message: str
    code: str = "invalid"
    params: Optional[Dict] = None

class ValidationRule:
    """验证规则基类"""
    def __init__(self, message: str = None):
        self.message = message
        
    def validate(self, value: Any) -> bool:
        raise NotImplementedError()

class Required(ValidationRule):
    """必填验证"""
    def __init__(self, message: str = "This field is required"):
        super().__init__(message)
        
    def validate(self, value: Any) -> bool:
        return value is not None and value != ""

class Length(ValidationRule):
    """长度验证"""
    def __init__(self, min: int = None, max: int = None, 
                 message: str = "Length must be between {min} and {max}"):
        super().__init__(message)
        self.min = min
        self.max = max
        
    def validate(self, value: Any) -> bool:
        if value is None:
            return True
        length = len(str(value))
        if self.min and length < self.min:
            return False
        if self.max and length > self.max:
            return False
        return True

class Range(ValidationRule):
    """范围验证"""
    def __init__(self, min: Union[int, float] = None, 
                 max: Union[int, float] = None,
                 message: str = "Value must be between {min} and {max}"):
        super().__init__(message)
        self.min = min
        self.max = max
        
    def validate(self, value: Any) -> bool:
        if value is None:
            return True
        try:
            num = float(value)
            if self.min and num < self.min:
                return False
            if self.max and num > self.max:
                return False
            return True
        except (TypeError, ValueError):
            return False

class Pattern(ValidationRule):
    """正则表达式验证"""
    def __init__(self, pattern: str, 
                 message: str = "Value does not match pattern"):
        super().__init__(message)
        self.pattern = re.compile(pattern)
        
    def validate(self, value: Any) -> bool:
        if value is None:
            return True
        return bool(self.pattern.match(str(value)))

class Email(Pattern):
    """邮箱验证"""
    def __init__(self, message: str = "Invalid email address"):
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        super().__init__(pattern, message)

class DateTime(ValidationRule):
    """日期时间验证"""
    def __init__(self, format: str = "%Y-%m-%d %H:%M:%S",
                 message: str = "Invalid datetime format"):
        super().__init__(message)
        self.format = format
        
    def validate(self, value: Any) -> bool:
        if value is None:
            return True
        try:
            datetime.strptime(str(value), self.format)
            return True
        except ValueError:
            return False

class Validator:
    """验证器基类"""
    def __init__(self):
        self.errors: List[ValidationError] = []
        
    def rules(self) -> Dict[str, List[ValidationRule]]:
        """定义验证规则"""
        return {}
        
    def validate(self, data: Dict[str, Any]) -> bool:
        """验证数据"""
        self.errors = []
        for field, rules in self.rules().items():
            value = data.get(field)
            for rule in rules:
                if not rule.validate(value):
                    message = rule.message.format(
                        field=field,
                        value=value,
                        min=getattr(rule, 'min', None),
                        max=getattr(rule, 'max', None)
                    )
                    self.errors.append(ValidationError(
                        field=field,
                        message=message,
                        code=rule.__class__.__name__.lower(),
                        params={
                            'value': value,
                            'min': getattr(rule, 'min', None),
                            'max': getattr(rule, 'max', None)
                        }
                    ))
        return len(self.errors) == 0

    def get_errors(self) -> Dict[str, List[str]]:
        """获取错误信息"""
        errors = {}
        for error in self.errors:
            if error.field not in errors:
                errors[error.field] = []
            errors[error.field].append(error.message)
        return errors

# 使用示例
class UserValidator(Validator):
    def rules(self):
        return {
            'username': [
                Required(),
                Length(min=3, max=32)
            ],
            'email': [
                Required(),
                Email()
            ],
            'age': [
                Required(),
                Range(min=0, max=150)
            ],
            'birth_date': [
                Required(),
                DateTime(format="%Y-%m-%d")
            ]
        }