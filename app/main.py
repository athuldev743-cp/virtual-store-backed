import os
import sys
import traceback
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

from app.database import connect_db, close_db
from app.routers import users, store, payment  # FIX: Added payment router


app = FastAPI(title="Virtual Store Backend")

# CORS
origins = [
    "https://vstore-kappa.vercel.app",
    "http://localhost:3000",
]

# Debug endpoints
@app.get("/debug/users-code")
async def debug_users_code():
    import inspect
    try:
        from app.routers import users
        signup_source = inspect.getsource(users.signup)
        return {
            "status": "success",
            "signup_function_code": signup_source
        }
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@app.get("/debug/auth-code")
async def debug_auth_code():
    import inspect
    try:
        from app.auth import hash_password
        hash_source = inspect.getsource(hash_password)
        return {
            "status": "success",
            "hash_password_function_code": hash_source
        }
    except Exception as e:
        return {"status": "error", "detail": str(e)}


@app.get("/debug/versions")
async def debug_versions():
    import passlib
    import pydantic
    import fastapi
    return {
        "passlib_version": passlib.__version__,
        "pydantic_version": pydantic.__version__,
        "fastapi_version": fastapi.__version__,
        "python_version": sys.version
    }


app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Error middleware
@app.middleware("http")
async def catch_exceptions_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as e:
        print("=" * 80)
        print("FULL ERROR TRACEBACK:")
        print(traceback.format_exc())
        print("=" * 80)
        print(f"Request: {request.method} {request.url}")
        return JSONResponse(
            status_code=500,
            content={"detail": f"Internal server error: {str(e)}"}
        )


# Routers
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(store.router, prefix="/api/store", tags=["Store"])
app.include_router(payment.router, prefix="/api/payments", tags=["Payments"])   # FIX ADDED


# Serve uploads
UPLOAD_DIR = "uploads"
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")


@app.get("/")
async def root():
    return {"message": "Backend is running!"}


# Startup & Shutdown
@app.on_event("startup")
async def startup_event():
    await connect_db()
    print("Database connected ✅")


@app.on_event("shutdown")
async def shutdown_event():
    await close_db()
    print("Database disconnected ✅")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
