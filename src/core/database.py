import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv()

# Database Configuration
# Priorizar DATABASE_URL si existe (para Supabase o conexiones directas)
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    # Fallback a variables individuales (para Easypanel o configuración legacy)
    DB_USER = os.getenv("POSTGRES_USER", "postgres")
    DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "password")
    DB_HOST = os.getenv("POSTGRES_HOST") or os.getenv("POSTGRES_SERVER") or "localhost"
    DB_PORT = os.getenv("POSTGRES_PORT", "5432")
    DB_NAME = os.getenv("POSTGRES_DB", "dogbot_db")
    DATABASE_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Supabase Transaction Pooler compatibility
connect_args = {"server_settings": {"jit": "off"}} # Basic safe setting
# For asyncpg with Supabase pooler, we often need to disable prepared statements:
# connect_args["statement_cache_size"] = 0 

engine = create_async_engine(
    DATABASE_URL, 
    echo=False,
    pool_pre_ping=True, # Verify connection before usage
    pool_recycle=1800,  # Recycle connections every 30 mins
    connect_args={"statement_cache_size": 0} # Disable prepared statements for pgbouncer compatibility
)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
