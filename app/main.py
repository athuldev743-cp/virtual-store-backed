# app/main.py
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.database import connect_db, close_db
from app.routers import users, store

# -------------------------
# FastAPI App
# -------------------------
app = FastAPI(title="Virtual Store Backend")

# -------------------------
# CORS configuration
# -------------------------
# Exact frontend domains
origins = [
    "https://vstore-kappa.vercel.app",  # production frontend
    "http://localhost:3000",             # local frontend
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,      # allows cookies / Authorization headers
    allow_methods=["*"],         # all HTTP methods
    allow_headers=["*"],         # all headers
    expose_headers=["*"],        # expose all headers
)

# -------------------------
# Include Routers
# -------------------------
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(store.router, prefix="/api/store", tags=["Store"])

# -------------------------
# Serve uploaded files
# -------------------------
UPLOAD_DIR = "uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

# -------------------------
# Root endpoint
# -------------------------
@app.get("/")
async def root():
    return {"message": "Backend is running!"}

# -------------------------
# Startup & Shutdown Events
# -------------------------
@app.on_event("startup")
async def startup_event():
    await connect_db()
    print("Database connected ✅")

@app.on_event("shutdown")
async def shutdown_event():
    await close_db()
    print("Database disconnected ✅")

# -------------------------
# Local run (optional)
# -------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=os.environ.get("APP_HOST", "0.0.0.0"),
        port=int(os.environ.get("APP_PORT", 8000)),
        reload=True
    )
