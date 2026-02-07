import asyncio
from src.core.database import AsyncSessionLocal
from src.models.models import User, Organization
from sqlalchemy import select, update, delete

async def reset_saas():
    async with AsyncSessionLocal() as session:
        # 1. Get superadmin
        res = await session.execute(select(User).where(User.username == 'superadmin'))
        admin = res.scalar()
        if not admin:
            print("Superadmin user not found!")
            return

        print(f"Superadmin currently at Org ID: {admin.org_id}")

        # 2. Try to set org_id to None
        try:
            admin.org_id = None
            await session.commit()
            print("Successfully detached superadmin from any organization.")
        except Exception as e:
            print(f"Failed to detach superadmin (org_id might be non-nullable): {e}")
            await session.rollback()
            return

        # 3. Delete ALL organizations
        print("Deleting all organizations...")
        await session.execute(delete(Organization))
        await session.commit()
        print("All organizations deleted.")

        # 4. Verify state
        orgs = (await session.execute(select(Organization))).scalars().all()
        users = (await session.execute(select(User))).scalars().all()
        print(f"Remaining Organizations: {len(orgs)}")
        print(f"Remaining Users: {[u.username for u in users]}")

if __name__ == "__main__":
    asyncio.run(reset_saas())
