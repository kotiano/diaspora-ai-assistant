from flask import Blueprint, render_template
from app.models import Task

tasks_bp = Blueprint("tasks", __name__)


@tasks_bp.route("/")
def dashboard():
    tasks = Task.query.order_by(Task.created_at.desc()).all()
    return render_template("dashboard.html", tasks=tasks)