import json
import re
from datetime import date

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import CLAUDE_API_KEY, CLAUDE_MODEL
from app.core.database import get_db
from app.models import (
    Application,
    DocumentChecklist,
    Match,
    MockMessage,
    Profile,
    Reminder,
    Scheme,
    SchemeDocument,
    SchemeRule,
    SchemeStep,
    User,
)
from app.schemas.api import (
    ApplicationCreate,
    ApplicationUpdate,
    ChecklistUpdate,
    ProfileCreate,
    ProfileExtractRequest,
    ProfileFields,
    ReminderCreate,
)
from app.services.rules_engine import evaluate_rules

router = APIRouter(prefix="/api")
DISCLAIMER = "This is an estimate. Final eligibility is decided by the official authority."


def _profile_dict(profile: Profile) -> dict:
    return {field: getattr(profile, field) for field in ProfileFields.model_fields}


def _scheme_payload(db: Session, scheme: Scheme, include_content: bool = False) -> dict:
    result = {
        "id": scheme.id,
        "name_en": scheme.name_en,
        "name_mr": scheme.name_mr,
        "name_hi": scheme.name_hi,
        "description_en": scheme.description_en,
        "description_mr": scheme.description_mr,
        "description_hi": scheme.description_hi,
        "department": scheme.department,
        "level": scheme.level,
        "benefit_summary": scheme.benefit_summary,
        "official_url": scheme.official_url,
        "source_name": scheme.source_name,
        "last_verified_date": scheme.last_verified_date.isoformat(),
        "is_outdated": (date.today() - scheme.last_verified_date).days > 90,
        "deadline_date": scheme.deadline_date.isoformat() if scheme.deadline_date else None,
        "is_active": scheme.is_active,
        "version": scheme.version,
    }
    if include_content:
        result["rules"] = [
            {"id": rule.id, "field": rule.field, "operator": rule.operator, "value_json": rule.value_json,
             "weight": rule.weight, "explanation_en": rule.explanation_en,
             "explanation_mr": rule.explanation_mr, "explanation_hi": rule.explanation_hi}
            for rule in db.scalars(select(SchemeRule).where(SchemeRule.scheme_id == scheme.id))
        ]
        result["documents"] = [
            {"id": doc.id, "doc_name_en": doc.doc_name_en, "doc_name_mr": doc.doc_name_mr,
             "doc_name_hi": doc.doc_name_hi, "where_to_get": doc.where_to_get,
             "is_mandatory": doc.is_mandatory}
            for doc in db.scalars(select(SchemeDocument).where(SchemeDocument.scheme_id == scheme.id))
        ]
        result["steps"] = [
            {"id": step.id, "step_no": step.step_no, "text_en": step.text_en, "text_mr": step.text_mr,
             "text_hi": step.text_hi, "link_nullable": step.link_nullable}
            for step in db.scalars(select(SchemeStep).where(SchemeStep.scheme_id == scheme.id).order_by(SchemeStep.step_no))
        ]
    return result


def _missing_fields(profile: ProfileFields) -> list[str]:
    fields = profile.model_dump()
    priority = ["district", "land_acres", "land_ownership", "has_bank_account", "category"]
    return [field for field in priority if fields.get(field) is None][:3]


