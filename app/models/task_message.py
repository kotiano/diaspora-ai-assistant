from app import db


class TaskMessage(db.Model):
    __tablename__ = "task_messages"

    id      = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey("tasks.id"), nullable=False)
    channel = db.Column(db.String(20), nullable=False)    # whatsapp | email | sms
    subject = db.Column(db.String(200), nullable=True)    # email only
    content = db.Column(db.Text, nullable=False)

    task = db.relationship("Task", back_populates="messages")

    def to_dict(self):
        return {
            "channel": self.channel,
            "subject": self.subject,
            "content": self.content,
        }