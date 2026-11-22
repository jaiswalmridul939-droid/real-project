from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.core.config import ADMIN_EMAIL, ADMIN_PASSWORD
from app.core import config as app_config
from app.main import app
from app.models import Base, Scheme


@pytest.fixture
def client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(engine)
    with TestingSession() as db:
        db.add(Scheme(name_en="Demo Farm Scheme", official_url="https://example.gov.in", source_name="Demo",
                      last_verified_date=date(2026, 11, 20), benefit_summary="Public program information"))
        db.commit()

    def override_get_db():
        with TestingSession() as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)


def test_health_and_scheme_listing(client):
    assert client.get("/api/health").json() == {"status": "ok"}
    response = client.get("/api/schemes")
    assert response.status_code == 200
    assert response.json()[0]["name_en"] == "Demo Farm Scheme"


def test_profile_extract_falls_back_to_manual_form(client):
    response = client.post("/api/profile/extract", json={"text": "I have 2 acres in Nashik Maharashtra, low income, bank account", "language": "en"})
    assert response.status_code == 200
    assert response.json()["mode"] == "manual"
    assert response.json()["profile"]["land_acres"] == 2
    assert response.json()["profile"]["district"] == "Nashik"
    assert response.json()["profile"]["has_bank_account"] is True


def test_twelve_digit_free_text_is_rejected(client):
    response = client.post("/api/profile/extract", json={"text": "My number is 123456789012", "language": "en"})
    assert response.status_code == 422


def test_twelve_digit_profile_field_is_rejected(client):
    response = client.post("/api/profile", json={"district": "123456789012"})
    assert response.status_code == 422


def test_profile_save_then_match_uses_rules_data(client):
    profile = client.post("/api/profile", json={"state": "Maharashtra", "occupation": "farmer"}).json()
    result = client.post("/api/match", json={"profile_id": profile["profile_id"]})
    assert result.status_code == 200
    assert result.json()["matches"][0]["status"] == "Maybe, needs more info"
    assert "Final eligibility" in result.json()["disclaimer"]


def test_admin_routes_require_authentication(client):
    assert client.get("/api/admin/schemes").status_code == 401


def test_production_configuration_rejects_demo_credentials(monkeypatch):
    monkeypatch.setattr(app_config, "APP_ENV", "production")
    monkeypatch.setattr(app_config, "JWT_SECRET", "change-me-before-deploying")
    monkeypatch.setattr(app_config, "ADMIN_PASSWORD", "demo-admin-change-me")
    monkeypatch.setattr(app_config, "FRONTEND_ORIGINS", ["http://localhost:3000"])
    monkeypatch.setattr(app_config, "DATABASE_URL", "postgresql+psycopg://postgres:postgres@db:5432/claimwhatsyours")
    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        app_config.validate_production_settings()


def test_production_configuration_accepts_unique_secrets_and_https_origin(monkeypatch):
    monkeypatch.setattr(app_config, "APP_ENV", "production")
    monkeypatch.setattr(app_config, "JWT_SECRET", "unique-production-jwt-secret-value-32")
    monkeypatch.setattr(app_config, "ADMIN_PASSWORD", "a-unique-admin-passphrase")
    monkeypatch.setattr(app_config, "FRONTEND_ORIGINS", ["https://claims.example.org"])
    monkeypatch.setattr(app_config, "DATABASE_URL", "postgresql+psycopg://claimapp:unique-database-password@db:5432/claimwhatsyours")
    app_config.validate_production_settings()


def test_admin_login_can_export_and_edit_rules(client):
    login = client.post("/api/admin/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    exported = client.get("/api/admin/export", headers=headers)
    assert exported.status_code == 200
    scheme_id = exported.json()["schemes"][0]["id"]
    rule = client.post(f"/api/admin/schemes/{scheme_id}/rules", headers=headers,
                       json={"field": "land_acres", "operator": "lte", "value_json": 5, "explanation_en": "Small plot"})
    assert rule.status_code == 200
    invalid = client.post(f"/api/admin/schemes/{scheme_id}/rules", headers=headers,
                          json={"field": "land_acres", "operator": "approx", "value_json": 5})
    assert invalid.status_code == 422


def test_admin_scheme_update_preserves_deadline(client):
    login = client.post("/api/admin/login", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    scheme_id = client.get("/api/admin/schemes", headers=headers).json()[0]["id"]
    update = {
        "name_en": "Demo Farm Scheme",
        "official_url": "https://example.gov.in",
        "source_name": "Demo",
        "last_verified_date": "2026-11-21",
        "deadline_date": "2027-01-15",
        "benefit_summary": "Public program information",
        "department": "Demo",
        "level": "central",
        "is_active": True,
    }
    response = client.put(f"/api/admin/schemes/{scheme_id}", headers=headers, json=update)
    assert response.status_code == 200
    updated = client.get("/api/admin/schemes", headers=headers).json()[0]
    assert updated["deadline_date"] == "2027-01-15"