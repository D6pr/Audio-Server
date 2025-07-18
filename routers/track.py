import os
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
from db.database import SessionLocal
from models.models import Track, User
from routers.dependencies import get_current_user
from schemas.schemas import TrackCreate, TrackOut
from fastapi.responses import FileResponse
from routers.dependencies import get_current_user, get_db

UPLOAD_DIR = "static/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

router = APIRouter(prefix="/tracks", tags=["Tracks"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/", response_model=list[TrackOut])
def get_all_tracks(db: Session = Depends(get_db)):
    return db.query(Track).all()

@router.post("/add", response_model=TrackOut)
async def upload_track(file: UploadFile = File(...), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    track = TrackCreate(name=file.filename)
    filepath = os.path.join(UPLOAD_DIR, file.filename)
    with open(filepath, "wb") as buffer:
        buffer.write(await file.read())
    db_track = Track(title=file.filename, filename=file.filename, author_id=1)
    db.add(db_track)
    db.commit()
    db.refresh(db_track)
    return db_track

@router.put("/update/{id}", response_model=TrackOut)
def update_track(id: int, title: str = Form(...), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    track = db.query(Track).filter(Track.id == id).first()
    if not track:
        raise HTTPException(status_code=404, detail="Трек не знайдено")
    track.title = title
    db.commit()
    db.refresh(track)
    return track

@router.delete("/delete/{id}")
def delete_track(id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    track = db.query(Track).filter(Track.id == id).first()
    if not track:
        raise HTTPException(status_code=404, detail="Трек не знайдено")
    db.delete(track)    
    db.commit()
    filepath = os.path.join(UPLOAD_DIR, track.filename)
    if os.path.exists(filepath):
        os.remove(filepath)
    return {"message": "Трек видалено"}

@router.get("/play/{id}")
def play_track(id: int, db: Session = Depends(get_db)):
    track = db.query(Track).filter(Track.id == id).first()
    if not track:
        raise HTTPException(status_code=404, detail="Трек не знайдено")
    filepath = os.path.join(UPLOAD_DIR, track.filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="Файл не знайдено")
    return FileResponse(filepath, media_type="audio/mpeg")

@router.get("/search", response_model=list[TrackOut])
def search_tracks(query: str, db: Session = Depends(get_db)):
    return db.query(Track).filter(Track.title.ilike(f"%{query}%")).all()