from db.database import engine
from models.models import Base

Base.metadata.create_all(bind=engine)

print("Таблиці створено! База готова...")