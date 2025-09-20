#app/main.py
import os
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from .database import connect_db, close_db, db
from .routers import users, store

app = FastAPI(title="Real Estate Backend")

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)}
    )

# Routers
app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(store.router, prefix="/api/store", tags=["store"])

@app.get("/")
async def read_root():
    return {"message": "Backend is running!"}

# Startup and shutdown events
@app.on_event("startup")
async def startup_db():
    await connect_db()

@app.on_event("shutdown")
async def shutdown_db():
    await close_db()

# Only run directly
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)
