from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.db.session import get_db
from app.models.entities import FlashcardTopic, Flashcard

router = APIRouter()

@router.get("/api/flashcards/topics")
def get_topics(db: Session = Depends(get_db)):
    topics = db.query(FlashcardTopic).all()
    return topics

@router.get("/api/flashcards/topics/{topic_code}/cards")
def get_cards_by_topic(topic_code: str, db: Session = Depends(get_db)):
    topic = db.query(FlashcardTopic).filter(FlashcardTopic.code == topic_code).first()
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")
    
    cards = db.query(Flashcard).filter(Flashcard.topic_id == topic.id).all()
    return cards
