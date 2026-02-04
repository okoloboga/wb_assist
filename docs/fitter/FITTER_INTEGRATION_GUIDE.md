# Интеграция функционала примерки (Fitter) - инструкция по КОПИРОВАНИЮ кода

## КРИТИЧЕСКИ ВАЖНО - ПРОЧИТАЙ ПЕРЕД НАЧАЛОМ РАБОТЫ

**Это задача КОПИРОВАНИЯ готового рабочего кода, а НЕ разработка с нуля.**

В проекте уже есть склонированный репозиторий бота-донора по пути `fitting_bot/`.
Весь код примерки уже написан и протестирован. Твоя задача:

1. **ПРОЧИТАТЬ** исходные файлы из `fitting_bot/`
2. **СКОПИРОВАТЬ** их в целевую папку `gpt_integration/fitter/`
3. **ИСПРАВИТЬ ТОЛЬКО ИМПОРТЫ** в скопированных файлах
4. **ДОБАВИТЬ endpoint** в существующий `gpt_integration/service.py`

**НЕ ПИШИ код генерации, промптов, клиентов или валидации заново. Он уже существует.**

---

## Шаг 0: Прочитай исходные файлы

Перед любыми действиями ОБЯЗАТЕЛЬНО прочитай содержимое этих файлов из донора:

| # | Исходный файл (ДОНОР) | Что содержит |
|---|---|---|
| 1 | `fitting_bot/gpt_integration/photo_processing/prompts.py` | Промпты TRYON_SINGLE_ITEM, TRYON_FULL_OUTFIT, VALIDATION_PROMPT |
| 2 | `fitting_bot/gpt_integration/photo_processing/image_client.py` | Класс ImageGenerationClient с поддержкой Gemini + GPT Image моделей |
| 3 | `fitting_bot/gpt_integration/photo_processing/validator.py` | Функция validate_photo() - валидация фото через ChatGPT |
| 4 | `fitting_bot/gpt_integration/photo_processing/generator.py` | Функция generate_tryon() - основная логика генерации примерки |

Также прочитай файлы целевого проекта, чтобы понять существующую архитектуру:

| # | Целевой файл (ПРОЕКТ) | Зачем читать |
|---|---|---|
| 1 | `gpt_integration/service.py` | FastAPI app - сюда добавляется новый endpoint |
| 2 | `gpt_integration/gpt_client.py` | GPTClient целевого проекта - используется в validator.py |
| 3 | `gpt_integration/photo_processing/image_client.py` | Существующий ImageGenerationClient - будет заменён более полной версией из донора |

---

## Шаг 1: Создать папку `gpt_integration/fitter/`

```bash
mkdir -p gpt_integration/fitter
```

---

## Шаг 2: Скопировать 4 файла из донора

### 2.1 prompts.py - копировать БЕЗ ИЗМЕНЕНИЙ

**Откуда:** `fitting_bot/gpt_integration/photo_processing/prompts.py`
**Куда:** `gpt_integration/fitter/prompts.py`

Файл не имеет импортов - копируется as-is, никаких изменений не нужно.

### 2.2 image_client.py - копировать БЕЗ ИЗМЕНЕНИЙ

**Откуда:** `fitting_bot/gpt_integration/photo_processing/image_client.py`
**Куда:** `gpt_integration/fitter/image_client.py`

Файл использует только стандартные и pip-библиотеки (httpx, PIL, tenacity) - копируется as-is.

**ВНИМАНИЕ:** Этот файл НЕ тот же самый, что `gpt_integration/photo_processing/image_client.py`.
Версия из донора - расширенная: поддерживает GPT Image модели через multipart/form-data, загрузку локальных файлов, и метод `process_images()` (во множественном числе). Существующий файл в `photo_processing/` поддерживает только Gemini и имеет метод `process_image()` (в единственном числе). Это РАЗНЫЕ файлы, они НЕ конфликтуют - новый кладётся в `fitter/`, старый остаётся в `photo_processing/`.

### 2.3 generator.py - копировать, ИСПРАВИТЬ 2 ИМПОРТА

**Откуда:** `fitting_bot/gpt_integration/photo_processing/generator.py`
**Куда:** `gpt_integration/fitter/generator.py`

После копирования заменить ровно 2 строки импортов в начале файла:

```python
# БЫЛО (в доноре):
from gpt_integration.photo_processing.image_client import ImageGenerationClient
from gpt_integration.photo_processing.prompts import (
    TRYON_SINGLE_ITEM,
    TRYON_FULL_OUTFIT,
)

# ЗАМЕНИТЬ НА:
from .image_client import ImageGenerationClient
from .prompts import (
    TRYON_SINGLE_ITEM,
    TRYON_FULL_OUTFIT,
)
```

**Больше НИЧЕГО в файле не менять.** Вся логика generate_tryon() остаётся без изменений.

### 2.4 validator.py - копировать, ИСПРАВИТЬ 1 ИМПОРТ

**Откуда:** `fitting_bot/gpt_integration/photo_processing/validator.py`
**Куда:** `gpt_integration/fitter/validator.py`

После копирования заменить 1 строку импорта:

```python
# БЫЛО (в доноре):
from gpt_integration.gpt_client import GPTClient

# ЗАМЕНИТЬ НА:
from gpt_integration.gpt_client import GPTClient
```

