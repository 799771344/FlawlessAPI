from typing import Dict, List, Optional
from dataclasses import dataclass

@dataclass
class APIEndpoint:
    """API端点信息"""
    path: str
    method: str
    summary: str
    description: Optional[str] = None
    parameters: List[Dict] = None
    request_body: Dict = None
    responses: Dict = None
    tags: List[str] = None

class APIDocGenerator:
    """API文档生成器"""
    
    def __init__(self, title: str, version: str):
        self.title = title
        self.version = version
        self.endpoints: List[APIEndpoint] = []
        
    def add_endpoint(self, endpoint: APIEndpoint):
        """添加API端点"""
        self.endpoints.append(endpoint)
        
    def generate_openapi_spec(self) -> Dict:
        """生成OpenAPI规范"""
        spec = {
            "openapi": "3.0.0",  # 明确指定OpenAPI版本
            "info": {
                "title": self.title,
                "version": self.version,
                "description": "API Documentation"
            },
            "servers": [
                {
                    "url": "/"  # 基础URL
                }
            ],
            "paths": {},
            "components": {  # 添加组件定义
                "schemas": {},
                "securitySchemes": {}
            }
        }
        
        # 组织端点信息
        for endpoint in self.endpoints:
            if endpoint.path not in spec["paths"]:
                spec["paths"][endpoint.path] = {}
                
            method_spec = {
                "summary": endpoint.summary,
                "description": endpoint.description,
                "tags": endpoint.tags,
                "responses": endpoint.responses or {
                    "200": {
                        "description": "Successful response"
                    }
                }
            }
            
            # 添加参数
            if endpoint.parameters:
                method_spec["parameters"] = endpoint.parameters
                
            # 添加请求体
            if endpoint.request_body:
                method_spec["requestBody"] = endpoint.request_body
                
            spec["paths"][endpoint.path][endpoint.method.lower()] = method_spec
            
        return spec

    def generate_swagger_ui(self) -> dict:
        """生成Swagger UI HTML"""
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