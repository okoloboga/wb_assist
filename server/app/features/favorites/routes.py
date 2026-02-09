"""
API endpoints для работы с избранными товарами
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import List

from .models import Favorite
from .schemas import FavoriteCreate, FavoriteResponse
from ...core.database import get_db

router = APIRouter(prefix="/favorites", tags=["favorites"])


@router.post("/", response_model=FavoriteResponse)
async def add_to_favorites(
    favorite: FavoriteCreate,
    db: Session = Depends(get_db)
):
    """Добавить товар в избранное"""
    try:
        db_favorite = Favorite(**favorite.dict())
        db.add(db_favorite)
        db.commit()
        db.refresh(db_favorite)
        return db_favorite
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Product already in favorites"
        )


@router.get("/{user_telegram_id}", response_model=List[FavoriteResponse])
async def get_favorites(user_telegram_id: int, db: Session = Depends(get_db)):
    """Получить список избранных товаров"""
    favorites = db.query(Favorite).filter(
        Favorite.user_telegram_id == user_telegram_id
    ).order_by(Favorite.added_at.desc()).all()
    return favorites


@router.delete("/{user_telegram_id}/{product_id}")
async def remove_from_favorites(
    user_telegram_id: int,
    product_id: str,
    db: Session = Depends(get_db)
):
    """Удалить товар из избранного"""
    favorite = db.query(Favorite).filter(
        Favorite.user_telegram_id == user_telegram_id,
        Favorite.product_id == product_id
    ).first()

    if not favorite:
        raise HTTPException(status_code=404, detail="Favorite not found")

    db.delete(favorite)
    db.commit()
    return {"status": "ok", "message": "Removed from favorites"}


@router.get("/{user_telegram_id}/check/{product_id}")
async def check_favorite(
    user_telegram_id: int,
    product_id: str,
    db: Session = Depends(get_db)
):
    """Проверить, в избранном ли товар"""
    favorite = db.query(Favorite).filter(
        Favorite.user_telegram_id == user_telegram_id,
        Favorite.product_id == product_id
    ).first()

    return {"is_favorite": favorite is not None}
