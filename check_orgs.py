import asyncio
from src.core.database import AsyncSessionLocal
from src.models.models import Organization
from sqlalchemy import select

async def list_orgs():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Organization))
        orgs = result.scalars().all()
        print(f"Found {len(orgs)} organizations:")
        for org in orgs:
            print(f"ID: {org.id}, Name: {repr(org.name)}, Slug: {repr(org.slug)}, Active: {org.is_active}")

if __name__ == "__main__":
    asyncio.run(list_orgs())
