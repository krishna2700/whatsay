from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from app.core.config import settings
import ssl

# Build engine kwargs
engine_kwargs = {
    "pool_pre_ping": True,
    "echo": settings.DEBUG,
    "pool_size": settings.DATABASE_POOL_SIZE,
    "max_overflow": settings.DATABASE_MAX_OVERFLOW,
}

# Handle Neon PostgreSQL SSL
db_url = settings.async_database_url
connect_args = {}

if "neon.tech" in db_url:
    ssl_ctx = ssl.create_default_context()
    ssl_ctx.check_hostname = False
    ssl_ctx.verify_mode = ssl.CERT_NONE
    connect_args["ssl"] = ssl_ctx
    # Neon uses pooler — disable server-side pooling params
    engine_kwargs["pool_size"] = 2
    engine_kwargs["max_overflow"] = 5

if connect_args:
    engine_kwargs["connect_args"] = connect_args

engine = create_async_engine(db_url, **engine_kwargs)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def init_db() -> None:
    from app.db.base import Base
    # Import all models to register them
    from app.models import user, question, recommendation, product, affiliate, analytics  # noqa
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
