import asyncio
import aiohttp
import logging

logging.basicConfig(level=logging.INFO)


async def test_connection():
    """Тестирование подключения к разным endpoint"""
    endpoints = [
        "https://api.telegram.org",
        "https://google.com",
        "https://github.com",
        "https://8.8.8.8"  # Google DNS
    ]

    for endpoint in endpoints:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(endpoint, timeout=10, ssl=False) as response:
                    logging.info(f"✅ {endpoint} - доступен (статус: {response.status})")
        except Exception as e:
            logging.error(f"❌ {endpoint} - недоступен: {e}")


if __name__ == "__main__":
    asyncio.run(test_connection())