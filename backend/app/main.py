from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.scan import router as scan_router
from app.api import auth, history
from app.db.database import engine, Base, AsyncSessionLocal
from app.db.seed import seed_fonts
from app.scoring.font_catalog import warm_cache


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # Seed font catalog
    async with AsyncSessionLocal() as session:
        await seed_fonts(session)
    # Pre-load Monotype font catalog into memory for fast license lookups
    warm_cache()
    yield


app = FastAPI(title="TypeScore Font Dashboard API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(history.router, prefix="/history", tags=["history"])
app.include_router(scan_router, tags=["scan"])
