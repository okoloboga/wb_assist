# Production Deployment Guide

## Обзор

Руководство по развертыванию аналитического дашборда в production окружении.

## Предварительные требования

### Системные требования

- **OS:** Ubuntu 20.04+ / Debian 11+ / CentOS 8+
- **CPU:** минимум 2 cores (рекомендуется 4+)
- **RAM:** минимум 4GB (рекомендуется 8GB+)
- **Disk:** минимум 20GB SSD
- **Network:** Статический IP адрес

### Программное обеспечение

- **Python:** 3.11+
- **PostgreSQL:** 14+
- **Redis:** 7+
- **Nginx:** 1.18+
- **Docker:** 20.10+ (опционально)
- **Docker Compose:** 2.0+ (опционально)

---

## Вариант 1: Деплой с Docker Compose (Рекомендуется)

### Шаг 1: Подготовка сервера

```bash
# Обновление системы
sudo apt update && sudo apt upgrade -y

# Установка Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Установка Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Проверка установки
docker --version
docker-compose --version
```

### Шаг 2: Клонирование репозитория

```bash
# Клонирование
git clone https://github.com/your-repo/wb_assist.git
cd wb_assist

# Переключение на production ветку
git checkout production
```

### Шаг 3: Конфигурация окружения

```bash
# Копирование примера конфигурации
cp .env.example .env

# Редактирование конфигурации
nano .env
```

**Обязательные переменные для production:**

```bash
# === Production Configuration ===

# Database
POSTGRES_USER=wb_user
POSTGRES_PASSWORD=<STRONG_PASSWORD>
POSTGRES_DB=wb_assist_db
DATABASE_URL=postgresql://wb_user:<STRONG_PASSWORD>@postgres:5432/wb_assist_db

# Redis
REDIS_URL=redis://redis:6379/0

# Security
API_SECRET_KEY=<GENERATE_STRONG_KEY>

# CORS (ваш домен)
CORS_ORIGINS=https://dashboard.yourdomain.com
CORS_ALLOW_CREDENTIALS=true

# Server
DEBUG=false
LOG_LEVEL=WARNING

# Bot
BOT_TOKEN=<YOUR_BOT_TOKEN>

# Trusted hosts
TRUSTED_HOSTS=dashboard.yourdomain.com,api.yourdomain.com
```

**Генерация безопасных ключей:**

```bash
# API Secret Key
python -c "import secrets; print(secrets.token_urlsafe(32))"

# PostgreSQL Password
openssl rand -base64 32
```

### Шаг 4: Запуск сервисов

```bash
# Сборка и запуск
docker-compose up -d

# Проверка статуса
docker-compose ps

# Просмотр логов
docker-compose logs -f server
```

### Шаг 5: Применение миграций БД

```bash
# Вход в контейнер сервера
docker-compose exec server bash

# Применение миграций
alembic upgrade head

# Проверка миграций
alembic current

# Выход
exit
```

### Шаг 6: Применение индексов БД

```bash
# Создание миграции для индексов
docker-compose exec server bash
alembic revision -m "add_analytics_dashboard_indexes"

# Скопировать содержимое из docs/database/INDEXES_RECOMMENDATIONS.md
# в созданный файл миграции

# Применить миграцию
alembic upgrade head

# Проверка индексов
docker-compose exec postgres psql -U wb_user -d wb_assist_db -c "\di"
```

### Шаг 7: Настройка Nginx

```bash
# Установка Nginx
sudo apt install nginx -y

# Создание конфигурации
sudo nano /etc/nginx/sites-available/dashboard
```

**Конфигурация Nginx:**

```nginx
# HTTP -> HTTPS redirect
server {
    listen 80;
    server_name api.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

# HTTPS
server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;

    # SSL сертификаты (Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/api.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.yourdomain.com/privkey.pem;
    
    # SSL настройки
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    
    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # Proxy settings
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
        
        # Buffering
        proxy_buffering on;
        proxy_buffer_size 4k;
        proxy_buffers 8 4k;
    }
    
    # Health check
    location /system/health {
        proxy_pass http://localhost:8000/system/health;
        access_log off;
    }
    
    # Static files (если есть)
    location /static/ {
        alias /var/www/dashboard/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
```

**Активация конфигурации:**

