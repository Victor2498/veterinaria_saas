import os
import json
import redis.asyncio as redis
from dotenv import load_dotenv

load_dotenv()

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)

class RedisManager:
    def __init__(self):
        self.redis = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            password=REDIS_PASSWORD,
            decode_responses=True
        )
        self.ttl = 7200 # 2 hours
        self.config_ttl = 3600 # 1 hour for org config

    # Caching Org Config
    async def get_org_config(self, slug: str):
        key = f"org:config:{slug}"
        config = await self.redis.get(key)
        return json.loads(config) if config else None

    async def set_org_config(self, slug: str, config_dict: dict):
        key = f"org:config:{slug}"
        # Remove non-serializable objects if any
        serializable = {k: v for k, v in config_dict.items() if isinstance(v, (str, int, float, bool, type(None)))}
        await self.redis.set(key, json.dumps(serializable), ex=self.config_ttl)

    # User State & History
    async def get_state(self, user_id: str):
        key = f"user:{user_id}:state"
        state = await self.redis.get(key)
        return state if state else "START"

    async def set_state(self, user_id: str, state: str):
        key = f"user:{user_id}:state"
        await self.redis.set(key, state, ex=self.ttl)

    async def save_context(self, user_id: str, key: str, value: str):
        redis_key = f"user:{user_id}:context"
        await self.redis.hset(redis_key, key, value)
        await self.redis.expire(redis_key, self.ttl)

    async def get_context(self, user_id: str):
        redis_key = f"user:{user_id}:context"
        return await self.redis.hgetall(redis_key)

    async def get_history(self, user_id: str):
        key = f"user:{user_id}:history"
        history = await self.redis.get(key)
        return json.loads(history) if history else []

    async def save_history(self, user_id: str, messages: list):
        key = f"user:{user_id}:history"
        await self.redis.set(key, json.dumps(messages[-10:]), ex=self.ttl)

    async def clear_session(self, user_id: str):
        await self.redis.delete(f"user:{user_id}:state")
        await self.redis.delete(f"user:{user_id}:context")
        await self.redis.delete(f"user:{user_id}:history")

redis_client = RedisManager()
