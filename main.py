from fastapi import FastAPI, Request, Depends, UploadFile, File, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from routers.track import router as track_router
from db.database import Base, engine, SessionLocal
from models.models import Track
import os
from sqlalchemy.orm import Session
from starlette import status

UPLOAD_DIR = "static/uploads"

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(track_router)

templates = Jinja2Templates(directory="templates")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/", response_class=HTMLResponse)
def read_index(request: Request):
    db = SessionLocal()
    tracks = db.query(Track).all()
    db.close()
    return templates.TemplateResponse("index.html", {"request": request, "tracks": tracks})

@app.get("/search", response_class=HTMLResponse)
def search_tracks_html(request: Request, query: str):
    db = SessionLocal()
    tracks = db.query(Track).filter(Track.title.ilike(f"%{query}%")).all()
    db.close()
    return templates.TemplateResponse("index.html", {"request": request, "tracks": tracks})

@app.post("/add")
async def add_track_html(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    filepath = os.path.join(UPLOAD_DIR, file.filename)
    with open(filepath, "wb") as buffer:
        buffer.write(await file.read())
    db_track = Track(title=file.filename, filename=file.filename, author_id=1)
    db.add(db_track)
    db.commit()
    db.refresh(db_track)
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

@app.post("/delete")
def delete_track_html(
    name: str = Form(...),  # имя трека из формы
    db: Session = Depends(get_db)
):
    track = db.query(Track).filter(Track.title == name).first()
    if not track:
        raise HTTPException(status_code=404, detail="Трек не знайдено")
    filepath = os.path.join(UPLOAD_DIR, track.filename)
    db.delete(track)
    db.commit()
    if os.path.exists(filepath):
        os.remove(filepath)
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)

@app.get("/tracks/list", response_class=HTMLResponse)
def list_tracks_page(request: Request):
    db = SessionLocal()
    tracks = db.query(Track).all()
    db.close()
    return templates.TemplateResponse("tracks_list.html", {"request": request, "tracks": tracks})