**ВАЖНО о GPTClient:** В доноре и в целевом проекте классы GPTClient РАЗНЫЕ по реализации, но имеют ОДИНАКОВЫЙ интерфейс - метод `async complete_messages(messages) -> str`. Поэтому импорт остаётся тем же путём (`gpt_integration.gpt_client`), но будет использоваться GPTClient целевого проекта. Это корректно, т.к. API совпадает.

---

## Шаг 3: Создать `__init__.py` (единственный НОВЫЙ файл)

**Файл:** `gpt_integration/fitter/__init__.py`

```python
"""
Модуль виртуальной примерки одежды (Fitter).
Код перенесён из fitting_bot/gpt_integration/photo_processing/.
"""
from .generator import generate_tryon
from .validator import validate_photo
```

Это единственный файл, который нужно написать с нуля. Он содержит только 2 импорта.

---

## Шаг 4: Добавить endpoint в существующий service.py

**Файл:** `gpt_integration/service.py`

Добавить Pydantic-модель и endpoint в существующий файл. Не создавать отдельных роутеров.

### 4.1 Добавить модель запроса (рядом с другими моделями, после класса SemanticCoreRequest):

```python
class TryOnRequest(BaseModel):
    user_photo_url: str
    product_photo_urls: List[str]
    model: str = "gemini-2.5-flash-image"
    mode: str = "single_item"
    item_name: str = "одежда"
    category: str = "одежда"
```

### 4.2 Добавить endpoint (в секцию после Semantic Core Endpoints):

```python
# ============================================================================
# Fitter / Try-On Endpoints
# ============================================================================

@app.post("/v1/fitter/try-on")
async def fitter_try_on(
    req: TryOnRequest,
    x_api_key: Optional[str] = Header(None)
) -> Dict[str, Any]:
    """Виртуальная примерка одежды."""
    expected_key = os.getenv("API_SECRET_KEY", "")
    if not x_api_key or x_api_key != expected_key:
        raise HTTPException(status_code=403, detail="Invalid or missing API key")

    from gpt_integration.fitter import generate_tryon

    result = await generate_tryon(
        user_photo_source=req.user_photo_url,
        product_photo_sources=req.product_photo_urls,
        api_key=os.getenv("COMET_API_KEY"),
        base_url=os.getenv("IMAGE_GEN_BASE_URL", "https://api.cometapi.com"),
        model=req.model,
        tryon_mode=req.mode,
        item_name=req.item_name,
        category=req.category
    )

    return result
```

---

## Шаг 5: Проверить зависимости

Убедиться, что в `gpt_integration/requirements.txt` есть:

```
httpx
Pillow
tenacity
```

Эти пакеты скорее всего уже установлены (httpx и Pillow используются в существующем photo_processing). Проверь и добавь только недостающие.

---

## Итоговая структура после интеграции

```
gpt_integration/
├── fitter/                          # НОВАЯ ПАПКА
│   ├── __init__.py                  # Написать (3 строки)
│   ├── generator.py                 # Скопировать из донора, поправить 2 импорта
│   ├── image_client.py              # Скопировать из донора as-is
│   ├── prompts.py                   # Скопировать из донора as-is
│   └── validator.py                 # Скопировать из донора, проверить 1 импорт
├── photo_processing/                # НЕ ТРОГАТЬ - существующий модуль
│   ├── image_client.py              # Старый клиент (только Gemini) - оставить
│   ├── service.py                   # Существующий сервис - оставить
│   └── ...
├── gpt_client.py                    # НЕ ТРОГАТЬ - используется validator.py
├── comet_client.py                  # НЕ ТРОГАТЬ
└── service.py                       # ИЗМЕНИТЬ - добавить TryOnRequest + endpoint
```

---

## Чек-лист

- [ ] Прочитаны все 4 исходных файла из `fitting_bot/gpt_integration/photo_processing/`
- [ ] Создана папка `gpt_integration/fitter/`
- [ ] `prompts.py` скопирован без изменений
- [ ] `image_client.py` скопирован без изменений
- [ ] `generator.py` скопирован, исправлены 2 импорта на относительные
- [ ] `validator.py` скопирован, проверен импорт GPTClient
- [ ] Создан `__init__.py` с 2 импортами
- [ ] В `service.py` добавлена модель TryOnRequest
- [ ] В `service.py` добавлен endpoint `/v1/fitter/try-on`
- [ ] Проверены зависимости в requirements.txt

---

## Чего НЕ НУЖНО делать

- НЕ создавать отдельный FastAPI роутер (router.py) - endpoint добавляется прямо в service.py по аналогии с остальными
- НЕ создавать service.py внутри fitter/ - функция generate_tryon() из generator.py уже является точкой входа
- НЕ создавать exceptions.py - generator.py уже обрабатывает все ошибки и возвращает dict с success/error
- НЕ создавать models.py внутри fitter/ - одна Pydantic-модель TryOnRequest добавляется в основной service.py
- НЕ трогать существующий photo_processing/ - это другой модуль для другого функционала
- НЕ переписывать логику генерации, валидации или работы с API - она уже написана и работает
- НЕ менять GPTClient или CometClient - validator.py использует существующий GPTClient через стандартный интерфейс
