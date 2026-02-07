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

    # --- WIPE DATA (Optional: Can be toggleable) ---
    async with AsyncSessionLocal() as session:
        # Tables to wipe in order to respect foreign keys
        tables_to_wipe = [
            "vaccinations", "clinical_records", "appointments", 
            "patients", "owners", "services", "users", "organizations"
        ]
        print("🧹 Starting total system wipe...")
        for table in tables_to_wipe:
            try:
                await session.execute(text(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE;"))
                print(f"   Deleted all data from {table}")
            except Exception as e:
                print(f"   Error wiping {table}: {e}")
        await session.commit()

    # Seed
    async with AsyncSessionLocal() as session:
        # 1. Create Default Org for SuperAdmin
        default_org = Organization(name="Veterinaria Central", slug="central")
        session.add(default_org)
        await session.commit()
        await session.refresh(default_org)

        # 2. Create ONLY the SuperAdmin
        super_pwd = "admin123456" # Predeterminada solicitada por el usuario
        new_user = User(
            username="superadmin",
            password_hash=get_password_hash(super_pwd),
            org_id=default_org.id,
            is_admin=True,
            is_superadmin=True
        )
        session.add(new_user)
        print(f"✅ System reset complete. SuperAdmin created with username 'superadmin' and password '{super_pwd}'.")
        
        await session.commit()
