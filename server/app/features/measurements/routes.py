"""
API endpoints для работы с параметрами пользователей
"""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from .models import UserMeasurements
from .schemas import UserMeasurementsCreate, UserMeasurementsUpdate, UserMeasurementsResponse
from ...core.database import get_db

router = APIRouter(prefix="/measurements", tags=["measurements"])


@router.get("/{user_telegram_id}", response_model=UserMeasurementsResponse)
async def get_measurements(user_telegram_id: int, db: Session = Depends(get_db)):
    """Получить параметры пользователя"""
    measurements = db.query(UserMeasurements).filter(
        UserMeasurements.user_telegram_id == user_telegram_id
    ).first()

    if not measurements:
        raise HTTPException(status_code=404, detail="Measurements not found")

    return measurements


@router.post("/", response_model=UserMeasurementsResponse)
async def create_measurements(
    measurements: UserMeasurementsCreate,
    db: Session = Depends(get_db)
):
    """Создать параметры пользователя"""
    # Проверяем, есть ли уже параметры
    existing = db.query(UserMeasurements).filter(
        UserMeasurements.user_telegram_id == measurements.user_telegram_id
    ).first()

    if existing:
        raise HTTPException(
            status_code=400,
            detail="Measurements already exist. Use PUT to update."
        )

    db_measurements = UserMeasurements(**measurements.dict())
    db.add(db_measurements)
    db.commit()
    db.refresh(db_measurements)
    return db_measurements


@router.put("/{user_telegram_id}", response_model=UserMeasurementsResponse)
async def update_measurements(
    user_telegram_id: int,
    measurements: UserMeasurementsUpdate,
    db: Session = Depends(get_db)
):
    """Обновить параметры пользователя"""
    db_measurements = db.query(UserMeasurements).filter(
        UserMeasurements.user_telegram_id == user_telegram_id
    ).first()

    if not db_measurements:
        # Создаем новые параметры, если их нет
        db_measurements = UserMeasurements(
            user_telegram_id=user_telegram_id,
            **measurements.dict(exclude_unset=True)
        )
        db.add(db_measurements)
    else:
        # Обновляем существующие
        for key, value in measurements.dict(exclude_unset=True).items():
            setattr(db_measurements, key, value)

    db.commit()
    db.refresh(db_measurements)
    return db_measurements


@router.post("/{user_telegram_id}/recommend-size")
async def recommend_size(
    user_telegram_id: int,
    product_id: str,
    db: Session = Depends(get_db)
):
    """Рекомендовать размер на основе параметров пользователя"""
    measurements = db.query(UserMeasurements).filter(
        UserMeasurements.user_telegram_id == user_telegram_id
    ).first()

    if not measurements:
        return {
            "success": False,
            "message": "Параметры не найдены. Укажите свои размеры."
        }

    # Простая логика рекомендации на основе российского размера
    if measurements.russian_size:
        return {
            "success": True,
            "recommended_size": measurements.russian_size,
            "message": f"Рекомендуемый размер: {measurements.russian_size}"
        }

    return {
        "success": False,
        "message": "Укажите российский размер для получения рекомендации"
    }
