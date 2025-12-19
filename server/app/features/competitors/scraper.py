"""
Модуль скрапинга данных о конкурентах Wildberries
Адаптирован из scrapping/test.py для использования в сервере
"""

import os
import re
import time
import logging
from typing import List, Dict, Any, Optional
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from pyvirtualdisplay import Display

logger = logging.getLogger(__name__)


def get_driver(headless: bool = True):
    """
    Создает и настраивает WebDriver для Chrome с оптимизациями производительности.
    
    Args:
        headless: Запускать в headless режиме (по умолчанию True для сервера)
    """
    chrome_options = Options()
    
    if headless:
        chrome_options.add_argument('--headless=new')
    
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    chrome_options.add_argument('--disable-gpu')  # Добавлено для Docker
    chrome_options.add_argument('--window-size=1920,1080')  # Явно задаем размер окна
    
    # НЕ отключаем изображения - они могут быть нужны для загрузки контента
    prefs = {
        # "profile.managed_default_content_settings.images": 2,  # Закомментировано
        "profile.default_content_setting_values.notifications": 2
    }
    chrome_options.add_experimental_option("prefs", prefs)
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    # Используем системный Chrome, если доступен (в Docker)
    try:
        # Пробуем использовать системный Chrome
        import subprocess
        result = subprocess.run(['which', 'chromedriver'], capture_output=True, text=True)
        chromedriver_path = result.stdout.strip() if result.returncode == 0 else '/usr/bin/chromedriver'
        
        if os.path.exists(chromedriver_path):
            service = Service(chromedriver_path)
            driver = webdriver.Chrome(service=service, options=chrome_options)
            logger.info(f"Используется системный chromedriver: {chromedriver_path}")
        else:
            raise FileNotFoundError("Системный chromedriver не найден")
            
    except Exception as e:
        # Fallback на webdriver-manager
        logger.warning(f"Не удалось использовать системный chromedriver: {e}")
        try:
            from webdriver_manager.chrome import ChromeDriverManager
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=chrome_options)
            logger.info("Используется webdriver-manager")
        except Exception as e:
            logger.error(f"Не удалось инициализировать Chrome driver: {e}")
            raise
    
    # Устанавливаем таймаут загрузки страницы
    driver.set_page_load_timeout(60)  # Увеличено с 30 до 60
    driver.implicitly_wait(10)  # Добавлено неявное ожидание
    
    # Скрываем признаки автоматизации
    driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
        'source': '''
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            })
        '''
    })
    
    return driver


def get_product_urls(brand_url: str, driver: webdriver.Chrome, count: int = 30) -> List[str]:
    """
    Получает HTML страницы бренда/селлера и находит ссылки на указанное количество товаров.
    
    Args:
        brand_url: URL страницы бренда или селлера
        driver: Экземпляр WebDriver
        count: Максимальное количество товаров для сбора
        
    Returns:
        Список URL товаров
    """
    product_urls = []
    try:
        logger.info(f"Загрузка страницы бренда: {brand_url}")
        driver.get(brand_url)
        
        # Ждем появления первой ссылки на товар.
        # Структура ссылок на товары на WB могла измениться, поэтому больше
        # не полагаемся на наличие 'detail.aspx' в href, а ищем любые ссылки
        # с подстрокой '/catalog/'.
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.XPATH, "//a[contains(@href, '/catalog/')]"))
        )
        
        # Даем странице время на полную загрузку
        time.sleep(2)
        
        # Прокручиваем страницу, чтобы загрузить больше товаров
        last_height = driver.execute_script("return document.body.scrollHeight")
        scroll_attempts = 0
        max_scroll_attempts = 20
        
        while len(product_urls) < count and scroll_attempts < max_scroll_attempts:
            # Ищем ссылки на товары
            product_links_selenium = driver.find_elements(
                By.XPATH,
                "//a[contains(@href, '/catalog/')]"
            )
            
            for link_element in product_links_selenium:
                href = link_element.get_attribute('href')
                # Берём только ссылки, в которых явно присутствует числовой nm_id
                # в сегменте /catalog/<nm_id>
                if href and "/catalog/" in href:
                    if not re.search(r"/catalog/\d+", href):
                        continue
                    if href not in product_urls:
                        product_urls.append(href)
                        if len(product_urls) >= count:
                            break
            
            # Если нашли достаточно ссылок, выходим
            if len(product_urls) >= count:
                break
            
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)  # Даем время на подгрузку контента
            
            # Ждем, пока высота страницы не увеличится
            try:
                WebDriverWait(driver, 5).until(
                    lambda d: d.execute_script("return document.body.scrollHeight") > last_height
                )
            except TimeoutException:
                # Если высота не изменилась, значит, больше нет контента
                break
            
            new_height = driver.execute_script("return document.body.scrollHeight")
            last_height = new_height
            scroll_attempts += 1
        
        logger.info(f"Найдено {len(product_urls)} товаров на странице")
        return product_urls[:count]
        
    except Exception as e:
        logger.error(f"Ошибка при получении страницы бренда {brand_url}: {e}")
        return []


