from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.config import get_settings
from app.security_logging import install_secret_filter
from app.storage.database import connect

settings = get_settings()
install_secret_filter(settings.secret_values())
connect(settings.database_path)

app = FastAPI(
    title="OAuth Launchpad",
    description="Research-agent backend that generates evidence-backed OAuth setup guides.",
    version="1.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)
app.include_router(router)
