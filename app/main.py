from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from .database import db  # async Mongo client
from .routers import users, store

app = FastAPI()

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
