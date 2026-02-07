from sqlalchemy import select, text
from src.core.security import get_password_hash
from src.core.database import engine, AsyncSessionLocal, Base
from src.models.models import Organization, User

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Simple migration/patching
    async with AsyncSessionLocal() as session:
        alterations = [
            ("appointments", "reason", "VARCHAR"),
            ("appointments", "status", "VARCHAR DEFAULT 'confirmed'"),
            ("appointments", "org_id", "INTEGER"),
            ("owners", "org_id", "INTEGER"),
            ("patients", "org_id", "INTEGER"),
            ("vaccinations", "org_id", "INTEGER"),
            ("services", "org_id", "INTEGER"),
            ("patients", "breed", "VARCHAR"),
            ("patients", "birth_date", "TIMESTAMP WITH TIME ZONE"),
            ("patients", "weight", "FLOAT"),
            ("patients", "height", "FLOAT"),
            ("patients", "sex", "VARCHAR"),
            ("clinical_records", "org_id", "INTEGER"),
            ("organizations", "is_active", "BOOLEAN DEFAULT TRUE"),
            ("organizations", "evolution_api_url", "VARCHAR"),
            ("organizations", "evolution_api_key", "VARCHAR"),
            ("organizations", "evolution_instance", "VARCHAR"),
            ("organizations", "openai_api_key", "VARCHAR"),
            ("organizations", "plan_type", "VARCHAR DEFAULT 'basic'"),
            ("users", "is_superadmin", "BOOLEAN DEFAULT FALSE"),
        ]
        
        for table, col, col_type in alterations:
            try:
                check_sql = f"SELECT column_name FROM information_schema.columns WHERE table_name='{table}' AND column_name='{col}';"
                res = await session.execute(text(check_sql))
                if not res.scalar():
                    print(f"Adding column {col} to {table}...")
                    await session.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {col_type};"))
                    await session.commit()
            except Exception as e:
                print(f"Skipping alteration for {table}.{col}: {e}")
                await session.rollback()

    # Seed
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(Organization).where(Organization.slug == "central"))
        default_org = res.scalar()
        if not default_org:
            default_org = Organization(name="Veterinaria Central", slug="central")
            session.add(default_org)
            await session.commit()
            await session.refresh(default_org)

        users_to_seed = [
            {"username": "admin", "pwd": "admin123", "is_admin": True, "is_superadmin": False},
            {"username": "superadmin", "pwd": "super123", "is_admin": True, "is_superadmin": True}
        ]
        
        for u_data in users_to_seed:
            res = await session.execute(select(User).where(User.username == u_data["username"]))
            user = res.scalar()
            if not user:
                new_user = User(
                    username=u_data["username"],
                    password_hash=get_password_hash(u_data["pwd"]),
                    org_id=default_org.id,
                    is_admin=u_data["is_admin"],
                    is_superadmin=u_data["is_superadmin"]
                )
                session.add(new_user)
        
        await session.commit()
