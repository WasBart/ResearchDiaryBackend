from fastapi import FastAPI, Header, Depends, UploadFile, HTTPException, File, Form

from fastapi.responses import StreamingResponse, FileResponse
from io import BytesIO

from app.db import async_engine, get_async_session, User, TextNote, TextNoteCreate, VoiceNote, TextNoteUpdate, VoiceNoteSimple, VoiceNoteCreate

import datetime

from typing import Annotated, List

from sqlmodel import Session, SQLModel, select

from sqlmodel.ext.asyncio.session import AsyncSession

import aiofiles
import secrets
import os

import shutil
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Callable

app = FastAPI(title="Research Diary Backend")

async def get_current_user(x_token: Annotated[str, Header()], db: AsyncSession = Depends(get_async_session)):
    statement = select(User).where(User.device_id == x_token)
    results = await db.exec(statement)
    user = results.first()
    if user is None:
        user = User(device_id = x_token)
        db.add(user)
        await db.commit()
        await db.refresh(user)
    return user

@app.put("/text_notes/", response_model=TextNote)
async def create_text_note(textNote: TextNoteCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_async_session)):
    db_text_note = TextNote.from_orm(textNote)
    db_text_note.user_id = user.id
    db.add(db_text_note)
    await db.commit()
    await db.refresh(db_text_note)
    return db_text_note

@app.patch("/text_notes/{note_id}", response_model=TextNote)
async def update_text_note(note_id: int, text_note: TextNoteUpdate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_async_session)):
    db_text_note = await db.get(TextNote, note_id)
    if not db_text_note:
        raise HTTPException(status_code=404, detail="text note not found.")
    if db_text_note.user_id != user.id:
        raise HTTPException(status_code=403, detail="not allowed to update note.")
    text_note_data = text_note.dict(exclude_unset=True)
    for key, value in text_note_data.items():
        setattr(db_text_note, key, value)
    db.add(db_text_note)
    await db.commit()
    await db.refresh(db_text_note)
    return db_text_note

@app.delete("/text_notes/{note_id}")
async def delete_text_note(note_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_async_session)):
    db_text_note = await db.get(TextNote, note_id)
    if not db_text_note:
        raise HTTPException(status_code=404, detail="text note not found.")
    if db_text_note.user_id != user.id:
        raise HTTPException(status_code=403, detail="not allowed to update note.")
    await db.delete(db_text_note)
    await db.commit()
    return {"ok" : True}

@app.get("/text_notes/", response_model=List[TextNote])
async def get_text_notes(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_async_session)):
    result = await db.exec(select(TextNote).where(TextNote.user_id == user.id).order_by(TextNote.date.desc()))
    result = result.all()
    return result

@app.put("/voice_notes/")#, response_model=VoiceNote)
async def create_voice_note(voiceNote: UploadFile, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_async_session)):
    contents = await voiceNote.read()
    db_voice_note = VoiceNote(content=contents)
    db_voice_note.user_id = user.id
    db.add(db_voice_note)
    await db.commit()
    await db.refresh(db_voice_note)
    #return db_voice_note

@app.get("/voice_notes/", response_model=List[VoiceNote])
async def get_voice_notes(user: User = Depends(get_current_user), db: AsyncSession = Depends(get_async_session)):
    result = await db.exec(select(VoiceNote).where(VoiceNote.user_id == user.id))
    result = result.all()
    return result

@app.get("/voice_note/{note_id}")
async def get_voice_note(note_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_async_session)):
    db_voice_note = await db.get(VoiceNote, note_id)
    if not db_voice_note:
        raise HTTPException(status_code=404, detail="voice note not found.")
    if db_voice_note.user_id != user.id:
        raise HTTPException(status_code=403, detail="not allowed to access note.")
    #file = BytesIO(db_voice_note.content)
    return FileResponse(db_voice_note.path)
    #return StreamingResponse(file, media_type="audio/mpeg")

@app.on_event("startup")
async def startup():
    async with async_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all) 
    # create a dummy entry
    #await User.objects.get_or_create(email="test@test.com")
    #await Item.objects.get_or_create(path="/test.txt", day=datetime.datetime.now())

@app.post("/new_voice_notes/")
async def post_voice_note(date: datetime.datetime = Form(...), in_file: UploadFile=File(...), user: User = Depends(get_current_user), db: AsyncSession = Depends(get_async_session)):
    # ...
    filename = f'{secrets.token_hex(8)}.m4a'
    file_path = Path('/data') / filename
    db_voice_note = VoiceNote(date=date, user_id=user.id, path=str(file_path))
    #db_voice_note.user_id = user.id
    #db_voice_note.path = in_file.filename
    async with aiofiles.open(file_path, 'wb') as out_file:
        while content := await in_file.read(1024):  # async read chunk
            await out_file.write(content)  # async write chunk
    db.add(db_voice_note)
    await db.commit()
    await db.refresh(db_voice_note)
    return db_voice_note

@app.delete("/voice_notes/{note_id}")
async def delete_voice_note(note_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_async_session)):
    db_voice_note = await db.get(VoiceNote, note_id)
    if not db_voice_note:
        raise HTTPException(status_code=404, detail="text note not found.")
    if db_voice_note.user_id != user.id:
        raise HTTPException(status_code=403, detail="not allowed to update note.")
    try:
        os.remove(db_voice_note.path)
    except FileNotFoundError:
        print("File was not found")
    await db.delete(db_voice_note)
    await db.commit()
    return {"ok" : True}