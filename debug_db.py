import asyncio
from src.core.database import AsyncSessionLocal
from src.models.models import Organization, User
from sqlalchemy import select, outerjoin

async def debug_all():
    async with AsyncSessionLocal() as session:
        # Orgs
        res_orgs = await session.execute(select(Organization))
        orgs = res_orgs.scalars().all()
        print("\n--- ORGANIZATIONS ---")
        for o in orgs:
            print(f"ID: {o.id}, Name: {o.name}, Slug: {o.slug}")

        # Users
        res_users = await session.execute(select(User))
        users = res_users.scalars().all()
        print("\n--- USERS ---")
        for u in users:
            print(f"ID: {u.id}, Username: {u.username}, Org ID: {u.org_id}, Superadmin: {u.is_superadmin}")

if __name__ == "__main__":
    asyncio.run(debug_all())
