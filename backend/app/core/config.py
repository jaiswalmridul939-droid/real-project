import os
from dotenv import load_dotenv
from sqlalchemy.engine import make_url

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./claim_whats_yours.db")
APP_ENV = os.getenv("APP_ENV", "development").lower()
FRONTEND_ORIGINS = [
	origin.strip().rstrip("/")
	for origin in os.getenv("FRONTEND_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",")
	if origin.strip()
]
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY", "")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-haiku-4-5-20251001")
JWT_SECRET = os.getenv("JWT_SECRET", "change-me-before-deploying")
ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@example.test")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "demo-admin-change-me")
ENABLE_SCHEDULER = os.getenv("ENABLE_SCHEDULER", "false").lower() == "true"


def validate_production_settings() -> None:
	if APP_ENV != "production":
		return
	if JWT_SECRET == "change-me-before-deploying" or len(JWT_SECRET) < 32:
		raise RuntimeError("Production requires a unique JWT_SECRET of at least 32 characters.")
	if ADMIN_PASSWORD == "demo-admin-change-me" or len(ADMIN_PASSWORD) < 12:
		raise RuntimeError("Production requires a unique ADMIN_PASSWORD of at least 12 characters.")
	if not FRONTEND_ORIGINS or any(not origin.startswith("https://") for origin in FRONTEND_ORIGINS):
		raise RuntimeError("Production FRONTEND_ORIGINS must contain only HTTPS origins.")
	database_url = make_url(DATABASE_URL)
	if database_url.get_backend_name() == "postgresql" and (not database_url.password or len(database_url.password) < 16 or database_url.password == "postgres"):
		raise RuntimeError("Production PostgreSQL requires a unique password of at least 16 characters.")
