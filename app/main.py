# app/main.py
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.database import connect_db, close_db
from app.routers import users, store

app = FastAPI(title="Virtual Store Backend")

# -------------------------
# CORS configuration
# -------------------------
# Allow your frontend domain(s)
origins = [
    "https://vstore-kappa.vercel.app",  # production frontend
    "http://localhost:3000",             # local frontend
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,       # must match frontend exactly
    allow_credentials=True,      # allow cookies or Authorization headers
    allow_methods=["*"],         # allow all HTTP methods
    allow_headers=["*"],         # allow all headers including Authorization
)

# -------------------------
# Include Routers
# -------------------------
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(store.router, prefix="/api/store", tags=["Store"])
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# -------------------------
# Root endpoint to check backend
# -------------------------
@app.get("/")
async def root():
    return {"message": "Backend is running!"}

# -------------------------
# Startup & Shutdown events
# -------------------------
@app.on_event("startup")
async def startup_event():
    await connect_db()

@app.on_event("shutdown")
async def shutdown_event():
    await close_db()

# -------------------------
# Run locally
# -------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8000)),
        reload=True
    )