def scrape_product_data(product_url: str, driver: webdriver.Chrome) -> Optional[Dict[str, Any]]:
    """
    Получает данные для одного товара: название, цена, категория, рейтинг, описание.
    
    Args:
        product_url: URL товара
        driver: Экземпляр WebDriver
        
    Returns:
        Словарь с данными товара или None при ошибке
    """
    try:
        # Извлекаем nm_id из URL (WB мог изменить структуру ссылок,
        # поэтому ищем просто /catalog/<число> независимо от хвоста)
        nm_id_match = re.search(r'/catalog/(\d+)', product_url)
        nm_id = nm_id_match.group(1) if nm_id_match else None
        
        if not nm_id:
            logger.warning(f"Не удалось извлечь nm_id из URL: {product_url}")
            return None
        
        logger.info(f"Загрузка страницы товара: {product_url}")
        driver.get(product_url)
        
        # Ждем загрузки основного контента
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "//h1[contains(@class, 'product-page__title')] | //h3[contains(@class, 'productTitle')]"))
        )
        
        # КРИТИЧЕСКИ ВАЖНО: даем время на загрузку всего динамического контента
        time.sleep(3)
        
        # Прокручиваем страницу вниз и вверх для триггера ленивой загрузки
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(1)
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(1)
        
        name, current_price, original_price, brand, category, rating, description = None, None, None, None, None, None, None
        
        # Название
        try:
            name_elements = driver.find_elements(
                By.XPATH, 
                "//h1[contains(@class, 'product-page__title')] | //h3[contains(@class, 'productTitle')]"
            )
            if name_elements:
                name = name_elements[0].text.strip()
                logger.info(f"Название найдено: {name}")
            else:
                logger.warning(f"Элемент названия не найден для {product_url}")
        except Exception as e:
            logger.warning(f"Ошибка при поиске названия для {product_url}: {e}")
        
        # Текущая цена (со скидкой)
        try:
            price_elements = driver.find_elements(
                By.XPATH, 
                "//ins[contains(@class, 'priceBlockFinalPrice')] | //span[@class='price-block__final-price']"
            )
            if price_elements:
                price_text = price_elements[0].text
                current_price = float(''.join(filter(str.isdigit, price_text)))
                logger.info(f"Текущая цена найдена: {current_price}")
            else:
                logger.warning(f"Элемент текущей цены не найден для {product_url}")
        except (NoSuchElementException, ValueError, IndexError) as e:
            logger.warning(f"Ошибка при поиске текущей цены для {product_url}: {e}")
        
        # Оригинальная цена (без скидки)
        try:
            original_price_elements = driver.find_elements(
                By.CSS_SELECTOR, 
                "span.priceBlockOldPrice--qSWAf"
            )
            if original_price_elements:
                original_price_text = original_price_elements[0].text
                original_price = float(''.join(filter(str.isdigit, original_price_text)))
                logger.info(f"Оригинальная цена найдена: {original_price}")
        except (NoSuchElementException, ValueError, IndexError):
            # Это не критическая ошибка
            logger.debug(f"Оригинальная цена не найдена для {product_url} (это нормально)")
        
        # Бренд из хлебных крошек
        try:
            # Ждем загрузки хлебных крошек
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//div[contains(@class, 'breadcrumbs')]//span[@itemprop='name']"))
            )
            
            breadcrumb_elements = driver.find_elements(
                By.XPATH, 
                "//div[contains(@class, 'breadcrumbs')]//span[@itemprop='name']"
            )
            breadcrumb_texts = [elem.text.strip() for elem in breadcrumb_elements if elem.text.strip()]
            
            if breadcrumb_texts:
                brand = breadcrumb_texts[-1]
                logger.info(f"Бренд найден: {brand}")
            else:
                logger.warning(f"Хлебные крошки пусты для {product_url}")
                
        except TimeoutException:
            logger.warning(f"Timeout при ожидании хлебных крошек для {product_url}")
        except Exception as e:
            logger.warning(f"Ошибка при поиске бренда для {product_url}: {e}")
        
        # Категория
        try:
            # Ждем загрузки категории
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "span.categoryLinkCategory--VSJ8c"))
            )
            
            category_elements = driver.find_elements(
                By.CSS_SELECTOR, 
                "span.categoryLinkCategory--VSJ8c"
            )
            if category_elements:
                category = category_elements[0].text.strip()
                logger.info(f"Категория найдена: {category}")
            else:
                logger.warning(f"Элемент категории не найден для {product_url}")
                
        except TimeoutException:
            logger.warning(f"Timeout при ожидании категории для {product_url}")
        except Exception as e:
            logger.warning(f"Ошибка при поиске категории для {product_url}: {e}")
        
        # Рейтинг
        try:
            rating_elements = driver.find_elements(
                By.CSS_SELECTOR, 
                "b.user-opinion__rating-numb, span.product-review__rating"
            )
            if rating_elements:
                rating_text = rating_elements[0].text
                rating = float(rating_text.replace(',', '.'))
                logger.info(f"Рейтинг найден: {rating}")
            else:
                logger.warning(f"Элемент рейтинга не найден для {product_url}")
        except (NoSuchElementException, ValueError, IndexError) as e:
            logger.warning(f"Ошибка при поиске рейтинга для {product_url}: {e}")
        
        # Описание
        try:
            # Ждем появления кнопки "Подробнее"
            button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button.btnDetail--im7UR"))
            )
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
            time.sleep(1)  # Даем время на прокрутку
            
            # Кликаем через JavaScript для надежности
            driver.execute_script("arguments[0].click();", button)
            
            # Ждем появления описания
            description_element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//h3[text()='Описание']/following-sibling::p[contains(@class, 'descriptionText--Jq9n2')]")
                )
            )
            description = description_element.text.strip()
            logger.info(f"Описание найдено (длина: {len(description)} символов)")
            
        except TimeoutException:
            logger.warning(f"Timeout при ожидании описания для {product_url}")
        except Exception as e:
            logger.warning(f"Ошибка при сборе описания для {product_url}: {e}")
        
        result = {
            "product_url": product_url,
            "nm_id": nm_id,
            "name": name,
            "current_price": current_price,
            "original_price": original_price,
            "brand": brand,
            "category": category,
            "rating": rating,
            "description": description,
        }
        
        # Логируем что удалось собрать
        filled_fields = sum(1 for v in result.values() if v is not None)
        logger.info(f"Собрано {filled_fields}/{len(result)} полей для товара {nm_id}")
        
        return result
        
    except Exception as e:
        logger.error(f"Критическая ошибка при сборе данных для товара {product_url}: {e}", exc_info=True)
        return None


