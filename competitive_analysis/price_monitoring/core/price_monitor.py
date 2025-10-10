"""
Основной класс для мониторинга цен товаров.

Содержит логику для добавления товаров в мониторинг, обновления цен,
сравнения с пороговыми значениями и управления процессом мониторинга.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Callable, Set
from enum import Enum
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
import threading

# Импорты моделей
from ..models.product import Product
from ..models.price_history import PriceHistory, PriceHistoryEntry, PriceSource, PriceChangeType
from ..models.competitor import Competitor, CompetitorProduct
from .exceptions import PriceMonitorError, ProductNotFoundError, InvalidPriceError


class MonitoringStatus(Enum):
    """Статус мониторинга."""
    ACTIVE = "active"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"


class PriceChangeEvent(Enum):
    """Типы событий изменения цены."""
    THRESHOLD_EXCEEDED = "threshold_exceeded"
    PRICE_INCREASED = "price_increased"
    PRICE_DECREASED = "price_decreased"
    COMPETITOR_PRICE_CHANGED = "competitor_price_changed"
    TARGET_PRICE_REACHED = "target_price_reached"
    PRICE_BELOW_MINIMUM = "price_below_minimum"
    PRICE_ABOVE_MAXIMUM = "price_above_maximum"


@dataclass
class MonitoringConfig:
    """Конфигурация мониторинга."""
    update_interval: int = 3600  # Интервал обновления в секундах (по умолчанию 1 час)
    max_concurrent_updates: int = 10  # Максимальное количество одновременных обновлений
    retry_attempts: int = 3  # Количество попыток при ошибке
    retry_delay: int = 60  # Задержка между попытками в секундах
    enable_notifications: bool = True  # Включить уведомления
    log_level: str = "INFO"  # Уровень логирования


@dataclass
class PriceAlert:
    """Уведомление об изменении цены."""
    product_id: str
    event_type: PriceChangeEvent
    old_price: float
    new_price: float
    change_percent: float
    timestamp: datetime = field(default_factory=datetime.now)
    message: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class PriceMonitor:
    """
    Основной класс для мониторинга цен товаров.
    
    Управляет процессом мониторинга цен, включая добавление товаров,
    обновление цен, сравнение с пороговыми значениями и генерацию уведомлений.
    """
    
    def __init__(self, config: Optional[MonitoringConfig] = None):
        """
        Инициализация монитора цен.
        
        Args:
            config: Конфигурация мониторинга
        """
        self.config = config or MonitoringConfig()
        self.status = MonitoringStatus.STOPPED
        
        # Хранилища данных
        self._monitored_products: Dict[str, Product] = {}
        self._price_histories: Dict[str, PriceHistory] = {}
        self._competitors: Dict[str, List[Competitor]] = {}
        
        # Обработчики событий
        self._event_handlers: Dict[PriceChangeEvent, List[Callable]] = {
            event: [] for event in PriceChangeEvent
        }
        
        # Управление потоками
        self._executor = ThreadPoolExecutor(max_workers=self.config.max_concurrent_updates)
        self._monitoring_task: Optional[asyncio.Task] = None
        self._stop_event = threading.Event()
        
        # Настройка логирования
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(getattr(logging, self.config.log_level))
        
        # Статистика
        self._stats = {
            "total_products": 0,
            "active_products": 0,
            "last_update": None,
            "total_updates": 0,
            "failed_updates": 0,
            "alerts_generated": 0
        }
    
    def add_product(self, product: Product, competitors: Optional[List[Competitor]] = None) -> None:
        """
        Добавляет товар в мониторинг.
        
        Args:
            product: Товар для мониторинга
            competitors: Список конкурентов (опционально)
            
        Raises:
            PriceMonitorError: При ошибке добавления товара
        """
        try:
            if not product.id:
                raise ValueError("ID товара не может быть пустым")
            
            if product.current_price <= 0:
                raise InvalidPriceError(f"Некорректная цена товара: {product.current_price}")
            
            # Добавляем товар в мониторинг
            self._monitored_products[product.id] = product
            
            # Создаем историю цен если её нет
            if product.id not in self._price_histories:
                self._price_histories[product.id] = PriceHistory(product_id=product.id)
            
            # Добавляем первую запись в историю
            initial_entry = PriceHistoryEntry(
                product_id=product.id,
                price=product.current_price,
                timestamp=datetime.now(),
                source=PriceSource.MANUAL,
                change_type=PriceChangeType.STABLE
            )
            self._price_histories[product.id].entries.append(initial_entry)
            
            # Добавляем конкурентов если они есть
            if competitors:
                self._competitors[product.id] = competitors
            
            # Обновляем статистику
            self._stats["total_products"] = len(self._monitored_products)
            if product.tracking_enabled:
                self._stats["active_products"] += 1
            
            self.logger.info(f"Товар {product.name} (ID: {product.id}) добавлен в мониторинг")
            
        except Exception as e:
            raise PriceMonitorError(f"Ошибка при добавлении товара в мониторинг: {str(e)}")
    
    def remove_product(self, product_id: str) -> None:
        """
        Удаляет товар из мониторинга.
        
        Args:
            product_id: ID товара для удаления
            
        Raises:
            ProductNotFoundError: Если товар не найден
        """
        if product_id not in self._monitored_products:
            raise ProductNotFoundError(f"Товар с ID {product_id} не найден в мониторинге")
        
        # Проверяем, был ли товар активным
        was_active = self._monitored_products[product_id].tracking_enabled
        
        # Удаляем товар и связанные данные
        del self._monitored_products[product_id]
        if product_id in self._competitors:
            del self._competitors[product_id]
        
        # Обновляем статистику
        self._stats["total_products"] = len(self._monitored_products)
        if was_active:
            self._stats["active_products"] -= 1
        
        self.logger.info(f"Товар с ID {product_id} удален из мониторинга")
    
    def update_product_price(self, product_id: str, new_price: float, 
                           source: PriceSource = PriceSource.MANUAL) -> Optional[PriceAlert]:
        """
        Обновляет цену товара и проверяет пороговые значения.
        
        Args:
            product_id: ID товара
            new_price: Новая цена
            source: Источник информации о цене
            
        Returns:
            Уведомление об изменении цены, если превышен порог
            
        Raises:
            ProductNotFoundError: Если товар не найден
            InvalidPriceError: Если цена некорректна
        """
        if product_id not in self._monitored_products:
            raise ProductNotFoundError(f"Товар с ID {product_id} не найден в мониторинге")
        
        if new_price <= 0:
            raise InvalidPriceError(f"Некорректная цена: {new_price}")
        
        product = self._monitored_products[product_id]
        old_price = product.current_price
        
        # Обновляем цену товара
        product.current_price = new_price
        product.last_updated = datetime.now()
        
        # Определяем тип изменения
        if new_price > old_price:
            change_type = PriceChangeType.INCREASE
        elif new_price < old_price:
            change_type = PriceChangeType.DECREASE
        else:
            change_type = PriceChangeType.STABLE
        
        # Добавляем запись в историю
        history_entry = PriceHistoryEntry(
            product_id=product_id,
            price=new_price,
            timestamp=datetime.now(),
            source=source,
            change_type=change_type,
            metadata={"old_price": old_price}
        )
        self._price_histories[product_id].entries.append(history_entry)
        
        # Обновляем статистику
        self._stats["total_updates"] += 1
        self._stats["last_update"] = datetime.now()
        
        # Проверяем пороговые значения
        alert = self._check_price_thresholds(product, old_price, new_price)
        
        if alert:
            self._trigger_event(alert.event_type, alert)
            self._stats["alerts_generated"] += 1
        
        self.logger.info(f"Цена товара {product.name} обновлена: {old_price} -> {new_price}")
        
        return alert
    
    def _check_price_thresholds(self, product: Product, old_price: float, new_price: float) -> Optional[PriceAlert]:
        """
        Проверяет пороговые значения и создает уведомления.
        
        Args:
            product: Товар
            old_price: Старая цена
            new_price: Новая цена
            
        Returns:
            Уведомление, если порог превышен
        """
        if old_price == new_price:
            return None
        
        # Рассчитываем процент изменения
        change_percent = ((new_price - old_price) / old_price) * 100
        
        # Проверяем достижение целевой цены (приоритет выше порога)
        if product.target_price and abs(new_price - product.target_price) <= 0.01:
            alert = PriceAlert(
                product_id=product.id,
                event_type=PriceChangeEvent.TARGET_PRICE_REACHED,
                old_price=old_price,
                new_price=new_price,
                change_percent=change_percent,
                message=f"Товар '{product.name}' достиг целевой цены {product.target_price}"
            )
            return alert
        
        # Проверяем выход за границы min/max цены (приоритет выше порога)
        if product.min_price and new_price < product.min_price:
            alert = PriceAlert(
                product_id=product.id,
                event_type=PriceChangeEvent.PRICE_BELOW_MINIMUM,
                old_price=old_price,
                new_price=new_price,
                change_percent=change_percent,
                message=f"Цена товара '{product.name}' упала ниже минимальной ({product.min_price})"
            )
            return alert
        
        if product.max_price and new_price > product.max_price:
            alert = PriceAlert(
                product_id=product.id,
                event_type=PriceChangeEvent.PRICE_ABOVE_MAXIMUM,
                old_price=old_price,
                new_price=new_price,
                change_percent=change_percent,
                message=f"Цена товара '{product.name}' превысила максимальную ({product.max_price})"
            )
            return alert
        
        # Проверяем основной порог изменения цены
        if abs(change_percent) >= product.price_threshold:
            event_type = PriceChangeEvent.PRICE_INCREASED if change_percent > 0 else PriceChangeEvent.PRICE_DECREASED
            
            alert = PriceAlert(
                product_id=product.id,
                event_type=PriceChangeEvent.THRESHOLD_EXCEEDED,
                old_price=old_price,
                new_price=new_price,
                change_percent=change_percent,
                message=f"Цена товара '{product.name}' изменилась на {change_percent:.2f}%"
            )
            return alert

        return None
    
    def add_event_handler(self, event_type: PriceChangeEvent, handler: Callable[[PriceAlert], None]) -> None:
        """
        Добавляет обработчик события изменения цены.
        
        Args:
            event_type: Тип события
            handler: Функция-обработчик
        """
        self._event_handlers[event_type].append(handler)
        self.logger.info(f"Добавлен обработчик для события {event_type.value}")
    
    def _trigger_event(self, event_type: PriceChangeEvent, alert: PriceAlert) -> None:
        """
        Запускает обработчики события.
        
        Args:
            event_type: Тип события
            alert: Данные уведомления
        """
        handlers = self._event_handlers.get(event_type, [])
        for handler in handlers:
            try:
                handler(alert)
            except Exception as e:
                self.logger.error(f"Ошибка в обработчике события {event_type.value}: {str(e)}")
    
    def get_product(self, product_id: str) -> Product:
        """
        Получает товар по ID.
        
        Args:
            product_id: ID товара
            
        Returns:
            Объект товара
            
        Raises:
            ProductNotFoundError: Если товар не найден
        """
        if product_id not in self._monitored_products:
            raise ProductNotFoundError(f"Товар с ID {product_id} не найден в мониторинге")
        
        return self._monitored_products[product_id]
    
    def get_price_history(self, product_id: str) -> PriceHistory:
        """
        Получает историю цен товара.
        
        Args:
            product_id: ID товара
            
        Returns:
            История цен товара
            
        Raises:
            ProductNotFoundError: Если товар не найден
        """
        if product_id not in self._price_histories:
            raise ProductNotFoundError(f"История цен для товара {product_id} не найдена")
        
        return self._price_histories[product_id]
    
    def get_monitored_products(self) -> List[Product]:
        """
        Получает список всех товаров в мониторинге.
        
        Returns:
            Список товаров
        """
        return list(self._monitored_products.values())
    
    def get_active_products(self) -> List[Product]:
        """
        Получает список активных товаров в мониторинге.
        
        Returns:
            Список активных товаров
        """
        return [product for product in self._monitored_products.values() if product.tracking_enabled]
    
    def enable_product_tracking(self, product_id: str) -> None:
        """
        Включает мониторинг для товара.
        
        Args:
            product_id: ID товара
            
        Raises:
            ProductNotFoundError: Если товар не найден
        """
        if product_id not in self._monitored_products:
            raise ProductNotFoundError(f"Товар с ID {product_id} не найден в мониторинге")
        
        product = self._monitored_products[product_id]
        if not product.tracking_enabled:
            product.tracking_enabled = True
            self._stats["active_products"] += 1
            self.logger.info(f"Мониторинг товара {product.name} включен")
    
    def disable_product_tracking(self, product_id: str) -> None:
        """
        Отключает мониторинг для товара.
        
        Args:
            product_id: ID товара
            
        Raises:
            ProductNotFoundError: Если товар не найден
        """
        if product_id not in self._monitored_products:
            raise ProductNotFoundError(f"Товар с ID {product_id} не найден в мониторинге")
        
        product = self._monitored_products[product_id]
        if product.tracking_enabled:
            product.tracking_enabled = False
            self._stats["active_products"] -= 1
            self.logger.info(f"Мониторинг товара {product.name} отключен")
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Получает статистику мониторинга.
        
        Returns:
            Словарь со статистикой
        """
        return {
            **self._stats,
            "status": self.status.value,
            "config": {
                "update_interval": self.config.update_interval,
                "max_concurrent_updates": self.config.max_concurrent_updates,
                "enable_notifications": self.config.enable_notifications
            }
        }
    
    def start_monitoring(self) -> None:
        """Запускает процесс мониторинга."""
        if self.status == MonitoringStatus.ACTIVE:
            self.logger.warning("Мониторинг уже запущен")
            return
        
        self.status = MonitoringStatus.ACTIVE
        self._stop_event.clear()
        self.logger.info("Мониторинг цен запущен")
    
    def stop_monitoring(self) -> None:
        """Останавливает процесс мониторинга."""
        if self.status == MonitoringStatus.STOPPED:
            self.logger.warning("Мониторинг уже остановлен")
            return
        
        self.status = MonitoringStatus.STOPPED
        self._stop_event.set()
        self.logger.info("Мониторинг цен остановлен")
    
    def pause_monitoring(self) -> None:
        """Приостанавливает процесс мониторинга."""
        if self.status != MonitoringStatus.ACTIVE:
            self.logger.warning("Мониторинг не активен")
            return
        
        self.status = MonitoringStatus.PAUSED
        self.logger.info("Мониторинг цен приостановлен")
    
    def resume_monitoring(self) -> None:
        """Возобновляет процесс мониторинга."""
        if self.status != MonitoringStatus.PAUSED:
            self.logger.warning("Мониторинг не приостановлен")
            return
        
        self.status = MonitoringStatus.ACTIVE
        self.logger.info("Мониторинг цен возобновлен")
    
    def __del__(self):
        """Деструктор для корректного завершения работы."""
        try:
            self.stop_monitoring()
            if self._executor:
                self._executor.shutdown(wait=True)
        except Exception:
            pass  # Игнорируем ошибки при завершении