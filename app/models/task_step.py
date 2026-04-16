from app import db


class TaskStep(db.Model):
    __tablename__ = "task_steps"

    id          = db.Column(db.Integer, primary_key=True)
    task_id     = db.Column(db.Integer, db.ForeignKey("tasks.id"), nullable=False)
    step_number = db.Column(db.Integer, nullable=False)
    description = db.Column(db.Text, nullable=False)
    is_complete = db.Column(db.Boolean, default=False)

    task = db.relationship("Task", back_populates="steps")

    def to_dict(self):
        return {
            "step_number": self.step_number,
            "description": self.description,
            "is_complete": self.is_complete,
        }