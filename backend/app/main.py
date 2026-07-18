import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import accounts, dashboard, kis, market, stocks, strategies, transactions
from app.db.db import init_db
from app.scheduler import run_catchup_sync_and_scheduler
from app.seed import init_default_data


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup ---
    init_db()
    init_default_data()
    asyncio.create_task(run_catchup_sync_and_scheduler())
    yield
    # --- Shutdown (cleanup if needed) ---


app = FastAPI(title="Astron Trading Engine API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dashboard.router)
app.include_router(transactions.router)
app.include_router(stocks.router)
app.include_router(market.router)
app.include_router(accounts.router)
app.include_router(strategies.router)
app.include_router(kis.router)
