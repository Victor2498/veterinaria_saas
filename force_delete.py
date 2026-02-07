import asyncio
from src.core.database import AsyncSessionLocal
from sqlalchemy import text

async def force_delete():
    async with AsyncSessionLocal() as session:
        print("Intentando eliminar ID 1 via SQL directo...")
        # Desactivar check de FK si es necesario, o borrar en cascada
        # Primero borramos usuarios de esa org
        await session.execute(text("DELETE FROM users WHERE org_id = 1"))
        # Luego la org
        await session.execute(text("DELETE FROM organizations WHERE id = 1"))
        await session.commit()
        print("Eliminación completada.")

if __name__ == "__main__":
    asyncio.run(force_delete())
