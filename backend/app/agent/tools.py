"""
The five LangGraph tools the HCP-interaction agent has access to.

1. log_interaction        (required by the task)
2. edit_interaction       (required by the task)
3. get_interaction_history
4. schedule_follow_up
5. flag_compliance_risk

Each tool is a plain Python function decorated with @tool so it can be bound
directly to a Groq chat model inside the LangGraph agent (app/agent/graph.py).
Tools open their own short-lived DB session rather than depending on FastAPI's
request-scoped session, since the agent graph runs independently of the request
lifecycle (and could eventually be triggered by things other than an HTTP call,
e.g. a scheduled job).
"""
import json
from datetime import datetime
from typing import List, Optional

from langchain_core.tools import tool
from pydantic import BaseModel, Field

from app.database import SessionLocal
from app.models import Interaction
from app.agent.llm import get_default_llm, get_large_llm

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _interaction_to_dict(i: Interaction) -> dict:
    return {
        "id": i.id,
        "hcp_name": i.hcp_name,
        "interaction_type": i.interaction_type,
        "interaction_date": i.interaction_date,
        "interaction_time": i.interaction_time,
        "attendees": i.attendees or [],
        "topics_discussed": i.topics_discussed,
        "materials_shared": i.materials_shared or [],
        "samples_distributed": i.samples_distributed or [],
        "sentiment": i.sentiment,
        "outcomes": i.outcomes,
        "follow_up_actions": i.follow_up_actions or [],
        "compliance_flags": i.compliance_flags or [],
        "source": i.source,
    }


def _safe_json_parse(text: str) -> dict:
    """LLMs occasionally wrap JSON in prose or code fences - strip that defensively."""
    text = text.strip()
    if "```" in text:
        text = text.split("```")[1]
        text = text.replace("json", "", 1).strip() if text.lower().startswith("json") else text
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1:
        text = text[start:end + 1]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {}


EXTRACTION_PROMPT = """You are a life-science CRM assistant. Extract structured HCP
(Healthcare Professional) interaction data from a field representative's free-text note.

Return ONLY valid JSON with these keys (use null / empty list if not mentioned):
- hcp_name (string)
- interaction_type (one of: "Meeting", "Call", "Email", "Conference")
- topics_discussed (short string)
- materials_shared (list of strings, e.g. brochures)
- samples_distributed (list of strings, e.g. drug sample names)
- sentiment ("Positive", "Neutral", or "Negative")
- outcomes (short string - agreements or next steps mentioned)

Field rep note: "{note}"

JSON:"""


# ---------------------------------------------------------------------------
# Tool 1 (required): Log Interaction
# ---------------------------------------------------------------------------

class LogInteractionArgs(BaseModel):
    note: str = Field(..., description=(
        "Free-text description of the HCP interaction as typed or spoken by the "
        "field representative, e.g. 'Met Dr. Smith, discussed Prodo-X efficacy, "
        "positive sentiment, shared brochure'."
    ))


@tool("log_interaction", args_schema=LogInteractionArgs)
def log_interaction(note: str) -> str:
    """Log a new HCP interaction from a natural-language note. Uses the LLM to pull
    out entities (HCP name, interaction type, topics, materials/samples, sentiment,
    outcomes) and saves a new interaction record. Use this whenever the rep describes
    a visit/call that hasn't been logged yet."""
    llm = get_default_llm()
    resp = llm.invoke(EXTRACTION_PROMPT.format(note=note))
    extracted = _safe_json_parse(resp.content)

    db = SessionLocal()
    try:
        interaction = Interaction(
            hcp_name=extracted.get("hcp_name") or "Unknown HCP",
            interaction_type=extracted.get("interaction_type") or "Meeting",
            interaction_date=datetime.utcnow().strftime("%Y-%m-%d"),
            interaction_time=datetime.utcnow().strftime("%H:%M"),
            topics_discussed=extracted.get("topics_discussed") or "",
            materials_shared=extracted.get("materials_shared") or [],
            samples_distributed=extracted.get("samples_distributed") or [],
            sentiment=extracted.get("sentiment") or "Neutral",
            outcomes=extracted.get("outcomes") or "",
            follow_up_actions=[],
            compliance_flags=[],
            source="chat",
            raw_input=note,
        )
        db.add(interaction)
        db.commit()
        db.refresh(interaction)
        result = _interaction_to_dict(interaction)
    finally:
        db.close()

    return json.dumps({"status": "logged", "interaction": result})


