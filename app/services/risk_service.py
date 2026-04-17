def calculate_risk(intent: str, entities: dict) -> tuple[int, str]:
    """
    Calculate risk score for a task.

    Returns
    -------
    (score, label) where score is 0-100 and label is one of:
    'low' | 'medium' | 'high' | 'critical'
    """
    score = 0
    factors = []  

    # Base intent risk
    base_scores = {
        "verify_document":  25,   
        "send_money":       20,   
        "hire_service":     10,   
        "airport_transfer": 8,    
        "check_status":     0,    
    }
    base = base_scores.get(intent, 10)
    score += base
    factors.append(f"base({intent})=+{base}")

    # Urgency pressure risk
    urgency = str(entities.get("urgency") or "normal").lower().strip()
    urgency_scores = {
        "low":      -5,
        "normal":    0,
        "high":     15,
        "critical": 30,
    }
    urgency_delta = urgency_scores.get(urgency, 0)
    score += urgency_delta
    if urgency_delta != 0:
        factors.append(f"urgency({urgency})={urgency_delta:+d}")

    # Financial exposure (send_money only)
    amount = 0
    if intent == "send_money":
        try:
            amount = float(entities.get("amount") or 0)
        except (TypeError, ValueError):
            amount = 0

        if amount > 500_000:
            delta = 25    # above M-Pesa daily limit — unusual
            reason = ">500k"
        elif amount > 100_000:
            delta = 18    # substantial amount
            reason = ">70k"
        elif amount > 50_000:
            delta = 10   
            reason = ">20k"
        elif amount > 5_000:
            delta = 5    
            reason = ">5k"
        else:
            delta = 0
            reason = "small"

        score += delta
        if delta:
            factors.append(f"amount({reason})=+{delta}")

    # Document risk stratification 
    if intent == "verify_document":
        doc = str(entities.get("document_type") or "").lower()

        if any(w in doc for w in ("land", "title", "plot", "deed")):
            delta = 25    # land fraud: most common scam in Kenya
            reason = "land_title"
        elif any(w in doc for w in ("id", "passport", "national")):
            delta = 15    # identity fraud
            reason = "id_document"
        elif any(w in doc for w in ("degree", "certificate", "diploma", "transcript")):
            delta = 10    # academic fraud
            reason = "academic"
        elif any(w in doc for w in ("business", "kra", "company", "registration")):
            delta = 12    # business/tax docs: financial fraud risk
            reason = "business_doc"
        else:
            delta = 5     # unknown document type: flag for review
            reason = "unknown_doc"

        score += delta
        factors.append(f"doc_type({reason})=+{delta}")

    # Customer trust signal
    is_first = entities.get("is_first_time_customer")
    if is_first is None:
        is_first = True
    elif isinstance(is_first, str):
        is_first = is_first.lower() not in ("false", "no", "0")

    if is_first:
        score += 15
        factors.append("first_time=+15")
    else:
        score -= 10      # returning customer
        factors.append("returning=-10")

    # Compound risk penalties

    if intent == "send_money" and urgency in ("high", "critical") and amount > 20_000:
        compound = 15
        score += compound
        factors.append(f"compound(urgent+large_transfer)=+{compound}")


    if intent == "verify_document" and is_first:
        doc = str(entities.get("document_type") or "").lower()
        if any(w in doc for w in ("land", "title", "plot", "deed")):
            compound = 10
            score += compound
            factors.append(f"compound(new_customer+land_title)=+{compound}")


    if is_first and urgency == "critical":
        compound = 10
        score += compound
        factors.append(f"compound(new_customer+critical_urgency)=+{compound}")

    # Cap and label 
    score = max(0, min(score, 100))

    if score <= 20:
        label = "low"
    elif score <= 45:
        label = "medium"
    elif score <= 70:
        label = "high"
    else:
        label = "critical"

    return score, label


def get_risk_factors(intent: str, entities: dict) -> list[str]:
    """
    Return a human-readable list of risk factors for a given task.
    Used for debugging and could be surfaced in the admin UI.
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


def get_risk_factors(intent: str, entities: dict) -> list[str]:
    """
    Return a human-readable list of risk factors for a given task.
    Used for debugging and could be surfaced in the admin UI.
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