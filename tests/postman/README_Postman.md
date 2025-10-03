# 🚀 Тестирование WB API в Postman

## 📋 Быстрый старт

### 1. Импорт коллекции
1. Откройте Postman
2. Нажмите **Import** → **Upload Files**
3. Выберите файл `WB_API_Collection.postman_collection.json`
4. Импортируйте файл окружения `WB_Environment.postman_environment.json`

### 2. Настройка API ключа
1. Выберите окружение **WB API Environment**
2. Нажмите на иконку глаза 👁️ рядом с названием окружения
3. Найдите переменную `WB_API_KEY`
4. Нажмите **Edit** и вставьте ваш реальный API ключ
5. Сохраните изменения

## 🔧 Настройка авторизации

### Метод 1: Через коллекцию (рекомендуется)
Коллекция уже настроена с Bearer Token авторизацией:
```
Authorization: Bearer {{WB_API_KEY}}
```

### Метод 2: Ручная настройка
Для каждого запроса:
1. Перейдите на вкладку **Authorization**
2. Выберите тип **Bearer Token**
3. В поле Token введите: `{{WB_API_KEY}}`

## 📊 Доступные запросы

### 📈 Statistics API
- **Get Orders** - получение заказов
- **Get Sales** - получение продаж  
- **Get Stocks** - получение остатков

### 💰 Prices API
- **Get Prices** - получение цен на товары

### 🔧 Health Checks
- **Test API Key** - проверка валидности API ключа

## 🧪 Автоматические тесты

Каждый запрос содержит встроенные тесты:

### Пример тестов для Orders:
```javascript
// Проверяем статус ответа
pm.test("Status code is 200", function () {
    pm.response.to.have.status(200);
});

// Проверяем что ответ - массив
pm.test("Response is an array", function () {
    const jsonData = pm.response.json();
    pm.expect(jsonData).to.be.an('array');
});

// Проверяем структуру заказа
pm.test("Order structure is valid", function () {
    const jsonData = pm.response.json();
    if (jsonData.length > 0) {
        const order = jsonData[0];
        pm.expect(order).to.have.property('date');
        pm.expect(order).to.have.property('lastChangeDate');
    }
});
```

## 🎯 Пошаговое тестирование

### Шаг 1: Проверка API ключа
1. Запустите **Test API Key** из папки Health Checks
2. Проверьте результат в **Test Results**:
   - ✅ Если тест прошел - API ключ работает
   - ❌ Если 401 ошибка - проверьте API ключ

### Шаг 2: Тестирование основных endpoints
1. **Get Stocks** - самый простой запрос для начала
2. **Get Orders** - получение заказов за период
3. **Get Sales** - получение продаж
4. **Get Prices** - получение цен (может требовать особые права)

### Шаг 3: Анализ ответов
Проверьте в **Response**:
- **Status**: должен быть 200
- **Time**: время ответа
- **Size**: размер ответа
- **Test Results**: результаты автотестов

## 🔍 Отладка проблем

### 401 Unauthorized
```json
{
    "error": "Unauthorized"
}
```
**Решение**: Проверьте API ключ в переменных окружения

### 403 Forbidden
```json
{
    "error": "Access denied"
}
```
**Решение**: API ключ не имеет прав на этот endpoint

### 429 Too Many Requests
```json
{
    "error": "Rate limit exceeded"
}
```
**Решение**: Подождите и повторите запрос

### Пустой ответ []
```json
[]
```
**Это нормально**: Нет данных за указанный период

## 📝 Параметры запросов

### Общие параметры:
- `dateFrom` - дата начала периода (YYYY-MM-DD)
- `dateTo` - дата окончания периода (YYYY-MM-DD)
- `flag` - флаг для получения данных (обычно 1)

### Примеры дат:
- Сегодня: `{{$randomDateRecent}}`
- Вчера: `2024-01-01`
- Неделя назад: `2024-01-25`

## 🚀 Продвинутые возможности

### 1. Запуск коллекции целиком
1. Нажмите на коллекцию **Wildberries API Collection**
2. Нажмите **Run collection**
3. Выберите запросы для выполнения
4. Нажмите **Run Wildberries API Collection**

### 2. Мониторинг API
1. Настройте **Monitor** для автоматической проверки API
2. Установите расписание проверок
3. Получайте уведомления о проблемах

### 3. Экспорт результатов
1. После выполнения тестов нажмите **Export Results**
2. Выберите формат (JSON, HTML)
3. Сохраните отчет

## 💡 Полезные советы

1. **Используйте переменные** для API ключей и URL
2. **Сохраняйте ответы** как примеры для документации
3. **Группируйте запросы** по функциональности
4. **Добавляйте описания** к запросам
5. **Используйте Pre-request Scripts** для динамических данных

## 🔗 Полезные ссылки

- [Документация Postman](https://learning.postman.com/)
- [Wildberries API Docs](https://openapi.wildberries.ru/)
- [Postman Tests Examples](https://learning.postman.com/docs/writing-scripts/test-scripts/)