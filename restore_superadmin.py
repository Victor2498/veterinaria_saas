import asyncio
from src.core.database import AsyncSessionLocal
from src.models.models import User
from src.core.security import get_password_hash
from sqlalchemy import select

async def ensure_superadmin():
    async with AsyncSessionLocal() as session:
        stmt = select(User).where(User.username == "superadmin")
        result = await session.execute(stmt)
        user = result.scalar()
        
        if user:
            print("Superadmin already exists.")
            # Ensure it is superadmin and detached
            if not user.is_superadmin:
                user.is_superadmin = True
                print("Promoted to is_superadmin=True")
            if user.org_id is not None:
                user.org_id = None
                print("Detached from any organization")
            await session.commit()
        else:
            print("Creating Superadmin user...")
            new_sa = User(
                username="superadmin",
                password_hash=get_password_hash("admin123456"),
                is_superadmin=True,
                is_admin=True,
                org_id=None # IMPORTANT: Independent
            )
            session.add(new_sa)
            await session.commit()
            print("Superadmin created successfully.")

if __name__ == "__main__":
    asyncio.run(ensure_superadmin())
