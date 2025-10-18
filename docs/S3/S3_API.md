# 📘 S3 API: Система уведомлений

## 🎯 Цель этапа

Реализовать централизованную систему уведомлений для пользователей бота о ключевых событиях Wildberries. Уведомления доставляются через Telegram в реальном времени, настраиваются пользователем и обеспечивают устойчивую работу даже при временных сбоях интеграций.

## 🔔 Типы уведомлений

| Категория  | Событие             | Описание                      | Приоритет   |
| ---------- | ------------------- | ----------------------------- | ----------- |
| 📦 Заказы  | Новый заказ         | Новый заказ за период         | Высокий     |
| 📦 Заказы  | Заказ выкуплен      | Заказ перешел в статус "выкуплен" | Высокий |
| 📦 Заказы  | Заказ отменен       | Заказ перешел в статус "отменен" | Высокий |
| 📦 Заказы  | Заказ возвращен     | Заказ перешел в статус "возврат" | Высокий |
| ⭐ Отзывы   | Негативный отзыв    | Оценка 1–3★                   | Критический |
| 📉 Остатки | Критический остаток | Количество товара ниже порога | Высокий     |

---

## 🔄 Необходимые эндпоинты из S2 API

### **1. Мониторинг событий (Источник данных)**

#### **GET /api/v1/bot/orders/recent**
**Назначение:** Получение последних заказов для обнаружения новых и изменений статуса  
**Использование:** Сравнение с предыдущим состоянием для выявления новых заказов и изменений статуса (выкупы, отмены, возвраты)  
**Параметры:**
- `limit` (int, optional): Количество заказов (по умолчанию 10)
- `offset` (int, optional): Смещение для пагинации (по умолчанию 0)
- `include_status_changes` (bool, optional): Включить заказы с изменениями статуса (по умолчанию true)

**Ответ:**
```json
{
  "success": true,
  "data": {
    "orders": [
      {
        "id": 154,
        "date": "2025-10-03T12:48:00",
        "amount": 1410,
        "product_name": "Шифоновая блузка (S)",
        "brand": "SLAVALOOK BRAND",
        "warehouse_from": "Электросталь",
        "warehouse_to": "ЦФО/Москва",
        "commission_percent": 29.5,
        "rating": 4.8
      }
    ],
    "statistics": {
      "today_count": 19,
      "today_amount": 26790,
      "average_check": 1410,
      "growth_percent": 12,
      "amount_growth_percent": 8
    }
  }
}
```

#### **GET /api/v1/bot/reviews/summary**
**Назначение:** Получение новых отзывов для обнаружения событий  
**Использование:** Выявление новых отзывов и негативных оценок (1-3★)  
**Параметры:**
- `limit` (int, optional): Количество отзывов (по умолчанию 10)
- `offset` (int, optional): Смещение для пагинации (по умолчанию 0)

**Ответ:**
```json
{
  "success": true,
  "data": {
    "new_reviews": [
      {
        "id": "154",
        "product_name": "Шифоновая блузка",
        "rating": 5,
        "text": "Отличное качество, быстро доставили!",
        "time_ago": "2 часа назад",
        "order_id": 154
      }
    ],
    "statistics": {
      "average_rating": 4.8,
      "total_reviews": 214,
      "new_today": 5
    }
  }
}
```

#### **GET /api/v1/bot/stocks/critical**
**Назначение:** Получение критичных остатков для уведомлений  
**Использование:** Обнаружение товаров с остатками ниже порога (< 5 штук)  
**Параметры:**
- `limit` (int, optional): Количество товаров (по умолчанию 20)
- `offset` (int, optional): Смещение для пагинации (по умолчанию 0)

**Ответ:**
```json
{
  "success": true,
  "data": {
    "critical_products": [
      {
        "nm_id": 270591287,
        "name": "Шифоновая блузка",
        "brand": "SLAVALOOK BRAND",
        "stocks": {
          "S": 13,
          "M": 1,
          "L": 0,
          "XL": 0
        },
        "critical_sizes": ["M"],
        "zero_sizes": ["L", "XL"],
        "sales_per_day": 29.29,
        "price": 1410,
        "commission_percent": 29.5,
        "days_left": {
          "M": 0,
          "S": 1
        }
      }
    ],
    "summary": {
      "critical_count": 2,
      "zero_count": 1,
      "attention_needed": 3,
      "potential_losses": 52.7
    }
  }
}
```

#### **GET /api/v1/bot/analytics/sales**
**Назначение:** Получение аналитики для дневных сводок  
**Использование:** Формирование дневных отчетов (23:58)  
**Параметры:**
- `period` (string, optional): Период анализа (7d, 30d, 90d, по умолчанию 7d)

