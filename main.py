from fastapi import FastAPI, Request, Depends, UploadFile, File, Form, HTTPException, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from jose import JWTError, jwt
import os
from starlette import status
from routers.auth import authenticate_user, create_access_token, get_password_hash
from routers.track import router as track_router
from db.database import Base, engine, SessionLocal
from models.models import Track, User
from routers.auth import authenticate_user, create_access_token

UPLOAD_DIR = "static/uploads"

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(track_router)

templates = Jinja2Templates(directory="templates")

SECRET_KEY = "svinya"  # Используй свой секретный ключ
ALGORITHM = "HS256"

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Функция для получения текущего пользователя из токена, который хранится в cookie
def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get("access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str | None = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return user


@app.get("/", response_class=HTMLResponse)
def read_index(request: Request):
    db = next(get_db())
    tracks = db.query(Track).all()
    token = request.cookies.get("access_token")
    user = None
    if token:
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            username: str | None = payload.get("sub")
            if username:
                user = db.query(User).filter(User.username == username).first()
        except JWTError:
            pass  # токен недействителен — считаем, что пользователь не авторизован
    return templates.TemplateResponse("index.html", {"request": request, "tracks": tracks, "user": user})


@app.get("/search", response_class=HTMLResponse)
def search_tracks_html(request: Request, query: str):
    db = next(get_db())
    tracks = db.query(Track).filter(Track.title.ilike(f"%{query}%")).all()
    return templates.TemplateResponse("index.html", {"request": request, "tracks": tracks})


@app.post("/add")
async def add_track_html(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    filepath = os.path.join(UPLOAD_DIR, file.filename)
    with open(filepath, "wb") as buffer:
        buffer.write(await file.read())
    db_track = Track(title=file.filename, filename=file.filename, author_id=current_user.id)
    db.add(db_track)
    db.commit()
    db.refresh(db_track)
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)


@app.post("/delete")
def delete_track_html(
    name: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    track = db.query(Track).filter(Track.title == name).first()
    if not track:
        raise HTTPException(status_code=404, detail="Трек не найден")
    filepath = os.path.join(UPLOAD_DIR, track.filename)
    db.delete(track)
    db.commit()
    if os.path.exists(filepath):
        os.remove(filepath)
    return RedirectResponse(url="/", status_code=status.HTTP_303_SEE_OTHER)


@app.get("/tracks/list", response_class=HTMLResponse)
def list_tracks_page(request: Request):
    db = next(get_db())
    tracks = db.query(Track).all()
    return templates.TemplateResponse("tracks_list.html", {"request": request, "tracks": tracks})


@app.get("/login", response_class=HTMLResponse)
def login_form(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "error": None})


@app.post("/login", response_class=HTMLResponse)
def login_post(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = authenticate_user(db, username, password)
    if not user:
        return templates.TemplateResponse("login.html", {"request": request, "error": "Неверные данные"})

    token = create_access_token(username=username)
    response = RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    response.set_cookie("access_token", token, httponly=True, path="/")
    return response


@app.get("/logout")
def logout():
    response = RedirectResponse(url="/login")
    response.delete_cookie("access_token", path="/")
    return response


@app.get("/register", response_class=HTMLResponse)
def register_form(request: Request):
    return templates.TemplateResponse("register.html", {"request": request, "error": None})

@app.post("/register", response_class=HTMLResponse)
def register_post(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    # Проверка, есть ли пользователь с таким username
    if db.query(User).filter(User.username == username).first():
        return templates.TemplateResponse("register.html", {"request": request, "error": "Пользователь с таким именем уже существует"})
    
    # Хешируем пароль
    hashed_password = get_password_hash(password)
    new_user = User(username=username, email=email, hashed_password=hashed_password)
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # После успешной регистрации редиректим на логин
    return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)