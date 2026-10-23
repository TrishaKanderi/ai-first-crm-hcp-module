# AI-First CRM — HCP Module: Log Interaction Screen

An AI-first Customer Relationship Management module for pharma field representatives,
focused on the **Log Interaction** screen: logging a visit/call with a Healthcare
Professional (HCP) either through a structured form or through a natural-language
chat with an AI assistant — both writing to the same underlying record.

Built for the technical assignment: React + Redux frontend, FastAPI backend, a
LangGraph agent backed by Groq (`llama-3.1-8b-instant`, with `llama-3.3-70b-versatile` as a
fallback for the compliance check), and a SQL database (Postgres/MySQL-ready, SQLite
by default for zero-config local runs).

---

## Why it's designed this way (life-science lens)

Field reps are on the road, moving between offices, and the CRM step is the part
they resent most — it's paperwork sitting between them and the next visit. The
whole point of an AI-first HCP module is to let the rep talk (or type) the way they
already think about a visit — *"Met Dr. Smith, discussed Prodo-X efficacy, positive
sentiment, shared brochure"* — and have the system do the clerical work: figuring out
who, what, sentiment, and materials, and filing it correctly.

But this isn't a generic notes app — it's pharma. Two things follow from that:

1. **Every free-text log has to pass through a compliance lens.** A rep casually
   mentioning a patient side effect in a chat note is a pharmacovigilance event,
   not CRM trivia — it has to be caught and flagged even though the rep didn't
   flag it themselves. That's why `flag_compliance_risk` is one of the five tools
   rather than an afterthought.
2. **History has to be recall-ready, not just stored.** A rep prepping for a
   follow-up visit needs "what did we agree on with Dr. Smith last time," not a raw
   dump of old rows — hence `get_interaction_history` summarizes rather than lists.

---

## Role of the LangGraph Agent

The agent sits between the free-text chat box and the structured interaction
record. It doesn't replace the form — the form and the chat are two doors into the
same data. Concretely, the agent:

1. Reads the rep's message and decides which sales activity it corresponds to
   (a new visit to log, an edit to something already logged, a history lookup, a
   follow-up reminder, or a compliance check).
2. Calls the matching tool, which does the actual extraction/DB read-write using
   the LLM plus SQLAlchemy.
3. Turns the tool's structured JSON result back into a short, natural reply, and
   the same structured result is used to refresh the form panel in the UI — so
   logging via chat and logging via form always agree.

It's implemented with LangGraph's `create_react_agent` (a standard ReAct loop: LLM
node → conditional edge to a tool node whenever a tool call is emitted → back to
the LLM node until it returns a final answer), which is enough control for five
largely independent tools. See `backend/app/agent/graph.py`.

## The Five Tools

| # | Tool | Purpose |
|---|------|---------|
| 1 | **`log_interaction`** *(required)* | Takes the rep's free-text note, prompts the LLM to extract structured entities — HCP name, interaction type, topics discussed, materials/samples, sentiment, outcomes — and creates a new interaction row. |
| 2 | **`edit_interaction`** *(required)* | Takes an `interaction_id` + a natural-language instruction ("change sentiment to neutral"), sends the current record + instruction to the LLM, gets back only the fields that should change, and applies a partial update. |
| 3 | `get_interaction_history` | Looks up past interactions with a given HCP and asks the LLM to summarize sentiment trend and open follow-ups in 2–3 sentences — used before a visit or when asked "what did we discuss with Dr. X." |
| 4 | `schedule_follow_up` | Attaches a follow-up action/reminder (note + optional due date) to an already-logged interaction. |
| 5 | `flag_compliance_risk` | Screens interaction text with the larger model for adverse-event mentions, off-label discussion, or promissory language, and stores any flags on the record. Run automatically after every `log_interaction` call. |

### How `log_interaction` captures data (detail)

