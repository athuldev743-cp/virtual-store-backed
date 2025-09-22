import os
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.database import connect_db, close_db
from app.routers import users, store

app = FastAPI(title="Virtual Store Backend")

# -------------------------
# CORS
# -------------------------
origins = [
    "https://vstore-kappa.vercel.app",
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
# Global Exception Handler
# -------------------------
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)}
    )

# -------------------------
# Routers
# -------------------------
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(store.router, prefix="/api/store", tags=["Store"])

# -------------------------
# Root endpoint
# -------------------------
@app.get("/")
async def read_root():
    return {"message": "Backend is running!"}

# -------------------------
# Startup & Shutdown events
# -------------------------
@app.on_event("startup")
async def startup_db():
    await connect_db()

@app.on_event("shutdown")
async def shutdown_db():
    await close_db()

# -------------------------
# Run with uvicorn
# -------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)
