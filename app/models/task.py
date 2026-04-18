import json
import uuid
from datetime import datetime, timezone, timedelta

from app import db

EAT = timezone(timedelta(hours=3))


def _utcnow():
    return datetime.now(timezone.utc)


def _generate_task_code():
    """VG-XXXXXXXX — short enough for SMS, unique enough for lookup."""
    return f"VG-{uuid.uuid4().hex[:8].upper()}"

def _to_eat(dt):

    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(EAT).isoformat()


class Task(db.Model):
    __tablename__ = "tasks"

    id               = db.Column(db.Integer, primary_key=True)
    task_code        = db.Column(db.String(20), unique=True, nullable=False, default=_generate_task_code)
    original_request = db.Column(db.Text, nullable=False)
    intent           = db.Column(db.String(50), nullable=False)
    entities         = db.Column(db.Text, nullable=True)       # JSON string
    risk_score       = db.Column(db.Integer, nullable=False, default=0)
    risk_label       = db.Column(db.String(20), nullable=False, default="low")
    assigned_team    = db.Column(db.String(50), nullable=True)
    status           = db.Column(db.String(20), nullable=False, default="Pending")
    created_at       = db.Column(db.DateTime(timezone=True), default=_utcnow)
    updated_at       = db.Column(db.DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    steps          = db.relationship("TaskStep",      back_populates="task", cascade="all, delete-orphan", order_by="TaskStep.step_number")
    messages       = db.relationship("TaskMessage",   back_populates="task", cascade="all, delete-orphan")
    status_history = db.relationship("StatusHistory", back_populates="task", cascade="all, delete-orphan", order_by="StatusHistory.changed_at")

    @property
    def created_at_eat(self):
        return _to_eat(self.created_at)
    
    def _messages_dict(self):
        result = {}
        for m in self.messages:
            result[m.channel] = m.content
            if m.channel == "email" and m.subject:
                result["email_subject"] = m.subject
        return result

    def to_dict(self):

        return {
            "id":               self.id,
            "task_code":        self.task_code,
            "original_request": self.original_request,
            "intent":           self.intent,
            "entities":         json.loads(self.entities) if self.entities else {},
            "risk_score":       self.risk_score,
            "risk_label":       self.risk_label,
            "assigned_team":    self.assigned_team,
            "status":           self.status,
            "created_at":       _to_eat(self.created_at),
            "updated_at":       _to_eat(self.updated_at),
            "steps":            [s.to_dict() for s in self.steps],
            "messages":         self._messages_dict(),
            "status_history":   [h.to_dict() for h in self.status_history],
        }