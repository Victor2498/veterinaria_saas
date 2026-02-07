import asyncio
from src.core.database import AsyncSessionLocal
from src.models.models import User, Organization
from sqlalchemy import select

async def check_state():
    async with AsyncSessionLocal() as session:
        # Check Organizations
        orgs = (await session.execute(select(Organization))).scalars().all()
        print(f"Organizations found: {len(orgs)}")
        for org in orgs:
            print(f"Org ID: {org.id}, Name: {org.name}, Slug: {org.slug}")

        # Check Superadmin(s)
        users = (await session.execute(select(User).where(User.is_superadmin == True))).scalars().all()
        print(f"\nSuperadmins found: {len(users)}")
        for user in users:
            print(f"User: {user.username}, Org ID: {user.org_id}")

if __name__ == "__main__":
    asyncio.run(check_state())
