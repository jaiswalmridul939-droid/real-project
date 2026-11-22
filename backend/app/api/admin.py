from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.config import ADMIN_EMAIL, ADMIN_PASSWORD
from app.core.database import get_db
from app.core.security import create_access_token, hash_password, require_admin, verify_password
from app.models import Admin, Scheme, SchemeAuditLog, SchemeDocument, SchemeRule, SchemeStep
from app.schemas.api import AdminLogin, DocumentWrite, RuleWrite, SchemeWrite, StepWrite

router = APIRouter(prefix="/api/admin")


def _record_change(db: Session, scheme_id: int | None, email: str, action: str, changes: dict) -> None:
    db.add(SchemeAuditLog(scheme_id=scheme_id, changed_by=email, change_json={"action": action, "changes": changes}))


def _scheme_export(db: Session, scheme: Scheme) -> dict:
    from app.api.routes import _scheme_payload

    return _scheme_payload(db, scheme, include_content=True)


def _new_scheme(db: Session, payload: SchemeWrite) -> Scheme:
    scheme = Scheme(**payload.model_dump(), version=1)
    db.add(scheme)
    db.flush()
    return scheme


@router.post("/login")
def login(request: AdminLogin, db: Session = Depends(get_db)) -> dict:
    admin = db.scalar(select(Admin).where(Admin.email == request.email))
    if admin is None and request.email == ADMIN_EMAIL and request.password == ADMIN_PASSWORD:
        admin = Admin(email=ADMIN_EMAIL, password_hash=hash_password(ADMIN_PASSWORD))
        db.add(admin)
        db.commit()
    if admin is None or not verify_password(request.password, admin.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return {"access_token": create_access_token(admin.email), "token_type": "bearer"}


@router.get("/schemes")
def admin_schemes(db: Session = Depends(get_db), _: Admin = Depends(require_admin)) -> list[dict]:
    return [_scheme_export(db, item) for item in db.scalars(select(Scheme).order_by(Scheme.id))]


@router.post("/schemes")
def create_scheme(payload: SchemeWrite, db: Session = Depends(get_db), admin: Admin = Depends(require_admin)) -> dict:
    scheme = _new_scheme(db, payload)
    _record_change(db, scheme.id, admin.email, "create", payload.model_dump(mode="json"))
    db.commit()
    return {"id": scheme.id, "version": scheme.version}


@router.put("/schemes/{scheme_id}")
def update_scheme(scheme_id: int, payload: SchemeWrite, db: Session = Depends(get_db), admin: Admin = Depends(require_admin)) -> dict:
    scheme = db.get(Scheme, scheme_id)
    if scheme is None:
        raise HTTPException(status_code=404, detail="Scheme not found")
    changes = payload.model_dump(mode="json")
    for key, value in payload.model_dump().items():
        setattr(scheme, key, value)
    scheme.version += 1
    _record_change(db, scheme.id, admin.email, "update", changes)
    db.commit()
    return {"id": scheme.id, "version": scheme.version}


@router.delete("/schemes/{scheme_id}")
def disable_scheme(scheme_id: int, db: Session = Depends(get_db), admin: Admin = Depends(require_admin)) -> dict:
    scheme = db.get(Scheme, scheme_id)
    if scheme is None:
        raise HTTPException(status_code=404, detail="Scheme not found")
    scheme.is_active = False
    scheme.version += 1
    _record_change(db, scheme.id, admin.email, "disable", {"is_active": False})
    db.commit()
    return {"id": scheme.id, "is_active": scheme.is_active, "version": scheme.version}


@router.get("/schemes/{scheme_id}/rules")
def list_rules(scheme_id: int, db: Session = Depends(get_db), _: Admin = Depends(require_admin)) -> list[dict]:
    if db.get(Scheme, scheme_id) is None:
        raise HTTPException(status_code=404, detail="Scheme not found")
    return [{"id": row.id, "field": row.field, "operator": row.operator, "value_json": row.value_json,
             "weight": row.weight, "explanation_en": row.explanation_en,
             "explanation_mr": row.explanation_mr, "explanation_hi": row.explanation_hi}
            for row in db.scalars(select(SchemeRule).where(SchemeRule.scheme_id == scheme_id))]


@router.post("/schemes/{scheme_id}/rules")
def create_rule(scheme_id: int, payload: RuleWrite, db: Session = Depends(get_db), admin: Admin = Depends(require_admin)) -> dict:
    scheme = db.get(Scheme, scheme_id)
    if scheme is None:
        raise HTTPException(status_code=404, detail="Scheme not found")
    row = SchemeRule(scheme_id=scheme_id, **payload.model_dump())
    db.add(row)
    scheme.version += 1
    _record_change(db, scheme_id, admin.email, "add_rule", payload.model_dump(mode="json"))
    db.commit()
    return {"id": row.id, "scheme_version": scheme.version}


@router.put("/rules/{rule_id}")
def update_rule(rule_id: int, payload: RuleWrite, db: Session = Depends(get_db), admin: Admin = Depends(require_admin)) -> dict:
    row = db.get(SchemeRule, rule_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Rule not found")
    scheme = db.get(Scheme, row.scheme_id)
    for key, value in payload.model_dump().items():
        setattr(row, key, value)
    scheme.version += 1
    _record_change(db, scheme.id, admin.email, "update_rule", payload.model_dump(mode="json"))
    db.commit()
    return {"id": row.id, "scheme_version": scheme.version}


@router.delete("/rules/{rule_id}")
def delete_rule(rule_id: int, db: Session = Depends(get_db), admin: Admin = Depends(require_admin)) -> dict:
    row = db.get(SchemeRule, rule_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Rule not found")
    scheme = db.get(Scheme, row.scheme_id)
    _record_change(db, scheme.id, admin.email, "delete_rule", {"rule_id": rule_id})
    scheme.version += 1
    db.delete(row)
    db.commit()
    return {"deleted": True}


@router.get("/schemes/{scheme_id}/documents")
def list_documents(scheme_id: int, db: Session = Depends(get_db), _: Admin = Depends(require_admin)) -> list[dict]:
    if db.get(Scheme, scheme_id) is None:
        raise HTTPException(status_code=404, detail="Scheme not found")
    rows = db.scalars(select(SchemeDocument).where(SchemeDocument.scheme_id == scheme_id))
    return [{"id": row.id, "doc_name_en": row.doc_name_en, "doc_name_mr": row.doc_name_mr,
             "doc_name_hi": row.doc_name_hi, "where_to_get": row.where_to_get, "is_mandatory": row.is_mandatory} for row in rows]


@router.post("/schemes/{scheme_id}/documents")
def create_document(scheme_id: int, payload: DocumentWrite, db: Session = Depends(get_db), admin: Admin = Depends(require_admin)) -> dict:
    scheme = db.get(Scheme, scheme_id)
    if scheme is None:
        raise HTTPException(status_code=404, detail="Scheme not found")
    row = SchemeDocument(scheme_id=scheme_id, **payload.model_dump())
    db.add(row)
    scheme.version += 1
    _record_change(db, scheme_id, admin.email, "add_document", payload.model_dump(mode="json"))
    db.commit()
    return {"id": row.id, "scheme_version": scheme.version}


@router.put("/documents/{document_id}")
def update_document(document_id: int, payload: DocumentWrite, db: Session = Depends(get_db), admin: Admin = Depends(require_admin)) -> dict:
    row = db.get(SchemeDocument, document_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Document not found")
    scheme = db.get(Scheme, row.scheme_id)
    for key, value in payload.model_dump().items():
        setattr(row, key, value)
    scheme.version += 1
    _record_change(db, scheme.id, admin.email, "update_document", payload.model_dump(mode="json"))
    db.commit()
    return {"id": row.id, "scheme_version": scheme.version}


@router.delete("/documents/{document_id}")
def delete_document(document_id: int, db: Session = Depends(get_db), admin: Admin = Depends(require_admin)) -> dict:
    row = db.get(SchemeDocument, document_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Document not found")
    scheme = db.get(Scheme, row.scheme_id)
    _record_change(db, scheme.id, admin.email, "delete_document", {"document_id": document_id})
    scheme.version += 1
    db.delete(row)
    db.commit()
    return {"deleted": True}


@router.get("/schemes/{scheme_id}/steps")
def list_steps(scheme_id: int, db: Session = Depends(get_db), _: Admin = Depends(require_admin)) -> list[dict]:
    if db.get(Scheme, scheme_id) is None:
        raise HTTPException(status_code=404, detail="Scheme not found")
    rows = db.scalars(select(SchemeStep).where(SchemeStep.scheme_id == scheme_id).order_by(SchemeStep.step_no))
    return [{"id": row.id, "step_no": row.step_no, "text_en": row.text_en, "text_mr": row.text_mr,
             "text_hi": row.text_hi, "link_nullable": row.link_nullable} for row in rows]


@router.post("/schemes/{scheme_id}/steps")
def create_step(scheme_id: int, payload: StepWrite, db: Session = Depends(get_db), admin: Admin = Depends(require_admin)) -> dict:
    scheme = db.get(Scheme, scheme_id)
    if scheme is None:
        raise HTTPException(status_code=404, detail="Scheme not found")
    row = SchemeStep(scheme_id=scheme_id, **payload.model_dump())
    db.add(row)
    scheme.version += 1
    _record_change(db, scheme_id, admin.email, "add_step", payload.model_dump(mode="json"))
    db.commit()
    return {"id": row.id, "scheme_version": scheme.version}


@router.put("/steps/{step_id}")
def update_step(step_id: int, payload: StepWrite, db: Session = Depends(get_db), admin: Admin = Depends(require_admin)) -> dict:
    row = db.get(SchemeStep, step_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Step not found")
    scheme = db.get(Scheme, row.scheme_id)
    for key, value in payload.model_dump().items():
        setattr(row, key, value)
    scheme.version += 1
    _record_change(db, scheme.id, admin.email, "update_step", payload.model_dump(mode="json"))
    db.commit()
    return {"id": row.id, "scheme_version": scheme.version}


@router.delete("/steps/{step_id}")
def delete_step(step_id: int, db: Session = Depends(get_db), admin: Admin = Depends(require_admin)) -> dict:
    row = db.get(SchemeStep, step_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Step not found")
    scheme = db.get(Scheme, row.scheme_id)
    _record_change(db, scheme.id, admin.email, "delete_step", {"step_id": step_id})
    scheme.version += 1
    db.delete(row)
    db.commit()
    return {"deleted": True}


@router.get("/audit")
def audit_log(db: Session = Depends(get_db), _: Admin = Depends(require_admin)) -> list[dict]:
    rows = db.scalars(select(SchemeAuditLog).order_by(SchemeAuditLog.created_at.desc()))
    return [{"id": row.id, "scheme_id": row.scheme_id, "changed_by": row.changed_by,
             "change_json": row.change_json, "created_at": row.created_at.isoformat() if row.created_at else None} for row in rows]


@router.get("/export")
def export_schemes(db: Session = Depends(get_db), _: Admin = Depends(require_admin)) -> dict:
    return {"schemes": [_scheme_export(db, row) for row in db.scalars(select(Scheme).order_by(Scheme.id))]}


@router.post("/import")
def import_schemes(payload: dict, db: Session = Depends(get_db), admin: Admin = Depends(require_admin)) -> dict:
    items = payload.get("schemes")
    if not isinstance(items, list):
        raise HTTPException(status_code=422, detail="Expected a schemes array")
    imported = 0
    for item in items:
        try:
            scheme_data = SchemeWrite.model_validate(item)
        except Exception as error:
            raise HTTPException(status_code=422, detail=f"Invalid scheme import: {error}")
        scheme = db.scalar(select(Scheme).where(Scheme.official_url == scheme_data.official_url))
        if scheme is None:
            scheme = _new_scheme(db, scheme_data)
        else:
            for key, value in scheme_data.model_dump().items():
                setattr(scheme, key, value)
            scheme.version += 1
            db.execute(delete(SchemeRule).where(SchemeRule.scheme_id == scheme.id))
            db.execute(delete(SchemeDocument).where(SchemeDocument.scheme_id == scheme.id))
            db.execute(delete(SchemeStep).where(SchemeStep.scheme_id == scheme.id))
        for rule in item.get("rules", []):
            db.add(SchemeRule(scheme_id=scheme.id, **RuleWrite.model_validate(rule).model_dump()))
        for document in item.get("documents", []):
            db.add(SchemeDocument(scheme_id=scheme.id, **DocumentWrite.model_validate(document).model_dump()))
        for step in item.get("steps", []):
            db.add(SchemeStep(scheme_id=scheme.id, **StepWrite.model_validate(step).model_dump()))
        _record_change(db, scheme.id, admin.email, "import", {"official_url": scheme.official_url, "version": scheme.version})
        imported += 1
    db.commit()
    return {"imported": imported}