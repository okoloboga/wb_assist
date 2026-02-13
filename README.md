# 🚀 WB Assist

Комплексная платформа для автоматизации работы с маркетплейсом Wildberries.

## 📋 О проекте

**WB Assist** - это система управления продажами на Wildberries, включающая Telegram-бота, Backend API, AI-ассистента и веб-дашборд.

### Основные возможности

- 📊 **Dashboard** - мониторинг продаж, заказов и остатков в реальном времени
- 🛒 **Управление заказами** - просмотр, фильтрация, экспорт
- 📦 **Контроль остатков** - алерты и прогнозирование
- ⭐ **Работа с отзывами** - мониторинг и ответы
- 📈 **Аналитика** - статистика продаж и трендов
- 🤖 **AI-ассистент** - консультации и генерация контента (GPT-4)
- 👗 **Виртуальная примерка** - Stable Diffusion для одежды
- 🔍 **Анализ конкурентов** - мониторинг цен и остатков

## 🏗 Архитектура

```
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│ Telegram Bot│  │Web Dashboard│  │ Fitting Bot │
│   :8001     │  │   :3000     │  │             │
└──────┬──────┘  └──────┬──────┘  └──────┬──────┘
       │                │                │
       └────────────────┼────────────────┘
                        │
              ┌─────────▼─────────┐
              │  Backend API      │
              │  Server :8002     │
              └─────────┬─────────┘
                        │
       ┌────────────────┼────────────────┐
       │                │                │
┌──────▼──────┐  ┌─────▼─────┐  ┌──────▼──────┐
│ GPT Service │  │PostgreSQL │  │    Redis    │
│   :9000     │  │ +pgvector │  │   Cache     │
└─────────────┘  └───────────┘  └─────────────┘
```

## 🛠 Технологии

**Backend:** Python, FastAPI, SQLAlchemy, PostgreSQL, Redis, Celery  
**Frontend:** React, TypeScript, Vite, TanStack Query, Tailwind CSS  
**Bots:** aiogram 3.x, FSM  
**AI/ML:** OpenAI GPT-4, LangChain, RAG, Stable Diffusion  
**DevOps:** Docker, Docker Compose, Nginx

## 🚀 Быстрый старт

### 1. Клонирование
```bash
git clone https://github.com/okoloboga/wb_assist.git
cd wb_assist
```

### 2. Настройка окружения
```bash
cp .env.example .env
# Отредактируйте .env файл
```

### 3. Запуск
```bash
docker-compose up -d
```

### 4. Проверка
```bash
docker-compose ps
```

**Доступ:**
- Backend API: http://localhost:8002
- Dashboard: http://localhost:3000
- GPT Service: http://localhost:9000
- API Docs: http://localhost:8002/docs

## 📊 Текущая статистика (пример)

```
📦 ЗАКАЗЫ (сегодня)
• Новых заказов: 151
• На сумму: 1,536,289₽
• Вчера: 253 заказов на 2,621,944₽

📦 ОСТАТКИ
• Критичных товаров: 39
• С нулевыми остатками: 25

⭐️ ОТЗЫВЫ
• Средний рейтинг: 4.7/5
• Неотвеченных: 3,542
```

## 📁 Структура проекта

```
wb_assist/
├── bot/                    # Telegram бот
├── server/                 # Backend API
├── gpt_integration/        # GPT сервис
├── fitting_bot/            # Бот виртуальной примерки
├── dashboard/              # React веб-дашборд
├── docs/                   # Документация
└── docker-compose.yml      # Docker конфигурация
```

## 🔐 Переменные окружения

Основные переменные в `.env`:

```env
# Database
POSTGRES_USER=user
POSTGRES_PASSWORD=password
POSTGRES_DB=wb_assist_db

# API
API_SECRET_KEY=your_secret_key

# Telegram
BOT_TOKEN=your_bot_token

# OpenAI
OPENAI_API_KEY=your_openai_key
```

## 📚 Документация

- [Полное описание проекта](PROJECT_OVERVIEW.md)
- [API документация](docs/api/)
- [Deployment guide](docs/deployment/)
- [Dashboard integration](docs/dashboard/)
- [Fitting bot guide](docs/fitter/)

## 🧪 Тестирование

```bash
# Unit тесты
pytest tests/unit -v

# Integration тесты
pytest tests/integration -v

# С покрытием
pytest --cov=app --cov-report=html
```

## 📈 Статус

**Версия:** 2.0  
**Статус:** ✅ Production Ready  
**Последнее обновление:** 09.02.2026

### Готовые модули
- ✅ Dashboard с реальными данными
- ✅ Управление заказами
- ✅ Контроль остатков
- ✅ Работа с отзывами
- ✅ AI-ассистент (GPT-4)
- ✅ Виртуальная примерка
- ✅ Анализ конкурентов
- ✅ Экспорт в Google Sheets

## 🛣 Roadmap

- [ ] Мобильное приложение
- [ ] Telegram Mini App
- [ ] ML для прогнозирования
- [ ] Автоматическое ценообразование
- [ ] Интеграция с Ozon, Яндекс.Маркет

## 📄 Лицензия

Проприетарное ПО. Все права защищены.

## 🔗 Ссылки

- **GitHub:** https://github.com/okoloboga/wb_assist
- **API Docs:** http://localhost:8002/docs
- **Dashboard:** http://localhost:3000

---

Made with ❤️ for Wildberries sellers
