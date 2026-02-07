import asyncio
from src.core.database import AsyncSessionLocal
from src.models.models import Organization, User
from sqlalchemy import select, delete

async def delete_vet_central():
    async with AsyncSessionLocal() as session:
        # Buscar la org con ID 1 (Veterinaria Central)
        stmt = select(Organization).where(Organization.id == 1)
        result = await session.execute(stmt)
        org = result.scalar()
        
        if org:
            print(f"Encontrada organización a eliminar: {org.name} (ID: {org.id})")
            
            # Eliminar usuarios asociados primero (si no hay cascade)
            # Aunque SQLAlchemy relationship con cascade='all, delete' debería encargarse,
            # es mas seguro verificar o hacerlo manual si hay dudas.
            # En este caso asumiremos que la FK en User está configurada o lo haremos directo.
            
            # Borrar la organización
            await session.delete(org)
            await session.commit()
            print(" Organización 'Veterinaria Central' eliminada correctamente.")
        else:
            print("No se encontró la organización con ID 1.")

if __name__ == "__main__":
    asyncio.run(delete_vet_central())
