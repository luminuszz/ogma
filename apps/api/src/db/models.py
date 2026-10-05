import enum

from sqlalchemy import JSON, Column, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.sql import func
from src.db.database import Base


class TranslationStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    DONE = "done"
    ERROR = "error"

class Manga(Base):
    __tablename__ = "mangas"
    id = Column(String, primary_key=True, index=True)
    title = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Chapter(Base):
    __tablename__ = "chapters"
    id = Column(String, primary_key=True, index=True)
    manga_id = Column(String, ForeignKey("mangas.id"))
    chapter_number = Column(String, nullable=True)
    total_pages = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(Enum(TranslationStatus), default=TranslationStatus.PENDING)  # type: ignore

class Page(Base):
    __tablename__ = "pages"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    chapter_id = Column(String, ForeignKey("chapters.id"))
    page_index = Column(Integer)
    image_url = Column(String, nullable=True) # Cloudflare R2 URL
    status = Column(Enum(TranslationStatus), default=TranslationStatus.PENDING)  # type: ignore