```bash
# Создание символической ссылки
sudo ln -s /etc/nginx/sites-available/dashboard /etc/nginx/sites-enabled/

# Проверка конфигурации
sudo nginx -t

# Перезапуск Nginx
sudo systemctl restart nginx
```

### Шаг 8: Настройка SSL (Let's Encrypt)

```bash
# Установка Certbot
sudo apt install certbot python3-certbot-nginx -y

# Получение сертификата
sudo certbot --nginx -d api.yourdomain.com

# Автоматическое обновление
sudo certbot renew --dry-run
```

### Шаг 9: Настройка Firewall

```bash
# UFW
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable

# Проверка статуса
sudo ufw status
```

### Шаг 10: Проверка работоспособности

```bash
# Health check
curl https://api.yourdomain.com/system/health

# Тест API
curl https://api.yourdomain.com/api/v1/bot/warehouses?telegram_id=123 \
  -H "X-API-SECRET-KEY: your-key"
```

---

## Вариант 2: Деплой без Docker

### Шаг 1: Установка зависимостей

```bash
# Python и pip
sudo apt install python3.11 python3.11-venv python3-pip -y

# PostgreSQL
sudo apt install postgresql postgresql-contrib -y

# Redis
sudo apt install redis-server -y

# Nginx
sudo apt install nginx -y
```

### Шаг 2: Настройка PostgreSQL

```bash
# Вход в PostgreSQL
sudo -u postgres psql

# Создание пользователя и БД
CREATE USER wb_user WITH PASSWORD 'strong_password';
CREATE DATABASE wb_assist_db OWNER wb_user;
GRANT ALL PRIVILEGES ON DATABASE wb_assist_db TO wb_user;
\q

# Настройка pg_hba.conf
sudo nano /etc/postgresql/14/main/pg_hba.conf
# Добавить: local   all   wb_user   md5

# Перезапуск PostgreSQL
sudo systemctl restart postgresql
```

### Шаг 3: Настройка Redis

```bash
# Редактирование конфигурации
sudo nano /etc/redis/redis.conf

# Изменить:
# bind 127.0.0.1
# maxmemory 256mb
# maxmemory-policy allkeys-lru

# Перезапуск Redis
sudo systemctl restart redis-server
```

### Шаг 4: Установка приложения

```bash
# Клонирование
git clone https://github.com/your-repo/wb_assist.git
cd wb_assist

# Создание виртуального окружения
python3.11 -m venv venv
source venv/bin/activate

# Установка зависимостей
pip install -r requirements.txt

# Конфигурация
cp .env.example .env
nano .env
```

### Шаг 5: Применение миграций

```bash
# Активация виртуального окружения
source venv/bin/activate

# Применение миграций
cd server
alembic upgrade head

# Применение индексов
alembic revision -m "add_analytics_dashboard_indexes"
# Скопировать содержимое из docs/database/INDEXES_RECOMMENDATIONS.md
alembic upgrade head
```

### Шаг 6: Настройка systemd

```bash
# Создание service файла
sudo nano /etc/systemd/system/wb-assist.service
```

**Содержимое файла:**

```ini
[Unit]
Description=WB Assist API Server
After=network.target postgresql.service redis.service

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/var/www/wb_assist/server
Environment="PATH=/var/www/wb_assist/venv/bin"
ExecStart=/var/www/wb_assist/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Активация сервиса:**

```bash
# Перезагрузка systemd
sudo systemctl daemon-reload

# Запуск сервиса
sudo systemctl start wb-assist

# Автозапуск
sudo systemctl enable wb-assist

# Проверка статуса
sudo systemctl status wb-assist
```

---

## Мониторинг и логирование

### Настройка логирования

```bash
# Создание директории для логов
sudo mkdir -p /var/log/wb-assist
sudo chown www-data:www-data /var/log/wb-assist

