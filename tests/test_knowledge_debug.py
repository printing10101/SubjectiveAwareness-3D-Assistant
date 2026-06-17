"""Test knowledge endpoints to debug 500 errors."""
import asyncio
import httpx


async def test():
    async with httpx.AsyncClient() as client:
        # Login
        r = await client.post(
            "http://localhost:8000/api/auth/login",
            data={"username": "admin", "password": "admin123"},
        )
        if r.status_code != 200:
            print(f"Login failed: {r.status_code}")
            print(f"Response: {r.text}")
            return
        token = r.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Test knowledge tag listing
        print("=== 测试标签列表 ===")
        r = await client.get("http://localhost:8000/api/knowledge/tags", headers=headers)
        print(f"Status: {r.status_code}")
        print(f"Response: {r.text}")
        if r.status_code != 200:
            print(f"Error detail: {r.json() if r.headers.get('content-type', '').startswith('application/json') else 'Not JSON'}")
        else:
            data = r.json()
            print(f"OK: {data[:2] if data else 'empty'}")

        # Test knowledge entry creation
        print("\n=== 测试创建知识条目 ===")
        entry_data = {
            "title": "回归测试条目",
            "content": "这是回归测试创建的内容",
            "category": "law",
            "source_type": "manual",
        }
        r = await client.post(
            "http://localhost:8000/api/knowledge/entries",
            json=entry_data,
            headers=headers,
        )
        print(f"Status: {r.status_code}")
        print(f"Response: {r.text}")
        if r.status_code not in (200, 201):
            print(f"Error detail: {r.json() if r.headers.get('content-type', '').startswith('application/json') else 'Not JSON'}")
        else:
            print(f"OK: id={r.json().get('id', 'created')}")


asyncio.run(test())
