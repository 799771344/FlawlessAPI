# 路由前缀树节点类
import re
from typing import Dict, List, Optional


class TrieNode:
    def __init__(self):
        self.children = {}  # 存储子节点的字典,key为路径片段,value为子节点
        self.handler = None  # 存储该节点对应的处理函数
        self.methods = None  # 存储该节点支持的HTTP方法列表
        self.is_endpoint = False  # 标记该节点是否为路由终点
        self.pattern = None  # 存储路由模式
        self.param_name = None  # 存储参数名称(用于动态路由)
        self.is_wildcard = False  # 标记是否为通配符路由

class RouteParameter:
    """路由参数定义"""
    def __init__(self, name: str, type_: type, description: str = None):
        self.name = name
        self.type = type_
        self.description = description
