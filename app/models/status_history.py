from datetime import datetime, timezone, timedelta
from app import db


def _utcnow():
    return datetime.now(timezone.utc)


class StatusHistory(db.Model):
    __tablename__ = "status_history"

    id         = db.Column(db.Integer, primary_key=True)
    task_id    = db.Column(db.Integer, db.ForeignKey("tasks.id"), nullable=False)
    old_status = db.Column(db.String(20), nullable=True)
    new_status = db.Column(db.String(20), nullable=False)
    changed_at = db.Column(db.DateTime(timezone=True), default=_utcnow)

    task = db.relationship("Task", back_populates="status_history")

    def to_dict(self):
        # Convert UTC to East Africa Time (Kenya)
        changed_at_local = None
        if self.changed_at:
            eat = timezone(timedelta(hours=3))
            changed_at_local = self.changed_at.astimezone(eat).isoformat()

        return {
            "old_status": self.old_status,
            "new_status": self.new_status,
            "changed_at": changed_at_local,          # ← Now returns Kenya time
        }