import asyncio
from sqlalchemy import text
from src.core.database import AsyncSessionLocal

async def apply_migration():
    print("Applying migration: adding google_calendar_id to organizations table...")
    async with AsyncSessionLocal() as session:
        try:
            await session.execute(text("ALTER TABLE organizations ADD COLUMN IF NOT EXISTS google_calendar_id TEXT;"))
            await session.commit()
            print("Migration applied successfully!")
        except Exception as e:
            print(f"Error applying migration: {e}")
            await session.rollback()

if __name__ == "__main__":
    asyncio.run(apply_migration())