**Ответ:**
```json
{
  "success": true,
  "data": {
    "sales_periods": {
      "today": {"count": 19, "amount": 26790},
      "yesterday": {"count": 24, "amount": 33840},
      "7_days": {"count": 156, "amount": 234500},
      "30_days": {"count": 541, "amount": 892300},
      "90_days": {"count": 686, "amount": 1156800}
    },
    "dynamics": {
      "yesterday_growth_percent": -21,
      "week_growth_percent": 12,
      "average_check": 1410,
      "conversion_percent": 3.2
    },
    "top_products": [
      {
        "nm_id": 270591287,
        "name": "Шифоновая блузка",
        "sales_count": 73,
        "sales_amount": 46800,
        "rating": 4.8,
        "stocks": {"S": 13, "M": 1, "L": 0, "XL": 0}
      }
    ]
  }
}
```

---

## 🔧 Новые эндпоинты для системы уведомлений

### **1. Управление настройками уведомлений**

#### **GET /api/v1/bot/notifications/settings**
**Назначение:** Получение настроек уведомлений пользователя  
**Параметры:** Нет  
**Ответ:**
```json
{
  "success": true,
  "data": {
    "user_id": 123456789,
    "notifications_enabled": true,
    "frequency": "5_minutes",
    "notification_types": {
      "new_orders": {
        "enabled": true,
        "priority": "HIGH"
      },
      "order_buyouts": {
        "enabled": true,
        "priority": "HIGH"
      },
      "order_cancellations": {
        "enabled": true,
        "priority": "HIGH"
      },
      "order_returns": {
        "enabled": true,
        "priority": "HIGH"
      },
      "negative_reviews": {
        "enabled": true,
        "priority": "CRITICAL"
      },
      "critical_stocks": {
        "enabled": true,
        "priority": "HIGH"
      }
    },
    "grouping": {
      "enabled": true,
      "max_group_size": 5,
      "group_timeout": 300
    }
  },
  "telegram_text": "🔔 НАСТРОЙКИ УВЕДОМЛЕНИЙ\n\n✅ Уведомления включены\n⏰ Частота: каждые 5 минут\n\n📦 НОВЫЕ ЗАКАЗЫ: ✅ Включено (Высокий)\n💰 ВЫКУПЫ: ✅ Включено (Высокий)\n❌ ОТМЕНЫ: ✅ Включено (Высокий)\n🔄 ВОЗВРАТЫ: ✅ Включено (Высокий)\n⚠️ НЕГАТИВНЫЕ ОТЗЫВЫ: ✅ Включено (Критический)\n📉 ОСТАТКИ: ✅ Включено (Высокий)\n\n💡 Группировка: включена (до 5 сообщений, 5 мин)"
}
```

#### **POST /api/v1/bot/notifications/settings**
**Назначение:** Обновление настроек уведомлений  
**Параметры:**
```json
{
  "notifications_enabled": true,
  "frequency": "5_minutes",
  "notification_types": {
    "new_orders": {"enabled": true, "priority": "HIGH"},
    "order_buyouts": {"enabled": true, "priority": "HIGH"},
    "order_cancellations": {"enabled": true, "priority": "HIGH"},
    "order_returns": {"enabled": true, "priority": "HIGH"},
    "negative_reviews": {"enabled": true, "priority": "CRITICAL"},
    "critical_stocks": {"enabled": true, "priority": "HIGH"}
  },
  "grouping": {
    "enabled": true,
    "max_group_size": 5,
    "group_timeout": 300
  }
}
```
**Ответ:**
```json
{
  "success": true,
  "data": {
    "updated_at": "2025-01-28T14:30:15",
    "changes_count": 3
  },
  "telegram_text": "✅ НАСТРОЙКИ ОБНОВЛЕНЫ\n\n🔔 Уведомления: включены\n⏰ Частота: каждые 5 минут\n\n📦 Новые заказы: ✅ Включено\n💰 Выкупы: ✅ Включено\n❌ Отмены: ✅ Включено\n🔄 Возвраты: ✅ Включено\n⚠️ Негативные отзывы: ✅ Включено\n📉 Критичные остатки: ✅ Включено\n\n💡 Изменения сохранены и вступят в силу немедленно"
}
```

### **2. История уведомлений**

#### **GET /api/v1/bot/notifications/history**
**Назначение:** Получение истории уведомлений пользователя  
**Параметры:**
- `limit` (int, optional): Количество уведомлений (по умолчанию 20)
- `offset` (int, optional): Смещение для пагинации (по умолчанию 0)
- `type` (string, optional): Фильтр по типу уведомления
- `date_from` (string, optional): Дата начала (YYYY-MM-DD)
- `date_to` (string, optional): Дата окончания (YYYY-MM-DD)

