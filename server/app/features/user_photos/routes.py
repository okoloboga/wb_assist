"""
API endpoints для работы с фото пользователей
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List

from .models import UserPhoto
from .schemas import UserPhotoCreate, UserPhotoResponse
from ...core.database import get_db

router = APIRouter(prefix="/photos", tags=["user_photos"])


@router.post("/", response_model=UserPhotoResponse)
async def create_photo(photo: UserPhotoCreate, db: Session = Depends(get_db)):
    """Сохранить фото пользователя"""
    db_photo = UserPhoto(**photo.dict())
    db.add(db_photo)
    db.commit()
    db.refresh(db_photo)
    return db_photo


@router.get("/{user_telegram_id}", response_model=List[UserPhotoResponse])
async def get_user_photos(user_telegram_id: int, db: Session = Depends(get_db)):
    """Получить все фото пользователя"""
    photos = db.query(UserPhoto).filter(
        UserPhoto.user_telegram_id == user_telegram_id,
        UserPhoto.is_active == True
    ).order_by(UserPhoto.uploaded_at.desc()).all()
    return photos


@router.delete("/{photo_id}")
async def delete_photo(photo_id: int, db: Session = Depends(get_db)):
    """Удалить фото (мягкое удаление)"""
    photo = db.query(UserPhoto).filter(UserPhoto.id == photo_id).first()
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")

    photo.is_active = False
    db.commit()
    return {"status": "ok", "message": "Photo deleted"}
