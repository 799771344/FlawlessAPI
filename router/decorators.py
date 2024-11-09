from functools import wraps
import functools
import time
from typing import List, get_type_hints
from inspect import signature
import docstring_parser

class Route:
    """路由装饰器类"""
    def __init__(self, path: str, methods: List[str] = None, tags: List[str] = None):
        self.path = path
        self.methods = methods or ["GET"]
        self.tags = tags or ["default"]
        
    def __call__(self, func):
        # 获取函数签名
        sig = signature(func)
        # 获取类型注解
        type_hints = get_type_hints(func)
        # 解析docstring
        docstring = docstring_parser.parse(func.__doc__ or "")
        
        # 分析路径参数
        path_params = []
        for param_name, param in sig.parameters.items():
            if param_name == "request":
                continue
                
            # 检查是否是路径参数
            if '{' + param_name + '}' in self.path:
                param_type = type_hints.get(param_name, str)
                path_params.append({
                    "name": param_name,
                    "in": "path",
                    "required": True,
                    "schema": {"type": self._get_type_name(param_type)},
                    "description": self._get_param_description(docstring, param_name)
                })
        
        # 保存路由元数据
        func._route_info = {
            "path": self.path,
            "methods": self.methods,
            "tags": self.tags,
            "parameters": path_params,
            "docstring": docstring
        }
        
        return func
        
    @staticmethod
    def _get_type_name(type_: type) -> str:
        """获取类型的OpenAPI名称"""
        type_map = {
            str: "string",
            int: "integer",
            float: "number",
            bool: "boolean"
        }
        return type_map.get(type_, "string")
        
    @staticmethod
    def _get_param_description(docstring, param_name: str) -> str:
        """从docstring中获取参数描述"""
        if docstring.params:
            for param in docstring.params:
                if param.arg_name == param_name:
                    return param.description
        return ""