**Ответ:**
```json
{
  "success": true,
  "data": {
    "notifications": [
      {
        "id": "notif_12345",
        "type": "new_order",
        "priority": "HIGH",
        "title": "Новый заказ #154",
        "content": "Шифоновая блузка (S) | 1410₽",
        "sent_at": "2025-01-28T12:48:00",
        "status": "delivered",
        "delivery_time": "2025-01-28T12:48:02",
        "retry_count": 0
      },
      {
        "id": "notif_12346",
        "type": "order_buyout",
        "priority": "HIGH",
        "title": "Заказ выкуплен #154",
        "content": "Шифоновая блузка (S) | 1410₽ → Выкуплен",
        "sent_at": "2025-01-28T13:15:00",
        "status": "delivered",
        "delivery_time": "2025-01-28T13:15:01",
        "retry_count": 0
      },
      {
        "id": "notif_12347",
        "type": "order_cancellation",
        "priority": "HIGH",
        "title": "Заказ отменен #155",
        "content": "Джинсы классические (M) | 890₽ → Отменен",
        "sent_at": "2025-01-28T14:20:00",
        "status": "delivered",
        "delivery_time": "2025-01-28T14:20:01",
        "retry_count": 0
      },
      {
        "id": "notif_12348",
        "type": "order_return",
        "priority": "HIGH",
        "title": "Заказ возвращен #153",
        "content": "Платье вечернее (L) | 2340₽ → Возврат",
        "sent_at": "2025-01-28T15:30:00",
        "status": "delivered",
        "delivery_time": "2025-01-28T15:30:01",
        "retry_count": 0
      },
      {
        "id": "notif_12349",
        "type": "critical_stocks",
        "priority": "HIGH",
        "title": "Критичные остатки",
        "content": "Шифоновая блузка: M(1) - на 0 дней!",
        "sent_at": "2025-01-28T11:30:00",
        "status": "delivered",
        "delivery_time": "2025-01-28T11:30:01",
        "retry_count": 0
      }
    ],
    "statistics": {
      "total_notifications": 45,
      "delivered": 44,
      "failed": 1,
      "average_delivery_time": 1.2,
      "success_rate": 97.8
    },
    "pagination": {
      "limit": 20,
      "offset": 0,
      "total": 45,
      "has_more": true
    }
  },
  "telegram_text": "📋 ИСТОРИЯ УВЕДОМЛЕНИЙ\n\n🆕 НОВЫЙ ЗАКАЗ #154 | 12:48\n   Шифоновая блузка (S) | 1410₽\n   ✅ Доставлено (0.2с)\n\n💰 ВЫКУП #154 | 13:15\n   Шифоновая блузка (S) | 1410₽ → Выкуплен\n   ✅ Доставлено (0.1с)\n\n❌ ОТМЕНА #155 | 14:20\n   Джинсы классические (M) | 890₽ → Отменен\n   ✅ Доставлено (0.1с)\n\n🔄 ВОЗВРАТ #153 | 15:30\n   Платье вечернее (L) | 2340₽ → Возврат\n   ✅ Доставлено (0.1с)\n\n⚠️ КРИТИЧНЫЕ ОСТАТКИ | 11:30\n   Шифоновая блузка: M(1) - на 0 дней!\n   ✅ Доставлено (0.1с)\n\n📊 СТАТИСТИКА\n• Всего уведомлений: 45\n• Доставлено: 44 (97.8%)\n• Неудачных: 1\n• Среднее время доставки: 1.2с\n\n💡 Показано 20 из 45 уведомлений"
}
```

### **3. Управление очередью уведомлений**

#### **GET /api/v1/bot/notifications/queue/status**
**Назначение:** Статус очереди уведомлений  
**Параметры:** Нет  
**Ответ:**
```json
{
  "success": true,
  "data": {
    "queue_status": "active",
    "pending_notifications": 3,
    "processing_rate": "2.5/sec",
    "average_wait_time": "0.8s",
    "queue_health": "good",
    "last_processed": "2025-01-28T14:29:45",
    "errors_last_hour": 0,
    "retry_queue": 0
  },
  "telegram_text": "🔄 СТАТУС ОЧЕРЕДИ УВЕДОМЛЕНИЙ\n\n✅ Очередь активна\n⏳ Ожидает обработки: 3\n📈 Скорость обработки: 2.5/сек\n⏱️ Среднее время ожидания: 0.8с\n💚 Состояние: отличное\n\n🕐 Последняя обработка: 14:29:45\n❌ Ошибок за час: 0\n🔄 Повторных попыток: 0"
}
```

