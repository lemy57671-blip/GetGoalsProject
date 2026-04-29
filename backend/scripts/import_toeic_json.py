import json
import logging
import os
from pathlib import Path

from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.entities import (
    ToeicSet,
    ToeicQuestion,
    ToeicQuestionOption,
    ToeicPassage,
    ToeicQuestionAsset,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MANIFESTS_DIR = Path("runtime/static/toeic/manifests")


def import_json_file(db: Session, file_path: Path):
    logger.info(f"Importing {file_path.name}...")
    
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    if not isinstance(data, list):
        logger.warning(f"Skipping {file_path.name}: not a list")
        return

    # Determine set info
    file_stem = file_path.stem
    if file_stem.startswith("part"):
        set_type = "practice"
        part_num = int(file_stem.replace("part", "").replace("_questions", ""))
        set_code = f"practice_part{part_num}"
        set_title = f"Practice Part {part_num}"
    elif "minitest" in file_stem:
        set_type = "minitest"
        part_num = None
        set_code = file_stem
        set_title = "Mini Test 1"
    elif "fulltest" in file_stem:
        set_type = "fulltest"
        part_num = None
        set_code = file_stem
        set_title = "Full Test 1"
    else:
        set_type = "other"
        part_num = None
        set_code = file_stem
        set_title = file_stem

    # Create or get ToeicSet
    toeic_set = db.query(ToeicSet).filter(ToeicSet.code == set_code).first()
    if not toeic_set:
        toeic_set = ToeicSet(
            code=set_code,
            title=set_title,
            type=set_type,
            part=part_num,
            is_active=True
        )
        db.add(toeic_set)
        db.flush()
        logger.info(f"Created ToeicSet: {set_code}")
    else:
        logger.info(f"Clearing existing questions/passages for ToeicSet: {set_code}")
        # Clear existing data for this set to avoid duplicates
        # We need to delete in order: Assets -> Options -> Questions -> Passages
        questions = db.query(ToeicQuestion).filter(ToeicQuestion.set_id == toeic_set.id).all()
        q_ids = [q.id for q in questions]
        
        if q_ids:
            db.query(ToeicQuestionAsset).filter(ToeicQuestionAsset.question_id.in_(q_ids)).delete(synchronize_session=False)
            db.query(ToeicQuestionOption).filter(ToeicQuestionOption.question_id.in_(q_ids)).delete(synchronize_session=False)
            db.query(ToeicQuestion).filter(ToeicQuestion.id.in_(q_ids)).delete(synchronize_session=False)
        
        passages = db.query(ToeicPassage).filter(ToeicPassage.set_id == toeic_set.id).all()
        p_ids = [p.id for p in passages]
        if p_ids:
            db.query(ToeicQuestionAsset).filter(ToeicQuestionAsset.passage_id.in_(p_ids)).delete(synchronize_session=False)
            db.query(ToeicPassage).filter(ToeicPassage.id.in_(p_ids)).delete(synchronize_session=False)
        
        db.flush()

    # Track passages by group_code to avoid duplicates
    passages_by_group = {}

    for item in data:
        # 1. Handle Passage
        passage_id = None
        group_code = item.get("groupId")
        passage_data = item.get("passage")
        
        if group_code:
            if group_code in passages_by_group:
                passage_id = passages_by_group[group_code]
            elif passage_data or item.get("audioUrl") or item.get("audio"):
                # Create passage
                passage_text = None
                if isinstance(passage_data, dict):
                    passage_text = passage_data.get("text")
                elif isinstance(passage_data, str):
                    passage_text = passage_data

                audio_url = item.get("audioUrl")
                if not audio_url and item.get("audio"):
                    audio_url = item.get("audio").get("path")
                
                image_url = None
                if item.get("image"):
                    image_url = item.get("image").get("path")
                elif item.get("graphic"):
                    image_url = item.get("graphic").get("path")

                new_passage = ToeicPassage(
                    set_id=toeic_set.id,
                    group_code=group_code,
                    part=item.get("part", part_num or 0),
                    title=item.get("passageTitle") or (passage_data.get("title") if isinstance(passage_data, dict) else None),
                    passage_text=passage_text,
                    audio_path=audio_url,
                    image_path=image_url
                )
                db.add(new_passage)
                db.flush()
                passage_id = new_passage.id
                passages_by_group[group_code] = passage_id

        # 2. Create Question
        audio_url = item.get("audioUrl")
        if not audio_url and item.get("audio"):
            audio_url = item.get("audio").get("path")

        q = ToeicQuestion(
            set_id=toeic_set.id,
            passage_id=passage_id,
            test_number=item.get("test"),
            question_number=item.get("questionNumber", 0),
            part=item.get("part", part_num or 0),
            skill_code=item.get("skill"),
            subskill_code=item.get("subskill"),
            difficulty=item.get("difficulty"),
            question_text=item.get("question", ""),
            explanation=item.get("explanation"),
            correct_option_key=item.get("correctAnswer"),
            transcript=item.get("transcript"),
            section=item.get("section"),
            part_label=item.get("partLabel"),
            question_type=item.get("type"),
            group_code=group_code,
            ability_band=item.get("abilityBand"),
            min_score=item.get("minScore"),
            max_score=item.get("maxScore"),
            audio_url=audio_url,
            is_active=True
        )
        db.add(q)
        db.flush()

        # Handle Assets for Question
        if audio_url:
            db.add(ToeicQuestionAsset(
                question_id=q.id,
                asset_type="audio",
                relative_path=audio_url,
                sort_order=0
            ))
        
        image_obj = item.get("image") or item.get("graphic")
        if image_obj and image_obj.get("path"):
            db.add(ToeicQuestionAsset(
                question_id=q.id,
                asset_type="image",
                relative_path=image_obj.get("path"),
                sort_order=0
            ))

        # 3. Create Options
        options = item.get("options", [])
        for i, opt_text in enumerate(options):
            opt_key = chr(65 + i) # A, B, C, D
            opt = ToeicQuestionOption(
                question_id=q.id,
                option_key=opt_key,
                option_text=opt_text,
                sort_order=i
            )
            db.add(opt)

    db.commit()
    logger.info(f"Finished importing {len(data)} questions from {file_path.name}")


def main():
    db = SessionLocal()
    try:
        # Check if manifests dir exists
        if not MANIFESTS_DIR.exists():
            logger.error(f"Manifests directory not found: {MANIFESTS_DIR}")
            return

        # List all json files
        json_files = list(MANIFESTS_DIR.glob("*.json"))
        # Exclude rejected files
        json_files = [f for f in json_files if "rejected" not in f.name]
        
        logger.info(f"Found {len(json_files)} manifest files.")
        
        for f in json_files:
            import_json_file(db, f)
            
        logger.info("Import complete!")
    finally:
        db.close()

if __name__ == "__main__":
    main()
