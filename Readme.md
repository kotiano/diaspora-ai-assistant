# AI-Powered Diaspora Services Assistant

A Flask web application that helps Kenyan diaspora customers initiate and track home services through a conversational AI interface. Customers describe what they need in plain English — the system classifies the intent, scores the risk, generates fulfilment steps, assigns the task to the right team, and produces confirmation messages in three formats.

**Live demo:** https://diaspora-ai-assistant.onrender.com

---

## Table of Contents
1. [Quick Start](#quick-start)
2. [Project Structure](#project-structure)
3. [Features](#features)
4. [Risk Scoring Logic](#risk-scoring-logic)
5. [API Reference](#api-reference)
6. [Database Schema](#database-schema)
7. [Deployment on Render](#deployment-on-render)
8. [Decisions I Made and Why](#decisions-i-made-and-why)

---

## Quick Start

### Prerequisites
- Python 3.11 or higher
- A free Gemini API key — get one at https://aistudio.google.com/apikey

### 1. Clone and install

```bash
git clone https://github.com/kotiano/diaspora-ai-assistant.git
cd diaspora-ai-assistant

python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env`:

```env
FLASK_ENV=development
SECRET_KEY=any-random-string
GEMINI_API_KEY=your-key-from-aistudio
GEMINI_MODEL=gemini-flash-latest
DATABASE_URI=sqlite:///instance/diaspora.db
```

### 3. Seed the database with sample data

```bash
python3 seed_data.py
```

This creates the database with 6 sample tasks covering all five intents and writes `diaspora_seed.sql` for submission.

### 4. Run

```bash
python3 main.py
```

Open http://localhost:5000

### Using Docker

```bash
docker build -t diaspora-ai-assistant .
docker run -p 5000:5000 --env-file .env -v "$(pwd)/instance:/app/instance" diaspora-ai-assistant
```

---

## Project Structure

```
diaspora-ai-assistant/
├── main.py                      ← Entry point: python3 main.py
├── config.py                    ← Dev / Test / Prod config classes
├── seed_data.py                 ← Seeds DB + generates diaspora_seed.sql
├── requirements.txt
├── Dockerfile
├── .env.example
├── diaspora_seed.sql               ← SQL schema + 6 complete sample tasks
│
└── app/
    ├── __init__.py              ← App factory
    │
    ├── models/
    │   ├── __init__.py          ← Exports all models
    │   ├── task.py              ← Task — central record
    │   ├── task_step.py         ← TaskStep — fulfilment steps
    │   ├── task_message.py      ← TaskMessage — one row per channel
    │   └── status_history.py   ← StatusHistory — audit log
    │
    ├── routes/
    │   ├── home.py              ← GET / (homepage)
    │   ├── tasks.py             ← GET /tasks (dashboard)
    │   └── api.py               ← REST JSON API
    │
    ├── services/
    │   ├── ai_service.py        ← Gemini integration + system prompt
    │   ├── risk_service.py      ← Risk scoring engine
    │   └── task_service.py      ← Orchestration layer
    │
    ├── templates/
    │   ├── base.html
    │   ├── index.html           ← New request page
    │   └── dashboard.html       ← Task dashboard
    │
    └── static/
        ├── css/main.css
        └── js/
            ├── utils.js         ← DiasporaUtils namespace
            ├── request.js       ← Request form logic
            └── dashboard.js     ← Dashboard interactions
```

---

## Features

| Feature | Detail |
|---|---|
| Natural language input | Customer types in plain English; example pills for quick testing |
| AI intent extraction | Gemini classifies into an intent and extracts structured entities |
| Risk scoring | Factor-based engine with compound penalties — 0–100 score + label |
| Step generation | AI generates 3–5 request-specific fulfilment steps |
| Three-format messages | WhatsApp, email (with subject line), SMS (≤160 chars) |
| Employee assignment | Intent → team mapping stored and visible in UI |
| Task dashboard | Filter by status, relative timestamps in EAT, detail modal |
| Status updates | PATCH with toast feedback; full audit trail in DB |
| Copy buttons | One-click copy on all message formats |

---

## Risk Scoring Logic

The scoring engine uses a **factor-based model with compound penalties**. Individual factors add a base score; dangerous *combinations* add further penalties on top. This mirrors how a real compliance officer thinks — not just individual signals but patterns.

### Base intent risk

| Intent | Score | Reason |
|---|---|---|
| `verify_document` | 30 | Land fraud in Kenya is irreversible — wrong verification loses a customer's life savings |
| `send_money` | 25 | Financial transaction; amount and recipient trust determine real exposure |
| `hire_service` | 15 | Lower financial exposure; easier to cancel |
| `airport_transfer` | 12 | Logistics; main risk is scheduling failure |
| `check_status` | 5 | Read-only; no financial or legal exposure |

### Urgency pressure

| Urgency | Delta | Reason |
|---|---|---|
| `critical` | +30 | Extreme urgency is the primary social engineering trigger — "my mother is in hospital, send now" is a textbook fraud pattern |
| `high` | +15 | Elevated pressure reduces careful verification |
| `normal` | 0 | Standard |
| `low` | -5 | Patient customer; less pressure to skip steps |

The penalty is **non-linear** — critical (+30) is double high (+15) because the jump from high to critical urgency is a qualitative shift in fraud risk, not just quantitative.

### Financial exposure (send_money only)

| Amount | Delta | Reason |
|---|---|---|
| > KES 500,000 | +28 | Above M-Pesa daily send limit — unusual for personal diaspora transfers |
| > KES 200,000 | +22 | Substantial; requires enhanced verification |
| > KES 100,000 | +15 | Mid-range; standard KYC warranted |
| > KES 50,000 | +8 | Small but trackable |

Thresholds mirror Kenya's M-Pesa and banking regulatory limits, not arbitrary numbers.

### Document type (verify_document only)

| Document | Delta | Reason |
|---|---|---|
| Land title / deed / plot | +28 | Most common high-value fraud in Kenya; Karen, Kiambu, Westlands are hotspots |
| National ID / passport | +15 | Identity fraud precedes financial fraud |
| Degree / certificate | +12 | Academic fraud for UK/AU job applications is rising |
| Business / KRA | +14 | Tax and business document fraud |
| Unknown document | +8 | Flag for manual review |

### Customer trust

| Signal | Delta | Reason |
|---|---|---|
| First-time customer | +18 | No prior history — we cannot assess intent |
| Returning customer | -12 | Prior successful transaction reduces fraud probability |

### Compound risk penalties

These fire only when dangerous **combinations** appear — patterns seen in actual diaspora fraud:

| Pattern | Extra | Reason |
|---|---|---|
| Urgent + large transfer | +15 | Classic advance-fee fraud: create pressure, bypass verification |
| New customer + land title | +12 | Most common Nairobi land scam setup |
| New customer + critical urgency (any) | +10 | Social engineering: strangers who are urgently insistent is a red flag |

### Score → Label

| Score | Label | Action |
|---|---|---|
| 0–25 | low | Standard processing |
| 26–50 | medium | Routine KYC before proceeding |
| 51–75 | high | Senior staff review; call the customer |
| 76–100 | critical | Hold for manual approval |

---

## API Reference

### POST /api/tasks
Submit a new customer request.

**Body:** `{ "message": "I need to send KES 15,000 to my mother in Kisumu" }`

**Response 201:**
```json
{
  "task_code": "VG-3F8A1B2C",
  "intent": "send_money",
  "entities": { "amount": 15000, "recipient_location": "Kisumu", "urgency": "normal" },
  "risk_score": 35,
  "risk_label": "medium",
  "assigned_team": "Finance Team",
  "status": "Pending",
  "steps": [...],
  "messages": { "whatsapp": "...", "email": "...", "email_subject": "...", "sms": "..." },
  "created_at": "2026-04-18T14:00:00+03:00"
}
```

### GET /api/tasks — list all tasks (newest first)

### GET /api/tasks/:id — single task with full detail

### PATCH /api/tasks/:id — update status
**Body:** `{ "status": "In Progress" }`
Valid: `Pending` | `In Progress` | `Completed`

---

## Database Schema

```sql
tasks           -- central record: intent, entities (JSON), risk, status, team
task_steps      -- 1:many from tasks; ordered by step_number
task_messages   -- 1:many from tasks; one row per channel (whatsapp/email/sms)
status_history  -- append-only audit log; every status change with timestamp
```

Four normalised tables. This structure answers queries like:
- "All critical-risk tasks assigned to Legal Team" → one query on `tasks`
- "Full audit trail for VG-XXXX" → join `tasks` + `status_history`
- "All WhatsApp messages this week" → query `task_messages` where channel='whatsapp'

---

## Deployment on Render


### Full Render environment variables

```
FLASK_ENV        = production
SECRET_KEY       = (32 random chars — use https://djecrety.ir)
GEMINI_API_KEY   = your-gemini-key
GEMINI_MODEL     = gemini-flash-latest
DATABASE_URI     = postgresql://...  (Internal Database URL from Render)
```

### Build and start commands

| Field | Value |
|---|---|
| Build Command | `pip install -r requirements.txt` |
| Start Command | `gunicorn main:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120` |

---

## Decisions I Made and Why

### AI tools used

I primarily used Claude 3.5 Sonnet for code architecture suggestions, debugging complex issues (especially JSON parsing and Docker permission problems), and refining the system prompt. I used Grok for quick syntax checks and second opinions on risk scoring logic.  The actual AI backend is Google Gemini (gemini-flash-latest). I chose it over Groq and OpenAI because:It has native support for responseMimeType: "application/json", which significantly improves structured output reliability.
The free tier was sufficient during development.
It offered the best balance between speed and consistency for this use case.


### System prompt design

I iterated on the system prompt four times. Early versions were too vague ("extract key details"), which led to inconsistent field names and poor JSON structure.Key decisions in the final prompt:Explicitly listed the exact intent strings the model must use — preventing hallucinations like transfer_money instead of send_money.
Defined every entity field with expected types and defaults (e.g., urgency must be one of low|normal|high|critical).
Included the exact JSON schema as a literal example in the rules section.
Added a strict instruction: "Respond with EXACTLY this JSON and nothing else."
Set temperature: 0.3 — low enough for consistent structure, high enough for natural message tone.

I deliberately excluded few-shot examples. With a clear schema and strict rules, they added unnecessary prompt length without improving output quality.


### Risk scoring: one decision where I changed what the AI suggested

Claude initially suggested a simple keyword-based risk system (flagging words like "urgent", "immediately", "help"). I rejected this approach because it is brittle and easily gamed.Instead, I built a factor-based + compound risk model that only uses the structured data coming from the AI (intent, urgency, amount, document_type, is_first_time_customer, etc.). I also added compound penalties for dangerous combinations (e.g., new customer + critical urgency, or urgent + large transfer). This mirrors how real fraud detection works — it's the interaction of signals that matters most, not isolated keywords.



### One thing that didn't work as expected

The `{{TASK_CODE}}` placeholder caused a subtle sequencing problem. The AI generates messages before the task is saved to the database (so the task code doesn't exist yet). My first approach was to generate the code first and pass it to the AI — but this created tight coupling between the AI service and the database layer, making testing harder.

The fix: the AI uses `{{TASK_CODE}}` as a literal placeholder, and `task_service.py` does a string replace after `db.session.flush()` generates the real code. This keeps the AI service completely unaware of the database and makes it independently testable.

### Timezone handling

All timestamps are stored in UTC. The models convert to East Africa Time (UTC+3) before returning data to the frontend, using a `_to_eat()` helper that explicitly attaches `timezone.utc` to naive datetimes before converting. This matters because SQLite strips timezone info on read — calling `astimezone()` directly on a naive datetime assumes system local time, which produces wrong results in Docker where `TZ=Africa/Nairobi` is set.

### Frontend architecture

The frontend uses vanilla JavaScript as specified. Two patterns worth explaining:

**IIFE wrappers** — both `request.js` and `dashboard.js` are wrapped in immediately invoked function expressions. Nothing leaks to global scope. The one deliberate exception is `window.updateStatus` and `window.openDetail` — they are on `window` explicitly because the Jinja template uses inline `onchange` attributes that need to call them.

**Event delegation for message tabs** — the tab buttons live inside `#resultPanel` which is `display:none` on page load. Rather than attaching listeners directly to hidden elements, I delegate to the stable parent panel.

**`DiasporaUtils` namespace** — shared helpers live in `utils.js` as a single IIFE namespace object. No module bundler, no duplication, no globals beyond the one namespace.