def _manual_extract(text: str) -> ProfileFields:
    values = {}
    if re.search(r"\b(maharashtra|महाराष्ट्र|महाराष्ट्रात)\b", text, re.IGNORECASE):
        values["state"] = "Maharashtra"
    if re.search(r"\b(farmer|farming|sheti|किसान|शेतकरी)\b", text, re.IGNORECASE):
        values["occupation"] = "farmer"
    for district in ("Nashik", "Pune", "Nanded", "Nagpur", "Gadchiroli", "Solapur"):
        if re.search(rf"\b{district}\b", text, re.IGNORECASE):
            values["district"] = district
            values["state"] = "Maharashtra"
            break
    acreage = re.search(r"(\d+(?:\.\d+)?)\s*(?:acre|acres|एकर)", text, re.IGNORECASE)
    if acreage:
        values["land_acres"] = float(acreage.group(1))
    if re.search(r"\b(bank account|bank khata|बँक खाते|बैंक खाता)\b", text, re.IGNORECASE):
        values["has_bank_account"] = True
    elif re.search(r"\b(no bank account|without a bank account|बँक खाते नाही|बैंक खाता नहीं)\b", text, re.IGNORECASE):
        values["has_bank_account"] = False
    if re.search(r"\b(low income|income is low|कम आय|उत्पन्न कमी|उत्पन्न कमी आहे)\b", text, re.IGNORECASE):
        values["income_band"] = "low"
    if re.search(r"\b(tenant|rented land|भाडे तत्त्वावर|किराये की जमीन)\b", text, re.IGNORECASE):
        values["land_ownership"] = "tenant"
    elif re.search(r"\b(landless|no land|भूमिहीन|जमीन नाही)\b", text, re.IGNORECASE):
        values["land_ownership"] = "landless"
    elif re.search(r"\b(own land|my land|मेरी जमीन|माझी जमीन)\b", text, re.IGNORECASE):
        values["land_ownership"] = "owner"
    return ProfileFields(**values)


async def _claude_extract(text: str, language: str) -> ProfileFields | None:
    if not CLAUDE_API_KEY:
        return None
    prompt = (
        "Extract only profile facts explicitly stated by the user. Never infer eligibility. "
        "Return one JSON object with keys age, gender, state, district, land_acres, "
        "land_ownership (owner/tenant/landless), income_band, category (General/OBC/SC/ST), "
        "has_bank_account, is_woman, crops (array), family_size, occupation. Use null when unknown. "
        "Do not return or retain identity numbers or other sensitive identifiers. "
        f"Output language context: {language}. User text: {text}"
    )
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": CLAUDE_API_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"},
                json={"model": CLAUDE_MODEL, "max_tokens": 500,
                      "system": "You extract structured profile fields only. Return JSON, never eligibility decisions.",
                      "messages": [{"role": "user", "content": prompt}]},
            )
            response.raise_for_status()
            content = response.json()["content"][0]["text"]
        match = re.search(r"\{.*\}", content, re.DOTALL)
        return ProfileFields.model_validate(json.loads(match.group(0))) if match else None
    except (httpx.HTTPError, KeyError, ValueError, TypeError):
        return None


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}


@router.post("/profile/extract")
async def extract_profile(request: ProfileExtractRequest) -> dict:
    extracted = await _claude_extract(request.text, request.language)
    mode = "ai" if extracted is not None else "manual"
    if extracted is None:
        extracted = _manual_extract(request.text)
    return {"profile": extracted.model_dump(), "missing_fields": _missing_fields(extracted), "mode": mode}


@router.post("/profile")
def save_profile(request: ProfileCreate, db: Session = Depends(get_db)) -> dict:
    values = request.model_dump(exclude={"user_id", "raw_text", "language"})
    user = db.get(User, request.user_id) if request.user_id else None
    if request.user_id and user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if user is None:
        user = User(language=request.language)
        db.add(user)
        db.flush()
    profile = Profile(user_id=user.id, raw_text=request.raw_text, **values)
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return {"user_id": user.id, "profile_id": profile.id, "profile": _profile_dict(profile)}


@router.get("/schemes")
def list_schemes(db: Session = Depends(get_db)) -> list[dict]:
    schemes = db.scalars(select(Scheme).where(Scheme.is_active.is_(True)).order_by(Scheme.name_en)).all()
    return [_scheme_payload(db, scheme) for scheme in schemes]


