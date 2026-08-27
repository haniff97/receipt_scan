from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import Base, engine
from .routes import analytics, lhdn, query, receipts, transactions

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Receipt Tracker")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(query.router, prefix="/api")
app.include_router(receipts.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")
app.include_router(transactions.router, prefix="/api")
app.include_router(lhdn.router, prefix="/api")
