from datetime import date, timedelta

from sqlalchemy import select

from app.core.database import SessionLocal
from app.models import Application, MockMessage, Reminder, Scheme


def process_deadline_reminders(today: date | None = None) -> None:
    today = today or date.today()
    with SessionLocal() as db:
        applications = db.scalars(select(Application).where(Application.status.notin_(["Approved", "Rejected"]))).all()
        for application in applications:
            scheme = db.get(Scheme, application.scheme_id)
            if scheme is None or scheme.deadline_date is None:
                continue
            for days_before in (7, 3, 1):
                remind_on = scheme.deadline_date - timedelta(days=days_before)
                if remind_on < today:
                    continue
                existing = db.scalar(select(Reminder.id).where(
                    Reminder.application_id == application.id,
                    Reminder.remind_on == remind_on,
                ).limit(1))
                if existing is None:
                    db.add(Reminder(
                        user_id=application.user_id,
                        application_id=application.id,
                        scheme_id=scheme.id,
                        remind_on=remind_on,
                        message=f"{scheme.name_en}: deadline in {days_before} day(s). Check the official source for current details.",
                    ))

        due_reminders = db.scalars(select(Reminder).where(
            Reminder.sent_flag.is_(False), Reminder.remind_on <= today,
        )).all()
        for reminder in due_reminders:
            db.add(MockMessage(user_id=reminder.user_id, channel="mock-whatsapp", body=reminder.message))
            reminder.sent_flag = True
        db.commit()