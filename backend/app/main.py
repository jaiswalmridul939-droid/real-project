from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.admin import router as admin_router
from app.api.routes import router as api_router
from app.core.config import ENABLE_SCHEDULER, FRONTEND_ORIGINS, validate_production_settings
from app.services.reminders import process_deadline_reminders

scheduler = BackgroundScheduler()


@asynccontextmanager
async def lifespan(_: FastAPI):
    validate_production_settings()
    if ENABLE_SCHEDULER:
        process_deadline_reminders()
        scheduler.add_job(process_deadline_reminders, "interval", hours=24, id="scheme-deadlines", replace_existing=True)
        scheduler.start()
    yield
    if scheduler.running:
        scheduler.shutdown(wait=False)


app = FastAPI(title="Claim What's Yours API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router)
app.include_router(admin_router)

@app.get("/")
def root():
    return {"status": "ok", "service": "Claim What's Yours API"}