@router.get("/schemes/{scheme_id}")
def get_scheme(scheme_id: int, db: Session = Depends(get_db)) -> dict:
    scheme = db.get(Scheme, scheme_id)
    if scheme is None or not scheme.is_active:
        raise HTTPException(status_code=404, detail="Scheme not found")
    return _scheme_payload(db, scheme, include_content=True)


@router.post("/match")
def match_schemes(payload: dict, db: Session = Depends(get_db)) -> dict:
    try:
        profile_id = int(payload["profile_id"])
    except (KeyError, TypeError, ValueError):
        raise HTTPException(status_code=422, detail="profile_id is required")
    profile = db.get(Profile, profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    db.execute(delete(Match).where(Match.profile_id == profile_id))
    user = db.get(User, profile.user_id) if profile.user_id else None
    language = user.language if user and user.language in {"en", "hi", "mr"} else "en"
    results = []
    schemes = db.scalars(select(Scheme).where(Scheme.is_active.is_(True))).all()
    for scheme in schemes:
        rules = db.scalars(select(SchemeRule).where(SchemeRule.scheme_id == scheme.id)).all()
        evaluation = evaluate_rules(_profile_dict(profile), rules, language)
        db.add(Match(profile_id=profile.id, scheme_id=scheme.id, status=evaluation["status"], reasoning_json=evaluation["reasoning"]))
        results.append({"scheme": _scheme_payload(db, scheme), **evaluation, "disclaimer": DISCLAIMER})
    db.commit()
    results.sort(key=lambda result: ["Likely eligible", "Maybe, needs more info", "Likely not eligible"].index(result["status"]))
    return {"profile_id": profile.id, "matches": results, "disclaimer": DISCLAIMER}


@router.get("/checklist")
def get_checklist(user_id: int, db: Session = Depends(get_db)) -> list[dict]:
    profile = db.scalar(select(Profile).where(Profile.user_id == user_id).order_by(Profile.id.desc()).limit(1))
    scheme_ids = set()
    if profile:
        scheme_ids = set(db.scalars(select(Match.scheme_id).where(
            Match.profile_id == profile.id,
            Match.status.in_(["Likely eligible", "Maybe, needs more info"]),
        )).all())
    documents = {}
    for document in db.scalars(select(SchemeDocument).where(SchemeDocument.scheme_id.in_(scheme_ids) if scheme_ids else False)):
        entry = documents.setdefault(document.doc_name_en.casefold(), {
            "doc_name": document.doc_name_en, "where_to_get": document.where_to_get, "scheme_count": 0,
        })
        entry["scheme_count"] += 1
    stored = {item.doc_name.casefold(): item.is_ready for item in db.scalars(select(DocumentChecklist).where(DocumentChecklist.user_id == user_id))}
    return [{**item, "is_ready": stored.get(key, False)} for key, item in documents.items()]


@router.post("/checklist")
def update_checklist(request: ChecklistUpdate, db: Session = Depends(get_db)) -> dict:
    item = db.scalar(select(DocumentChecklist).where(
        DocumentChecklist.user_id == request.user_id,
        DocumentChecklist.doc_name == request.doc_name,
    ))
    if item is None:
        item = DocumentChecklist(user_id=request.user_id, doc_name=request.doc_name, is_ready=request.is_ready)
        db.add(item)
    else:
        item.is_ready = request.is_ready
    db.commit()
    return {"user_id": item.user_id, "doc_name": item.doc_name, "is_ready": item.is_ready}


@router.post("/applications")
def create_application(request: ApplicationCreate, db: Session = Depends(get_db)) -> dict:
    if db.get(User, request.user_id) is None or db.get(Scheme, request.scheme_id) is None:
        raise HTTPException(status_code=404, detail="User or scheme not found")
    application = Application(**request.model_dump())
    db.add(application)
    db.commit()
    db.refresh(application)
    return {"id": application.id, "user_id": application.user_id, "scheme_id": application.scheme_id,
            "status": application.status, "notes": application.notes}


@router.patch("/applications/{application_id}")
def update_application(application_id: int, request: ApplicationUpdate, db: Session = Depends(get_db)) -> dict:
    application = db.get(Application, application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found")
    for key, value in request.model_dump(exclude_unset=True).items():
        setattr(application, key, value)
    db.commit()
    db.refresh(application)
    return {"id": application.id, "status": application.status, "notes": application.notes,
            "applied_on": application.applied_on.isoformat() if application.applied_on else None}


@router.get("/reminders")
def get_reminders(user_id: int, db: Session = Depends(get_db)) -> list[dict]:
    reminders = db.scalars(select(Reminder).where(Reminder.user_id == user_id).order_by(Reminder.remind_on)).all()
    return [{"id": item.id, "scheme_id": item.scheme_id, "application_id": item.application_id,
             "remind_on": item.remind_on.isoformat(), "message": item.message, "sent_flag": item.sent_flag}
            for item in reminders]


@router.post("/reminders")
def create_reminder(request: ReminderCreate, db: Session = Depends(get_db)) -> dict:
    if db.get(User, request.user_id) is None or db.get(Scheme, request.scheme_id) is None:
        raise HTTPException(status_code=404, detail="User or scheme not found")
    reminder = Reminder(**request.model_dump())
    db.add(reminder)
    db.commit()
    db.refresh(reminder)
    return {"id": reminder.id, "remind_on": reminder.remind_on.isoformat(), "message": reminder.message}


@router.get("/dashboard")
def dashboard(user_id: int, db: Session = Depends(get_db)) -> dict:
    today = date.today()
    applications = db.scalars(select(Application).where(Application.user_id == user_id)).all()
    application_rows = []
    upcoming = []
    for application in applications:
        scheme = db.get(Scheme, application.scheme_id)
        if scheme is None:
            continue
        application_rows.append({"id": application.id, "scheme_id": scheme.id, "scheme_name": scheme.name_en, "status": application.status})
        if scheme.deadline_date and scheme.deadline_date >= today:
            days_left = (scheme.deadline_date - today).days
            upcoming.append({"scheme_id": scheme.id, "scheme_name": scheme.name_en, "deadline_date": scheme.deadline_date.isoformat(), "days_left": days_left, "urgent": days_left < 7})
    due_count = len(db.scalars(select(Reminder).where(Reminder.user_id == user_id, Reminder.sent_flag.is_(False), Reminder.remind_on <= today)).all())
    return {"applications": application_rows, "upcoming_deadlines": sorted(upcoming, key=lambda item: item["days_left"]),
            "checklist": get_checklist(user_id, db), "notification_count": due_count}


@router.get("/outbox")
def outbox(user_id: int | None = None, db: Session = Depends(get_db)) -> list[dict]:
    query = select(MockMessage).order_by(MockMessage.created_at.desc())
    if user_id is not None:
        query = query.where(MockMessage.user_id == user_id)
    return [{"id": item.id, "channel": item.channel, "body": item.body,
             "created_at": item.created_at.isoformat() if item.created_at else None}
            for item in db.scalars(query)]


@router.delete("/users/{user_id}")
def delete_user_data(user_id: int, db: Session = Depends(get_db)) -> dict:
    if db.get(User, user_id) is None:
        raise HTTPException(status_code=404, detail="User not found")
    profile_ids = select(Profile.id).where(Profile.user_id == user_id)
    db.execute(delete(Match).where(Match.profile_id.in_(profile_ids)))
    db.execute(delete(Reminder).where(Reminder.user_id == user_id))
    db.execute(delete(DocumentChecklist).where(DocumentChecklist.user_id == user_id))
    db.execute(delete(Application).where(Application.user_id == user_id))
    db.execute(delete(MockMessage).where(MockMessage.user_id == user_id))
    db.execute(delete(Profile).where(Profile.user_id == user_id))
    db.execute(delete(User).where(User.id == user_id))
    db.commit()
    return {"deleted": True}