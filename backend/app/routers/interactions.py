from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models import Interaction
from app.schemas import InteractionCreate, InteractionUpdate, InteractionOut

router = APIRouter(prefix="/api/interactions", tags=["interactions"])


@router.get("/", response_model=List[InteractionOut])
def list_interactions(hcp_name: str = None, db: Session = Depends(get_db)):
    q = db.query(Interaction)
    if hcp_name:
        q = q.filter(Interaction.hcp_name.ilike(f"%{hcp_name}%"))
    return q.order_by(Interaction.created_at.desc()).all()


@router.get("/{interaction_id}", response_model=InteractionOut)
def get_interaction(interaction_id: int, db: Session = Depends(get_db)):
    obj = db.query(Interaction).filter(Interaction.id == interaction_id).first()
    if not obj:
        raise HTTPException(404, "Interaction not found")
    return obj


@router.post("/", response_model=InteractionOut)
def create_interaction(payload: InteractionCreate, db: Session = Depends(get_db)):
    obj = Interaction(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.patch("/{interaction_id}", response_model=InteractionOut)
def update_interaction(interaction_id: int, payload: InteractionUpdate, db: Session = Depends(get_db)):
    obj = db.query(Interaction).filter(Interaction.id == interaction_id).first()
    if not obj:
        raise HTTPException(404, "Interaction not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(obj, field, value)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{interaction_id}")
def delete_interaction(interaction_id: int, db: Session = Depends(get_db)):
    obj = db.query(Interaction).filter(Interaction.id == interaction_id).first()
    if not obj:
        raise HTTPException(404, "Interaction not found")
    db.delete(obj)
    db.commit()
    return {"status": "deleted"}
