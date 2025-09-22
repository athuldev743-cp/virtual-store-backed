# app/main.py
import os
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import connect_db, close_db
from app.routers import users, store

app = FastAPI(title="Virtual Store Backend")

# -------------------------
# CORS
# -------------------------
origins = [
    "https://vstore-kappa.vercel.app",  # your frontend URL
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------
# Routers
# -------------------------
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(store.router, prefix="/api/store", tags=["Store"])

@app.get("/")
async def root():
    return {"message": "Backend is running!"}

# -------------------------
# Startup & Shutdown
# -------------------------
@app.on_event("startup")
async def startup():
    await connect_db()

@app.on_event("shutdown")
async def shutdown():
    await close_db()

# -------------------------
# Run locally
# -------------------------
if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)), reload=True)