# ---------------------------------------------------------------------------
# Tool 2 (required): Edit Interaction
# ---------------------------------------------------------------------------

class EditInteractionArgs(BaseModel):
    interaction_id: int = Field(..., description="ID of the interaction to modify.")
    instruction: str = Field(..., description=(
        "Natural-language description of the change, e.g. 'change sentiment to "
        "neutral' or 'add that I also shared a dosage chart'."
    ))


@tool("edit_interaction", args_schema=EditInteractionArgs)
def edit_interaction(interaction_id: int, instruction: str) -> str:
    """Modify a previously logged interaction using a natural-language instruction.
    Reads the existing record, asks the LLM to produce only the fields that should
    change, and applies a partial update. Use this when the rep wants to correct or
    add to something already logged (identified by interaction_id)."""
    db = SessionLocal()
    try:
        interaction = db.query(Interaction).filter(Interaction.id == interaction_id).first()
        if not interaction:
            return json.dumps({"status": "error", "message": f"No interaction with id {interaction_id}"})

        current = _interaction_to_dict(interaction)
        prompt = f"""You are editing an existing HCP interaction record.

Current record (JSON): {json.dumps(current)}

Requested change: "{instruction}"

Return ONLY a JSON object containing just the fields that should change and their
new values (subset of: hcp_name, interaction_type, topics_discussed, materials_shared,
samples_distributed, sentiment, outcomes). Do not include unchanged fields.

JSON:"""
        llm = get_default_llm()
        resp = llm.invoke(prompt)
        changes = _safe_json_parse(resp.content)

        for field, value in changes.items():
            if hasattr(interaction, field):
                setattr(interaction, field, value)
        interaction.raw_input = (interaction.raw_input or "") + f"\n[edit] {instruction}"
        db.commit()
        db.refresh(interaction)
        result = _interaction_to_dict(interaction)
    finally:
        db.close()

    return json.dumps({"status": "updated", "interaction": result})


# ---------------------------------------------------------------------------
# Tool 3: Get Interaction History
# ---------------------------------------------------------------------------

class HistoryArgs(BaseModel):
    hcp_name: str = Field(..., description="Name of the HCP to look up past interactions for.")
    limit: int = Field(5, description="Max number of past interactions to return.")


@tool("get_interaction_history", args_schema=HistoryArgs)
def get_interaction_history(hcp_name: str, limit: int = 5) -> str:
    """Retrieve a summarized history of past interactions with a given HCP, most
    recent first. Use this before a visit so the rep can be reminded what was
    discussed / promised last time, or when asked 'what did we talk about with Dr. X'."""
    db = SessionLocal()
    try:
        records = (
            db.query(Interaction)
            .filter(Interaction.hcp_name.ilike(f"%{hcp_name}%"))
            .order_by(Interaction.created_at.desc())
            .limit(limit)
            .all()
        )
        history = [_interaction_to_dict(r) for r in records]
    finally:
        db.close()

    if not history:
        return json.dumps({"status": "empty", "message": f"No prior interactions found for {hcp_name}."})

    llm = get_default_llm()
    summary_prompt = f"""Summarize this HCP's interaction history for a field rep in
2-3 short sentences, highlighting sentiment trend and any open follow-ups.

History (JSON): {json.dumps(history)}

Summary:"""
    summary = llm.invoke(summary_prompt).content

    return json.dumps({"status": "ok", "summary": summary, "history": history})


