import asyncio
from src.core.database import AsyncSessionLocal
from src.models.models import User
from sqlalchemy import select

async def list_users():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User))
        users = result.scalars().all()
        print(f"Total Users: {len(users)}")
        for u in users:
            print(f"ID: {u.id}, Username: {u.username}, Role: {'SuperAdmin' if u.is_superadmin else 'Admin'}, Org ID: {u.org_id}")

if __name__ == "__main__":
    asyncio.run(list_users())
