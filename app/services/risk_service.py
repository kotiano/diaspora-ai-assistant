def calculate_risk(intent: str, entities: dict) -> tuple[int, str]:
    """
    Calculate risk score (0-100) and label for a task.
    """
    score = 0
    factors = []

    # BASE RISK
    base_scores = {
        "verify_document":  30,   # Highest due to land fraud prevalence
        "send_money":       25,
        "hire_service":     15,
        "airport_transfer": 12,
        "check_status":      5,
    }
    base = base_scores.get(intent, 10)
    score += base
    factors.append(f"Base risk for {intent}: +{base}")

    # URGENCY 
    urgency = str(entities.get("urgency") or "normal").lower().strip()
    urgency_scores = {"low": -5, "normal": 0, "high": 15, "critical": 30}
    urgency_delta = urgency_scores.get(urgency, 0)
    score += urgency_delta
    if urgency_delta != 0:
        factors.append(f"Urgency ({urgency}): {urgency_delta:+d}")

    # AMOUNT (send_money) 
    if intent == "send_money":
        try:
            amount = float(entities.get("amount") or 0)
        except (TypeError, ValueError):
            amount = 0

        if amount > 500_000:
            delta = 28
            reason = "Very high amount (>500k)"
        elif amount > 200_000:
            delta = 22
            reason = "High amount (>200k)"
        elif amount > 100_000:
            delta = 15
            reason = "Substantial amount"
        elif amount > 50_000:
            delta = 8
            reason = "Moderate amount"
        else:
            delta = 0
            reason = None

        if delta:
            score += delta
            factors.append(f"Amount risk ({reason}): +{delta}")

    # DOCUMENT TYPE 
    if intent == "verify_document":
        doc = str(entities.get("document_type") or "").lower()
        
        doc_risk_map = {
            ("land", "title", "plot", "deed"): 28,      # Most common fraud
            ("id", "passport", "national"):    15,
            ("degree", "certificate", "diploma"): 12,
            ("kra", "business", "company", "registration"): 14,
        }

        delta = 8  # default for unknown document
        reason = "unknown document type"

        for keywords, risk_value in doc_risk_map.items():
            if any(kw in doc for kw in keywords):
                delta = risk_value
                reason = f"{'_'.join(keywords[:2])} document"
                break

        score += delta
        factors.append(f"Document risk ({reason}): +{delta}")

    # CUSTOMER TRUST 
    is_first_time = entities.get("is_first_time_customer")
    if is_first_time is None:
        is_first_time = True
    elif isinstance(is_first_time, str):
        is_first_time = is_first_time.lower() not in ("false", "no", "0", "false")

    if is_first_time:
        score += 18
        factors.append("First-time customer: +18")
    else:
        score -= 12
        factors.append("Returning customer: -12")

    # COMPOUND / INTERACTION RISKS 
    if intent == "send_money" and urgency in ("high", "critical") and amount > 50_000:
        score += 15
        factors.append("Compound: Urgent + Large transfer (+15)")

    if intent == "verify_document" and is_first_time:
        score += 12
        factors.append("Compound: New customer + Document verification (+12)")

    if is_first_time and urgency == "critical":
        score += 10
        factors.append("Compound: New customer + Critical urgency (+10)")

    # Final capping
    score = max(0, min(100, int(score)))

    # Determine label
    if score <= 25:
        label = "low"
    elif score <= 50:
        label = "medium"
    elif score <= 75:
        label = "high"
    else:
        label = "critical"

    return score, label


def get_risk_factors(intent: str, entities: dict) -> list[str]:
    """
    Return a human-readable list of risk factors for a given task.
    """
    factors = []

    urgency = str(entities.get("urgency") or "normal").lower()
    is_first = entities.get("is_first_time_customer", True)
    if isinstance(is_first, str):
        is_first = is_first.lower() not in ("false", "no", "0")

    if intent == "verify_document":
        doc = str(entities.get("document_type") or "").lower()
        if any(w in doc for w in ("land", "title", "plot", "deed")):
            factors.append("Land title verification — highest fraud surface in Kenya")

    if intent == "send_money":
        try:
            amount = float(entities.get("amount") or 0)
        except (TypeError, ValueError):
            amount = 0
        if amount > 70_000:
            factors.append(f"Large transfer (KES {amount:,.0f}) — requires enhanced verification")
        if urgency in ("high", "critical") and amount > 20_000:
            factors.append("Urgent + large transfer — common advance-fee fraud pattern")

    if urgency == "critical":
        factors.append("Critical urgency — high-pressure requests are a manipulation tactic")

    if is_first:
        factors.append("First-time customer — no prior history to establish trust")

    if is_first and urgency == "critical":
        factors.append("New customer with critical urgency — social engineering pattern")

    return factors if factors else ["No specific risk factors identified"]


def assign_team(intent: str) -> str:
    """Map intent to the responsible internal team."""
    teams = {
        "send_money":       "Finance Team",
        "hire_service":     "Operations Team",
        "verify_document":  "Legal Team",
        "airport_transfer": "Logistics Team",
        "check_status":     "Customer Support",
    }
    return teams.get(intent, "General Support")