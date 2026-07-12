from sqlalchemy import Column, Integer, String, Text, DateTime, JSON
from datetime import datetime
from app.database import Base


class Interaction(Base):
    __tablename__ = "interactions"

    id = Column(Integer, primary_key=True, index=True)
    hcp_name = Column(String(255), nullable=False, index=True)
    interaction_type = Column(String(50), default="Meeting")  # Meeting, Call, Email, Conference
    interaction_date = Column(String(30), nullable=True)
    interaction_time = Column(String(30), nullable=True)
    attendees = Column(JSON, default=list)
    topics_discussed = Column(Text, default="")
    materials_shared = Column(JSON, default=list)
    samples_distributed = Column(JSON, default=list)
    sentiment = Column(String(20), default="Neutral")  # Positive, Neutral, Negative
    outcomes = Column(Text, default="")
    follow_up_actions = Column(JSON, default=list)  # list of {note, due_date, status}
    compliance_flags = Column(JSON, default=list)   # list of {type, note, severity}
    source = Column(String(20), default="form")     # "form" or "chat"
    raw_input = Column(Text, default="")             # original free-text used to log/edit
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
