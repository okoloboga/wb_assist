# 📚 AI Chat Service - Документация

Полная документация AI Chat Service для продавцов Wildberries.

---

## 📖 Основная документация

### 🎯 [AI_CHAT_SPECIFICATION.md](./AI_CHAT_SPECIFICATION.md)
**Техническое задание и спецификация**
- Полное описание функционала
- Требования к системе
- API спецификации
- Интеграция с Telegram ботом
- Примеры использования

### 🏗️ [ARCHITECTURE.md](./ARCHITECTURE.md)
**Архитектура сервиса**
- Общая архитектура
- Компоненты системы
- Схемы баз данных
- Потоки данных
- Технологический стек

### 📋 [INDEX.md](./INDEX.md)
**Навигация и быстрый старт**
- Оглавление всей документации
- Быстрый доступ к разделам
- Ссылки на важные документы

---

## 🚀 Руководства

### 🎯 [PERSONALIZATION_GUIDE.md](./PERSONALIZATION_GUIDE.md)
**Персонализация ответов AI**
- Как работает персонализация
- Доступ к данным пользователя
- Примеры персонализированных ответов
- Архитектура и поток данных
- Тестирование персонализации

📊 **Что включено:**
- Статистика продаж за 7 дней
- Данные о заказах и остатках
- Топ-3 товара по продажам
- Отзывы и рейтинги

### 🧪 [TELEGRAM_TEST_GUIDE.md](./TELEGRAM_TEST_GUIDE.md)
**Руководство по тестированию в Telegram**
- Как запустить систему
- Навигация в боте
- Сценарии тестирования
- Примеры вопросов
- Проверка функций

---

## 📝 История и изменения

### 📅 [CHANGELOG.md](./CHANGELOG.md)
**История изменений**
- Версия 1.1.0 - Персонализация и UX улучшения
- Версия 1.0.1 - UX улучшения (кнопки)
- Версия 1.0.0 - Первый релиз

### 🔄 [UPDATES.md](./UPDATES.md)
**Детальные обновления**
- Подробное описание изменений
- Технические детали
- Миграция и обновление
- Changelog по версиям

---

## 🎯 Быстрая навигация

### Для разработчиков

- 🔧 **Настройка и запуск** → [AI_CHAT_SPECIFICATION.md](./AI_CHAT_SPECIFICATION.md#запуск)
- 🏗️ **Архитектура** → [ARCHITECTURE.md](./ARCHITECTURE.md)
- 🎯 **Персонализация** → [PERSONALIZATION_GUIDE.md](./PERSONALIZATION_GUIDE.md)
- 📝 **API документация** → [AI_CHAT_SPECIFICATION.md](./AI_CHAT_SPECIFICATION.md#эндпоинты)

### Для тестировщиков

- 🧪 **Тестирование в Telegram** → [TELEGRAM_TEST_GUIDE.md](./TELEGRAM_TEST_GUIDE.md)
- ✅ **Сценарии тестов** → [TELEGRAM_TEST_GUIDE.md](./TELEGRAM_TEST_GUIDE.md#сценарий-тестирования)
- 🎯 **Примеры вопросов** → [TELEGRAM_TEST_GUIDE.md](./TELEGRAM_TEST_GUIDE.md#примеры-вопросов-для-ai)

### Для менеджеров

- 📊 **Возможности сервиса** → [AI_CHAT_SPECIFICATION.md](./AI_CHAT_SPECIFICATION.md#основные-возможности)
- 🎯 **Персонализация** → [PERSONALIZATION_GUIDE.md](./PERSONALIZATION_GUIDE.md#обзор)
- 📅 **История изменений** → [CHANGELOG.md](./CHANGELOG.md)

---

## 📦 Структура документации

```
docs/
├── README.md                      # Этот файл
├── AI_CHAT_SPECIFICATION.md       # Полное ТЗ (34KB)
├── ARCHITECTURE.md                # Архитектура (18KB)
├── INDEX.md                       # Оглавление (9KB)
├── PERSONALIZATION_GUIDE.md       # Руководство по персонализации (17KB)
├── TELEGRAM_TEST_GUIDE.md         # Руководство по тестированию (7KB)
├── CHANGELOG.md                   # История изменений (7KB)
└── UPDATES.md                     # Детали обновлений (5KB)
```

**Общий размер:** ~97KB высококачественной документации

---

## 🔍 Поиск по документации

### По функционалу

- **AI чат** → [AI_CHAT_SPECIFICATION.md](./AI_CHAT_SPECIFICATION.md)
- **Rate limiting** → [ARCHITECTURE.md](./ARCHITECTURE.md) + [AI_CHAT_SPECIFICATION.md](./AI_CHAT_SPECIFICATION.md)
- **Персонализация** → [PERSONALIZATION_GUIDE.md](./PERSONALIZATION_GUIDE.md)
- **API эндпоинты** → [AI_CHAT_SPECIFICATION.md](./AI_CHAT_SPECIFICATION.md#эндпоинты)
- **База данных** → [ARCHITECTURE.md](./ARCHITECTURE.md#база-данных)

### По технологиям

- **FastAPI** → [ARCHITECTURE.md](./ARCHITECTURE.md#технологии)
- **OpenAI** → [AI_CHAT_SPECIFICATION.md](./AI_CHAT_SPECIFICATION.md) + [PERSONALIZATION_GUIDE.md](./PERSONALIZATION_GUIDE.md)
- **PostgreSQL** → [ARCHITECTURE.md](./ARCHITECTURE.md#база-данных)
- **Docker** → [AI_CHAT_SPECIFICATION.md](./AI_CHAT_SPECIFICATION.md#docker)
- **Telegram Bot** → [TELEGRAM_TEST_GUIDE.md](./TELEGRAM_TEST_GUIDE.md)

---

## 💡 Полезные ссылки

### Внутренние

- [Главный README](../README.md)
- [Исходный код](../app/)
- [Тесты](../tests/)
- [Конфигурация](../requirements.txt)

### Внешние

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [OpenAI API Reference](https://platform.openai.com/docs/api-reference)
- [Aiogram Documentation](https://docs.aiogram.dev/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)

---

## 📞 Поддержка

Для вопросов и предложений:
- 📧 Email: support@wb-assist.ru
- 💬 Telegram: @wb_assist_support
- 🐛 Issues: [GitHub Issues](https://github.com/your-repo/issues)

---

**Версия документации:** 1.1.0  
**Последнее обновление:** 29 октября 2025  
**Автор:** WB Assist Team

