import asyncio
from src.core.database import AsyncSessionLocal
from src.models.models import Organization, User
from sqlalchemy import select, outerjoin
from src.core.security import verify_password

async def test_login_logic(username, password):
    print(f"\nTesting login for: {username}")
    async with AsyncSessionLocal() as session:
        res = await session.execute(
            select(User, Organization)
            .outerjoin(Organization, User.org_id == Organization.id)
            .where(User.username == username)
        )
        row = res.first()
        
        if not row:
            print("FAILED: User not found")
            return
            
        user, org = row
        if verify_password(password, user.password_hash):
            print("PASSWORD OK")
            if not user.is_superadmin:
                if not org:
                    print("FAILED: Org is None for non-superadmin")
                    return
                if not org.is_active:
                    print("FAILED: Org is inactive")
                    return
            print(f"SUCCESS: Logged in as {'Superadmin' if user.is_superadmin else 'Admin'} for org '{org.name if org else 'N/A'}'")
        else:
            print("FAILED: Invalid password")

async def run_tests():
    # 1. Test Superadmin
    await test_login_logic("superadmin", "admin123456")
    
    # 2. Test Organization user (vet1)
    await test_login_logic("vet1", "vet1_pass_or_whatever") # I don't know the exact pass, but I'll see if it finds it.
    
if __name__ == "__main__":
    asyncio.run(run_tests())
