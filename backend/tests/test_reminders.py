from datetime import date, timedelta

from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models import Application, Base, MockMessage, Reminder, Scheme, User
from app.services import reminders


def test_deadline_reminders_are_idempotent_and_mock_only(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    Base.metadata.create_all(engine)
    today = date(2026, 11, 21)
    with factory() as db:
        user = User(language="en")
        scheme = Scheme(name_en="Test scheme", official_url="https://example.gov.in", source_name="Test",
                        last_verified_date=today, deadline_date=today + timedelta(days=7))
        db.add_all([user, scheme])
        db.flush()
        db.add(Application(user_id=user.id, scheme_id=scheme.id))
        db.commit()

    monkeypatch.setattr(reminders, "SessionLocal", factory)
    reminders.process_deadline_reminders(today)
    reminders.process_deadline_reminders(today)
    with factory() as db:
        assert db.scalar(select(func.count(Reminder.id))) == 3
        assert db.scalar(select(func.count(MockMessage.id))) == 1
        assert db.scalar(select(MockMessage.channel)) == "mock-whatsapp"
    Base.metadata.drop_all(engine)