import json
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Interaction
from app.schemas import ChatRequest, ChatResponse, InteractionOut
from app.agent.graph import run_agent

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("/", response_model=ChatResponse)
def chat(payload: ChatRequest, db: Session = Depends(get_db)):
    reply_text, tool_calls = run_agent(payload.message, thread_id="hcp-log-session")

    tool_used = tool_calls[-1] if tool_calls else None

    # If a log/edit tool ran, pull back the freshest interaction row so the
    # frontend can refresh the structured form panel in sync with the chat.
    interaction_out = None
    if tool_used in ("log_interaction", "edit_interaction", "schedule_follow_up", "flag_compliance_risk"):
        latest = db.query(Interaction).order_by(Interaction.updated_at.desc()).first()
        if latest:
            interaction_out = InteractionOut.model_validate(latest)

    return ChatResponse(
        reply=reply_text,
        tool_used=tool_used,
        interaction=interaction_out,
    )
