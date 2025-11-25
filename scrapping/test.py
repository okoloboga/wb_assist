from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import time
import json
import re


def get_driver():
    """
    Создает и настраивает WebDriver для Chrome с оптимизациями производительности.
    """
    chrome_options = Options()
    # chrome_options.add_argument('--headless=new')
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    chrome_options.add_argument('--disable-blink-features=AutomationControlled')
    prefs = {
        "profile.managed_default_content_settings.images": 2,
        "profile.default_content_setting_values.notifications": 2
    }
    chrome_options.add_experimental_option("prefs", prefs)
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    # Устанавливаем таймаут загрузки страницы
    driver.set_page_load_timeout(30)
    
    driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
        'source': '''
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            })
        '''
    })
    return driver


def get_product_urls(brand_url, driver, count=1):
    """
    Получает HTML страницы бренда и находит ссылки на указанное количество товаров.
    """
    product_urls = []
    try:
        driver.get(brand_url)
        # Ждем появления первой ссылки на товар
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.XPATH, "//a[contains(@href, '/catalog/') and contains(@href, 'detail.aspx')]"))
        )
        
        # Прокручиваем страницу, чтобы загрузить больше товаров
        last_height = driver.execute_script("return document.body.scrollHeight")
        scroll_attempts = 0
        max_scroll_attempts = 20  # Достаточный лимит попыток
        
        while len(product_urls) < count and scroll_attempts < max_scroll_attempts:
            # Ищем ссылки на товары
            product_links_selenium = driver.find_elements(By.XPATH, "//a[contains(@href, '/catalog/') and contains(@href, 'detail.aspx')]")
            for link_element in product_links_selenium:
                href = link_element.get_attribute('href')
                if href and href not in product_urls:
                    product_urls.append(href)
                    if len(product_urls) >= count:
                        break
            
            # Если нашли достаточно ссылок, выходим
            if len(product_urls) >= count:
                break

            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
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
        
        return product_urls[:count]
    except Exception as e:
        print(f"Ошибка при получении страницы бренда: {e}")
        return []


def scrape_product_data(product_url, driver):
    """
    Получает данные для одного товара: название, цена, категория, рейтинг, описание.
    Оптимизированная версия с сокращенными таймаутами и убранными задержками.
    """
    try:
        # Extract nm_id
        nm_id_match = re.search(r'/catalog/(\d+)/detail.aspx', product_url)
        nm_id = nm_id_match.group(1) if nm_id_match else None
        
        driver.get(product_url)
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "//h1[contains(@class, 'product-page__title')] | //h3[contains(@class, 'productTitle')]"))
        )
        # time.sleep(2) # Removed redundant sleep

        name, current_price, original_price, brand, category, rating, description = None, None, None, None, None, None, None

        # Оптимизируем поиск элементов - используем find_elements для избежания исключений
        try:
            name_elements = driver.find_elements(By.XPATH, "//h1[contains(@class, 'product-page__title')] | //h3[contains(@class, 'productTitle')]")
            if name_elements:
                name = name_elements[0].text
        except Exception:
            print(f"Warning: Название не найдено для {product_url}")

        try:
            # Текущая цена (со скидкой)
            price_elements = driver.find_elements(By.XPATH, "//ins[contains(@class, 'priceBlockFinalPrice')] | //span[@class='price-block__final-price']")
            if price_elements:
                price_text = price_elements[0].text
                current_price = float(''.join(filter(str.isdigit, price_text)))
        except (NoSuchElementException, ValueError, IndexError):
            print(f"Warning: Текущая цена не найдена для {product_url}")

        try:
            # Оригинальная цена (без скидки)
            original_price_elements = driver.find_elements(By.CSS_SELECTOR, "span.priceBlockOldPrice--qSWAf")
            if original_price_elements:
                original_price_text = original_price_elements[0].text
                original_price = float(''.join(filter(str.isdigit, original_price_text)))
        except (NoSuchElementException, ValueError, IndexError):
            # Это не критическая ошибка, так как старой цены может и не быть
            pass

        try:
            # Получаем бренд из хлебных крошек (последний элемент)
            breadcrumb_elements = driver.find_elements(By.XPATH, "//div[contains(@class, 'breadcrumbs')]//span[@itemprop='name']")
            breadcrumb_texts = [elem.text for elem in breadcrumb_elements if elem.text.strip()]
            if breadcrumb_texts:
                brand = breadcrumb_texts[-1]
        except Exception:
            print(f"Warning: Бренд не найден для {product_url}")

        try:
            # Получаем категорию из специального элемента
            category_elements = driver.find_elements(By.CSS_SELECTOR, "span.categoryLinkCategory--VSJ8c")
            if category_elements:
                category = category_elements[0].text
        except Exception:
            print(f"Warning: Категория не найдена для {product_url}")

        try:
            rating_elements = driver.find_elements(By.CSS_SELECTOR, "b.user-opinion__rating-numb, span.product-review__rating")
            if rating_elements:
                rating_text = rating_elements[0].text
                rating = float(rating_text.replace(',', '.'))
        except (NoSuchElementException, ValueError, IndexError):
            print(f"Warning: Рейтинг не найден для {product_url}")

        # Описание
        try:
            button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button.btnDetail--im7UR"))
            )
            driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
            # time.sleep(1) # Removed redundant sleep
            button.click()
            
            description_element = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//h3[text()='Описание']/following-sibling::p[contains(@class, 'descriptionText--Jq9n2')]"))
            )
            description = description_element.text
        except TimeoutException:
             print(f"Warning: Описание не найдено для {product_url}")
        except Exception as e:
             print(f"Произошла ошибка при сборе описания: {e}")

        return {
            "product_url": product_url, "nm_id": nm_id, "name": name,
            "current_price": current_price, "original_price": original_price,
            "brand": brand, "category": category, "rating": rating, "description": description,
        }
    except Exception as e:
        print(f"Критическая ошибка при сборе данных для товара {product_url}: {e}")
        return None


