import json
import logging
import os
import re
import time

import requests
from flask import current_app

logger = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are an intelligent assistant for a platform that helps
Kenyan diaspora customers manage tasks back home. You process customer requests and return
ONLY a valid JSON object — no markdown, no explanation, no preamble, no code fences.

INTENTS — classify into exactly one of these strings:
  send_money | hire_service | verify_document | airport_transfer | check_status

ENTITY FIELDS — extract only what is present in the message:
  amount              (number, KES unless stated)
  recipient_name      (string)
  recipient_location  (string)
  service_type        (string)
  document_type       (string, e.g. "land title deed", "national ID", "degree certificate")
  plot_location       (string)
  urgency             (exactly one of: low | normal | high | critical — default "normal")
  preferred_date      (string)
  is_first_time_customer  (boolean — default false)
  notes               (string, any extra context)

STEPS — 3 to 5 fulfilment steps tailored to the intent:
  send_money:       verify identity → confirm recipient → initiate transfer → confirm receipt
  hire_service:     match provider → confirm schedule → brief provider → sign off
  verify_document:  receive document → run registry/institution check → cross-check records → issue report
  airport_transfer: confirm flight details → assign driver → send driver info → confirm pickup
  check_status:     look up task → return status to customer

MESSAGES — write all three:
  whatsapp:      conversational, 1-2 relevant emojis, natural line breaks, under 200 words
  email_subject: concise subject line including {{TASK_CODE}}
  email_body:    formal, structured paragraphs, includes {{TASK_CODE}}, professional sign-off
  sms:           HARD LIMIT 160 characters, task code {{TASK_CODE}} + key action, no emoji

RULES:
  - Respond with EXACTLY this JSON and nothing else — no markdown, no backticks, no preamble:
    {"intent":"...","entities":{...},"steps":["..."],"messages":{"whatsapp":"...","email_subject":"...","email_body":"...","sms":"..."}}
  - Default urgency to "normal" if not stated.
  - Never invent amounts, names, or dates not present in the message.
  - SMS MUST be 160 characters or fewer — count every character before responding.
  - Both email_body and sms must contain the literal string {{TASK_CODE}}.
"""


#  Retry with exponential backoff 
def _with_retry(fn, max_attempts=3, retryable_codes=(429, 500, 502, 503, 504)):
    """Retry transient failures: 1s → 2s → 4s backoff."""
    last_exc = None
    for attempt in range(max_attempts):
        try:
            return fn()
        except requests.exceptions.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else 0
            if status in retryable_codes:
                last_exc = exc
                wait = 2 ** attempt
                current_app.logger.warning(
                    f"Gemini returned {status}, retrying in {wait}s "
                    f"(attempt {attempt + 1}/{max_attempts})"
                )
                time.sleep(wait)
            else:
                raise   # 400, 401, 403 — don't retry
        except requests.exceptions.Timeout:
            last_exc = Exception("Gemini request timed out after 30s")
            time.sleep(2 ** attempt)
    raise last_exc


# JSON parser
def _find_json_object(text: str):
    """
    Extract the outermost {...} using brace-depth counting.
    Handles preamble text before the JSON object.
    More reliable than a non-greedy regex which stops at the first }.
    """
    start = text.find("{")
    if start == -1:
        return None
    depth, in_string, escape_next = 0, False, False
    for i, ch in enumerate(text[start:], start):
        if escape_next:
            escape_next = False
            continue
        if ch == "\\" and in_string:
            escape_next = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    return None


def _parse_json_response(raw: str) -> dict:
    """
    Parse Gemini's response into a dict.
    Four-layer defence against malformed output:
      1. Strip markdown fences
      2. Direct json.loads
      3. Brace-depth extraction (handles preamble text)
      4. Fix truncation by balancing braces
    """
    if not raw or not raw.strip():
        raise ValueError("Empty response from Gemini")

    # Layer 1: strip markdown fences
    cleaned = re.sub(r"```(?:json)?\s*", "", raw, flags=re.IGNORECASE)
    cleaned = cleaned.strip().rstrip("`").strip()

    # Layer 2: direct parse
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Layer 3: brace-depth extraction
    extracted = _find_json_object(cleaned)
    if extracted:
        try:
            result = json.loads(extracted)
            logger.warning("Recovered JSON using brace-depth extraction")
            return result
        except json.JSONDecodeError:
            pass

    # Layer 4: fix truncation
    try:
        fixed  = cleaned
        fixed += "}" * (fixed.count("{") - fixed.count("}"))
        fixed += "]" * (fixed.count("[") - fixed.count("]"))
        result = json.loads(fixed)
        if "intent" in result:
            logger.warning("Fixed truncated JSON by adding closing braces")
            return result
    except Exception:
        pass

    raise ValueError(
        f"Could not parse JSON from Gemini response.\n"
        f"First 400 chars: {raw[:400]}"
    )


def call_llm(user_message: str) -> dict:
    """
    Send user_message to Gemini and return parsed dict with keys:
    intent, entities, steps, messages
    """
    api_key = current_app.config.get("GEMINI_API_KEY", "")
    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY is not set. "
            "Get a free key at https://aistudio.google.com/apikey "
            "and add GEMINI_API_KEY=your-key to your .env file."
        )


    model = (
        current_app.config.get("GEMINI_MODEL")
        or os.getenv("GEMINI_MODEL", "gemini-flash-latest")
    )

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={api_key}"
    )

    payload = {
        "contents": [{
            "parts": [{"text": f"{SYSTEM_PROMPT}\n\nCustomer request: {user_message}"}]
        }],
        "generationConfig": {
            "temperature": 0.3,
            "maxOutputTokens": 10000,
            "responseMimeType": "application/json",
        },
    }

    def _do_request():
        resp = requests.post(url, json=payload, timeout=30)
        resp.raise_for_status()
        return resp

    resp    = _with_retry(_do_request)
    content = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
    return _parse_json_response(content)