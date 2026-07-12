from pydantic import BaseModel
from typing import List, Optional, Any
from datetime import datetime


class InteractionCreate(BaseModel):
    hcp_name: str
    interaction_type: Optional[str] = "Meeting"
    interaction_date: Optional[str] = None
    interaction_time: Optional[str] = None
    attendees: Optional[List[str]] = []
    topics_discussed: Optional[str] = ""
    materials_shared: Optional[List[str]] = []
    samples_distributed: Optional[List[str]] = []
    sentiment: Optional[str] = "Neutral"
    outcomes: Optional[str] = ""
    follow_up_actions: Optional[List[Any]] = []
    source: Optional[str] = "form"


class InteractionUpdate(BaseModel):
    hcp_name: Optional[str] = None
    interaction_type: Optional[str] = None
    interaction_date: Optional[str] = None
    interaction_time: Optional[str] = None
    attendees: Optional[List[str]] = None
    topics_discussed: Optional[str] = None
    materials_shared: Optional[List[str]] = None
    samples_distributed: Optional[List[str]] = None
    sentiment: Optional[str] = None
    outcomes: Optional[str] = None
    follow_up_actions: Optional[List[Any]] = None


class InteractionOut(BaseModel):
    id: int
    hcp_name: str
    interaction_type: str
    interaction_date: Optional[str]
    interaction_time: Optional[str]
    attendees: List[str]
    topics_discussed: str
    materials_shared: List[str]
    samples_distributed: List[str]
    sentiment: str
    outcomes: str
    follow_up_actions: List[Any]
    compliance_flags: List[Any]
    source: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ChatRequest(BaseModel):
    message: str
    # Optional: if the chat is about editing a specific interaction already on screen
    active_interaction_id: Optional[int] = None


class ChatResponse(BaseModel):
    reply: str
    tool_used: Optional[str] = None
    interaction: Optional[InteractionOut] = None
    data: Optional[Any] = None