#### **POST /api/v1/bot/notifications/queue/clear**
**Назначение:** Очистка очереди уведомлений (административная функция)  
**Параметры:** Нет  
**Ответ:**
```json
{
  "success": true,
  "data": {
    "cleared_count": 3,
    "cleared_at": "2025-01-28T14:30:15"
  },
  "telegram_text": "🧹 ОЧЕРЕДЬ ОЧИЩЕНА\n\n🗑️ Удалено уведомлений: 3\n🕐 Время очистки: 14:30:15\n\n💡 Очередь готова к новым уведомлениям"
}
```

### **4. Тестирование уведомлений**

#### **POST /api/v1/bot/notifications/test**
**Назначение:** Отправка тестового уведомления  
**Параметры:**
```json
{
  "type": "order_buyout",
  "test_data": {
    "order_id": 999,
    "product_name": "Тестовый товар",
    "amount": 1000,
    "previous_status": "active",
    "new_status": "buyout"
  }
}
```
**Ответ:**
```json
{
  "success": true,
  "data": {
    "test_notification_id": "test_12345",
    "sent_at": "2025-01-28T14:30:15",
    "delivery_time": "2025-01-28T14:30:16",
    "status": "delivered"
  },
  "telegram_text": "🧪 ТЕСТОВОЕ УВЕДОМЛЕНИЕ\n\n💰 ВЫКУП #999\n   Тестовый товар | 1000₽\n   Статус: активный → выкуплен\n\n✅ Уведомление отправлено\n🆔 ID: test_12345\n🕐 Отправлено: 14:30:15\n📨 Доставлено: 14:30:16\n⏱️ Время доставки: 1.0с\n\n💡 Если вы получили это сообщение, система уведомлений работает корректно"
}
```


---

## 🔄 Архитектура системы уведомлений

### **Компоненты:**

1. **Event Detector** - Обнаружение изменений в данных WB (новые заказы, изменения статуса)
2. **Status Change Monitor** - Отслеживание изменений статуса заказов (выкупы, отмены, возвраты)
3. **Notification Generator** - Создание уведомлений на основе событий
4. **Queue Manager** - Управление очередью уведомлений (Redis)
5. **Delivery Service** - Доставка через Telegram
6. **Settings Manager** - Управление настройками пользователей
7. **History Tracker** - Отслеживание истории уведомлений

### **Потоки данных:**

```
WB API → Event Detector → Status Change Monitor → Notification Generator → Queue Manager → Delivery Service → Telegram
                ↓                    ↓
        Settings Manager ← History Tracker
```

### **Redis структуры:**

- `notifications:queue` - Очередь уведомлений
- `notifications:settings:{user_id}` - Настройки пользователя
- `notifications:history:{user_id}` - История уведомлений
- `notifications:state:{user_id}` - Состояние последней проверки
- `notifications:order_status:{user_id}` - Последние статусы заказов для сравнения
- `notifications:status_changes:{user_id}` - Очередь изменений статуса заказов

---

## 📊 Технические характеристики

### **Производительность:**
- **Частота проверки:** каждые 5 минут
- **Время обработки события:** < 2 секунд
- **Время доставки:** < 5 секунд
- **Пропускная способность:** до 1000 уведомлений/минуту
- **Отслеживание статусов:** до 10,000 заказов одновременно
- **Детекция изменений:** < 1 секунда на пользователя

### **Надежность:**
- **Retry логика:** 5 попыток с экспоненциальной задержкой
- **Очередь:** Redis с персистентностью
- **Мониторинг:** Логирование всех операций
- **Fallback:** Кэширование при недоступности Telegram
- **Статус-трекинг:** Сохранение состояния заказов в Redis
- **Дублирование:** Предотвращение повторных уведомлений об одном событии

### **Масштабируемость:**
- **Архитектура:** Микросервисная
- **Очереди:** Redis кластер
- **База данных:** PostgreSQL для истории
- **Кэш:** Redis для состояния
- **Статус-хранилище:** Redis для отслеживания изменений заказов
- **Параллельная обработка:** До 100 пользователей одновременно

---

*Последнее обновление: 2025-01-28*
*Версия API: S3.01*
*✅ Система уведомлений готова к реализации*
*✅ Все необходимые эндпоинты определены*
*✅ Архитектура спроектирована*
*✅ Поддержка выкупов, отмен и возвратов*
*✅ Отслеживание изменений статуса заказов*
