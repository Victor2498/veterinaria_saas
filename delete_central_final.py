import asyncio
from src.core.database import AsyncSessionLocal
from src.models.models import Organization, User
from sqlalchemy import select, delete

async def delete_central_specifically():
    async with AsyncSessionLocal() as session:
        # Find orgs matching the description
        stmt = select(Organization).where(
            (Organization.slug == 'central') | (Organization.name == 'Veterinaria Central')
        )
        result = await session.execute(stmt)
        orgs = result.scalars().all()
        
        if not orgs:
            print("No se encontró 'Veterinaria Central'.")
            return

        print(f"Encontradas {len(orgs)} organizaciones para eliminar.")
        
        for org in orgs:
            print(f"Eliminando: {org.name} (ID: {org.id}, Slug: {org.slug})")
            
            # Delete users first (if not cascading)
            await session.execute(delete(User).where(User.org_id == org.id))
            
            # Delete the org
            await session.delete(org)
            
        await session.commit()
        print("Eliminación completada.")

if __name__ == "__main__":
    asyncio.run(delete_central_specifically())