# ---------------------------------------------------------------------------
# Tool 4: Schedule Follow-Up
# ---------------------------------------------------------------------------

class FollowUpArgs(BaseModel):
    interaction_id: int = Field(..., description="Interaction this follow-up relates to.")
    note: str = Field(..., description="What the follow-up action is, e.g. 'send updated efficacy study'.")
    due_date: Optional[str] = Field(None, description="Due date in YYYY-MM-DD format, if mentioned.")


@tool("schedule_follow_up", args_schema=FollowUpArgs)
def schedule_follow_up(interaction_id: int, note: str, due_date: Optional[str] = None) -> str:
    """Attach a follow-up action/reminder to an already-logged interaction, e.g.
    'send Dr. Smith the updated efficacy study by Friday'. Use this whenever the
    rep mentions something they still need to do after a visit."""
    db = SessionLocal()
    try:
        interaction = db.query(Interaction).filter(Interaction.id == interaction_id).first()
        if not interaction:
            return json.dumps({"status": "error", "message": f"No interaction with id {interaction_id}"})

        actions = list(interaction.follow_up_actions or [])
        actions.append({
            "note": note,
            "due_date": due_date,
            "status": "open",
            "created_at": datetime.utcnow().isoformat(),
        })
        interaction.follow_up_actions = actions
        db.commit()
        db.refresh(interaction)
        result = _interaction_to_dict(interaction)
    finally:
        db.close()

    return json.dumps({"status": "scheduled", "interaction": result})


# ---------------------------------------------------------------------------
# Tool 5: Flag Compliance / Adverse Event Risk
# ---------------------------------------------------------------------------

class ComplianceArgs(BaseModel):
    interaction_id: Optional[int] = Field(None, description="Interaction ID to check, if already logged.")
    text: Optional[str] = Field(None, description="Raw text to check, if not yet logged as an interaction.")


@tool("flag_compliance_risk", args_schema=ComplianceArgs)
def flag_compliance_risk(interaction_id: Optional[int] = None, text: Optional[str] = None) -> str:
    """Screen an interaction's notes for pharma-compliance risk: potential adverse
    event (AE) mentions, off-label discussion, or promissory/guarantee language.
    This is safety-critical for a life-science CRM - any AE mention must be
    escalated to pharmacovigilance regardless of how the rep phrased it. Use this
    after logging any interaction, or whenever asked to review one for risk."""
    db = SessionLocal()
    try:
        content = text
        interaction = None
        if interaction_id is not None:
            interaction = db.query(Interaction).filter(Interaction.id == interaction_id).first()
            if interaction:
                content = f"{interaction.topics_discussed}\n{interaction.outcomes}"

        if not content:
            return json.dumps({"status": "error", "message": "No text or valid interaction_id provided."})

        llm = get_large_llm()  # stronger model for a safety-critical check
        prompt = f"""You are a pharmacovigilance/compliance screener for a pharma CRM.
Review the following field-rep note and flag any of:
- Potential adverse event (AE) mentions (side effects, patient harm, unexpected reactions)
- Off-label usage discussion
- Guarantee/promissory language about outcomes ("will definitely cure", etc.)

Note: "{content}"

Return ONLY JSON: {{"flags": [{{"type": "...", "detail": "...", "severity": "low|medium|high"}}]}}
If nothing found, return {{"flags": []}}.

JSON:"""
        resp = llm.invoke(prompt)
        parsed = _safe_json_parse(resp.content)
        flags = parsed.get("flags", [])

        if interaction is not None:
            interaction.compliance_flags = flags
            db.commit()
            db.refresh(interaction)
    finally:
        db.close()

    return json.dumps({"status": "ok", "flags": flags})


ALL_TOOLS = [
    log_interaction,
    edit_interaction,
    get_interaction_history,
    schedule_follow_up,
    flag_compliance_risk,
]
