import asyncio

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import accounts, dashboard, market, stocks, strategies, transactions
from app.db.db import init_db
from app.scheduler import run_catchup_sync, run_catchup_sync_and_scheduler, schedule_daily_sync
from app.seed import init_default_data

app = FastAPI(title="Astron Trading Engine API")

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

@app.on_event("startup")
async def startup_event():
    init_db()
    init_default_data()
    asyncio.create_task(run_catchup_sync_and_scheduler())


@app.on_event("startup")
def on_startup():
    asyncio.create_task(asyncio.to_thread(run_catchup_sync))
    asyncio.create_task(schedule_daily_sync())
