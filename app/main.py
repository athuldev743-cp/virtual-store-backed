from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from .database import Base, engine
from .routers import users, store

app = FastAPI()

# ✅ Global exception handler for debugging
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)}
    )

# Create DB tables
Base.metadata.create_all(bind=engine)

# Routers
app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(store.router, prefix="/api/store", tags=["store"])

# Optional root route
@app.get("/")
def read_root():
    return {"message": "Backend is running!"}
