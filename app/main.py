import os
import traceback
import sys  # Add this import
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from app.database import connect_db, close_db
from app.routers import users, store  # Remove , sys from here

app = FastAPI(title="Virtual Store Backend")

# CORS
origins = [
    "https://vstore-kappa.vercel.app",
    "http://localhost:3000",
]

# Debug endpoints - move before CORS middleware
@app.get("/debug/users-code")
async def debug_users_code():
    """Check what code is actually running in the users router"""
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
    """Check what code is actually running in auth"""
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

# More detailed error middleware
@app.middleware("http")
async def catch_exceptions_middleware(request: Request, call_next):
    try:
        response = await call_next(request)
        return response
    except Exception as e:
        # Print FULL traceback to identify exact location
        print("=" * 80)
        print("FULL ERROR TRACEBACK:")
        error_traceback = traceback.format_exc()
        print(error_traceback)
        print("=" * 80)
        
        # Also log the request details
        print(f"Request: {request.method} {request.url}")
        
        return JSONResponse(
            status_code=500,
            content={"detail": f"Internal server error: {str(e)}"}
        )

# Routers
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(store.router, prefix="/api/store", tags=["Store"])

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