def scrape_competitor(competitor_url: str, max_products: int = 30) -> Dict[str, Any]:
    """
    Основная функция скрапинга конкурента.
    Собирает данные о товарах конкурента и возвращает структурированные данные.
    
    Args:
        competitor_url: URL страницы бренда или селлера
        max_products: Максимальное количество товаров для сбора
        
    Returns:
        Словарь с данными:
        {
            "competitor_name": str,  # Название бренда/магазина
            "products": List[Dict],  # Список товаров
            "success_count": int,    # Количество успешно собранных товаров
            "error_count": int       # Количество ошибок
        }
    """
    driver = None
    display = None
    result = {
        "competitor_name": None,
        "products": [],
        "success_count": 0,
        "error_count": 0
    }
    
    try:
        logger.info(f"Начало скрапинга конкурента: {competitor_url}")
        
        # Запускаем виртуальный дисплей для headless режима
        display = Display(visible=0, size=(1920, 1080))
        display.start()
        logger.info("Виртуальный дисплей запущен")
        
        # Запускаем драйвер в headless режиме
        driver = get_driver(headless=True)
        logger.info("WebDriver инициализирован")
        
        # Получаем список URL товаров
        product_urls = get_product_urls(competitor_url, driver, count=max_products)
        
        if not product_urls:
            logger.error(f"Не удалось найти товары на странице: {competitor_url}")
            return result
        
        logger.info(f"Начинаю сбор данных для {len(product_urls)} товаров...")
        
        # Собираем данные по каждому товару
        competitor_name = None
        for i, product_url in enumerate(product_urls):
            logger.info(f"Обработка товара {i+1}/{len(product_urls)}")
            product_data = scrape_product_data(product_url, driver)
            
            if product_data:
                # Проверяем что хотя бы основные поля заполнены
                has_essential_data = all([
                    product_data.get('nm_id'),
                    product_data.get('name'),
                    product_data.get('current_price')
                ])
                
                if has_essential_data:
                    # Извлекаем название конкурента из первого товара
                    if not competitor_name and product_data.get('brand'):
                        competitor_name = product_data.get('brand')
                        logger.info(f"Название конкурента определено: {competitor_name}")
                    
                    result["products"].append(product_data)
                    result["success_count"] += 1
                    logger.info(f"✓ Товар {product_data.get('nm_id')} успешно добавлен")
                else:
                    logger.warning(f"✗ Товар пропущен: недостаточно данных")
                    result["error_count"] += 1
            else:
                result["error_count"] += 1
                logger.warning(f"✗ Не удалось собрать данные для товара")
        
        result["competitor_name"] = competitor_name
        logger.info(f"Скрапинг завершен: успешно {result['success_count']}, ошибок {result['error_count']}")
        
        return result
        
    except Exception as e:
        logger.error(f"Критическая ошибка при скрапинге конкурента {competitor_url}: {e}", exc_info=True)
        return result
        
    finally:
        if driver:
            try:
                driver.quit()
                logger.info("Браузер закрыт")
            except Exception as e:
                logger.error(f"Ошибка при закрытии браузера: {e}")
        
        if display:
            try:
                display.stop()
                logger.info("Виртуальный дисплей остановлен")
            except Exception as e:
                logger.error(f"Ошибка при остановке дисплея: {e}")