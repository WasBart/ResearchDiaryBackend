from sqlmodel import SQLModel, Field, create_engine
from typing import Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel.ext.asyncio.session import AsyncSession
import sqlalchemy as sa

from .config import settings


class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key = True)
    device_id: str = Field(unique=True)

class TextNoteBase(SQLModel):
    text: str
    date: datetime

class TextNote(TextNoteBase, table=True):
    id: Optional[int] = Field(default=None, primary_key = True)
    user_id: Optional[int] = Field(default=None, foreign_key = "user.id")
    #date: datetime = Field(sa_column=sa.Column(sa.DateTime(timezone=True), nullable=False), default_factory=datetime.utcnow)

class TextNoteCreate(TextNoteBase):
    pass

class TextNoteUpdate(TextNoteBase):
    pass

class VoiceNoteBase(SQLModel):
    content: bytes
    date: datetime

class VoiceNoteSimple(SQLModel):
    id: Optional[int] = Field(default=None, primary_key = True)
    #date: datetime = Field(sa_column=sa.Column(sa.DateTime(timezone=True), nullable=False), default_factory=datetime.utcnow)

class VoiceNote(VoiceNoteBase, VoiceNoteSimple, table=True):
    user_id: Optional[int] = Field(default=None, foreign_key = "user.id")
    
async_engine = create_async_engine(
    settings.db_url,
    echo=True,
    future=True
)


async def get_async_session() -> AsyncSession:
    async_session = sessionmaker(
        bind=async_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with async_session() as session:
        yield session

#SQLModel.metadata.create_all(engine)