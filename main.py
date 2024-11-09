import aiohttp
import asyncio

async def fetch(session, url):
    async with session.get(url) as response:
        return await response.text()

async def main():
    try:
        async with aiohttp.ClientSession() as session:
            html = await fetch(session, 'http://127.0.0.1:8000/users/1')
            print(html)
    except Exception as e:
        print(f"Request failed: {e}")

asyncio.run(main())