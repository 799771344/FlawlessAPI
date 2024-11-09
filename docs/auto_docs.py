# docs/auto_docs.py
from typing import Type, get_type_hints, Any, Dict, List, Optional
from dataclasses import dataclass
from inspect import signature, Parameter
import docstring_parser
from pydantic import BaseModel
from requests import AsyncRequest

@dataclass
class AutoAPIEndpoint:
    """自动生成的API端点信息"""
    path: str
    method: str
    summary: str
    description: Optional[str] = None
    parameters: List[Dict] = None 
    request_body: Dict = None
    responses: Dict = None
    tags: List[str] = None

class AutoDocGenerator:
    """自动API文档生成器"""
    
    def __init__(self, title: str, version: str):
        self.title = title
        self.version = version
        self.endpoints: List[AutoAPIEndpoint] = []
        
    def add_endpoint(self, endpoint: AutoAPIEndpoint):
        """添加API端点到文档
        
        Args:
            endpoint: API端点信息
        """
        self.endpoints.append(endpoint)

    def document(self, path: str, methods: List[str], tags: List[str] = None):
        """API文档装饰器"""
        def decorator(func):
            # 获取函数签名
            sig = signature(func)
            # 获取类型注解
            type_hints = get_type_hints(func)
            # 解析docstring
            docstring = docstring_parser.parse(func.__doc__ or "")
            
            # 提取请求参数
            parameters = []
            request_body = None
            
            for param_name, param in sig.parameters.items():
                if param_name == "request":
                    continue
                    
                param_type = type_hints.get(param_name)
                if param_type:
                    if issubclass(param_type, BaseModel):
                        # Pydantic模型作为请求体
                        request_body = self._get_model_schema(param_type)
                    else:
                        # 路径参数或查询参数
                        parameters.append({
                            "name": param_name,
                            "in": "path" if "{" + param_name + "}" in path else "query",
                            "required": param.default == Parameter.empty,
                            "schema": self._get_type_schema(param_type)
                        })
            
            # 提取响应信息
            return_type = type_hints.get("return")
            responses = {
                "200": {
                    "description": "Successful response",
                    "content": {
                        "application/json": {
                            "schema": self._get_type_schema(return_type)
                        }
                    }
                }
            }
            
            # 为每个HTTP方法创建端点文档
            for method in methods:
                endpoint = AutoAPIEndpoint(
                    path=path,
                    method=method,
                    summary=docstring.short_description or func.__name__,
                    description=docstring.long_description,
                    parameters=parameters,
                    request_body=request_body,
                    responses=responses,
                    tags=tags
                )
                self.add_endpoint(endpoint)
                
            return func
        return decorator
        
    def _get_type_schema(self, type_hint: Type) -> Dict:
        """获取类型的JSON Schema"""
        if type_hint is None:
            return {}
            
        if hasattr(type_hint, "__origin__"):  # 处理泛型类型
            origin = type_hint.__origin__
            if origin in (list, List):
                return {
                    "type": "array",
                    "items": self._get_type_schema(type_hint.__args__[0])
                }
            elif origin in (dict, Dict):
                return {
                    "type": "object",
                    "additionalProperties": self._get_type_schema(type_hint.__args__[1])
                }
                
        # 基本类型映射
        type_map = {
            str: {"type": "string"},
            int: {"type": "integer"},
            float: {"type": "number"},
            bool: {"type": "boolean"},
            Any: {"type": "object"}
        }
        
        return type_map.get(type_hint, {"type": "object"})
        
    def _get_model_schema(self, model: Type[BaseModel]) -> Dict:
        """获取Pydantic模型的JSON Schema"""
        return {
            "content": {
                "application/json": {
                    "schema": model.schema()
                }
            }
        }

    async def generate_openapi_spec(self, request=None) -> Dict:
        """生成OpenAPI规范文档
        Args:
            request: 可选的请求对象
        Returns:
            Dict: OpenAPI规范文档
        """
        spec = {
            "openapi": "3.0.0",
            "info": {
                "title": self.title,
                "version": self.version,
                "description": "API Documentation"
            },
            "servers": [
                {
                    "url": "/"
                }
            ],
            "paths": {},
            "components": {
                "schemas": {},
                "securitySchemes": {}
            }
        }

        # 整理所有端点信息
        for endpoint in self.endpoints:
            if endpoint.path not in spec["paths"]:
                spec["paths"][endpoint.path] = {}

            method_spec = {
                "summary": endpoint.summary,
                "description": endpoint.description,
                "tags": endpoint.tags,
                "responses": endpoint.responses
            }

            if endpoint.parameters:
                method_spec["parameters"] = endpoint.parameters

            if endpoint.request_body:
                method_spec["requestBody"] = endpoint.request_body

            spec["paths"][endpoint.path][endpoint.method.lower()] = method_spec

        return spec

    async def generate_swagger_ui(self, request=None) -> Dict:
        """生成Swagger UI HTML
        Args:
            request: 可选的请求对象
        Returns:
            Dict: 包含HTML内容和headers的字典
        """
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{self.title}</title>
            <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@4/swagger-ui.css">
            <style>
                body {{
                    margin: 0;
                    padding: 0;
                }}
                #swagger-ui {{
                    max-width: 1200px;
                    margin: 0 auto;
                }}
            </style>
        </head>
        <body>
            <div id="swagger-ui"></div>
            <script src="https://unpkg.com/swagger-ui-dist@4/swagger-ui-bundle.js"></script>
            <script>
                window.onload = () => {{
                    window.ui = SwaggerUIBundle({{
                        url: "/api/docs/spec",
                        dom_id: '#swagger-ui',
                        deepLinking: true,
                        presets: [
                            SwaggerUIBundle.presets.apis,
                            SwaggerUIBundle.SwaggerUIStandalonePreset
                        ],
                        layout: "BaseLayout",
                        docExpansion: 'list',
                        defaultModelsExpandDepth: 1,
                        defaultModelExpandDepth: 1,
                    }});
                }};
            </script>
        </body>
        </html>
        """
        return {
            "body": html,
            "headers": [
                (b"content-type", b"text/html; charset=utf-8")
            ]
        }
