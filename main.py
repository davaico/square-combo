"""
Main FastAPI application entry point.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from routes.auth import router as auth_router
from routes.admin import router as admin_router
from routes.templates import router as templates_router
from utils.config import settings
from utils.logging import setup_logging

# Setup logging
setup_logging()

app = FastAPI(
    title="Square-Combo Integration",
    description="Daily revenue sync between Square and Combo",
    version="0.0.1",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth_router, prefix="/auth", tags=["authentication"])
app.include_router(admin_router, prefix="/admin", tags=["admin"])
app.include_router(templates_router, prefix="/templates", tags=["templates"])


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/")
async def root():
    """Root endpoint."""
    return {"message": "Square-Combo Integration", "version": "0.0.1"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=True)
