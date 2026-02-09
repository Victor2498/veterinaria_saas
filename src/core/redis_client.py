import os
import json
import redis.asyncio as redis
from dotenv import load_dotenv

load_dotenv()

# Intelligent fallback for Easypanel service naming
DEFAULT_REDIS_HOST = os.getenv("REDIS_HOST")
if not DEFAULT_REDIS_HOST:
    # Try to guess based on PROJECT_NAME if available
    project_name = os.getenv("PROJECT_NAME", "sistema_veterinaria")
    DEFAULT_REDIS_HOST = f"{project_name}_evolution-api-redis"

REDIS_HOST = DEFAULT_REDIS_HOST or "localhost"
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)

class RedisManager:
    def __init__(self):
        print(f"DEBUG: Initializing Redis on {REDIS_HOST}:{REDIS_PORT}")
        self.redis = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            password=REDIS_PASSWORD,
            decode_responses=True,
            socket_connect_timeout=2 # Fast fail
        )
        self.ttl = 7200 # 2 hours
        self.config_ttl = 3600 # 1 hour for org config

    async def _safe_call(self, func, *args, default=None, **kwargs):
        """Wrapper to prevent Redis crashes from breaking the app"""
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            print(f"⚠️ Redis Error: {e}")
            return default

    # Caching Org Config
    async def get_org_config(self, slug: str):
        key = f"org:config:{slug}"
        res = await self._safe_call(self.redis.get, key, default=None)
        try:
            return json.loads(res) if res else None
        except:
            return None

    async def set_org_config(self, slug: str, config_dict: dict):
        key = f"org:config:{slug}"
        serializable = {k: v for k, v in config_dict.items() if isinstance(v, (str, int, float, bool, type(None)))}
        await self._safe_call(self.redis.set, key, json.dumps(serializable), ex=self.config_ttl)

    # User State & History
    async def get_state(self, user_id: str):
        key = f"user:{user_id}:state"
        res = await self._safe_call(self.redis.get, key, default="START")
        return res if res else "START"

    async def set_state(self, user_id: str, state: str):
        key = f"user:{user_id}:state"
        await self._safe_call(self.redis.set, key, state, ex=self.ttl)

    async def save_context(self, user_id: str, key: str, value: str):
        redis_key = f"user:{user_id}:context"
        await self._safe_call(self.redis.hset, redis_key, key, value)
        await self._safe_call(self.redis.expire, redis_key, self.ttl)

    async def get_context(self, user_id: str):
        redis_key = f"user:{user_id}:context"
        return await self._safe_call(self.redis.hgetall, redis_key, default={})

    async def get_history(self, user_id: str):
        key = f"user:{user_id}:history"
        res = await self._safe_call(self.redis.get, key, default="[]")
        try:
            return json.loads(res) if res else []
        except:
            return []

    async def save_history(self, user_id: str, messages: list):
        key = f"user:{user_id}:history"
        await self._safe_call(self.redis.set, key, json.dumps(messages[-10:]), ex=self.ttl)

    async def clear_session(self, user_id: str):
        await self._safe_call(self.redis.delete, f"user:{user_id}:state")
        await self._safe_call(self.redis.delete, f"user:{user_id}:context")
        await self._safe_call(self.redis.delete, f"user:{user_id}:history")

    async def get_services_text(self, org_id: str):
        """Get cached formatted services list"""
        key = f"org:{org_id}:services_text"
        return await self._safe_call(self.redis.get, key)

    async def set_services_text(self, org_id: str, text: str):
        """Cache formatted services list for 1 hour"""
        key = f"org:{org_id}:services_text"
        await self._safe_call(self.redis.set, key, text, ex=3600)

redis_client = RedisManager()
