import asyncio
from cache import cached
from cache import lru_cache


@cached(expire=300, key_prefix="user")
async def get_user(user_id: int):
    # ... 获取用户信息的代码 ...
    return {"user_id": user_id}

# 获取缓存统计
stats = lru_cache.get_stats()
print(f"缓存命中率: {stats['hit_rate']}")

# 清除特定缓存
asyncio.run(get_user.clear_cache(user_id=123))