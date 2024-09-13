"""
redis cache
"""

import logging
import os

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)


class RedisWrapper:
    """
    Redis wrapper
    """

    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL")
        self.redis_auth_string = os.getenv("REDIS_AUTH_STRING")
        self.redis = None
        self.connect_retry = 3

        for _ in range(self.connect_retry):
            try:
                self.redis = aioredis.from_url(
                    self.redis_url,
                    password=self.redis_auth_string,
                    encoding="utf-8",
                    decode_responses=True,
                )
                pong = self.redis.ping()
                if pong:
                    break
            except aioredis.ConnectionError:
                logger.error("redis not connected")
                continue

    async def get(self, key: str):
        """
        get value (str)
        """
        value = await self.redis.get(key)
        return value.decode("utf-8") if value else None

    async def set(self, key: str, value: str, ttl=-1):
        """
        set kv
        """

        await self.redis.set(key, value)
        if ttl > 0:
            await self.redis.expire(key, ttl)

    async def setnx(self, key: str, value: str, ttl=-1):
        """
        setnx
        """
        result = await self.redis.set(key, value, ex=ttl, nx=True)
        return result

    async def delete(self, key: str):
        """
        delete key
        """
        await self.redis.delete(key)

    async def lrange(self, key: str, start: int = 0, end: int = -1):
        """
        lrange
        """
        values = await self.redis.lrange(key, start, end)
        return [value.decode("utf-8") for value in values]

    async def lpush(self, key: str, value: str, ttl=-1):
        """
        lpush
        """
        await self.redis.lpush(key, value)
        if ttl > 0:
            await self.redis.expire(key, ttl)

    async def close(self):
        """
        close
        """
        await self.redis.close()


redis = RedisWrapper()
