from flask import Blueprint, jsonify, request

from app.models import Task
from app.services.task_service import process_new_request, update_task_status

api_bp = Blueprint("api", __name__)


def _error(msg, code=400):
    return jsonify({"error": msg}), code


@api_bp.route("/tasks", methods=["POST"])
def create_task():
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()

    if not message:
        return _error("message is required")
    if len(message) > 1000:
        return _error("message too long (max 1000 characters)")

    try:
        task = process_new_request(message)
    except ValueError as exc:
        return _error(str(exc), 422)
    except Exception as exc:
        # return a safe message to the client
        import traceback
        traceback.print_exc()
        return _error(f"AI processing failed: {str(exc)}", 500)

    return jsonify(task.to_dict()), 201



@api_bp.route("/tasks", methods=["GET"])
def list_tasks():
    tasks = Task.query.order_by(Task.created_at.desc()).all()
    return jsonify([t.to_dict() for t in tasks])



@api_bp.route("/tasks/<int:task_id>", methods=["GET"])
def get_task(task_id):
    task = Task.query.get_or_404(task_id)
    return jsonify(task.to_dict())



@api_bp.route("/tasks/<int:task_id>", methods=["PATCH"])
def patch_task(task_id):
    task = Task.query.get_or_404(task_id)
    data = request.get_json(silent=True) or {}
    new_status = data.get("status", "").strip()

    if not new_status:
        return _error("status field is required")

    try:
        task = update_task_status(task, new_status)
    except ValueError as exc:
        return _error(str(exc))

    return jsonify(task.to_dict())