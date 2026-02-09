import asyncio
import sys
import os

# Add the project root to python path
sys.path.append(os.getcwd())

from src.core.init_db import init_db

async def main():
    print("Starting manual migration...")
    try:
        await init_db()
        print("Migration completed successfully.")
    except Exception as e:
        print(f"Migration failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
