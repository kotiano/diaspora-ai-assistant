import json

from app import db
from app.models import Task, TaskStep, TaskMessage, StatusHistory
from app.services.ai_service import call_llm
from app.services.risk_service import calculate_risk, assign_team


def process_new_request(user_message: str) -> Task:
    """
    Full pipeline: AI → risk → persist → return Task.
    Raises on AI or DB failure .
    """
    # AI extraction
    ai_result = call_llm(user_message)

    intent = ai_result.get("intent", "hire_service")
    entities = ai_result.get("entities", {})
    steps_text = ai_result.get("steps", [])
    messages_dict = ai_result.get("messages", {})

    # Risk scoring
    risk_score, risk_label = calculate_risk(intent, entities)

    # Team assignment
    team = assign_team(intent)

    # Create Task record
    task = Task(
        original_request=user_message,
        intent=intent,
        entities=json.dumps(entities),
        risk_score=risk_score,
        risk_label=risk_label,
        assigned_team=team,
        status="Pending",
    )
    db.session.add(task)
    db.session.flush()

    for i, step_text in enumerate(steps_text, start=1):
        step = TaskStep(
            task_id=task.id,
            step_number=i,
            description=step_text,
        )
        db.session.add(step)

    code = task.task_code

    whatsapp_msg = messages_dict.get("whatsapp", "")
    email_subject = messages_dict.get("email_subject", f"Task {code}")
    email_body = messages_dict.get("email_body", "")
    sms_msg = messages_dict.get("sms", "")

    for channel, content, subject in [
        ("whatsapp", whatsapp_msg.replace("{{TASK_CODE}}", code), None),
        ("email",    email_body.replace("{{TASK_CODE}}", code), email_subject),
        ("sms",      sms_msg.replace("{{TASK_CODE}}", code)[:160], None),
    ]:
        msg = TaskMessage(
            task_id=task.id,
            channel=channel,
            subject=subject,
            content=content,
        )
        db.session.add(msg)

    history = StatusHistory(
        task_id=task.id,
        old_status=None,
        new_status="Pending",
    )
    db.session.add(history)

    db.session.commit()
    return task


def update_task_status(task: Task, new_status: str) -> Task:
    """Change task status and record the transition."""
    valid_statuses = {"Pending", "In Progress", "Completed"}
    if new_status not in valid_statuses:
        raise ValueError(f"Invalid status: {new_status}")

    old_status = task.status
    task.status = new_status

    history = StatusHistory(
        task_id=task.id,
        old_status=old_status,
        new_status=new_status,
    )
    db.session.add(history)
    db.session.commit()
    return task