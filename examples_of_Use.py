import uvicorn

from requests import AsyncRequest
from router import FlawlessAPI


# 示例中间件函数
# 用户定义的逻辑函数
async def middleware_logic(scope, timing):
    if timing == 'before':
        print(f"Before request in {scope['path']}")
    elif timing == 'after':
        print(f"After request in {scope['path']}")


app = FlawlessAPI()

# 将示例中间件添加到应用中
app.add_middleware(middleware_logic)


# 处理函数: 返回 "Hello, World!"
async def hello_world(request: AsyncRequest):
    query_params = await request.query_string()
    if query_params:
        return {"msg": "", "code": 200, "data": query_params}
    body = await request.body()
    if body:
        return {"msg": "", "code": 200, "data": body}
    return {"msg": "", "code": 200, "data": 'Hello, World!'}


# 处理函数: 返回 "This is the about page."
async def about_page(request: AsyncRequest):
    return b'This is the about page.'


app.routes = {
    "/hello": (["GET"], hello_world),
    "/about": (["POST", "GET"], about_page),
}

# 当该脚本被作为程序运行时，执行 main 函数
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