`log_interaction(note: str)` → prompts `llama-3.1-8b-instant` with a strict JSON-extraction
prompt asking for `hcp_name`, `interaction_type`, `topics_discussed`,
`materials_shared`, `samples_distributed`, `sentiment`, `outcomes` → parses the JSON
defensively (stripping code fences/prose the model might add) → creates an
`Interaction` row with `source="chat"` and the original note preserved in
`raw_input` for auditability → returns the saved record.

### How `edit_interaction` applies changes (detail)

`edit_interaction(interaction_id, instruction)` → loads the current row → sends
**both** the current JSON and the instruction to the LLM, asking for *only the
diff* → applies just those fields with `setattr`, leaving everything else
untouched → appends the instruction to `raw_input` so there's a lightweight audit
trail of what was changed and why.

---

## Tech Stack

- **Frontend:** React 18 + Redux Toolkit, Google Inter font, plain CSS (no UI kit,
  so the design has no hidden dependencies).
- **Backend:** FastAPI, SQLAlchemy.
- **AI Agent Framework:** LangGraph (`create_react_agent`).
- **LLMs:** Groq — `llama-3.1-8b-instant` (primary, fast tool-routing/extraction),
  `llama-3.3-70b-versatile` (compliance screening).
- **Database:** SQLite by default (zero config); swap in Postgres or MySQL by
  changing one env var (`DATABASE_URL`) — the code path is identical because it's
  all SQLAlchemy.

---

## Project Structure

```
aivoa-crm-hcp/
├── backend/
│   ├── app/
│   │   ├── main.py                # FastAPI app, CORS, router wiring
│   │   ├── database.py            # SQLAlchemy engine/session (Postgres/MySQL/SQLite)
│   │   ├── models.py              # Interaction table
│   │   ├── schemas.py             # Pydantic request/response models
│   │   ├── config.py              # env var loading
│   │   ├── agent/
│   │   │   ├── llm.py             # Groq client wrappers (llama-3.1-8b-instant / llama-3.3-70b)
│   │   │   ├── tools.py           # the 5 LangGraph tools
│   │   │   └── graph.py           # the LangGraph agent (create_react_agent)
│   │   └── routers/
│   │       ├── interactions.py    # structured-form CRUD endpoints
│   │       └── chat.py            # conversational endpoint -> agent
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    ├── src/
    │   ├── components/
    │   │   ├── LogInteractionScreen.jsx   # side-by-side form + chat layout
    │   │   ├── InteractionForm.jsx        # structured form path
    │   │   └── ChatPanel.jsx              # conversational path
    │   ├── store/                          # Redux Toolkit slices
    │   ├── api.js
    │   └── App.jsx
    ├── package.json
    └── .env.example
```

---

## Running It

### 1. Backend

```bash
cd backend
python3 -m venv venv && source venv/bin/activate   # optional but recommended
pip install -r requirements.txt

cp .env.example .env
# edit .env and set GROQ_API_KEY (create one at https://console.groq.com/keys)
# DATABASE_URL defaults to local SQLite - leave as-is to run with zero extra setup,
# or point it at Postgres/MySQL (examples are commented in .env.example)

uvicorn app.main:app --reload --port 8000
```

The API is now live at `http://localhost:8000` (interactive docs at `/docs`).

### 2. Frontend

```bash
cd frontend
npm install
cp .env.example .env   # VITE_API_URL defaults to http://localhost:8000
npm run dev
```

Open `http://localhost:5173`. The left panel is the structured form; the right
panel is the AI Assistant chat. Logging via either one updates the same record —
try typing a note in the chat and watching the form fill in.

---

## Notes / Assumptions

- SQLite is used as the default DB for a frictionless local run; `DATABASE_URL`
  is the only thing that needs to change to point at Postgres or MySQL, since the
  whole data layer goes through SQLAlchemy.
- The "Summarize from Voice Note" control on the form is shown as a UI affordance
  per the reference mockup but isn't wired to real speech-to-text in this build —
  out of scope for the assignment's time box, and voice capture would be its own
  tool if extended.
- The agent keeps short-term conversational memory per session via LangGraph's
  `MemorySaver` checkpointer, so follow-up messages like "actually make that
  neutral" resolve against the interaction just discussed.