# Настройка ротации логов
sudo nano /etc/logrotate.d/wb-assist
```

**Конфигурация logrotate:**

```
/var/log/wb-assist/*.log {
    daily
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 www-data www-data
    sharedscripts
    postrotate
        systemctl reload wb-assist > /dev/null 2>&1 || true
    endscript
}
```

### Мониторинг с Prometheus (опционально)

```bash
# Установка Prometheus
wget https://github.com/prometheus/prometheus/releases/download/v2.40.0/prometheus-2.40.0.linux-amd64.tar.gz
tar xvfz prometheus-*.tar.gz
cd prometheus-*

# Конфигурация
nano prometheus.yml
```

**Конфигурация Prometheus:**

```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'wb-assist'
    static_configs:
      - targets: ['localhost:8000']
```

---

## Резервное копирование

### Автоматическое резервное копирование БД

```bash
# Создание скрипта
sudo nano /usr/local/bin/backup-wb-db.sh
```

**Скрипт резервного копирования:**

```bash
#!/bin/bash

BACKUP_DIR="/var/backups/wb-assist"
DATE=$(date +%Y%m%d_%H%M%S)
DB_NAME="wb_assist_db"
DB_USER="wb_user"

# Создание директории
mkdir -p $BACKUP_DIR

# Резервное копирование
pg_dump -U $DB_USER $DB_NAME | gzip > $BACKUP_DIR/backup_$DATE.sql.gz

# Удаление старых бэкапов (старше 7 дней)
find $BACKUP_DIR -name "backup_*.sql.gz" -mtime +7 -delete

echo "Backup completed: backup_$DATE.sql.gz"
```

**Настройка cron:**

```bash
# Сделать скрипт исполняемым
sudo chmod +x /usr/local/bin/backup-wb-db.sh

# Добавить в cron (каждый день в 2:00)
sudo crontab -e
# Добавить: 0 2 * * * /usr/local/bin/backup-wb-db.sh
```

---

## Обновление приложения

### С Docker Compose

```bash
# Остановка сервисов
docker-compose down

# Обновление кода
git pull origin production

# Пересборка и запуск
docker-compose up -d --build

# Применение миграций
docker-compose exec server alembic upgrade head

# Проверка логов
docker-compose logs -f server
```

### Без Docker

```bash
# Остановка сервиса
sudo systemctl stop wb-assist

# Обновление кода
cd /var/www/wb_assist
git pull origin production

# Активация виртуального окружения
source venv/bin/activate

# Обновление зависимостей
pip install -r requirements.txt --upgrade

# Применение миграций
cd server
alembic upgrade head

# Запуск сервиса
sudo systemctl start wb-assist

# Проверка статуса
sudo systemctl status wb-assist
```

---

## Troubleshooting

### Проблема: Сервис не запускается

```bash
# Проверка логов
sudo journalctl -u wb-assist -n 100 --no-pager

# Проверка конфигурации
source venv/bin/activate
python -c "from app.core.config import settings; print(settings.DATABASE_URL)"

# Проверка подключения к БД
psql -U wb_user -d wb_assist_db -h localhost
```

### Проблема: Высокая нагрузка на БД

```bash
# Проверка медленных запросов
docker-compose exec postgres psql -U wb_user -d wb_assist_db

# В psql:
SELECT query, calls, total_time, mean_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;

# Проверка индексов
\di

# Анализ таблиц
ANALYZE VERBOSE;
```

### Проблема: Redis переполнен

```bash
# Проверка использования памяти
redis-cli INFO memory

# Очистка кэша
redis-cli FLUSHDB

# Увеличение maxmemory
sudo nano /etc/redis/redis.conf
# maxmemory 512mb
sudo systemctl restart redis-server
```

---

## Чеклист перед запуском

- [ ] Сервер настроен и обновлен
- [ ] Docker и Docker Compose установлены
- [ ] Переменные окружения настроены
- [ ] Сильные пароли сгенерированы
- [ ] SSL сертификаты получены
- [ ] Nginx настроен и запущен
- [ ] Firewall настроен
- [ ] Миграции БД применены
- [ ] Индексы БД созданы
- [ ] Сервисы запущены и работают
- [ ] Health check проходит
- [ ] Резервное копирование настроено
- [ ] Мониторинг настроен
- [ ] Логирование настроено
- [ ] Тесты пройдены

---

## Контакты и поддержка

Для вопросов по деплою обращайтесь к документации:
- **Конфигурация:** `docs/deployment/DASHBOARD_ENV_CONFIG.md`
- **Тестирование:** `docs/testing/DASHBOARD_TESTING_GUIDE.md`
- **API:** `docs/api/ANALYTICS_DASHBOARD_API.md`