def main():
    """
    Основная функция: организует запуск скрейпинга и сохранение результата.
    """
    brand_url = "https://www.wildberries.ru/brands/310770244-meromi"
    output_filename = 'data.json'
    num_products_to_scrape = 20
    
    # 1. Загружаем существующие данные
    try:
        with open(output_filename, 'r', encoding='utf-8') as f:
            data_tree = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        data_tree = {}

    print("Инициализация браузера...")
    driver = None
    start_time = time.time() # Start time measurement
    try:
        driver = get_driver()
        print("Браузер инициализирован.")

        print(f"Получаю {num_products_to_scrape} URL-ов товаров...")
        product_urls = get_product_urls(brand_url, driver, count=num_products_to_scrape)

        if not product_urls:
            print("Ошибка: не удалось найти товары на странице бренда.")
            return

        print(f"Начинаю сбор данных для {len(product_urls)} товаров...")
        save_batch_size = 5  # Сохраняем каждые 5 товаров вместо после каждого
        successful_count = 0
        
        for i, product_url in enumerate(product_urls):
            print(f"Сбор данных для товара {i+1}/{len(product_urls)}: {product_url}")
            product_data = scrape_product_data(product_url, driver)

            if product_data and product_data.get('brand') and product_data.get('category') and product_data.get('nm_id'):
                # 2. Обновляем структуру данных
                brand_name = product_data.pop('brand')
                category_name = product_data.pop('category')
                product_id = product_data.pop('nm_id')
                product_name_for_log = product_data.get('name') # Для лога
                
                # Строим вложенную структуру: Бренд -> Категория -> Товар
                data_tree.setdefault(brand_name, {}).setdefault(category_name, {})[product_id] = product_data
                successful_count += 1
                
                # Сохраняем пакетами вместо после каждого товара
                should_save = (successful_count % save_batch_size == 0) or (i == len(product_urls) - 1)
                if should_save:
                    try:
                        with open(output_filename, 'w', encoding='utf-8') as f:
                            json.dump(data_tree, f, ensure_ascii=False, indent=4)
                        print(f"Данные сохранены в {output_filename} (обработано {successful_count} товаров)")
                    except Exception as e:
                        print(f"Ошибка при сохранении данных: {e}")
                else:
                    print(f"Данные для товара '{product_name_for_log}' добавлены в память")
            elif product_data:
                print(f"Не удалось получить достаточно данных для структурирования товара {product_url} (бренд, категория или nm_id).")
            else:
                print(f"Не удалось собрать данные для товара {product_url}.")

    finally:
        # Финальное сохранение данных на случай, если что-то не сохранилось
        try:
            if 'data_tree' in locals() and data_tree:
                with open(output_filename, 'w', encoding='utf-8') as f:
                    json.dump(data_tree, f, ensure_ascii=False, indent=4)
                print(f"Финальное сохранение данных в {output_filename}")
        except (NameError, Exception) as e:
            # Игнорируем если data_tree не определена или другая ошибка
            pass
        
        if driver:
            driver.quit()
            print("Браузер закрыт.")
        end_time = time.time() # End time measurement
        total_time = end_time - start_time
        print(f"Общее время выполнения скрипта: {total_time:.2f} секунд.")


if __name__ == "__main__":
    main()