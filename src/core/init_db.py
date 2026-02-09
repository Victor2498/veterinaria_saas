from sqlalchemy import select, text
from src.core.security import get_password_hash
from src.core.database import engine, AsyncSessionLocal, Base
from src.models.models import Organization, User, MedicalAttention, Ticket, TicketItem

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
            ("vaccinations", "is_signed", "BOOLEAN DEFAULT FALSE"),
            ("vaccinations", "signed_at", "TIMESTAMP WITH TIME ZONE"),
            ("vaccinations", "batch_number", "VARCHAR"),
            ("vaccinations", "signature_hash", "VARCHAR"),
            ("vaccinations", "signature_data", "TEXT"),
            ("vaccinations", "vet_stamp", "TEXT"),
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

        # 1.5 Create Indexes
        indexes = [
            ("idx_apps_org_status", "appointments", "(org_id, status)"),
            ("idx_apps_org_date", "appointments", "(org_id, date)"),
        ]
        
        for idx_name, table, columns in indexes:
            try:
                # Check if index exists
                check_idx = f"SELECT indexname FROM pg_indexes WHERE tablename = '{table}' AND indexname = '{idx_name}';"
                res = await session.execute(text(check_idx))
                if not res.scalar():
                    print(f"Creating index {idx_name} on {table}...")
                    await session.execute(text(f"CREATE INDEX {idx_name} ON {table} {columns};"))
                    await session.commit()
            except Exception as e:
                print(f"Skipping index {idx_name}: {e}")
                await session.rollback()

    # Seed (Only if not already seeded)
    async with AsyncSessionLocal() as session:
        # 1. Check if we have any organizations, if not create default
        org_check = await session.execute(select(Organization).limit(1))
        if not org_check.scalar():
            print("🌱 Seeding default organization...")
            default_org = Organization(name="Veterinaria Central", slug="central")
            session.add(default_org)
            await session.commit()
            await session.refresh(default_org)
        else:
            default_org = (await session.execute(select(Organization).where(Organization.slug == "central"))).scalar()

        # 2. Check if superadmin exists, if not create
        user_check = await session.execute(select(User).where(User.username == "superadmin"))
        if not user_check.scalar():
            super_pwd = "admin123456" 
            new_user = User(
                username="superadmin",
                password_hash=get_password_hash(super_pwd),
                org_id=default_org.id if default_org else None,
                is_admin=True,
                is_superadmin=True
            )
            session.add(new_user)
            await session.commit()
            print(f"✅ SuperAdmin created with username 'superadmin' and password '{super_pwd}'.")
        else:
            print("ℹ️ Superadmin already exists. Skipping seed.")
